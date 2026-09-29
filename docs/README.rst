=====
nelly
=====
A grammar-based test case generator.
------------------------------------
Matthew Shaw <mshaw.cx@gmail.com>

Nelly reads a BNF-style grammar, expands it at random from a starting
non-terminal, and hands each result to embedded Python code. It is useful for
producing fuzzing inputs, protocol messages, and test data: anything that has
structure but should vary on every run. It can also export the literal strings
in a grammar as an `AFL <https://github.com/google/AFL>`_ dictionary.

Nelly is pure Python 3 with no dependencies.

.. contents::
   :local:
   :depth: 1

Installation
============

.. code-block:: sh

    pip install nelly          # from PyPI
    pip install .              # from a source checkout

This installs a ``nelly`` command. From a checkout you can also run
``python3 nelly.py`` without installing.

Quick start
===========

Save this as ``hello.bnf``:

.. code-block::

    GREETING(start): SALUTATION ', ' NAME PUNCTUATION;

    SALUTATION: 'Hello' | 'Hi' | 'Greetings';
    NAME:       'world' | 'nelly' | 'there';
    PUNCTUATION: '!' <3> | '.' <1>;   // '!' is three times as likely

    <%post
        print($$)
    %>

Then generate five strings:

.. code-block:: sh

    $ nelly -c 5 hello.bnf
    Hi, there!
    Hello, nelly!
    Hi, there!
    Hello, nelly.
    Hello, nelly!

``$$`` holds the result of the last expansion; in a ``post`` block that is the
whole generated string. Nelly's own log messages go to stderr, so stdout
contains only what the grammar prints. To write results as raw bytes instead
of printing them, see `Output`_.

Command line
============

.. code-block::

    nelly [options] [grammar]

The grammar is read from stdin if no file is given.

====================================  ============================================
Option                                Description
====================================  ============================================
``-c N``, ``--count N``               Generate N results (default 1), not counting
                                      any discarded by ``fail()``. 0 or less runs
                                      until interrupted or ``bail()``.
``-s NAME``, ``--start NAME``         Use NAME as the entry point instead of those
                                      marked ``start``. May be repeated.
``-v KEY=VALUE``, ``--vars``          Set the variable ``$KEY`` for code blocks.
                                      May be repeated.
``-i DIR``, ``--include DIR``         Add a directory to search for ``include``.
                                      May be repeated.
``-o PATH``, ``--output PATH``        Write each result as bytes to stdout (``-``),
                                      to one file per result (a path containing
                                      ``%d``) or all to one file. See `Output`_.
``-x``, ``--hexdump``                 Print a hexdump of each result.
``-e ENC``, ``--encode ENC``          Encode text with ENC instead of UTF-8, and
                                      build every value as ``bytes``. See
                                      `Text and bytes`_.
``-d FILE``, ``--dictionary FILE``    Write an AFL dictionary instead of
                                      generating. See `AFL dictionaries`_.
``-D``, ``--debug``                   Enable debug logging.
====================================  ============================================

Grammar basics
==============

A grammar is a list of definitions. Each one names a non-terminal and lists
one or more alternatives separated by ``|``, ending with ``;``:

.. code-block::

    NAME: alternative | alternative | ... ;

Any definition marked with the ``start`` option is an entry point. If there
are several, one is chosen at random for each result.

.. code-block::

    REQUEST(start): 'GET ' PATH;
    PATH: '/' | '/index.html';

Comments start with ``//`` or ``#`` and run to the end of the line.
``/* ... */`` comments may span lines, be nested, and appear anywhere.

If a name is defined twice, the later definition wins. This lets a grammar
include another and replace parts of it (see `Includes`_).

Terminals
---------

.. code-block::

    A: "A" | 'A' | '''A''' | \d65 | \x41;

Strings may use single, double or triple quotes and support the usual Python
escapes (``\n``, ``\t``, ``\xNN``, ``\uNNNN``, ``\UNNNNNNNN``, ...). They
produce text (``str``).

