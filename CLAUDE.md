# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Nelly is a grammar-based test case / fuzz input generator. It reads a BNF-like grammar (`.bnf`) with embedded Python, randomly expands it from a start non-terminal, and runs user Python on the results. It can also emit an AFL dictionary of all literal terminals in a grammar. Pure Python 3, no third-party dependencies. The grammar language is documented in `docs/README.rst`, which is also the PyPI long description, so keep it valid reST: `python -m docutils --halt=warning docs/README.rst /dev/null` (needs `docutils` and `pygments`). Each file in `examples/` starts with a comment giving its usage.

## Commands

```sh
python3 nelly.py examples/ab.bnf              # run from the source tree (no install needed)
python3 nelly.py examples/ab.bnf -c 10        # 10 iterations; -c 0 (or negative) loops until Ctrl-C / bail()
python3 nelly.py g.bnf -s NAME                # override entry point(s); repeatable
python3 nelly.py g.bnf -v key=value           # sets grammar variable $key; repeatable
python3 nelly.py g.bnf -o -                   # write results as raw bytes to stdout
python3 nelly.py g.bnf -c 9 -o 'out/%02d.bin'  # one file per result (also: -o FILE for all in one file)
python3 nelly.py g.bnf -x                     # hexdump each result
python3 nelly.py g.bnf -e latin-1             # encode text with latin-1 and force bytes everywhere
python3 nelly.py g.bnf -d out.dict            # write AFL dictionary instead of executing
python3 nelly.py g.bnf -D                     # debug logging
pip install .                                 # installs the `nelly` console script (nelly.main:main)
```

```sh
pytest                                        # run all tests (config in pytest.ini)
pytest tests/test_nelly.py::TestDictionary    # one class
pytest -k bail_in_post                        # one test by name
```

Tests live in `tests/test_nelly.py`: CLI-level tests write a grammar to `tmp_path` and call `nelly.main.main(argv)`, capturing stdout. Every `.bnf` in `examples/` and `nelly/grammars/` is parse-checked, and the examples in `RUNNABLE` are executed. Grammar output only appears if the grammar prints it (typically in a `<%post print($$) %>` block); nelly's own log lines go to stderr. No linter is configured.

## Architecture

Pipeline: `main.py` → `Parser` (uses `Scanner`) → `Program` → `Sandbox.Execute` per iteration (or `Dictionary.Walk`).

- **`rules.lex` + `scanner.py`**: The lexer is data-driven. `rules.lex` is a Python dict literal `eval`'d with the `@action`-decorated `Scanner` methods (`Push`, `Pop`, `AddToken`, `Sub`, `Unescape`, ...) in scope. It defines a stack of lexer states (`bnf`, `python_code`, quote/byte-string states, nested `comment`); the first matching regex in the current state wins, so **rule order matters**. Adding syntax usually means adding a rule here plus a token handler in the parser. Inside `<% %>` code, `$$`, `$*` and `$name` are rewritten by `Sub` to `_g_var["..."]` lookups.
- **`parser.py`**: Hand-written recursive-descent parser over the token list. `/* */` comment tokens are filtered out right after scanning, so the parser never sees them. Parse errors are `nelly.error`s, which `main()` logs and turns into exit status -1. Builds `Nonterminal` → `Expression` (one per `|` alternative) → `Statement` objects (`types.py`). Parenthesized groups and function-call arguments become `ANONYMOUS` nonterminals. Slices `[a:b]` and ranges `{n,m}` attach as operations to the preceding statement; `<n>` sets an alternative's weight. Code blocks are dedented and `compile()`d to code objects at parse time. `include '...'` recursively parses other files, searching the including file's dir, then `-i` dirs (default `.`), then `nelly/grammars/` (the bundled stdlib, e.g. `constants.bnf`, `pack.bnf`).
- **`sandbox.py`**: The interpreter. One fresh `Sandbox` per iteration; it holds a shared `globals` dict used for every `exec`/`eval` of grammar code (so `<%pre %>` definitions are visible to later actions, `%func(...)` calls, `&refs`, and `@decorators`). Grammar variables live in `globals['_g_var']` (`$$` = last result, `$*` = varterminal result, `$count` = iteration number, plus `-v` vars). `Sandbox.LOOKUP` maps `Types` statement constants to handler methods by index — keep it in sync with the order in `types.Types`. Backreferences (`\NAME`) return the last value produced by that nonterminal in this iteration.
- **Control flow from grammars**: `bail()` (raises `SystemExit`) stops all iterations and `fail()` (raises `SystemError`) discards the current result and retries with the same `$count`, so `-c N` means N kept results; `main.MAX_FAILURES` consecutive failures stop the run. Both come from `utils.py` and are in the sandbox globals (also as `nelly.bail()`/`nelly.fail()`). `Sandbox.__ExecPython` deliberately re-raises these two so they reach the loop in `main.py`. Any other exception in a code block is logged; in a semantic action it then raises `nelly.error` (ending the run), while in pre/post blocks execution continues.
- **Text vs bytes**: Values stay `str` while only text is involved; `sandbox._join` (used for concatenation and `{n,m}` repetition) promotes to `bytes` when str meets bytes, encoding via `nelly.tobytes` (`utils.py`, UTF-8 unless `nelly.encode` is set). Joining other types raises `nelly.error` with the location. `\xNN`/`\dNN` outside quotes are scanned as single `bytes`. `nelly.encode` (set by `-e` or a grammar's `pre` block) is the legacy mode that encodes every str as soon as it's produced, so actions see `bytes`; `ssl.bnf`, `base64.bnf` and `http-post.bnf` rely on it. Library grammars should not set it; use `nelly.tobytes` in helper functions instead (see `protocols/dhcp.bnf`).
- **Output** (`main.Output`): `-o`/`-x` write the value returned by `Sandbox.Execute` (the start's `$$` after post blocks, so post can replace it) via `nelly.tobytes`; `None` is skipped.
- **`dictionary.py`**: Recursively collects `TERMINAL` values (including inside groups and function arguments), encodes strings with `nelly.encode` or UTF-8, skips numeric constants and empty strings, and writes escaped `name_N="..."` lines in AFL dictionary format.
- **`program.py`**: `Program.Save/Load` pickles a parsed program (code objects via `marshal`); not used by the CLI.

Nonterminal options in `NAME(opt, @decorator): ...` — only `start` currently has runtime effect (marks an entry point; one is chosen at random per iteration). `override`, `pure` and `corrupt` are lexed and stored but not acted on.

## Packaging

Version/author metadata lives in `nelly/version.py` (read by `setup.py` via `exec`). `setup.py` ships every non-`.py` file under `nelly/` as package data, so new `.bnf` files in `nelly/grammars/` and `rules.lex` are included automatically. `deb_dist/` in `.gitignore` is from Debian package builds.
