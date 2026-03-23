# Python (programming language)

## History

== History ==

thumb|311x311px|The designer of Python, [[Guido van Rossum, at PyCon US 2024]]
Python was conceived in the late 1980s

The name Python derives from the British comedy series Monty Python's Flying Circus. (See .)

Python 2.0 was released on 16 October 2000, featuring many new features such as list comprehensions, cycle-detecting garbage collection, reference counting, and Unicode support. It no longer receives security patches or updates. While Python 2.7 and older versions are officially unsupported, a different unofficial Python implementation, PyPy, continues to support Python 2, i.e., "2.7.18+" (plus 3.11), with the plus signifying (at least some) "backported security updates".

Python&nbsp;3.0 was released on 3 December 2008, and was a major revision and not completely backward-compatible with earlier versions, with some new semantics and changed syntax. Python&nbsp;2.7.18, released in 2020, was the last release of Python&nbsp;2. Several releases in the Python 3.x series have added new syntax to the language, and made a few (considered very minor) backward-incompatible changes.

, Python  is the latest stable release. All older 3.x versions had a security update down to Python 3.9.24 then again with 3.9.25, the final version in 3.9 series. Python 3.10 is, since November 2025, the oldest supported branch. Python 3.15 has an alpha released, and Android has an official downloadable executable available for Python 3.14. Releases receive two years of full support followed by three years of security support.

## Design philosophy and features

==Design philosophy and features==
Python is a multi-paradigm programming language. Object-oriented programming and structured programming are fully supported, and many of their features support functional programming and aspect-oriented programming – including metaprogramming because it is purposely designed to be able to integrate components written in other languages.

Python uses dynamic typing and a combination of reference counting and a cycle-detecting garbage collector for memory management. It uses dynamic name resolution (late binding), which binds method and variable names during program execution.

Python's design offers some support for functional programming in the "Lisp tradition". It has , , and  functions; list comprehensions, dictionaries, sets, and generator expressions. Responses to these criticisms note that the Zen of Python is a guideline rather than a rule. The addition of some new features had been controversial: Guido van Rossum resigned as Benevolent Dictator for Life after conflict about adding the assignment expression operator in 

Nevertheless, rather than building all functionality into its core, Python was designed to be highly extensible via modules. This compact modularity has made it particularly popular as a means of adding programmable interfaces to existing applications. Van Rossum's vision of a small core language with a large standard library and easily extensible interpreter stemmed from his frustrations with ABC, which represented the opposite approach. In contrast to Perl's motto "there is more than one way to do it", Python advocates an approach where "there should be one – and preferably only one – obvious way to do it". Alex Martelli is a Fellow at the Python Software Foundation and Python book author; he wrote that "To describe something as 'clever' is not considered a compliment in the Python culture."

A common neologism in the Python community is pythonic, which has a broad range of meanings related to program style: Pythonic code may use Python idioms well; be natural or show fluency in the language; or conform with Python's minimalist philosophy and emphasis on readability.

## Syntax and semantics

==Syntax and semantics==

Python is meant to be an easily readable language. Its formatting is visually uncluttered and often uses English keywords where other languages use punctuation. Unlike many other languages, it does not use curly brackets to delimit blocks, and semicolons after statements are allowed but rarely used. It has fewer syntactic exceptions and special cases than C or Pascal. This feature is sometimes termed the off-side rule. Some other languages use indentation this way; but in most, indentation has no semantic meaning. The recommended indent size is four spaces.

===Statements and control flow===
Python's statements include the following:
* The assignment statement, using a single equals sign =
* The if statement, which conditionally executes a block of code, along with else and elif (a contraction of else if)
* The for statement, which iterates over an iterable object, capturing each element to a variable for use by the attached block; the variable is not deleted when the loop finishes
* The while statement, which executes a block of code as long as boolean condition is true
* The try statement, which allows exceptions raised in its attached code block to be caught and handled by except clauses (or new syntax except* in Python 3.11 for exception groups); the try statement also ensures that clean-up code in a finally block is always run regardless of how the block exits
* The raise statement, used to raise a specified exception or re-raise a caught exception
* The class statement, which executes a block of code and attaches its local namespace to a class, for use in object-oriented programming
* The def statement, which defines a function or method
* The with statement, which encloses a code block within a context manager, allowing resource-acquisition-is-initialization (RAII)-like behavior and replacing a common try/finally idiom Examples of a context include acquiring a lock before some code is run, and then releasing the lock; or opening and then closing a file
* The break statement, which exits a loop
* The continue statement, which skips the rest of the current iteration and continues with the next
* The del statement, which removes a variable—deleting the reference from the name to the value, and producing an error if the variable is referred to before it is redefined 
* The pass statement, serving as a NOP (i.e., no operation), which is syntactically needed to create an empty code block
* The assert statement, used in debugging to check for conditions that should apply
* The yield statement, which returns a value from a generator function (and also an operator); used to implement coroutines
* The return statement, used to return a value from a function
* The import and from statements, used to import modules whose functions or variables can be used in the current program
* The match and case statements, analogous to a switch statement construct, which compares an expression against one or more cases as a control-flow measure