Byte strings use a ``b`` prefix and produce ``bytes``:

.. code-block::

    MAGIC: b'\x89PNG\r\n\x1a\n';

``\dNN`` and ``\xNN`` outside quotes produce a single byte from a decimal or
hexadecimal value up to 255, so ``\xff`` is always the byte ``0xff``. Inside a
text string, ``'\xff'`` is the character ``ÿ`` and becomes two bytes when
encoded as UTF-8. See `Text and bytes`_ for how the two are combined.

Numbers (``65``, ``0x41``, ``0b1000001``, ``0101``, ``6.5``) are also
terminals. They are mostly useful as arguments to `Function calls`_; a number
cannot be concatenated with a string.

Concatenation
-------------

Items separated by white-space are concatenated.

.. code-block::

    CONCAT: "CONC" "A" "TEN" "A" "TION";     // CONCATENATION

Selection and weights
---------------------

When there are several alternatives one is chosen at random. By default every
alternative is equally likely; a weight in angle brackets changes that.
Weights are relative to each other.

.. code-block::

    DIGIT: '0' | '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9';

    COIN:  'heads' <1> | 'tails' <1>;
    DICE:  'six' <1> | 'other' <5>;

``empty`` is an explicit alternative that produces nothing:

.. code-block::

    SIGN: '-' | '+' | empty;

Grouping
--------

Parentheses create an unnamed choice inside an alternative.

.. code-block::

    GRP: ('A'|'B') ('C'|'D');

Possible values are 'AC', 'AD', 'BC', or 'BD'.

Repetition
----------

``{n}`` repeats the preceding item exactly n times; ``{n,m}`` repeats it a
random number of times between n and m. Each repetition is expanded
separately.

.. code-block::

    NUM1: DIGIT{3};          // three digits, e.g. 042
    NUM2: DIGIT{1,5};        // one to five digits
    OPTIONAL: 'x'{0,1};      // 'x' or nothing
    DIGIT: '0'|'1'|'2'|'3'|'4'|'5'|'6'|'7'|'8'|'9';

Slicing
-------

Python-style slices take part of the preceding item.

.. code-block::

    SLICE1: "0123456789" [:];    // 0123456789
    SLICE2: "0123456789" [4];    // 4
    SLICE3: "0123456789" [:4];   // 0123
    SLICE4: "0123456789" [4:];   // 456789
    SLICE5: "0123456789" [2:8];  // 234567
    SLICE6: "0123456789" [-4];   // 6
    SLICE7: "0123456789" [-4:];  // 6789
    SLICE8: "0123456789" [:-4];  // 012345
    SLICE9: "0123456789" [2:-2]; // 234567

Slices and repetition can be combined: ``'abc'[1:]{2}`` produces ``bcbc``.

Non-terminals and back references
---------------------------------

Using a name expands that non-terminal. Every use is expanded again, so it
may produce a different value each time.

.. code-block::

    NT1: "The value of NT2 is " NT2;
    NT2: "substitution";

A back reference, ``\NAME``, repeats the value that ``NAME`` most recently
produced instead of expanding it again:

.. code-block::

    BR: "A" | "B";
    NT: BR \BR;

``NT`` generates 'AA' or 'BB' but never 'AB' or 'BA'.

Embedded Python
===============

Code blocks
-----------

``<%pre ... %>`` runs before each result is generated and ``<%post ... %>``
runs after. All code blocks for a result share one namespace, so anything
defined in ``pre`` can be used later. The namespace is fresh for every
result, and ``nelly`` itself is always available.

.. code-block::

    <%pre
        import random
        import struct
    %>

A block of code after an alternative is a semantic action. It runs after that
alternative is expanded, with the result in ``$$``:

.. code-block::

    PSA1: PSA2 "/" &var;
    PSA2: ("one" | "two") <% var = $$ %>;   // PSA1 is one/one or two/two

