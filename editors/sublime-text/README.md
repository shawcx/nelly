# Nelly for Sublime Text

Syntax highlighting for nelly grammars (`.bnf`), with the `<% %>` blocks
highlighted as Python.

- Definitions appear in Goto Symbol (Ctrl+R / Cmd+R) and Goto Anything `@`.
- Toggle Comment uses `//`, or `#` inside Python blocks.
- `$$`, `$*` and `$name` inside Python blocks are highlighted as nelly
  variables.

## Installing

Link or copy this directory into your Sublime Text `Packages` directory as
`Nelly`:

```sh
# Linux
ln -s "$PWD/editors/sublime-text" ~/.config/sublime-text/Packages/Nelly

# macOS
ln -s "$PWD/editors/sublime-text" ~/Library/Application\ Support/Sublime\ Text/Packages/Nelly
```

On Windows, copy it to `%APPDATA%\Sublime Text\Packages\Nelly`.

`.bnf` files then open with the Nelly syntax. If another package also claims
`.bnf`, open a grammar and choose View → Syntax → Open all with current
extension as… → Nelly.

## Testing

`syntax_test_nelly.bnf` is a Sublime syntax test. With the package installed
as `Nelly`, open the file and run Tools → Build (Ctrl+B / Cmd+B).

The rules follow `nelly/rules.lex`, so update `Nelly.sublime-syntax` and the
test when the grammar language changes.