The assignment statement (=) binds a name as a reference to a separate, dynamically allocated object. Variables may subsequently be rebound at any time to any object. In Python, a variable name is a generic reference holder without a fixed data type; however, it always refers to some object with a type. This is called dynamic typing—in contrast to statically-typed languages, where each variable may contain only a value of a certain type.

Python does not support tail call optimization or first-class continuations; according to Van Rossum, the language never will. Python uses the ** operator for exponentiation.
* Python uses the + operator for string concatenation. The language uses the * operator for duplicating a string a specified number of times.
* The @ infix operator is intended to be used by libraries such as NumPy for matrix multiplication.
* The syntax :=, called the "", was introduced in Python 3.8. This operator assigns values to variables as part of a larger expression.
* In Python, == compares two objects by value. Python's is operator may be used to compare object identities (i.e., comparison by reference), and comparisons may be chained—for example, .
* Python uses and, or, and not as Boolean operators.
* Python has a type of expression called a list comprehension, and a more general expression called a generator expression.
* Python features sequence unpacking where multiple expressions, each evaluating to something assignable (e.g., a variable or a writable property) are associated just as in forming tuple literal; as a whole, the results are then put on the left-hand side of the equal sign in an assignment statement. This statement expects an iterable object on the right-hand side of the equal sign to produce the same number of values as the writable expressions on the left-hand side; while iterating, the statement assigns each of the values produced on the right to the corresponding expression on the left.
* Python has a "string format" operator % that functions analogously to printf format strings in the C language—e.g.  evaluates to "spam=blah eggs=2". In Python&nbsp;2.6+ and 3+, this operator was supplemented by the format() method of the str class, e.g., {{code|2=python|1="spam={0} eggs={1}".format("blah", 2)}}. Python&nbsp;3.6 added "f-strings": {{code|2=python|1=spam = "blah"; eggs = 2; f'spam={spam} eggs={eggs}'}}.
* Strings in Python can be concatenated by "adding" them (using the same operator as for adding integers and floats); e.g.,  returns "spameggs". If strings contain numbers, they are concatenated as strings rather than as integers, e.g.  returns "22".
* Python supports string literals in several ways:
** Delimited by single or double quotation marks; single and double quotation marks have equivalent functionality (unlike in Unix shells, Perl, and Perl-influenced languages). Both marks use the backslash (\) as an escape character. String interpolation became available in Python&nbsp;3.6 as "formatted string literals". These annotations are not enforced by the language, but may be used by external tools such as mypy to catch errors. Python includes a module typing including several type names for type annotations. Also, mypy supports a Python compiler called mypyc, which leverages type annotations for optimization.

{|class="wikitable"
|+ Summary of Python 3's built-in types
|-
! Type
! Mutability
! Description
! Syntax examples
|-
| bool
| immutable
| Boolean value
| 
|-
| bytearray
| mutable
| Sequence of bytes
| 
|-
| bytes
| immutable
| Sequence of bytes
| 
|-
| complex
| immutable
| Complex number with real and imaginary parts
| 
|-
| dict
| mutable
| Associative array (or dictionary) of key and value pairs; can contain mixed types (keys and values); keys must be a hashable type
| {{code|lang=python|{'key1': 1.0, 3: False} }}{{code|lang=python| {} }}
|-
| types.EllipsisType
| immutable
| An ellipsis placeholder to be used as an index in NumPy arrays
| 
|-
| float
| immutable
| Double-precision floating-point number. The precision is machine-dependent, but in practice it is generally implemented as a 64-bit IEEE&nbsp;754 number with 53&nbsp;bits of precision.
|

|-
| frozenset
| immutable
| Unordered set, contains no duplicates; can contain mixed types, if hashable
| {{code|lang=python|frozenset({4.0, 'string', True})}}

|-
| int
| immutable
| Integer of unlimited magnitude
| 
|-
| set
| mutable
| Unordered set, contains no duplicates; can contain mixed types, if hashable
| {{code|lang=python| {4.0, 'string', True} }}
|-
| str
| immutable
| A character string: sequence of Unicode codepoints
| """Spanning
multiple
lines"""
|-
| tuple
| immutable
| Tuple, can contain mixed types
| 
|}