The indentation of the first line of a block is removed from every line, so
blocks can be indented to match the grammar.

Variable non-terminals
----------------------

Assigning to ``$$`` does not change the generated value. To transform a value
with Python, use a variable non-terminal: its name starts with ``$`` and its
value is whatever the action stores in ``$*``.

.. code-block::

    NT1: $NT2;

    $NT2:
      "I WILL BE SUBSTITUTED INTO NT1 IN LOWERCASE"
      <%
        $* = $$.lower()
      %>
      ;

The value in ``$*`` may be any Python object; it does not have to be a
string. Back references work with variable non-terminals too:

.. code-block::

    $BR: ("a"|"b") <% $* = $$.upper() %>;
    NT: $BR \$BR;   // AA or BB

Function calls
--------------

``%name(...)`` calls a Python function with the expanded arguments and uses
its return value. The function can be a builtin, something imported in a
``pre`` block, or something defined there.

.. code-block::

    <%pre
        import base64
    %>

    ENCODED: %base64.b64encode(b'string');     // b'c3RyaW5n'
    LENGTH:  %str(%len(WORD)) ' bytes';
    OCTET:   %chr(%random.randint(0, 255));    // needs `import random`

Each argument is a full expression, so it may use concatenation, choices,
repetition and other calls.

References
----------

``&name`` inserts the value of a Python variable or attribute without
calling it.

.. code-block::

    <%pre
        import os
        host = 'example.com'
    %>

    URL: 'http://' &host '/';
    SEP: &os.sep;

Decorators
----------

A function named in a definition's options with ``@`` is applied to every
value that definition produces:

.. code-block::

    <%pre
        def shout(s):
            return s.upper() + '!'
    %>

    GREETING(start, @shout): 'hello' | 'hi';   // HELLO! or HI!

Variables
---------

Code blocks can read and write variables as ``$name``. ``-v name=value`` on
the command line sets ``$name``, and ``$count`` is the number of the result
being generated, starting from 0. Reading a variable that was never set is an
error, which makes a convenient check for required options:

.. code-block::

    // usage: nelly -v out=DIR grammar.bnf
    <%pre
        $out
    %>

Stopping early
--------------

``bail()`` ends the run. ``fail()`` throws away the current result and tries
again, so ``-c 10`` still produces 10 results and ``$count`` only advances
when a result is kept. Both can be called from any code block or function.
If ``fail()`` is called 1000 times in a row, nelly assumes the grammar can
never succeed and stops.

.. code-block::

    ID(start): DIGIT{1,3} <% if $$.startswith('0'): fail() %>;

    <%post
        print($$)
        if $count == 99:
            bail()
    %>

Any other exception in a semantic action is logged and ends the run.
Errors in the grammar itself, such as a missing ``;``, are reported with
their line and column, and nelly exits with a non-zero status.

Text and bytes
==============

Text stays ``str`` as long as only text is involved, so semantic actions on
text work with ordinary strings. When text is joined with ``bytes`` (a byte
string, a ``\xNN`` constant, or the result of a function such as
``struct.pack``) the text is encoded as UTF-8 and the result is ``bytes``.
Joining anything else, such as a number or ``None``, is an error.

.. code-block::

    include 'pack.bnf'

    <%pre
        import struct
    %>

    RECORD(start): b'\x7fREC' %BWORD(%len(NAME)) \NAME;   // bytes
    NAME: 'alice' | 'bob';                                // str

``%len()`` of text counts characters, not bytes, so use
``%len(%nelly.tobytes(NAME))`` for a length prefix in front of non-ASCII text.
``nelly.tobytes(value)`` is also handy in Python functions that must accept
either type.

``-e ENC`` changes the encoding used for text. It also makes every value
``bytes`` as soon as it is produced, including ``$$`` in semantic actions,
which older grammars may rely on; setting ``nelly.encode = 'utf-8'`` in a
``pre`` block does the same.

