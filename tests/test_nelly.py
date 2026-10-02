import glob
import io
import logging
import os
import random
import subprocess
import sys

import pytest

import nelly
import nelly.main

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, 'examples')
GRAMMARS = os.path.join(nelly.root, 'grammars')


@pytest.fixture(autouse=True)
def reset_encode():
    # main() sets this module-level global from --encode
    nelly.encode = None
    yield
    nelly.encode = None


@pytest.fixture
def run(tmp_path, capsys):
    def run(grammar, *argv):
        path = tmp_path / 'grammar.bnf'
        path.write_text(grammar)
        rc = nelly.main.main([str(path)] + list(argv))
        return rc, capsys.readouterr().out
    return run


POST = '''
<%post
    print($$)
%>
'''


class TestControlFlow:
    def test_bail_in_action_stops_run(self, run):
        rc, out = run("X(start): 'a' <% if $count == 2: bail() %>;" + POST, '-c', '5')
        assert rc == 0
        assert out == 'a\na\n'

    def test_nelly_bail_in_action_stops_run(self, run):
        rc, out = run("X(start): 'a' <% if $count == 2: nelly.bail() %>;" + POST, '-c', '5')
        assert out == 'a\na\n'

    def test_fail_in_action_retries(self, run):
        # every 'b' is discarded, and -c still produces three results
        grammar = "X(start): ('a' | 'b') <% if $$ == 'b': fail() %>;" + POST
        random.seed(0)
        rc, out = run(grammar, '-c', '3')
        assert rc == 0
        assert out == 'a\na\na\n'

    def test_fail_keeps_count(self, run):
        grammar = """
            <%pre
                import random
            %>
            X(start): 'n' <% if random.random() < 0.5: fail() %>;
            <%post
                print($count)
            %>
            """
        random.seed(0)
        rc, out = run(grammar, '-c', '4')
        assert out == '0\n1\n2\n3\n'

    def test_fail_every_time_stops(self, run, caplog):
        rc, out = run("X(start): 'a' <% fail() %>;" + POST, '-c', '1')
        assert out == ''
        assert 'fail() called 1000 times in a row' in caplog.text

    def test_bail_in_nested_action(self, run):
        grammar = "X(start): 'a' Y;\nY: 'b' <% if $count == 1: bail() %>;" + POST
        rc, out = run(grammar, '-c', '5')
        assert out == 'ab\n'

    def test_bail_in_post(self, run):
        grammar = '''
            X(start): 'a';
            <%post
                if $count == 1:
                    bail()
                print($$)
            %>
            '''
        rc, out = run(grammar, '-c', '5')
        assert out == 'a\n'

    def test_bail_in_pre(self, run):
        grammar = '''
            <%pre
                bail()
            %>
            X(start): 'a';
            ''' + POST
        rc, out = run(grammar, '-c', '5')
        assert rc == 0
        assert out == ''

    def test_exception_in_action_ends_run(self, run):
        rc, out = run("X(start): 'a' <% 1/0 %>;" + POST, '-c', '3')
        assert out == ''