===Arithmetic operations===
Python includes conventional symbols for arithmetic operators (+, -, *, /), the floor-division operator //, and the modulo operator %. (With the modulo operator, a remainder can be negative, e.g., 4 % -3 == -2.) Also, Python offers the ** symbol for exponentiation, e.g. 5**3 == 125 and 9**0.5 == 3.0. Also, it offers the matrix‑multiplication operator @ . These operators work as in traditional mathematics; with the same precedence rules, the infix operators + and - can also be unary, to represent positive and negative numbers respectively.

Division between integers produces floating-point results. The behavior of division has changed significantly over time:

Due to Python's extensive mathematics library and the third-party library NumPy, the language is frequently used for scientific scripting in tasks such as numerical data processing and manipulation.

===Function syntax===
Functions are created in Python by using the def keyword. A function is defined similarly to how it is called, by first providing the function name and then the required parameters. Here is an example of a function that prints its inputs:

def printer(input1, input2 = "already there"):
    print(input1)
    print(input2)
    
printer("hello")
    
# Example output:
# hello
# already there
To assign a default value to a function parameter in case no actual value is provided at run time, variable-definition syntax can be used inside the function header.

## Indentation

===Indentation===

Python uses whitespace indentation, rather than curly brackets or keywords, to delimit blocks. An increase in indentation comes after certain statements; a decrease in indentation signifies the end of the current block. This feature is sometimes termed the off-side rule. Some other languages use indentation this way; but in most, indentation has no semantic meaning. The recommended indent size is four spaces.

## Statements and control flow

===Statements and control flow===
Python's statements include the following:
* The assignment statement, using a single equals sign =
* The if statement, which conditionally executes a block of code, along with else and elif (a contraction of else if)
* The for statement, which iterates over an iterable object, capturing each element to a variable for use by the attached block; the variable is not deleted when the loop finishes
* The while statement, which executes a block of code as long as boolean condition is true
* The try statement, which allows exceptions raised in its attached code block to be caught and handled by except clauses (or new syntax except* in Python 3.11 for exception groups); the try statement also ensures that clean-up code in a finally block is always run regardless of how the block exits
* The raise statement, used to raise a specified exception or re-raise a caught exception
* The class statement, which executes a block of code and attaches its local namespace to a class, for use in object-oriented programming
* The def statement, which defines a function or method
* The with statement, which encloses a code block within a context manager, allowing resource-acquisition-is-initialization (RAII)-like behavior and replacing a common try/finally idiom Examples of a context include acquiring a lock before some code is run, and then releasing the lock; or opening and then closing a file
* The break statement, which exits a loop
* The continue statement, which skips the rest of the current iteration and continues with the next
* The del statement, which removes a variable—deleting the reference from the name to the value, and producing an error if the variable is referred to before it is redefined 
* The pass statement, serving as a NOP (i.e., no operation), which is syntactically needed to create an empty code block
* The assert statement, used in debugging to check for conditions that should apply
* The yield statement, which returns a value from a generator function (and also an operator); used to implement coroutines
* The return statement, used to return a value from a function
* The import and from statements, used to import modules whose functions or variables can be used in the current program
* The match and case statements, analogous to a switch statement construct, which compares an expression against one or more cases as a control-flow measure

The assignment statement (=) binds a name as a reference to a separate, dynamically allocated object. Variables may subsequently be rebound at any time to any object. In Python, a variable name is a generic reference holder without a fixed data type; however, it always refers to some object with a type. This is called dynamic typing—in contrast to statically-typed languages, where each variable may contain only a value of a certain type.

Python does not support tail call optimization or first-class continuations; according to Van Rossum, the language never will. However, better support for coroutine-like functionality is provided by extending Python's generators. Before 2.5, generators were lazy iterators; data was passed unidirectionally out of the generator. From Python&nbsp;2.5 on, it is possible to pass data back into a generator function; and from version 3.3, data can be passed through multiple stack levels.

## Expressions

