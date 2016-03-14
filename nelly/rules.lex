#
# (c) 2008-2016 Matthew Oertle
#

{
    'states': {
        'bnf': [
            ( r'<%(pre|post|)', Push,  'python_code'   ), # embedded Python code
            ( r"'''",           Push,  'triple_quote'  ), # a triple_quoted string
            ( r'"',             Push,  'double_quote'  ), # a double_quoted string
            ( r"'",             Push,  'single_quote'  ), # a single_quoted string
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
            ( r'[+-]?[0-9]+\.[0-9]+', AddNumber ), # floating point
            ( r'[+-]?[0-9]+',         AddNumber ), # decimal

            ( r'(::)?\$\w+',  AddToken, 'varterminal' ),
            ( r'\\\$?\w+',    AddToken, 'backref'     ),
            ( r'\%[\w\.]+\(', AddToken, 'function'    ),
            ( r'\&[\w\.]+',   AddToken, 'reference'   ),
            ( r'(::)?\w+',    AddToken, 'nonterminal' ),
            ( r'(\.[\w]+)+',  AddToken, 'member'      ),

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
            ( r'\$\w+',   Sub      ),
            ( r'\$\$',    Sub      ),
            ( r'\$\*',    Sub      ),
            ( r'\s*\#.*', Ignore   ),
            ( r'\n',      Append   ),
            ( r'.',       Append   ),
        ],
        'single_quote': [
            ( r"'",       Pop      ),
            ( r"\\x..",   Unescape ),
            ( r"\\.",     Unescape ),
            ( r".",       Append   ),
            ( r"\n",      Append   ),
        ],
        'double_quote': [
            ( r'"',       Pop      ),
            ( r'\\.',     Unescape ),
            ( r'.',       Append   ),
            ( r'\n',      Append   ),
        ],
        'triple_quote': [
            ( r"'''",     Pop      ),
            ( r'\\.',     Unescape ),
            ( r'.',       Append   ),
            ( r'\n',      Append   ),
        ],
        'comment': [
            ( r"/\*",     Push, 'comment' ), # nested comments
            ( r'\*/',     Pop      ),
            ( r'.',       Ignore   ),
            ( r'\n',      Ignore   ),
        ],
    }
}
