# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Nelly is a grammar-based test case / fuzz input generator. It reads a BNF-like grammar (`.bnf`) with embedded Python, randomly expands it from a start non-terminal, and runs user Python on the results. It can also emit an AFL dictionary of all literal terminals in a grammar. Pure Python 3, no third-party dependencies. The grammar language is documented in `docs/README.rst` (also the PyPI long description).

## Commands

```sh
python3 nelly.py examples/ab.bnf              # run from the source tree (no install needed)
python3 nelly.py examples/ab.bnf -c 10        # 10 iterations; -c 0 (or negative) loops until Ctrl-C / bail()
python3 nelly.py g.bnf -s NAME                # override entry point(s); repeatable
python3 nelly.py g.bnf -v key=value           # sets grammar variable $key; repeatable
python3 nelly.py g.bnf -e latin-1             # binary mode: encode str results to bytes
python3 nelly.py g.bnf -d out.dict            # write AFL dictionary instead of executing
python3 nelly.py g.bnf -D                     # debug logging
pip install .                                 # installs the `nelly` console script (nelly.main:main)
```

There is no test suite or linter configured. Verify changes by running the grammars in `examples/` (e.g. `ab.bnf`, `madlib.bnf`, `slice.bnf`, `strings.bnf`, `http-post.bnf`). Output only appears if the grammar prints it (typically in a `<%post print($$) %>` block); nelly's own log lines go to stderr.

## Architecture

Pipeline: `main.py` → `Parser` (uses `Scanner`) → `Program` → `Sandbox.Execute` per iteration (or `Dictionary.Walk`).

- **`rules.lex` + `scanner.py`**: The lexer is data-driven. `rules.lex` is a Python dict literal `eval`'d with the `@action`-decorated `Scanner` methods (`Push`, `Pop`, `AddToken`, `Sub`, `Unescape`, ...) in scope. It defines a stack of lexer states (`bnf`, `python_code`, quote/byte-string states, nested `comment`); the first matching regex in the current state wins, so **rule order matters**. Adding syntax usually means adding a rule here plus a token handler in the parser. Inside `<% %>` code, `$$`, `$*` and `$name` are rewritten by `Sub` to `_g_var["..."]` lookups.
- **`parser.py`**: Hand-written recursive-descent parser over the token list. Builds `Nonterminal` → `Expression` (one per `|` alternative) → `Statement` objects (`types.py`). Parenthesized groups and function-call arguments become `ANONYMOUS` nonterminals. Slices `[a:b]` and ranges `{n,m}` attach as operations to the preceding statement; `<n>` sets an alternative's weight. Code blocks are dedented and `compile()`d to code objects at parse time. `include '...'` recursively parses other files, searching the including file's dir, then `-i` dirs (default `.`), then `nelly/grammars/` (the bundled stdlib, e.g. `constants.bnf`, `pack.bnf`).
- **`sandbox.py`**: The interpreter. One fresh `Sandbox` per iteration; it holds a shared `globals` dict used for every `exec`/`eval` of grammar code (so `<%pre %>` definitions are visible to later actions, `%func(...)` calls, `&refs`, and `@decorators`). Grammar variables live in `globals['_g_var']` (`$$` = last result, `$*` = varterminal result, `$count` = iteration number, plus `-v` vars). `Sandbox.LOOKUP` maps `Types` statement constants to handler methods by index — keep it in sync with the order in `types.Types`. Backreferences (`\NAME`) return the last value produced by that nonterminal in this iteration.
- **Control flow from grammars**: `utils.py` provides `bail()` (raises `SystemExit`) and `fail()` (raises `SystemError`), reachable as `nelly.bail()`/`nelly.fail()`. `main.py` treats an escaping `SystemExit` as "stop all iterations" and `SystemError` as "skip this iteration" — but only when they propagate out uncaught (e.g. from a `%func(...)` call). Inside `<% %>` blocks, `Sandbox.__ExecPython` intercepts them and returns a status instead: in semantic actions a bare `SystemExit` is ignored, while `SystemExit(truthy)` or any other exception (including `SystemError`, which is also logged) raises `nelly.error` and ends the run; in pre/post blocks a bare `SystemExit` raises `nelly.error`, and other failures are logged and execution continues.
- **`nelly.encode`**: A module-level global set from `-e`. When set, expressions accumulate `bytes` and `str` results are encoded; mixing str and bytes otherwise raises a `TypeError` reported with the expression location.
- **`dictionary.py`**: Walks all `TERMINAL` statements and writes escaped `name_N="..."` lines in AFL dictionary format.
- **`program.py`**: `Program.Save/Load` pickles a parsed program (code objects via `marshal`); not used by the CLI.

Nonterminal options in `NAME(opt, @decorator): ...` — only `start` currently has runtime effect (marks an entry point; one is chosen at random per iteration). `override`, `pure` and `corrupt` are lexed and stored but not acted on.

## Packaging

Version/author metadata lives in `nelly/version.py` (read by `setup.py` via `exec`). `setup.py` ships every non-`.py` file under `nelly/` as package data, so new `.bnf` files in `nelly/grammars/` and `rules.lex` are included automatically. `deb_dist/` in `.gitignore` is from Debian package builds.