===Expressions===
Python's expressions include the following:
* The +, -, and * operators for mathematical addition, subtraction, and multiplication are similar to other languages, but the behavior of division differs. There are two types of division in Python: floor division (or integer division) //, and floating-point division /. Python uses the ** operator for exponentiation.
* Python uses the + operator for string concatenation. The language uses the * operator for duplicating a string a specified number of times.
* The @ infix operator is intended to be used by libraries such as NumPy for matrix multiplication.
* The syntax :=, called the "", was introduced in Python 3.8. This operator assigns values to variables as part of a larger expression.
* In Python, == compares two objects by value. Python's is operator may be used to compare object identities (i.e., comparison by reference), and comparisons may be chained—for example, .
* Python uses and, or, and not as Boolean operators.
* Python has a type of expression called a list comprehension, and a more general expression called a generator expression.
* Python features sequence unpacking where multiple expressions, each evaluating to something assignable (e.g., a variable or a writable property) are associated just as in forming tuple literal; as a whole, the results are then put on the left-hand side of the equal sign in an assignment statement. This statement expects an iterable object on the right-hand side of the equal sign to produce the same number of values as the writable expressions on the left-hand side; while iterating, the statement assigns each of the values produced on the right to the corresponding expression on the left.
* Python has a "string format" operator % that functions analogously to printf format strings in the C language—e.g.  evaluates to "spam=blah eggs=2". In Python&nbsp;2.6+ and 3+, this operator was supplemented by the format() method of the str class, e.g., {{code|2=python|1="spam={0} eggs={1}".format("blah", 2)}}. Python&nbsp;3.6 added "f-strings": {{code|2=python|1=spam = "blah"; eggs = 2; f'spam={spam} eggs={eggs}'}}.
* Strings in Python can be concatenated by "adding" them (using the same operator as for adding integers and floats); e.g.,  returns "spameggs". If strings contain numbers, they are concatenated as strings rather than as integers, e.g.  returns "22".
* Python supports string literals in several ways:
** Delimited by single or double quotation marks; single and double quotation marks have equivalent functionality (unlike in Unix shells, Perl, and Perl-influenced languages). Both marks use the backslash (\) as an escape character. String interpolation became available in Python&nbsp;3.6 as "formatted string literals".
** Triple-quoted, i.e., starting and ending with three single or double quotation marks; this may span multiple lines and function like here documents in shells, Perl, and Ruby.
** Raw string varieties, denoted by prefixing the string literal with r. Escape sequences are not interpreted; hence raw strings are useful where literal backslashes are common, such as in regular expressions and Windows-style paths. (Compare "@-quoting" in C#.)
* Python has array index and array slicing expressions in lists, which are written as a[key],  or . Indexes are zero-based, and negative indexes are relative to the end. Slices take elements from the start index up to, but not including, the stop index. The (optional) third slice parameter, called step or stride, allows elements to be skipped or reversed. Slice indexes may be omitted—for example,  returns a copy of the entire list. Each element of a slice is a shallow copy.

In Python, a distinction between expressions and statements is rigidly enforced, in contrast to languages such as Common Lisp, Scheme, or Ruby. This distinction leads to duplicating some functionality, for example:
* List comprehensions vs. for-loops
* Conditional expressions vs. if blocks
* The eval() vs. exec() built-in functions (in Python&nbsp;2, exec is a statement); the former function is for expressions, while the latter is for statements

A statement cannot be part of an expression; because of this restriction, expressions such as list and dict comprehensions (and lambda expressions) cannot contain statements. As a particular case, an assignment statement such as  cannot be part of the conditional expression of a conditional statement.

## Typing

===Typing===
thumb|The standard type hierarchy in Python&nbsp;3
Python uses duck typing, and it has typed objects but untyped variable names. Type constraints are not checked at definition time; rather, operations on an object may fail at usage time, indicating that the object is not of an appropriate type. Despite being dynamically typed, Python is strongly typed, forbidding operations that are poorly defined (e.g., adding a number and a string) rather than quietly attempting to interpret them.

Python allows programmers to define their own types using classes, most often for object-oriented programming. New instances of classes are constructed by calling the class, for example,  or ); the classes are instances of the metaclass type (which is an instance of itself), thereby allowing metaprogramming and reflection.

Before version 3.0, Python had two kinds of classes, both using the same syntax: old-style and new-style. These annotations are not enforced by the language, but may be used by external tools such as mypy to catch errors. Python includes a module typing including several type names for type annotations. Also, mypy supports a Python compiler called mypyc, which leverages type annotations for optimization.

{|class="wikitable"
|+ Summary of Python 3's built-in types
|-
! Type
! Mutability
! Description
! Syntax examples
|-
| bool
| immutable
| Boolean value
| 
|-
| bytearray
| mutable
| Sequence of bytes
| 
|-
| bytes
| immutable
| Sequence of bytes
| 
|-
| complex
| immutable
| Complex number with real and imaginary parts
| 
|-
| dict
| mutable
| Associative array (or dictionary) of key and value pairs; can contain mixed types (keys and values); keys must be a hashable type
| {{code|lang=python|{'key1': 1.0, 3: False} }}{{code|lang=python| {} }}
|-
| types.EllipsisType
| immutable
| An ellipsis placeholder to be used as an index in NumPy arrays
| 
|-
| float
| immutable
| Double-precision floating-point number. The precision is machine-dependent, but in practice it is generally implemented as a 64-bit IEEE&nbsp;754 number with 53&nbsp;bits of precision.
|

|-
| frozenset
| immutable
| Unordered set, contains no duplicates; can contain mixed types, if hashable
| {{code|lang=python|frozenset({4.0, 'string', True})}}

|-
| int
| immutable
| Integer of unlimited magnitude
| 
|-
| set
| mutable
| Unordered set, contains no duplicates; can contain mixed types, if hashable
| {{code|lang=python| {4.0, 'string', True} }}
|-
| str
| immutable
| A character string: sequence of Unicode codepoints
| """Spanning
multiple
lines"""
|-
| tuple
| immutable
| Tuple, can contain mixed types
| 
|}