Output
======

A grammar can print results itself in a ``post`` block, but for binary data
it is simpler to let nelly write them. Each result is converted to bytes
(encoding text as UTF-8) and written to:

.. code-block:: sh

    nelly -o - grammar.bnf                    # stdout, with no separator
    nelly -c 100 -o 'out/%04d.bin' grammar.bnf  # out/0000.bin ... out/0099.bin
    nelly -c 100 -o all.bin grammar.bnf       # every result, one after another
    nelly -c 5 -x grammar.bnf                 # a hexdump of each result

Directories are created as needed. The number in a file name is the same as
``$count``. Results discarded with ``fail()`` are not written, and a ``post``
block can assign to ``$$`` to change what is written.

``nelly.hexdump(data)`` prints the same hexdump from Python.

Includes
========

``include 'file.bnf'`` parses another grammar in place. The file is searched
for in the including file's directory, then each ``-i`` directory (the
current directory by default), then nelly's bundled grammars.

Because later definitions replace earlier ones, a grammar can include a
library and override pieces of it:

.. code-block::

    include 'protocols/http.bnf'

    HTTP_HOST: 'localhost';

Bundled grammars
----------------

============================  ==================================================
File                          Contents
============================  ==================================================
``constants.bnf``             ``SP``, ``CR``, ``LF``, ``CRLF``, ``TAB``,
                              ``NULL``, ``UPPER``, ``LOWER``, ``WORD``,
                              ``LONGWORD``, ``NUMBER_0_9``, ``RANDCHAR``,
                              ``RANDBYTE``
``pack.bnf``                  Python functions ``BYTE``, ``WORD``, ``DWORD``,
                              ``QWORD`` in native order, with ``L`` and ``B``
                              prefixes for little- and big-endian (e.g.
                              ``%BWORD(80)``); needs ``import struct``
``protocols/http.bnf``        HTTP requests (``HTTP_GET``, ``HTTP_POST``, ...)
``protocols/dhcp.bnf``        DHCP messages (``DHCP``, ``DHCP_CLIENT``,
                              ``DHCP_SERVER``)
``protocols/upnp.bnf``        UPnP and SSDP messages (``UPNP_HTTP_START``,
                              ``SSDP_DISCOVER``)
``formats/wmf.bnf``           Windows Metafile documents (``WMF``)
``ssl/ssl.bnf``               An SSL handshake client that connects to
                              ``localhost:4433``; needs the ``cryptography``
                              package
============================  ==================================================

AFL dictionaries
================

.. code-block:: sh

    nelly -d http.dict grammar.bnf

writes every literal string in the grammar and its includes to ``http.dict``
in AFL's dictionary format, one ``name_N="..."`` entry per line, for use with
``afl-fuzz -x http.dict``. Nothing is generated. Text is encoded with the
``-e`` encoding (UTF-8 by default); byte strings and ``\xNN`` constants are
written exactly.

Examples
========

The ``examples`` directory has a grammar for each feature:

======================  ==========================================================
Example                 Shows
======================  ==========================================================
``ab.bnf``              Choices, groups and repetition
``madlib.bnf``          Building a document from nested non-terminals
``weights.bnf``         Weights, ``empty``, decorators and ``fail()``
``slice.bnf``           Slices and function calls
``strings.bnf``         String and byte string escapes
``base64.bnf``          Back references, functions and variable non-terminals
``class.bnf``           Variable non-terminals holding Python objects
``html.bnf``            Writing each result to a file with ``-v``
``dhcp.bnf``            Binary packets from a bundled protocol grammar
``http-post.bnf``       Sending generated requests to a server
``upnp.bnf``            Choosing entry points with ``-s``
======================  ==========================================================

Each file starts with a comment showing how to run it.

Development
===========

.. code-block:: sh

    pip install pytest
    pytest