class TestErrors:
    @pytest.mark.parametrize('grammar, message', [
        ("X(start): 'a'", 'Missing ";" for the expression starting at line 1, column 11'),
        ("X(start): ('a' | 'b';", 'Missing ")" before ";" at line 1, column 21'),
        ("X(start): 'a' \\d300;", 'larger than a byte'),
        ("X(start) 'a';", 'missing colon'),
        ])
    def test_parse_error_is_logged(self, run, caplog, grammar, message):
        rc, out = run(grammar)
        assert rc == 1
        assert message in caplog.text

    def test_unknown_varterminal(self, run, caplog):
        rc, out = run("X(start): $Y;")
        assert 'Unknown varterminal: "$Y"' in caplog.text

    def test_missing_include(self, run, caplog):
        rc, out = run("include 'nope.bnf'\nX(start): 'a';")
        assert rc == 1
        assert "Could not find include file 'nope.bnf'" in caplog.text

    def test_unreadable_include(self, run, caplog, tmp_path):
        include = tmp_path / 'secret.bnf'
        include.write_text("Y: 'y';")
        include.chmod(0)
        try:
            if os.access(include, os.R_OK):
                pytest.skip('running with permission to read any file')
            rc, out = run("include 'secret.bnf'\nX(start): 'a';")
        finally:
            include.chmod(0o644)
        assert rc == 1
        assert 'Could not read include file' in caplog.text
        assert 'Permission denied' in caplog.text

    def test_missing_grammar(self, caplog):
        assert nelly.main.main(['/nonexistent/grammar.bnf']) == 1
        assert 'Could not open grammar' in caplog.text

    def test_var_without_value(self, run, capsys):
        with pytest.raises(SystemExit):
            run("X(start): 'a';", '-v', 'foo')
        assert "expected KEY=VALUE, got 'foo'" in capsys.readouterr().err

    def test_runtime_error_fails_run(self, run, caplog):
        caplog.set_level(logging.INFO)
        rc, out = run("X(start): 'a' 5;")
        assert rc == 1
        assert 'Cannot join str and int' in caplog.text
        assert 'Ran 0 iterations' in caplog.text


class TestCommandLine:
    def test_python_m(self, tmp_path):
        path = tmp_path / 'grammar.bnf'
        path.write_text("X(start): 'hi';")
        proc = subprocess.run([sys.executable, '-m', 'nelly', str(path), '-o', '-'],
            cwd=ROOT, capture_output=True)
        assert proc.returncode == 0
        assert proc.stdout == b'hi'

    def test_stdin(self, tmp_path):
        proc = subprocess.run([sys.executable, '-m', 'nelly', '-o', '-'],
            cwd=ROOT, input=b"X(start): 'in';", capture_output=True)
        assert proc.stdout == b'in'

    def test_error_exit_status(self, tmp_path):
        proc = subprocess.run([sys.executable, os.path.join(ROOT, 'nelly.py'), '/nonexistent.bnf'],
            capture_output=True)
        assert proc.returncode == 1

    def test_generate(self):
        program = nelly.Parser().Parse(named_io("X(start): 'a' <% if $count == 2: bail() %>;"))
        assert list(nelly.main.generate(program, {}, 5)) == [(0, 'a'), (1, 'a')]


def named_io(text):
    fp = io.StringIO(text)
    fp.name = '<test>'
    return fp


class TestComments:
    def test_comments_inside_definition(self, run):
        grammar = """
            /* before */ X(start) /* options */ : 'a' /* b /* nested */ */ 'b'
                | /* alternative */ 'a' 'b' // line
                ; /* after */
            """ + POST
        rc, out = run(grammar)
        assert out == 'ab\n'


class TestBytes:
    def result(self, grammar):
        with io.StringIO(grammar) as fp:
            fp.name = '<test>'
            program = nelly.Parser().Parse(fp)
        return nelly.Sandbox().Execute(program)

    def test_text_stays_str(self):
        assert self.result("X(start): 'a' ('b' 'c'){2};") == 'abcbc'

    def test_mixing_promotes_to_bytes(self):
        assert self.result("X(start): 'GET ' b'\\x00' 'é';") == b'GET \x00\xc3\xa9'

    def test_bytes_then_text(self):
        assert self.result("X(start): b'\\x01' Y; Y: 'a' 'b';") == b'\x01ab'

    def test_repetition_promotes(self):
        assert self.result("X(start): ('a' b'b'){2};") == b'abab'

    def test_empty_repetition(self):
        assert self.result("X(start): b'\\x01' 'a'{0} b'\\x02';") == b'\x01\x02'

    def test_action_sees_str_for_text(self):
        grammar = "X(start): $Y; $Y: 'a' 'b' <% $* = type($$).__name__ %>;"
        assert self.result(grammar) == 'str'

    def test_char_constants_are_bytes(self):
        assert self.result(r"X(start): \xff \d65;") == b'\xffA'

    def test_char_constant_too_large(self):
        with pytest.raises(nelly.error, match='larger than a byte'):
            self.result(r"X(start): \d256;")

    def test_join_error(self):
        with pytest.raises(nelly.error, match='Cannot join str and int in X at line 1, column 11'):
            self.result("X(start): 'a' 5;")

    def test_join_error_in_group_names_enclosing_nonterminal(self):
        with pytest.raises(nelly.error, match='Cannot join str and int in Y at line 1, column 18'):
            self.result("X(start): Y; Y: ('a' 5);")

    def test_encode_forces_bytes(self):
        nelly.encode = 'latin-1'
        assert self.result("X(start): 'é';") == b'\xe9'