## Arithmetic operations

===Arithmetic operations===
Python includes conventional symbols for arithmetic operators (+, -, *, /), the floor-division operator //, and the modulo operator %. (With the modulo operator, a remainder can be negative, e.g., 4 % -3 == -2.) Also, Python offers the ** symbol for exponentiation, e.g. 5**3 == 125 and 9**0.5 == 3.0. Also, it offers the matrix‑multiplication operator @ . These operators work as in traditional mathematics; with the same precedence rules, the infix operators + and - can also be unary, to represent positive and negative numbers respectively.

Division between integers produces floating-point results. The behavior of division has changed significantly over time:

Due to Python's extensive mathematics library and the third-party library NumPy, the language is frequently used for scientific scripting in tasks such as numerical data processing and manipulation.

## Function syntax

===Function syntax===
Functions are created in Python by using the def keyword. A function is defined similarly to how it is called, by first providing the function name and then the required parameters. Here is an example of a function that prints its inputs:

def printer(input1, input2 = "already there"):
    print(input1)
    print(input2)
    
printer("hello")
    
# Example output:
# hello
# already there
To assign a default value to a function parameter in case no actual value is provided at run time, variable-definition syntax can be used inside the function header.

## Code examples

==Code examples==
"Hello, World!" program:

print('Hello, World!')

Program to calculate the factorial of a non-negative integer:

text = input('Type a number, and its factorial will be printed: ')
n = int(text)

if n

## Development environments

==Development environments==

Most Python implementations (including CPython) include a read–eval–print loop (REPL); this permits the environment to function as a command line interpreter, with which users enter statements sequentially and receive results immediately.

Also, CPython is bundled with an integrated development environment (IDE) called IDLE, which is oriented toward beginners.

Other shells, including IDLE and IPython, add additional capabilities such as improved auto-completion, session-state retention, and syntax highlighting.

Standard desktop IDEs include PyCharm, Spyder, and Visual Studio Code; there are web browser-based IDEs, such as the following environments:

* Jupyter Notebooks, an open-source interactive computing platform;
* PythonAnywhere, a browser-based IDE and hosting environment; and
* Canopy, a commercial IDE from Enthought that emphasizes scientific computing.

## Implementations

==Implementations==

===Reference implementation===
CPython is the reference implementation of Python. This implementation is written in C, meeting the C11 standard since version 3.11. Older versions use the C89 standard with several select C99 features, but third-party extensions are not limited to older C versions—e.g., they can be implemented using C11 or C++. Windows XP was supported until Python&nbsp;3.5, with unofficial support for VMS. Platform portability was one of Python's earliest priorities. since that time, support has been dropped for many platforms.

All current Python versions (since 3.7) support only operating systems that feature multithreading, by now supporting not nearly as many operating systems (dropping many outdated) than in the past.

===Limitations of the reference implementation===
* The energy usage of Python with CPython for typically written code is much worse than C by a factor of 75.88.
* The throughput of Python with CPython for typically written code is worse than C by a factor of 71.9. yet there exist implementations that are capable of truly compiling Python. Alternative implementations include the following:

* PyPy is a faster, compliant interpreter of Python&nbsp;2.7 and  3.10. PyPy's just-in-time compiler often improves speed significantly relative to CPython, but PyPy does not support some libraries written in C. For example, Codon uses 64-bit machine integers for speed, not arbitrarily as with Python; Codon developers claim that speedups over CPython are usually on the order of ten to a hundred times. Codon compiles to machine code (via LLVM) and supports native multithreading.  Codon can also compile to Python extension modules that can be imported and used from Python.
* MicroPython and CircuitPython are Python&nbsp;3 variants that are optimized for microcontrollers, including the Lego Mindstorms EV3.
* Pyston is a variant of the Python runtime that uses just-in-time compilation to speed up execution of Python programs.
* Cinder is a performance-oriented fork of CPython 3.8 that features a number of optimizations, including bytecode inline caching, eager evaluation of coroutines, a method-at-a-time JIT, and an experimental bytecode compiler.
* The Snek embedded computing language "is Python-inspired, but it is not Python. It is possible to write Snek programs that run under a full Python system, but most Python programs will not run under Snek." Snek is compatible with 8-bit AVR microcontrollers such as ATmega 328P-based Arduino, as well as larger microcontrollers that are compatible with MicroPython. Snek is an imperative language that (unlike Python) omits object-oriented programming. Snek supports only one numeric data type, which features 32-bit single precision (resembling JavaScript numbers, though smaller).

