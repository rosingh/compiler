""" Decaf compiler
A compiler for Decaf programs
Usage: python decafc.py <filename>
where <filename> is the name of the file containing the Decaf program.
"""
import sys
import getopt
import pprint

import decafparser
import ast
import absmc

class Usage(Exception):
  def __init__(self, msg):
    self.msg = msg

  
def main(argv=None):
  if argv is None:
    argv = sys.argv
    
  # parse command line options
  try:
    try:
      opts, args = getopt.getopt(argv[1:], "h", ["help"])
    except getopt.error, msg:
      raise Usage(msg)
    for o,a in opts:
      if o in ("-h", "--help"):
        print __doc__
        return 0
    if (len(args) != 1):
      raise Usage("A single file name argument is required")
    fullfilename = args[0]
    if (fullfilename.endswith('.decaf')):
      (filename,s,e) = fullfilename.rpartition('.')
    else:
      filename=fullfilename
    infile = filename + ".decaf"
    ast.initialize_ast()
    if decafparser.from_file(infile):
      try:
        code = ast.generate_code()
        program = ''
        for inst in code:
          if len(inst) > 1:
            program += inst[0] + ' '
            program += ', '.join(inst[1:])
          else:
            program += inst[0]
          program += '\n'
        with open(filename + '.ami', 'w') as outfile:
          outfile.write(program)
        absmc.generate_ssa(code)

        pprint.pprint(absmc.cfg)

      except ast.CodeGenerationError, err:
        print >>sys.stderr, err.msg
      
    else:
      print "Failure: there were errors."
  except Usage, err:
    print >>sys.stderr, err.msg
    print >>sys.stderr, "For help use --help"
    return 2

if __name__ == "__main__":
  sys.exit(main())
