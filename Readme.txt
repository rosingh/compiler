Rodrigo Singh
Allison Ng
Decaf Intermediate Code Generator

README.txt:	this file
decaflexer.py	PLY/lex specification of Decaf tokens.
		Also defines "errorflag" used to signal error during scanning/parsing.
decafparser.py	PLY/yacc specification of Decaf grammar.
		The encoded grammar rules appear in the same order as in decaf manual.
		Defines "from_file" function that takes a file name
		and parses that file's contents. "from_file" returns
		True if no error, and False if error.

ast.py		Class structure and functions for AST construction.
					Also includes type checking by running a method called check
					for each node as it descends down the tree, which is called
					from the parser when a class declaration is completed.

					Also contains codegen functions

absmc.py 	Abstract machine related helper functions, such as generating
				  registers, allocating static space, and register scoping.

decafc.py	Driver: processes arguments and gets file name to pass
		to decafparser.from_file
		Decaf programs are assumed to be in files with ".decaf" suffix.
		Argument given to decafch may omit this suffix; e.g.
				python decafch test
		will read from test.decaf.

Note : We have reserved index 0 of the static area/heap for null comparisons.