class TestOutput:
    GRAMMAR = "X(start): 'n=' $N b'\\x00'; $N: <% $* = str($count) %>;"

    def test_stdout(self, tmp_path, capsysbinary):
        path = tmp_path / 'grammar.bnf'
        path.write_text(self.GRAMMAR)
        nelly.main.main([str(path), '-c', '2', '-o', '-'])
        assert capsysbinary.readouterr().out == b'n=0\x00n=1\x00'

    def test_text_result_is_encoded(self, tmp_path, capsysbinary):
        path = tmp_path / 'grammar.bnf'
        path.write_text("X(start): 'é';")
        nelly.main.main([str(path), '-o', '-'])
        assert capsysbinary.readouterr().out == b'\xc3\xa9'

    def test_file_per_result(self, tmp_path):
        path = tmp_path / 'grammar.bnf'
        path.write_text(self.GRAMMAR)
        nelly.main.main([str(path), '-c', '3', '-o', str(tmp_path / 'out' / 'r-%02d.bin')])
        files = sorted(os.listdir(tmp_path / 'out'))
        assert files == ['r-00.bin', 'r-01.bin', 'r-02.bin']
        assert (tmp_path / 'out' / 'r-02.bin').read_bytes() == b'n=2\x00'

    def test_single_file(self, tmp_path):
        path = tmp_path / 'grammar.bnf'
        path.write_text(self.GRAMMAR)
        nelly.main.main([str(path), '-c', '2', '-o', str(tmp_path / 'all.bin')])
        assert (tmp_path / 'all.bin').read_bytes() == b'n=0\x00n=1\x00'

    def test_failed_results_are_not_written(self, tmp_path, capsysbinary):
        path = tmp_path / 'grammar.bnf'
        path.write_text("X(start): ('r' | 'x') <% if $$ == 'x': fail() %>;")
        random.seed(0)
        nelly.main.main([str(path), '-c', '3', '-o', '-'])
        assert capsysbinary.readouterr().out == b'rrr'

    def test_post_can_replace_result(self, tmp_path, capsysbinary):
        path = tmp_path / 'grammar.bnf'
        path.write_text("X(start): 'abc';\n<%post\n    $$ = $$.upper()\n%>\n")
        nelly.main.main([str(path), '-o', '-'])
        assert capsysbinary.readouterr().out == b'ABC'

    def test_hexdump(self, run):
        rc, out = run("X(start): b'AB\\x00';", '-x')
        assert out.startswith('0: 41 42 00 ')
        assert out.endswith(' AB.\n\n')


