import glob
import os
import random

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

    def test_fail_in_action_skips_iteration(self, run):
        grammar = "X(start): 'a' <% if $count == 1: fail() %>;" + POST
        rc, out = run(grammar, '-c', '3')
        assert rc == 0
        assert out == 'a\na\n'

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
RUNNABLE = ['ab', 'base64', 'class', 'dhcp', 'madlib', 'slice', 'strings']


@pytest.mark.parametrize('name', RUNNABLE)
def test_example_runs(name, capsys):
    random.seed(0)
    with open(os.path.join(EXAMPLES, name + '.bnf')) as fp:
        program = nelly.Parser([EXAMPLES]).Parse(fp)
    for _ in range(20):
        nelly.Sandbox({'$count': 0}).Execute(program)
    assert capsys.readouterr().out


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