===Unsupported implementations===
Stackless Python is a significant fork of CPython that implements microthreads. This implementation uses the call stack differently, thus allowing massively concurrent programs. PyPy also offers a stackless version.

===Transpilers to other languages===
There are several compilers/transpilers to high-level object languages; the source language is unrestricted Python, a subset of Python, or a language similar to Python:
* Brython and Transcrypt compile Python to JavaScript.
* Cython compiles a superset of Python to C. The resulting code can be used with Python via direct C-level API calls into the Python interpreter.
* PyJL compiles/transpiles a subset of Python to "human-readable, maintainable, and high-performance Julia source code". Despite the developers' performance claims, this is not possible for arbitrary Python code; that is, compiling to a faster language or machine code is known to be impossible in the general case. The semantics of Python might potentially be changed, but in many cases speedup is possible with few or no changes in the Python code. The faster Julia source code can then be used from Python or compiled to machine code.
* Nuitka compiles Python into C. This compiler works with Python 3.4 to 3.13 (and 2.6 and 2.7) for Python's main supported platforms (and Windows 7 or even Windows XP) and for Android. The compiler developers claim full support for Python 3.10, partial support for Python 3.11 and 3.12,  and experimental support for Python 3.13. Nuitka supports macOS including Apple Silicon-based versions.  The compiler is free of cost, though it has commercial add-ons (e.g., for hiding source code).
* Numba is a JIT compiler that is used from Python; the compiler translates a subset of Python and NumPy code into fast machine code. This tool is enabled by adding a decorator to the relevant Python code.
* Pythran compiles a subset of Python&nbsp;3 to C++ (C++11).
* RPython can be compiled to C, and it is used to build the PyPy interpreter for Python.
* The Python → 11l → C++ transpiler compiles a subset of Python&nbsp;3 to C++ (C++17).

There are also specialized compilers:
* MyHDL is a Python-based hardware description language (HDL) that converts MyHDL code to Verilog or VHDL code.

Some older projects existed, as well as compilers not designed for use with Python 3.x and related syntax:
* Google's Grumpy transpiles Python&nbsp;2 to Go. The latest release was in 2017.
* IronPython allows running Python&nbsp;2.7 programs with the .NET Common Language Runtime. An alpha version (released in 2021), is available for "Python&nbsp;3.4, although features and behaviors from later versions may be included."
* Jython compiles Python&nbsp;2.7 to Java bytecode, allowing the use of Java libraries from a Python program.
* Pyrex (last released in 2010) and Shed Skin (last released in 2013) compile to C and C++ respectively.

===Performance===
A performance comparison among various Python implementations, using a non-numerical (combinatorial) workload, was presented at EuroSciPy '13. In addition, Python's performance relative to other programming languages is benchmarked by The Computer Language Benchmarks Game.

There are several approaches to optimizing Python performance, despite the inherent slowness of an interpreted language. These approaches include the following strategies or tools:

* Just-in-time compilation: Dynamically compiling parts of a Python program during the execution of the program. This technique is used in libraries such as Numba and PyPy.
* Static compilation: Sometimes, Python code can be compiled into machine code sometime before execution. An example of this approach is Cython, which compiles Python into C.
* Concurrency and parallelism: Multiple tasks can be run simultaneously. Python contains modules such as `multiprocessing` to support this form of parallelism. Moreover, this approach helps to overcome limitations of the Global Interpreter Lock (GIL) in CPU tasks.
* Efficient data structures: Performance can also be improved by using data types such as Set for membership tests, or deque from collections for queue operations.
* Performance gains can be observed by utilizing libraries such as NumPy. Most high performance Python libraries use C or Fortran under the hood instead of the Python interpreter.

## Reference implementation

===Reference implementation===
CPython is the reference implementation of Python. This implementation is written in C, meeting the C11 standard since version 3.11. Older versions use the C89 standard with several select C99 features, but third-party extensions are not limited to older C versions—e.g., they can be implemented using C11 or C++. Windows XP was supported until Python&nbsp;3.5, with unofficial support for VMS. Platform portability was one of Python's earliest priorities. since that time, support has been dropped for many platforms.