class TestDictionary:
    def walk(self, tmp_path, grammar):
        path = tmp_path / 'grammar.bnf'
        path.write_text(grammar)
        output = tmp_path / 'out.dict'
        assert nelly.main.main([str(path), '-d', str(output)]) == 0
        return output.read_text().splitlines()

    def test_collects_nested_terminals(self, tmp_path):
        grammar = r'''
            X(start): 'top' ('grp' | ('nested' 'top')) %str.upper('fn');
            '''
        assert self.walk(tmp_path, grammar) == [
            'out_dict_1="fn"',
            'out_dict_2="grp"',
            'out_dict_3="nested"',
            'out_dict_4="top"',
            ]

    def test_mixed_terminal_types(self, tmp_path):
        grammar = r'''
            X(start): 'a' \x42 %chr(65) '';
            Y: b'\x00\xff' | 'a';
            '''
        assert self.walk(tmp_path, grammar) == [
            r'out_dict_1="\x00\xFF"',
            'out_dict_2="B"',
            'out_dict_3="a"',
            ]

    def test_escaping(self, tmp_path):
        grammar = r'''
            X(start): 'q"b\\' | '\t' | 'é';
            '''
        assert self.walk(tmp_path, grammar) == [
            r'out_dict_1="\x09"',
            r'out_dict_2="q\"b\\"',
            r'out_dict_3="\xC3\xA9"',
            ]

    def test_encode_option(self, tmp_path):
        path = tmp_path / 'grammar.bnf'
        path.write_text("X(start): 'é';")
        output = tmp_path / 'out.dict'
        nelly.main.main([str(path), '-e', 'latin-1', '-d', str(output)])
        assert output.read_text() == 'out_dict_1="\\xE9"\n'


def all_grammars():
    paths  = glob.glob(os.path.join(EXAMPLES, '*.bnf'))
    paths += glob.glob(os.path.join(GRAMMARS, '**', '*.bnf'), recursive=True)
    return sorted(paths)


@pytest.mark.parametrize('path', all_grammars(), ids=lambda p: os.path.relpath(p, ROOT))
def test_grammar_parses(path):
    with open(path) as fp:
        nelly.Parser([os.path.dirname(path)]).Parse(fp)


# examples that run without variables, network access or writing files
RUNNABLE = ['ab', 'base64', 'class', 'dhcp', 'madlib', 'slice', 'strings', 'weights']


@pytest.mark.parametrize('name', RUNNABLE)
def test_example_runs(name, capsys):
    random.seed(0)
    with open(os.path.join(EXAMPLES, name + '.bnf')) as fp:
        program = nelly.Parser([EXAMPLES]).Parse(fp)
    results = []
    for count in range(20):
        try:
            results.append(nelly.Sandbox({'$count': count}).Execute(program))
        except SystemError:
            pass    # fail() skips a result, as in main()
    assert any(results)


class TestDHCP:
    CLIENT = {1: 'DISCOVER', 3: 'REQUEST', 4: 'DECLINE', 7: 'RELEASE', 8: 'INFORM'}
    SERVER = {2: 'OFFER', 5: 'ACK', 6: 'NAK'}

    def generate(self, start, count=300):
        random.seed(0)
        with open(os.path.join(GRAMMARS, 'protocols', 'dhcp.bnf')) as fp:
            program = nelly.Parser().Parse(fp)
        program.start = [start]
        for _ in range(count):
            yield nelly.Sandbox().Execute(program)

    def decode(self, packet):
        assert isinstance(packet, bytes)
        assert len(packet) > 240
        assert packet[1:3] == b'\x01\x06'        # ethernet, 6 byte MAC
        assert packet[34:44] == bytes(10)        # chaddr padding
        assert packet[236:240] == b'\x63\x82\x53\x63'

        options = {}
        idx = 240
        while packet[idx] != 0xff:
            code, length = packet[idx], packet[idx+1]
            options[code] = packet[idx+2:idx+2+length]
            assert len(options[code]) == length
            idx += 2 + length
        assert idx == len(packet) - 1, 'data after end option'
        return options

    def test_client_messages(self):
        seen = set()
        for packet in self.generate('DHCP_CLIENT'):
            options = self.decode(packet)
            assert packet[0] == 1                # BOOTREQUEST
            seen.add(self.CLIENT[options[53][0]])
            assert options[61] == b'\x01' + packet[28:34]
        assert seen == set(self.CLIENT.values())

    def test_server_messages(self):
        seen = set()
        for packet in self.generate('DHCP_SERVER'):
            options = self.decode(packet)
            assert packet[0] == 2                # BOOTREPLY
            seen.add(self.SERVER[options[53][0]])
            assert len(options[54]) == 4
        assert seen == set(self.SERVER.values())
