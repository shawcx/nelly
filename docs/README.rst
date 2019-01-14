=====
nelly
=====
A grammar-based generator.
--------------------------
Matthew Oertle <moertle@gmail.com>

.. code-block::

  <%pre
      import sys
  %>

  ::NT(start)
      : 'A' # comment
      | 'B' <% print($$) %>
      ;

  <%post
      print($$)
  %>

Constants
=========

Constants in productions can consist of double-quoted strings, single-quoted strings, decimal, hexadecimal, or octal numbers.

.. code-block::

    A: "A" | 'A' | 65 | 0x41 | 0101;

Concatenation
=============

Productions are concatenated when they are seperated by white-space.

.. code-block::

    CONCAT: "CONC" 0x41 "TEN" 65 "TION";

Selection
=========

When multiple productions are present one is chosen at random.

.. code-block::

    NUMBER: '0' | '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9';

Grouping
========

.. code-block::

    GRP: ('A'|'B') ('C'|'D');

Possible values are 'AC', 'AD', 'BC', or 'BD'.

Ranges
======

.. code-block::

    NUM1: ('0'|'1'|'2'|'3'|'4'|'5'|'6'|'7'|'8'|'9'){3};
    NUM2: ('0'|'1'|'2'|'3'|'4'|'5'|'6'|'7'|'8'|'9'){1,5};

NUM1 will generate a 3-digit number while NUM2 will generate a number of random length between 1 and 5 digits.

Slicing
=======

A sub-string of a production can be referenced using indices.

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

The output of each production is documented in the comment proceeding it.

Inline Python
=============

.. code-block::

    <%pre
        import base64
    %>

    NT: %base64.b64encode('string');

Non-Terminals
=============

.. code-block::

    NT1: "The value of NT2 is " NT2;
    NT2: "substitution";

Semantic Actions
================

$$

.. code-block::

    PSA1: PSA2 <% var = $$ %>;
    PSA2: "one" | "two";

In this example the Python variable **var** will contain either 'one' or 'two' for future use.

Variable Non-Terminals
======================

$*

.. code-block::

    NT1: $NT2;

    $NT2:
      "I WILL BE SUBSTITUTED INTO NT1 IN LOWERCASE"
      <%
        $* = $$.lower()
      %>
      ;


Back Reference
==============

.. code-block::

    BR: "A" | "B";
    NT: BR \BR;

.. code-block::

    $BR: ("a"|"b") <% $* = $$.upper() %>;
    NT: $BR \$BR;

In both cases **NT** will generate the string 'AA' or 'BB' but not 'AB' or 'BA'.