All current Python versions (since 3.7) support only operating systems that feature multithreading, by now supporting not nearly as many operating systems (dropping many outdated) than in the past.

## Limitations of the reference implementation

===Limitations of the reference implementation===
* The energy usage of Python with CPython for typically written code is much worse than C by a factor of 75.88.
* The throughput of Python with CPython for typically written code is worse than C by a factor of 71.9.
* The average memory usage of CPython for typically written code is worse than C by a factor of 2.4.

## Other implementations

===Other implementations===
All alternative implementations have at least slightly different semantics. For example, an alternative may include unordered dictionaries, in contrast to other current Python versions. As another example in the larger Python ecosystem, PyPy does not support the full C Python API.

Creating an executable with Python often is done by bundling an entire Python interpreter into the executable, which causes binary sizes to be massive for small programs, yet there exist implementations that are capable of truly compiling Python. Alternative implementations include the following:

* PyPy is a faster, compliant interpreter of Python&nbsp;2.7 and  3.10. PyPy's just-in-time compiler often improves speed significantly relative to CPython, but PyPy does not support some libraries written in C. For example, Codon uses 64-bit machine integers for speed, not arbitrarily as with Python; Codon developers claim that speedups over CPython are usually on the order of ten to a hundred times. Codon compiles to machine code (via LLVM) and supports native multithreading.  Codon can also compile to Python extension modules that can be imported and used from Python.
* MicroPython and CircuitPython are Python&nbsp;3 variants that are optimized for microcontrollers, including the Lego Mindstorms EV3.
* Pyston is a variant of the Python runtime that uses just-in-time compilation to speed up execution of Python programs.
* Cinder is a performance-oriented fork of CPython 3.8 that features a number of optimizations, including bytecode inline caching, eager evaluation of coroutines, a method-at-a-time JIT, and an experimental bytecode compiler.
* The Snek embedded computing language "is Python-inspired, but it is not Python. It is possible to write Snek programs that run under a full Python system, but most Python programs will not run under Snek." Snek is compatible with 8-bit AVR microcontrollers such as ATmega 328P-based Arduino, as well as larger microcontrollers that are compatible with MicroPython. Snek is an imperative language that (unlike Python) omits object-oriented programming. Snek supports only one numeric data type, which features 32-bit single precision (resembling JavaScript numbers, though smaller).

## Unsupported implementations

===Unsupported implementations===
Stackless Python is a significant fork of CPython that implements microthreads. This implementation uses the call stack differently, thus allowing massively concurrent programs. PyPy also offers a stackless version.

## Transpilers to other languages

===Transpilers to other languages===
There are several compilers/transpilers to high-level object languages; the source language is unrestricted Python, a subset of Python, or a language similar to Python:
* Brython and Transcrypt compile Python to JavaScript.
* Cython compiles a superset of Python to C. The resulting code can be used with Python via direct C-level API calls into the Python interpreter.
* PyJL compiles/transpiles a subset of Python to "human-readable, maintainable, and high-performance Julia source code". Despite the developers' performance claims, this is not possible for arbitrary Python code; that is, compiling to a faster language or machine code is known to be impossible in the general case. The semantics of Python might potentially be changed, but in many cases speedup is possible with few or no changes in the Python code. The faster Julia source code can then be used from Python or compiled to machine code.
* Nuitka compiles Python into C. This compiler works with Python 3.4 to 3.13 (and 2.6 and 2.7) for Python's main supported platforms (and Windows 7 or even Windows XP) and for Android. The compiler developers claim full support for Python 3.10, partial support for Python 3.11 and 3.12,  and experimental support for Python 3.13. Nuitka supports macOS including Apple Silicon-based versions.  The compiler is free of cost, though it has commercial add-ons (e.g., for hiding source code).
* Numba is a JIT compiler that is used from Python; the compiler translates a subset of Python and NumPy code into fast machine code. This tool is enabled by adding a decorator to the relevant Python code.
* Pythran compiles a subset of Python&nbsp;3 to C++ (C++11).
* RPython can be compiled to C, and it is used to build the PyPy interpreter for Python.
* The Python → 11l → C++ transpiler compiles a subset of Python&nbsp;3 to C++ (C++17).

There are also specialized compilers:
* MyHDL is a Python-based hardware description language (HDL) that converts MyHDL code to Verilog or VHDL code.

