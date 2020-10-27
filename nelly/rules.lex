#
# (c) 2008-2020 Matthew Shaw
#

{
    'states': {
        'bnf': [
            ( r'<%(pre|post|)', Push,  'python_code'   ), # embedded Python code
            ( r"'''",           Push,  'triple_quote'  ), # a triple_quoted string
            ( r'"',             Push,  'double_quote'  ), # a double_quoted string
            ( r"'",             Push,  'single_quote'  ), # a single_quoted string
            ( r"b'''",          Push,  'triple_bytes'  ), # a triple_quoted byte string
            ( r'b"',            Push,  'double_bytes'  ), # a double_quoted byte string
            ( r"b'",            Push,  'single_bytes'  ), # a single_quoted byte string
            ( r"/\*",           Push,  'comment'       ), # a multi-line comment
            ( r"//.*",          Ignore                 ), # a comment
            ( r"#.*",           Ignore                 ), # a comment

            ( r'include',        AddToken, 'include' ),

            ( r'start',    AddToken, 'option'  ),
            ( r'override', AddToken, 'option'  ),
            ( r'pure',     AddToken, 'option'  ),
            ( r'corrupt',  AddToken, 'option'  ),

            ( r'empty',    AddToken, 'empty'   ),  # explicit empty expression

            ( r'[+-]?0x[A-Fa-f0-9]+', AddNumber ), # hexadecimal
            ( r'[+-]?0b[0-1]+',       AddNumber ), # binary
            ( r'[+-]?0[0-7]+',        AddNumber ), # octal
            ( r'[+-]?[0-9]*\.[0-9]+', AddNumber ), # floating point
            ( r'[+-]?[0-9]+',         AddNumber ), # decimal

            ( r'(::)?\$\w+',  AddToken, 'varterminal' ),
            ( r'\\\$?\w+',    AddToken, 'backref'     ),
            ( r'\%[\w\.]+\(', AddToken, 'function'    ),
            ( r'\&[\w\.]+',   AddToken, 'reference'   ),
            ( r'(::)?\w+',    AddToken, 'nonterminal' ),
            ( r'(\.[\w]+)+',  AddToken, 'member'      ),
            ( r'@\w+',        AddToken, 'decorator'   ),

            ( r'\:', AddToken, 'colon'     ),
            ( r'\|', AddToken, 'pipe'      ),
            ( r'\;', AddToken, 'semicolon' ),
            ( r'\,', AddToken, 'comma'     ),
            ( r'\(', AddToken, 'lparen'    ),
            ( r'\)', AddToken, 'rparen'    ),
            ( r'\[', AddToken, 'lbracket'  ),
            ( r'\]', AddToken, 'rbracket'  ),
            ( r'\{', AddToken, 'lcurley'   ),
            ( r'\}', AddToken, 'rcurley'   ),
            ( r'\<', AddToken, 'langle'    ),
            ( r'\>', AddToken, 'rangle'    ),

            ( r'\s+', Ignore ),
            ( r'\n',  Ignore ),

            ( r'.', Error ),
        ],
        'python_code': [
            ( r'\s*%>',   Pop      ),
            ( r'\\\$',    Append   ),
            ( r'\$\w+',   Sub      ),
            ( r'\$\$',    Sub      ),
            ( r'\$\*',    Sub      ),
            ( r'\s*\#.*', Ignore   ),
            ( r'\n',      Append   ),
            ( r'.',       Append   ),
        ],
        'single_quote': [
            ( r"'",       Pop      ),
            ( r'\\\n',    Ignore   ),
            ( r"\\U[0-9A-Fa-f]{8}", Unescape ),
            ( r"\\u[0-9A-Fa-f]{4}", Unescape ),
            ( r"\\x[0-9A-Fa-f]{2}", Unescape ),
            ( r'\\[\\\'\"abfnrtv]', Unescape ),
            ( r".",       Append   ),
            ( r"\n",      Append   ),
        ],
        'double_quote': [
            ( r'"',       Pop      ),
            ( r'\\\n',    Ignore   ),
            ( r"\\U[0-9A-Fa-f]{8}", Unescape ),
            ( r"\\u[0-9A-Fa-f]{4}", Unescape ),
            ( r"\\x[0-9A-Fa-f]{2}", Unescape ),
            ( r'\\[\\\'\"abfnrtv]', Unescape ),
            ( r'.',       Append   ),
            ( r'\n',      Append   ),
        ],
        'triple_quote': [
            ( r"'''",     Pop      ),
            ( r'\\\n',    Ignore   ),
            ( r"\\U[0-9A-Fa-f]{8}", Unescape ),
            ( r"\\u[0-9A-Fa-f]{4}", Unescape ),
            ( r"\\x[0-9A-Fa-f]{2}", Unescape ),
            ( r'\\[\\\'\"abfnrtv]', Unescape ),
            ( r'.',       Append  ),
            ( r'\n',      Append  ),
        ],
        'single_bytes': [
            ( r"'",       PopByte  ),
            ( r'\\\n',    Ignore   ),
            ( r"\\x[0-9A-Fa-f]{2}", UnescapeHexByte ),
            ( r'\\[\\\'\"abfnrtv]', UnescapeByte ),
            ( r".",       AppendByte   ),
            ( r"\n",      AppendByte   ),
        ],
        'double_bytes': [
            ( r'"',       PopByte  ),
            ( r'\\\n',    Ignore   ),
            ( r"\\x[0-9A-Fa-f]{2}", UnescapeHexByte ),
            ( r'\\[\\\'\"abfnrtv]', UnescapeByte ),
            ( r".",       AppendByte   ),
            ( r"\n",      AppendByte   ),
        ],
        'triple_bytes': [
            ( r"'''",     PopByte  ),
            ( r'\\\n',    Ignore   ),
            ( r"\\x[0-9A-Fa-f]{2}", UnescapeHexByte ),
            ( r'\\[\\\'\"abfnrtv]', UnescapeByte ),
            ( r".",       AppendByte   ),
            ( r"\n",      AppendByte   ),
        ],
        'comment': [
            ( r"/\*",     Push, 'comment' ), # nested comments
            ( r'\*/',     Pop      ),
            ( r'.',       Ignore   ),
            ( r'\n',      Ignore   ),
        ],
    }
}