Some older projects existed, as well as compilers not designed for use with Python 3.x and related syntax:
* Google's Grumpy transpiles Python&nbsp;2 to Go. The latest release was in 2017.
* IronPython allows running Python&nbsp;2.7 programs with the .NET Common Language Runtime. An alpha version (released in 2021), is available for "Python&nbsp;3.4, although features and behaviors from later versions may be included."
* Jython compiles Python&nbsp;2.7 to Java bytecode, allowing the use of Java libraries from a Python program.
* Pyrex (last released in 2010) and Shed Skin (last released in 2013) compile to C and C++ respectively.

## Performance

===Performance===
A performance comparison among various Python implementations, using a non-numerical (combinatorial) workload, was presented at EuroSciPy '13. In addition, Python's performance relative to other programming languages is benchmarked by The Computer Language Benchmarks Game.

There are several approaches to optimizing Python performance, despite the inherent slowness of an interpreted language. These approaches include the following strategies or tools:

* Just-in-time compilation: Dynamically compiling parts of a Python program during the execution of the program. This technique is used in libraries such as Numba and PyPy.
* Static compilation: Sometimes, Python code can be compiled into machine code sometime before execution. An example of this approach is Cython, which compiles Python into C.
* Concurrency and parallelism: Multiple tasks can be run simultaneously. Python contains modules such as `multiprocessing` to support this form of parallelism. Moreover, this approach helps to overcome limitations of the Global Interpreter Lock (GIL) in CPU tasks.
* Efficient data structures: Performance can also be improved by using data types such as Set for membership tests, or deque from collections for queue operations.
* Performance gains can be observed by utilizing libraries such as NumPy. Most high performance Python libraries use C or Fortran under the hood instead of the Python interpreter.

## Language development

==Language development==
Python's development is conducted mostly through the Python Enhancement Proposal (PEP) process; this process is the primary mechanism for proposing major new features, collecting community input on issues, and documenting Python design decisions. Development originally took place on a self-hosted source-code repository running Mercurial, until Python moved to GitHub in January 2017.

CPython's public releases have three types, distinguished by which part of the version number is incremented:
* Backward-incompatible versions, where code is expected to break and must be manually ported. The first part of the version number is incremented. These releases happen infrequently—version 3.0 was released 8 years after 2.0. According to Guido van Rossum, a version 4.0 will probably never exist.
* Major or "feature" releases are largely compatible with the previous version but introduce new features. The second part of the version number is incremented. Starting with Python&nbsp;3.9, these releases are expected to occur annually. Each major version is supported by bug fixes for several years after its release.
* Bug fix releases, which introduce no new features, occur approximately every three months; these releases are made when a sufficient number of bugs have been fixed upstream since the last release. Security vulnerabilities are also patched in these releases. The third and final part of the version number is incremented.

Many alpha, beta, and release-candidates are also released as previews and for testing before final releases. Although there is a rough schedule for releases, they are often delayed if the code is not ready yet. Python's development team monitors the state of the code by running a large unit test suite during development.

The major academic conference on Python is PyCon. Also, there are special Python mentoring programs, such as PyLadies.

## Naming

==Naming==
Python's name is inspired by the British comedy group Monty Python, whom Python creator Guido van Rossum enjoyed while developing the language. Monty Python references appear frequently in Python code and culture; Python users are sometimes referred to as "Pythonistas".

## Languages influenced by Python

==Languages influenced by Python==
* Cobra has an Acknowledgements document that lists Python first among influencing languages.
* ECMAScript and JavaScript borrowed iterators and generators from Python.
* Go is designed for "speed of working in a dynamic language like Python".
* Julia was designed to be "as usable for general programming as Python".
* Mojo is almost a superset of Python.
* GDScript is strongly influenced by Python.
*  Groovy, Boo, CoffeeScript, F#, Nim, Ruby, and V have been influenced, as well.

## See also

==See also==

* List of Python programming books
* pip (package manager) (see also uv)
* Pydoc
* NumPy
* SciPy
* Jupyter
* PyTorch
* Cython
* CPython
* Mojo
* Pygame
* PyQt
* PyGTK
* PyPy
* PyCon
* Google Colab zero setup online IDE that runs Python
* Ren'Py

## External links

==External links==

* 
* Python documentation
* The Python Tutorial

 
Category:Articles with example Python (programming language) code
Category:Class-based programming languages
Category:Notebook interface
Category:Computer science in the Netherlands
Category:Concurrent programming languages
Category:Cross-platform free software
Category:Cross-platform software
Category:Dutch inventions
Category:Dynamically typed programming languages
Category:Educational programming languages
Category:High-level programming languages
Category:Information technology in the Netherlands
Category:Multi-paradigm programming languages
Category:Object-oriented programming languages
Category:Pattern matching programming languages
Category:Programming languages
Category:Programming languages created in 1991
Category:Scripting languages
Category:Text-oriented programming languages
Category:Monty Python references
