import absmc
from collections import OrderedDict

classtable = OrderedDict()  # initially empty dictionary of classes.
lastmethod = 0
lastconstructor = 0

current_class = None
is_constructor = False
current_method = None
curr_method_return = False

class CodeGenerationError(Exception):
  def __init__(self, msg):
    self.msg = msg

# Class table.  Only user-defined classes are placed in the class table.
def lookup(table, key):
  if key in table:
    return table[key]
  else:
    return None

def addtotable(table, key, value):
  table[key] = value


def print_ast():
  for cid in classtable:
    c = classtable[cid]
    c.printout()
  print "-----------------------------------------------------------------------------"


def initialize_ast():
  # define In class:
  cin = Class("In", None)
  cin.builtin = True     # this is a builtin class
  cout = Class("Out", None)
  cout.builtin = True     # this, too, is a builtin class

  scanint = Method('scan_int', cin, 'public', 'static', Type('int'))
  scanint.update_body(SkipStmt(None))    # No line number information for the empty body
  cin.add_method(scanint)

  scanfloat = Method('scan_float', cin, 'public', 'static', Type('float'))
  scanfloat.update_body(SkipStmt(None))    # No line number information for the empty body
  cin.add_method(scanfloat)

  printint = Method('print', cout, 'public', 'static', Type('void'))
  printint.update_body(SkipStmt(None))    # No line number information for the empty body
  printint.add_var('i', 'formal', Type('int'))   # single integer formal parameter
  cout.add_method(printint)
  
  printfloat = Method('print', cout, 'public', 'static', Type('void'))
  printfloat.update_body(SkipStmt(None))    # No line number information for the empty body
  printfloat.add_var('f', 'formal', Type('float'))   # single float formal parameter
  cout.add_method(printfloat)
  
  printboolean = Method('print', cout, 'public', 'static', Type('void'))
  printboolean.update_body(SkipStmt(None))    # No line number information for the empty body
  printboolean.add_var('b', 'formal', Type('boolean'))   # single boolean formal parameter
  cout.add_method(printboolean)
  
  printstring = Method('print', cout, 'public', 'static', Type('void'))
  printstring.update_body(SkipStmt(None))    # No line number information for the empty body
  printstring.add_var('b', 'formal', Type('string'))   # single string formal parameter
  cout.add_method(printstring)

  addtotable(classtable, "In", cin)
  addtotable(classtable, "Out", cout)

def generate_code():
  code = []
  for cls in classtable.values():
    code += cls.generate_code()

  code = [('.static_data ' + str(absmc.static_size),)] + code
  return code

class Class(object):
  """A class encoding Classes in Decaf"""
  def __init__(self, classname, superclass):
    self.name = classname
    self.superclass = superclass
    self.fields = {}  # dictionary, keyed by field name
    self.constructors = []
    self.methods = []
    self.builtin = False

  def printout(self):
    if (self.builtin):
      return     # Do not print builtin methods
    
    print "-----------------------------------------------------------------------------"
    print "Class Name: {0}".format(self.name)
    sc = self.superclass
    if (sc == None):
      scname = ""
    else:
      scname = sc.name
    print "Superclass Name: {0}".format(scname)
    print "Fields:"
    for f in self.fields:
      (self.fields[f]).printout()
    print "Constructors:"
    for k in self.constructors:
      k.printout()
    print "Methods:"
    for m in self.methods:
      m.printout()
    

  def add_field(self, fname, field):
    self.fields[fname] = field
  def add_constructor(self, constr):
    self.constructors.append(constr)
  def add_method(self, method):
    self.methods.append(method)

  def lookup_field(self, fname):
    return lookup(self.fields, fname)

  # check if this class is a subtype of class_name by going up the hierarchy
  def isSubClass(self, super_class):
    suclass = self
    while (suclass != None):
      if (suclass.name == super_class):
        return True
      suclass = suclass.superclass
    return False

  # Only runs after typechecking is successful
  def generate_code(self):
    global current_class
    code = [(" ".join(["#CLASS (", self.name, ")"]),)]
    current_class = self
    if self.superclass is not None:
      self.heap_size = self.superclass.heap_size
    else:
      self.heap_size = 0
    #generate code for fields
    #print "CLASS (",self.name,")"
    for field in self.fields.values():
      code += field.generate_code()

    #generate code for constructors
    for constructor in self.constructors:
      code += constructor.generate_code()
    #generate code for methods
    for method in self.methods:
      code += method.generate_code()

    return code


  def check(self):
    '''Type checking and name resolution starts here,
        by going down the nodes in a class.'''
    global current_class
    current_class = self
    success = True
    for constructor in self.constructors:
      if constructor.check() == False:
        success = False
    for method in self.methods:
      if method.check() == False:
        success = False
    return success
      
class Type(object):
  """A class encoding Types in Decaf"""
  def __init__(self, basetype, class_ref=None, params=None):
    if ((params == None) or (params == 0)):
      if (basetype in ['int', 'boolean', 'float', 'string', 'void', 'error', 'null']):
        self.kind = 'basic'
        self.typename = basetype
      elif (isinstance(basetype, Type)):
        self.kind = basetype.kind
        self.typename = basetype.typename
      #if in class table, it's a class literal
      elif class_ref:
        self.kind = 'class-literal'
        self.typename = basetype
      else:
        self.kind = 'class'
        self.typename = basetype
    else:
      bt = Type(basetype, params-1)
      self.kind = 'array'
      self.basetype = bt

  def __str__(self):
    if (self.kind == 'array'):
      return 'array(%s)'%(self.basetype.__str__())
    elif (self.kind == 'class'):
      return 'user(%s)'%(self.typename)
    else:
      return self.typename

  def __repr(self):
    return self.__str__()

  #self is a subclass of type2. whereever type 2 can go, self can go
  def compatible(self, type2):
    equal = self.typename == type2.typename
    is_subclass = False
    if self.typename == 'int' and type2.typename == 'float':
      is_subclass = True
    elif (self.kind == 'class' or self.kind == 'class-literal') and not equal:
      cls = lookup(classtable, self.typename)
      if cls is not None:
        is_subclass = cls.isSubClass(type2.typename)
      else:
        print "{0}: Class {1} not found".format(self.lines, self.typename)
        return False
    elif self.typename == 'null' and type2.kind == 'class':
      is_subclass = True
    return equal or is_subclass

class Field(object):
  """A class encoding fields and their attributes in Decaf"""
  lastfield = 0
  def __init__(self, fname, fclass, visibility, storage, ftype):
    Field.lastfield += 1
    self.name = fname
    self.id = Field.lastfield
    self.inclass = fclass
    self.visibility = visibility
    self.storage = storage
    self.type = ftype

  def printout(self):
    print "FIELD {0}, {1}, {2}, {3}, {4}, {5}".format(self.id, self.name, self.inclass.name, self.visibility, self.storage, self.type)
    print "offset("+str(self.offset)+")"

  def generate_code(self):
    if self.storage == 'static':
      self.offset = absmc.allocate_static_space()
    else:
      self.offset = self.inclass.heap_size
      self.inclass.heap_size += 1
    #print self.name, self.storage, self.offset
    return []

class Method(object):
  """A class encoding methods and their attributes in Decaf"""
  def __init__(self, mname, mclass, visibility, storage, rtype):
    global lastmethod
    self.name = mname
    lastmethod += 1
    self.id = lastmethod
    self.inclass = mclass
    self.visibility = visibility
    self.storage = storage
    self.rtype = rtype
    self.vars = VarTable()
    
  def update_body(self, body):
    self.body = body

  def add_var(self, vname, vkind, vtype):
    self.vars.add_var(vname, vkind, vtype)

  def get_label(self):
    if self.name == 'main':
      return '__main__'
    else:
      return '_'.join(['M', self.name, str(self.id)])

  def generate_code(self):
    global current_method, is_constructor, curr_method_return
    current_method = self
    is_constructor = False
    curr_method_return = False
    #generate label
    method_label = self.get_label()
    #set up registers for variables
    absmc.reset_argument_register(self.storage)
    #print "REGISTERS (",self.name,")"
    #code = [(method_label + ':',)]
    code = absmc.set_current_label(method_label, False)
    absmc.start_registers_scope()

    for b in range(self.vars.lastblock+1):
      for vname in self.vars.vars[b]:
        code += self.vars.vars[b][vname].generate_code()
        #print vname, self.vars.vars[b][vname].register

    #generate code for the body
    code += self.body.generate_code()

    #get rid of register cache
    absmc.kill_registers_scope()

    # add to processed methods list
    absmc.finished_processing(method_label)

    return code

  def check(self):
    global current_method, is_constructor, curr_method_return
    current_method = self
    is_constructor = False
    curr_method_return = False
    if self.body.check():
      if self.rtype.typename != 'void' and not curr_method_return:
        print "{0}: Method '{1}' must return a value of type {2}".format(self.body.lines, self.name, self.rtype.typename)
        return False
      return True
    return False

  def printout(self):
    print "METHOD: {0}, {1}, {2}, {3}, {4}, {5}".format(self.id, self.name, self.inclass.name, self.visibility, self.storage, self.rtype)
    print "Method Parameters:",
    args = map(lambda arg: str(arg.id), self.vars.get_params())
    print ', '.join(args)
    self.vars.printout()
    print "Method Body:"
    self.body.printout()
    
class Constructor(object):
  """A class encoding constructors and their attributes in Decaf"""
  def __init__(self, cname, visibility):
    global lastconstructor
    self.name = cname
    lastconstructor += 1
    self.id = lastconstructor
    self.visibility = visibility
    self.vars = VarTable()
    
  def update_body(self, body):
    self.body = body

  def add_var(self, vname, vkind, vtype):
    self.vars.add_var(vname, vkind, vtype)

  def get_label(self):
    return '_'.join(['C', str(self.id)])

  def generate_code(self):
    #set up registers for variables
    global current_method, is_constructor
    current_method = self
    is_constructor = True
    absmc.reset_argument_register("instance")
    constructor_label = self.get_label()
    #print "REGISTERS (",self.name,")"
    absmc.start_registers_scope()
    #generate code for body
    #code = [(constructor_label + ':',)]
    code = absmc.set_current_label(constructor_label, False)
    for b in range(self.vars.lastblock+1):
      for vname in self.vars.vars[b]:
        code += self.vars.vars[b][vname].generate_code()
        #print vname, self.vars.vars[b][vname].register

    
    code += self.body.generate_code()
    code.append(("ret",))
    absmc.kill_registers_scope()

    absmc.processed_method_labels.append(constructor_label)
    return code

  def check(self):
    global current_method, is_constructor
    current_method = self
    is_constructor = True
    return self.body.check()

  def printout(self):
    print "CONSTRUCTOR: {0}, {1}".format(self.id, self.visibility)
    print "Constructor Parameters:",
    args = map(lambda arg: str(arg.id), self.vars.get_params())
    print ', '.join(args)
    self.vars.printout()
    print "Constructor Body:"
    self.body.printout()
    

class VarTable(object):
  """ Table of variables in each method/constructor"""
  def __init__(self):
    self.vars = OrderedDict()
    self.vars[0] = OrderedDict()
    self.lastvar = 0
    self.lastblock = 0
    self.levels = [0]

  def enter_block(self):
    self.lastblock += 1
    self.levels.insert(0, self.lastblock)
    self.vars[self.lastblock] = {}

  def leave_block(self):
    self.levels = self.levels[1:]
    # where should we check if we can indeed leave the block?

  def add_var(self, vname, vkind, vtype):
    self.lastvar += 1
    c = self.levels[0]   # current block number
    v = Variable(vname, self.lastvar, vkind, vtype)
    vbl = self.vars[c]  # list of variables in current block
    vbl[vname] = v
  
  def _find_in_block(self, vname, b):
    if (b in self.vars):
      # block exists
      if (vname in self.vars[b]):
        return self.vars[b][vname]
    # Otherwise, either block b does not exist, or vname is not in block b
    return None

  def find_in_current_block(self, vname):
    return self._find_in_block(vname, self.levels[0])

  def find_in_scope(self, vname):
    for b in self.levels:
      v = self._find_in_block(vname, b)
      if v is not None:
        return v
      # otherwise, locate in enclosing block until we run out
    return None

  def get_params(self):
    outermost = self.vars[0]  # 0 is the outermost block
    ids = [outermost[vname] for vname in outermost if outermost[vname].kind=='formal']
    return ids

  def printout(self):
    print "Variable Table:"
    for b in range(self.lastblock+1):
      for vname in self.vars[b]:
        v = self.vars[b][vname]
        v.printout()
    

class Variable(object):
  """ Record for a single variable"""
  def __init__(self, vname, id, vkind, vtype):
    self.name = vname
    self.id = id
    self.kind = vkind
    self.type = vtype

  def printout(self):
    print "VARIABLE {0}, {1}, {2}, {3}".format(self.id, self.name, self.kind, self.type)
  
  def generate_code(self):
    if self.kind == 'formal':
      self.register = absmc.generate_argument_register()
      return []
    else:
      self.register = absmc.generate_temporary_register()
      #declare the variable -> define it to be 0
      return [("move_immed_i", self.register, '0')]

class Stmt(object): 
  """ Top-level (abstract) class representing all statements"""

class IfStmt(Stmt):
  def __init__(self, condition, thenpart, elsepart, lines):
    self.lines = lines
    self.condition = condition
    self.thenpart = thenpart
    self.elsepart = elsepart

  def generate_code(self):
    '''
      <condition stmt>
      bz $t0, else
      <then stuff>
      jmp exit_if:
      else:
      <else stuff>
      exit_if:
    '''
    then_label = absmc.get_new_label()
    else_label = absmc.get_new_label()
    exit_label = absmc.get_new_label()
    code = [("#if statement",)]

    #generate code for each part of if statement
    #generate condition
    code += self.condition.generate_code()
    #evaluate condition
    #code.append(('bz', self.condition.register, else_label))
    code += absmc.branch(self.condition.register, else_label, True)

    #then scope
    code += absmc.set_current_label(then_label, True)
    absmc.start_registers_scope()
    #condition = true, do this stuff
    code += self.thenpart.generate_code()
    #skip over the else
    code += absmc.jump(exit_label)
    #end of scope
    absmc.kill_registers_scope()

    #else scope
    absmc.start_registers_scope()
    #start the else part
    code += absmc.set_current_label(else_label, False)
    #else code
    code += self.elsepart.generate_code()
    #end of scope
    absmc.kill_registers_scope()

    #exit if statement
    code += absmc.set_current_label(exit_label, True)

    #print "\n".join(code)
    return code

  def check(self):
    cond_check = self.condition.check()
    then_check = self.thenpart.check()
    else_check = self.elsepart.check()
    if cond_check:
      if not self.condition.type.compatible(Type('boolean')):
        print "{0}: Invalid condition type {1}.".format(self.lines, self.condition.type.typename)
        return False
      return then_check and else_check
    return False

  def printout(self):
    print "If(",
    self.condition.printout()
    print ", ",
    self.thenpart.printout()
    print ", ",
    self.elsepart.printout()
    print ")"

class WhileStmt(Stmt):
  def __init__(self, cond, body, lines):
    self.lines = lines
    self.cond = cond
    self.body = body

  def generate_code(self):
    #gen : label here
    '''
    check_cond:
    bz t0, end_while
    # do loop things
    jmp check_cond
    end_while:
    # rest of program
    '''
    #generate code for loop condition
    #curr_label = absmc.get_current_label()
    check_cond = absmc.get_new_label()
    body_label = absmc.get_new_label()
    end_while = absmc.get_new_label()
    absmc.continue_labels.append(check_cond)
    absmc.break_labels.append(end_while)
    
    code = [("#while loop",)]
    absmc.start_registers_scope()
    # Check if condition is still true
    code += absmc.set_current_label(check_cond, True)
    code += self.cond.generate_code()
    #code.append(('bz', self.cond.register, end_while))
    code += absmc.branch(self.cond.register, end_while, True)

    #loop body
    code += absmc.set_current_label(body_label, True)
    # Get code for body
    code += self.body.generate_code()
    # jump back to condition check
    code += absmc.jump(check_cond)

    # label after the loop for failed conditions
    #code.append((end_while + ':',))
    code += absmc.set_current_label(end_while, False)

    absmc.continue_labels.pop()
    absmc.break_labels.pop()
    absmc.kill_registers_scope()

    return code

  def check(self):
    cond_check = self.cond.check()
    body_check = self.body.check()
    if cond_check:
      if not self.cond.type.compatible(Type('boolean')):
        print "{0}: Invalid condition type {1}.".format(self.lines, self.cond.type.typename)
        return False
      return body_check
    return False

  def printout(self):
    print "While(",
    self.cond.printout()
    print ", ",
    self.body.printout()
    print ")"

class ForStmt(Stmt):
  def __init__(self, init, cond, update, body, lines):
    self.lines = lines
    self.init = init
    self.cond = cond
    self.update = update
    self.body = body

  def generate_code(self):
    code = [("#for loop",)]
    absmc.start_registers_scope()

    #initialize all vars first
    if self.init is not None:
      code += self.init.generate_code()
    #gen : label
    for_start = absmc.get_new_label()
    for_update = absmc.get_new_label()
    for_end = absmc.get_new_label()
    absmc.continue_labels.append(for_update)
    absmc.break_labels.append(for_end)
    
    #start the for loop
    code += absmc.set_current_label(for_start, True)

    #check condition here
    if self.cond is not None:
      code += self.cond.generate_code()
      #branch if condition = 0
      #code.append(('bz', self.cond.register, for_end))
      code += absmc.branch(self.cond.register, for_end, True)
    
    #generate code for loop body
    if self.body is not None:
      for_body = absmc.get_new_label()
      code += absmc.set_current_label(for_body, True)
      code += self.body.generate_code()

    #update gets done at the end, right before jumping back to top of loop
    code += absmc.set_current_label(for_update, True)
    if self.update is not None:
      code += self.update.generate_code()

    #gen : jump to for start label 
    code += absmc.jump(for_start)

    #label to signify end of for
    code += absmc.set_current_label(for_end, False)

    absmc.continue_labels.pop()
    absmc.break_labels.pop()
    absmc.kill_registers_scope()

    return code

  def check(self):
    init_check = True
    update_check = True
    body_check = False
    cond_check = True
    if self.init is not None:
      init_check = self.init.check()
    if self.body is not None:
      body_check = self.body.check()
    if self.update is not None:
      update_check = self.update.check()
    if self.cond is not None:
      cond_check = self.cond.check()

    if cond_check and self.cond is not None:
      if not self.cond.type.compatible(Type('boolean')):
        print "{0}: Invalid condition type {1}.".format(self.lines, self.cond.type.typename)
        return False
    return init_check and body_check and update_check and cond_check

    
  def printout(self):
    print "For(",
    if (self.init != None):
      self.init.printout()
    print ", ",
    if (self.cond != None):
      self.cond.printout()
    print ", ",
    if (self.update != None):
      self.update.printout()
    print ", ",
    self.body.printout()
    print ")"

class ReturnStmt(Stmt):
  def __init__(self, expr, lines):
    self.lines = lines
    self.expr = expr

  def generate_code(self):
    #gen : save the return value
    #gen : return
    code = []
    if self.expr is not None:
      code += self.expr.generate_code()
      code.append(("#return",))
      code.append(('move', 'a0', self.expr.register))
    self.register = "a0"
    code += absmc.ret(current_method.get_label())
    return code

  # Check that the type of the expr is the same as the method return type
  def check(self):
    global curr_method_return
    # if doesn't return anything, make sure method signature is void type
    if self.expr == None:
      if current_method.rtype.compatible(Type('void')):
        curr_method_return = True
        return True
      else:
        print "{0}: Method '{1}' must return a value of type {2}".format(self.lines, current_method.name, current_method.rtype.typename)
        return False
    #otherwise, check the expression and make sure it's compatibe w/ method signature
    type_check = self.expr.check()
    if type_check:
      if self.expr.type.compatible(current_method.rtype):
        curr_method_return = True
        return True
      else:
        print "{0}: Cannot convert from {1} to {2}".format(self.lines, self.expr.type.typename, current_method.rtype.typename)
    return False

  def printout(self):
    print "Return(",
    if (self.expr != None):
      self.expr.printout()
    print ")"

class BlockStmt(Stmt):
  def __init__(self, stmtlist, lines):
    self.lines = lines
    self.stmtlist = [s for s in stmtlist if (s != None) and (not isinstance(s, SkipStmt))]

  def generate_code(self):
    #TODO: allocate variables and fields somewhere
    #might have to deal w/ activation record stuff?

    #generates code for each statement in the block
    code = [('# Start block',)]
    absmc.start_registers_scope()
    if self.stmtlist is not None:
      for stmt in self.stmtlist:
        code += stmt.generate_code()
    absmc.kill_registers_scope()
    code.append(('# End block',))
    return code
     
  def check(self):
    success = True
    for s in self.stmtlist:
      if not s.check():
        success = False
    return success

  def printout(self):
    print "Block(["
    if (len(self.stmtlist) > 0):
      self.stmtlist[0].printout()
    for s in self.stmtlist[1:]:
      print ", ",
      s.printout()
    print "])"

class BreakStmt(Stmt):
  def __init__(self, lines):
    self.lines = lines

  def generate_code(self):
    #can we guarentee that the there will always have a next label?
      #rodrigo said yes
    code = [("#break",)]
    #gen : jump out of the loop. to the next label
    break_label = absmc.get_break_label()
    if break_label is not None:
      code += absmc.jump(break_label)
      #generate label for the next basic block
      code += absmc.set_current_label(absmc.get_new_label(), False)
      return code
    else:
      raise CodeGenerationError('{0}: Unexpected break'.format(self.lines))

  def check(self):
    return True

  def printout(self):
    print "Break"
    
class ContinueStmt(Stmt):
  def __init__(self, lines):
    self.lines = lines

  def generate_code(self):
    #gen : jump back to the current label
    code = [("#continue",)]
    continue_label = absmc.get_continue_label()
    if continue_label is not None:
      code.append(('jmp', continue_label))
      code += absmc.jump(continue_label)

      #generate label for the next basic block
      code += absmc.set_current_label(absmc.get_new_label(), False)
      return code
    else:
      raise CodeGenerationError('{0}: Unexpected continue'.format(self.lines))

  def check(self):
    return True

  def printout(self):
    print "Continue"

class ExprStmt(Stmt):
  def __init__(self, expr, lines):
    self.lines = lines
    self.expr = expr

  def generate_code(self):
    code = self.expr.generate_code()
    self.register = self.expr.register
    return code

  def check(self):
    return self.expr.check()

  def printout(self):
    print "Expr(",
    self.expr.printout()
    print ")"
    
class SkipStmt(Stmt):
  def __init__(self, lines):
    self.lines = lines

  def generate_code(self):
    #nop
    code = []
    return code

  def check(self):
    return True

  def printout(self):
    print "Skip"
    

class Expr(object):
  def __repr__(self):
    return "Unknown expression"
  def printout(self):
    print self, 


class ConstantExpr(Expr):
  def __init__(self, kind, arg=None, lines=None):
    self.lines = lines
    self.kind = kind
    self.data = arg
    if (kind=='int'):
      self.int = arg
    elif (kind == 'float'):
      self.float = arg
    elif (kind == 'string'):
      self.string = arg
  
  def generate_code(self):
    #returns the constant value
    self.register = absmc.generate_temporary_register()
    code = [("#load constant : " + str(self.data),)]
    if self.kind == 'int':
      args = (self.register, str(self.data))
      code.append(('move_immed_i',) + args)
    elif self.kind == 'float':
      args = (self.register, str(self.data))
      code.append(('move_immed_f',) + args)
    elif self.kind == 'True':
      args = (self.register, '1')
      code.append(('move_immed_i',) + args)
    elif self.kind == 'False' or self.kind == 'null':
      args = (self.register, '0')
      code.append(('move_immed_i',) + args)
    return code

  def check(self):
    if self.kind == 'True' or self.kind == 'False':
      self.type = Type('boolean')
    else:
      self.type = Type(self.kind)
    return True

  def __repr__(self):
    s = "Unknown"
    if (self.kind == 'int'):
      s = "Integer-constant(%d)"%self.int
    elif (self.kind == 'float'):
      s = "Float-constant(%g)"%self.float
    elif (self.kind == 'string'):
      s = "String-constant(%s)"%self.string
    elif (self.kind == 'null'):
      s = "Null"
    elif (self.kind == 'True'):
      s = "True"
    elif (self.kind == 'False'):
      s = "False"
    return "Constant({0})".format(s)

class VarExpr(Expr):
  def __init__(self, var, lines):
    self.lines = lines
    self.var = var
  def __repr__(self):
    return "Variable(%d)"%self.var.id
  
  def generate_code(self):
    #return the register that corresponds w/ the variable
    self.register = self.var.register
    code = [("#var expr : " + self.var.name,)]
    return code

  def check(self):
    self.type = self.var.type
    return True

class UnaryExpr(Expr):
  def __init__(self, uop, expr, lines):
    self.lines = lines
    self.uop = uop
    self.arg = expr
  def __repr__(self):
    return "Unary({0}, {1})".format(self.uop, self.arg)

  def generate_code(self):
    #code = [" ".join(["#unary expr", self.uop, self.arg])]
    code = []
    code += self.arg.generate_code()
    neg_one = absmc.generate_temporary_register()
    self.register = absmc.generate_temporary_register()
    #TODO:we can check if its a constant, then just load it in
    #uminus -> just multiply by -1
    code.append(("move_immed_i", neg_one, "-1"))
    code.append(("imul", self.register, self.arg.register, neg_one))
    
    if self.uop == 'neg':
    #negation -> multiply by -1 and add 1
      code.append(("isub", self.register, self.register, neg_one))
    #print "UNARY"
    #print "\n".join(code)
    return code

  def check(self):
    if self.arg.check():
      if (self.uop == 'uminus' and (self.arg.type.compatible(Type('float')))\
       or (self.uop == 'neg' and self.arg.type.compatible(Type('boolean')))):
        self.type = self.arg.type
        return True
      else:
        print "{0}: Operator {1} not compatible with type {2}.".format(self.lines, self.uop, self.arg.type)
    self.type = Type('error')
    return False

    
class BinaryExpr(Expr):
  def __init__(self, bop, arg1, arg2, lines):
    self.lines = lines
    self.bop = bop
    self.arg1 = arg1
    self.arg2 = arg2

  def __repr__(self):
    return "Binary({0}, {1}, {2})".format(self.bop, self.arg1, self.arg2)

  def generate_code(self):
    code = [("#binary expr : " + self.bop,)]
    code += self.arg1.generate_code()
    code += self.arg2.generate_code()
    self.register = absmc.generate_temporary_register()
    if self.bop in ['add', 'sub', 'mul', 'div', 'gt', 'geq', 'lt', 'leq']:
      inst = 'i'+self.bop
      args = (self.register, self.arg1.register, self.arg2.register)
      code.append((inst,) + args)
    #deal w/ eq/neq operations
    elif self.bop in ['eq', 'neq']:
      # Do an isub, then branch depending on if the value is zero or not
      '''isub t0, t1, t2
         bnz t0, L1
         move_immed_i t0, 1 #success
         jmp L2
         L1: #fail label
         move_immed_i t0, 0 #failure
         L2: #rest_label
          rest of code'''
      '''isub t0 t1 t2
          bz t0, L1 # Fail label'''
      code.append(('isub', self.register, self.arg1.register, self.arg2.register))
      
      #curr_label = absmc.get_current_label()
      succ_label = absmc.get_new_label()
      fail_label = absmc.get_new_label()
      rest_label = absmc.get_new_label()

      #check failure
      if self.bop == 'eq':
        code += absmc.branch(self.register, fail_label, False)
      else:
        code += absmc.branch(self.register, fail_label, True)

      #if they're equal, 
      code += absmc.set_current_label(succ_label, True)
      #load 1
      code.append(('move_immed_i', self.register, '1'))
      #and jump
      code += absmc.jump(rest_label)

      #add in the fail label
      code += absmc.set_current_label(fail_label, False)
      #if they're not equal, load 0
      code.append(('move_immed_i', self.register, '0'))

      #load in the label to denote where rest of code goes
      code += absmc.set_current_label(rest_label, True)
    elif self.bop == 'and':
      '''
      x and y: 
        if(x!=0):
          if(y!=0):
        ###
        bz x, L1
        bz y, L1
        move_immed_i $t0, 1
        jmp L2
        L1: #XY = 0
        move_immed_i $t0, 0
        L2:
        <other stuff>
      '''
      #curr_label = absmc.get_current_label()
      x_succ_label = absmc.get_new_label()
      y_succ_label = absmc.get_new_label()
      fail_label = absmc.get_new_label()
      rest_label = absmc.get_new_label()
      
      #if x is false, jmp to failure
      #code.append(('bz', self.arg1.register, fail_label))
      code += absmc.branch(self.arg1.register, fail_label, True)
      
      #x is true, check y
      code += absmc.set_current_label(x_succ_label, True)
      
      #if y is false, jmp to failure
      #code.append(('bz', self.arg2.register, fail_label))
      code += absmc.branch(self.arg2.register, fail_label, True)

      #if x is true, y is true
      code += absmc.set_current_label(y_succ_label, True)
      #set to 1
      code.append(('move_immed_i', self.register, '1'))
      
      #skip pass the failures
      code += absmc.jump(rest_label)

      #starting the failures
      code += absmc.set_current_label(fail_label, False)
      #failure => set to 0
      code.append(('move_immed_i', self.register, '0'))

      #start the label denoting other stuff
      code += absmc.set_current_label(rest_label, True)
    elif self.bop == 'or':
      '''
      x or y
        if(x!=0):
        elif(y!=0):
        ###
        bnz x, L1
        bnz y, L1
        move_immed_i $t0, 0
        jmp L2
        L1:
        move_immed_i $t0, 1
        L2:
        <stuff>
      '''
      #curr_label = absmc.get_current_label()
      x_fail_label = absmc.get_new_label()
      y_fail_label = absmc.get_new_label()
      success_label = absmc.get_new_label()
      rest_label = absmc.get_new_label()

      #if x is true, jmp to success
      #code.append(('bnz', self.arg1.register, success_label))
      code += absmc.branch(self.arg1.register, success_label, False)
      
      #x is false, check y
      code += absmc.set_current_label(x_fail_label, True)
      
      #if y is true, jmp to success
      #code.append(('bnz', self.arg2.register, success_label))
      code += absmc.branch(self.arg2.register, success_label, False)

      #x and y are false,
      code += absmc.set_current_label(y_fail_label, True)
      #set to 0
      code.append(('move_immed_i', self.register, '0'))
      #skip pass the failures
      code += absmc.jump(rest_label)

      #starting the successes
      code += absmc.set_current_label(success_label, False)
      #failure => set to 1
      code.append(('move_immed_i', self.register, '1'))

      #start the label denoting other stuff
      code += absmc.set_current_label(rest_label, True)
    return code

  def check(self):
    arg1_check = self.arg1.check()
    arg2_check = self.arg2.check()
    
    if arg1_check and arg2_check:
      #arithmetic operation
      if self.bop in ['add', 'sub', 'mul', 'div']:
        #if both args are int, it's of type int
        if self.arg2.type.typename == 'int' and self.arg1.type.typename == 'int':
          self.type = Type('int')
          return True
        #else if they're of type int and float, it's of type float
        elif self.arg1.type.compatible(Type('float')) and self.arg2.type.compatible(Type('float')):
          self.type = Type('float')
          return True

      #boolean operation
      elif self.bop in ['and', 'or' ]:
        #if both args are of type boolean, it's of type boolean
        if self.arg1.type.compatible(Type('boolean')) and self.arg2.type.compatible(Type('boolean')):
          self.type = Type('boolean')
          return True

      #Arithmetic comparisons
      elif self.bop in ['gt', 'lt', 'geq', 'leq']:
        #if the're of type int or float, it's of type boolean
        if self.arg1.type.compatible(Type('float')) and self.arg2.type.compatible(Type('float')):
          self.type = Type('boolean')
          return True

      #Equality comparisons
      elif self.bop in ['eq', 'neq']:
        #if one arg is a subtype of another
        if self.arg1.type.compatible(self.arg2.type) or self.arg2.type.compatible(self.arg1.type):
          self.type = Type('boolean')
          return True
    
      print "{0}: Operator {1} undefined for type(s) {2}, {3}.".format(self.lines, self.bop, self.arg1.type, self.arg2.type)
    
    self.type = Type('error')
    return False

class AssignExpr(Expr):
  def __init__(self, lhs, rhs, lines):
    self.lines = lines
    self.lhs = lhs
    self.rhs = rhs
  def __repr__(self):
    print "lhs", self.lhs, "rhs", self.rhs
    print self.type
    return "Assign({0}, {1}, {2}, {3})".format(self.lhs, self.rhs, self.lhs.type, self.rhs.type)

  def generate_code(self):
    rhs = self.rhs.generate_code()
    code = [("#assign expr",)]

    post_auto = False
    #write the code to set up lhs and rhs
    if isinstance(self.rhs, AutoExpr) and self.rhs.when == 'post':
      post_auto = True
    else:
      code += rhs

    lhs = []
    #if lhs is a field, we want to store into heap
    if isinstance(self.lhs, FieldAccessExpr):
      lhs = self.lhs.generate_code(self.rhs.register)
      self.register = self.rhs.register
    else:
      lhs = self.lhs.generate_code()
      self.register = self.lhs.register
    code += lhs

    #move the value of the rhs into the lhs
    if not isinstance(self.lhs, FieldAccessExpr):
      args = (self.lhs.register, self.rhs.register)
      code.append(('move',) + args)

    if post_auto:
      code += rhs

    return code

  def check(self):
    #check if they are None first
    if self.lhs is None or self.rhs is None:
      self.type = Type('error')
      return False

    #if lhs and rhs are type correct and rhs < lhs
    lhs_check = self.lhs.check()
    rhs_check = self.rhs.check()

    if lhs_check and rhs_check:
      if self.rhs.type.compatible(self.lhs.type):
        self.type = self.rhs.type
        return True
      else:
        print "{0}: Cannot assign argument of type {1} to variable/field of type {2}".format(self.lines, self.rhs.type, self.lhs.type)

    self.type = Type('error')
    return False
    
    
class AutoExpr(Expr):
  def __init__(self, arg, oper, when, lines):
    self.lines = lines
    self.arg = arg
    self.oper = oper
    self.when = when

  def __repr__(self):
    return "Auto({0}, {1}, {2})".format(self.arg, self.oper, self.when)

  def generate_code(self):
    code = self.arg.generate_code()
    code += [("#auto expression",)]
    self.register = self.arg.register
    #make a register holding 1
    one_reg = absmc.generate_temporary_register()
    code.append(('move_immed_i', one_reg, '1'))

    #figure out the operations
    if self.oper == 'inc':
      inst = 'iadd' 
    elif self.oper == 'dec':
      inst = 'isub'
    else:
      raise CodeGenerationError('{0}: Invalid Auto Operation'.format(self.lines))

    code.append((inst, self.register, self.register, one_reg))
    return code

  def check(self):
    #if arg is subtype of int
    if self.arg.check() and self.arg.type.compatible(Type('float')):
      self.type = self.arg.type
      return True

    self.type = 'error'
    if not self.arg.type.compatible(Type('error')):
      print "{0}: The operator {1} is undefined for the argument type {2}".format(self.lines, self.oper, self.arg.type)
    return False
    
class FieldAccessExpr(Expr):
  def __init__(self, base, fname, lines):
    self.lines = lines
    self.base = base
    self.fname = fname
  def __repr__(self):
    return "Field-access({0}, {1}, {2})".format(self.base, self.fname, self.field.id)

  #TODO: just set self.register to be value reg. avoids an extra move instruction
  def generate_code(self, value=None):
    #create a register and have it point to the sap+offset?
    offset_reg = absmc.generate_temporary_register()
    code = [("#field access : " + self.fname,)]
    code += self.base.generate_code()

    #grabs the offset and stick it into $t0
    code.append(('move_immed_i', offset_reg, str(self.field.offset)))
    
    #check if static or instance
    if self.field.storage == 'static':
      #NOTE : we reuse the register containing the offset to do hload
      #load sap+offset and stick it into $t0
      if value is None:
        dest = absmc.generate_temporary_register()
        code.append(('hload', dest, 'sap', offset_reg))
        self.register = dest
      #if a value is specified, we want to store, not load
      else:
        code.append(('hstore', 'sap', offset_reg, value))
        self.register = value
    else:
      if value is None:
        dest = absmc.generate_temporary_register()
        #load base+offset and set it into $t0
        code.append(('hload', dest, self.base.register, offset_reg))
        self.register = dest
      else:
        #if a value is specified, we want to store, not load
        code.append(('hstore', self.base.register, offset_reg, value))
        self.register = value

    return code

  def check(self):
    base_check = self.base.check()
    if base_check:
      if self.base.type.kind == 'class' or self.base.type.kind == 'class-literal':
        cls = lookup(classtable, self.base.type.typename)
        #if actual class doesn't exist
        if cls is None:
          print "{0}: Class '{1}' does not exist".format(self.lines, self.base.type.typename)
          self.type = Type('error')
          return False
        #loop through super classes
        while cls is not None:
          field = lookup(cls.fields, self.fname)
          #can't find field, go look in super
          if field is None:
            cls = cls.superclass
            continue
          if (field.storage == 'instance' and self.base.type.kind == 'class') or \
           (field.storage == 'static' and self.base.type.kind == 'class-literal'):
            if field.inclass == current_class or field.visibility == 'public':
              self.type = field.type
              self.field = field
              return True
            else:
              print "{0}: Cannot access private member in class '{1}'".format(self.lines, field.inclass.name)
              self.type = Type('error')
              return False
          elif field.storage == 'static' and self.base.type.kind == 'class':
            print "{0}: Cannot access static field '{1}' as an instance field".format(self.lines, self.fname)
            self.type = Type('error')
            return False
          else:
            print "{0}: Cannot access instance field '{1}' as a static field".format(self.lines, self.fname)
            self.type = Type('error')
            return False

        print "{0}: Reference '{1}' does not exist.".format(self.lines, self.fname)
        self.type = Type('error')
        return False
      else:
        print "{0}: '{1}' is not a class type".format(self.lines, self.base.type.typename)

    self.type = Type('error')
    return False

    
class MethodInvocationExpr(Expr):
  def __init__(self, field, args, lines):
    self.lines = lines
    self.base = field.base
    self.mname = field.fname
    self.args = args
  def __repr__(self):
    return "Method-call({0}, {1}, {2}, {3})".format(self.base, self.mname, self.args, self.method.id)

  def generate_code(self):
    code = [("#calling method : " + self.method.name,)]
    code += self.base.generate_code()
    #call label (M_<method_name>_<method_id>)
    #TODO: check arguments if they involve auto expressions. if post inc, do it after moving them to a registers
    
    #save all of caller's a registers
    num_regs_to_save = len(current_method.vars.get_params())

    # Figure out if a0 needs to be saved or not
    if isinstance(current_method, Constructor) or current_method.storage == 'instance':
      num_regs_to_save += 1
    for i in range(num_regs_to_save):
      code.append(('save', 'a'+ str(i)))

    absmc.reset_argument_register(self.method.storage)
    #set up the a registers
    if self.method.storage == 'instance':
      # if the base is not super or this, then it needs to be moved to a0
      if not (isinstance(self.base, ThisExpr) or isinstance(self.base, SuperExpr)):
        code.append(('move', 'a0', self.base.register))

    arg_setup = []
    post_auto_args = []
    for arg in self.args:
      arg_code = arg.generate_code()
      if isinstance(arg, AutoExpr) and arg.when == 'post':
        post_auto_args += arg_code
      elif isinstance(arg, AutoExpr) and arg.when == 'pre':
        code = arg_code + code
      else:
        code += arg_code
      curr_reg = absmc.generate_argument_register()
      curr_value = arg.register
      #this prevents moving a register into the same register
      if curr_reg == curr_value:
        continue
      if absmc.is_prev_arg(curr_value, curr_reg):
        #save the original $a value
        temp_reg = absmc.generate_temporary_register()
        #move the prev $a register into a $t register
        code.append(('move', temp_reg, curr_value))
        curr_value = temp_reg
      arg_setup.append(('move', curr_reg, curr_value))
    #add the arg setup stuff into code
    code += arg_setup

    #save temp registers
    for t in absmc.get_live_registers():
      code.append(('save', t))

    #actually call the method
    code += absmc.call(self.method.get_label())

    #restore all of the original temp registers
    for t in reversed(absmc.get_live_registers()):
      code.append(('restore', t))

    #save the return value
    self.register = absmc.generate_temporary_register()
    code.append(('move', self.register, 'a0'))

    #restore all the original arguments
    for i in reversed(range(num_regs_to_save)):
      code.append(('restore', 'a' + str(i)))

    code += post_auto_args

    return code

  def check(self):
    self.method = None
    base_check = self.base.check()
    if base_check:
      basetype = self.base.type.kind
      if basetype == 'class' or basetype == 'class-literal':
        cls = lookup(classtable, self.base.type.typename)
        if cls is None:
          print "{0}: Class '{1}' does not exist".format(self.lines, self.base.type.typename)
          self.type = Type('error')
          return False
        while cls is not None:
          found_exact_method = False
          mult_applicable = False
          for method in cls.methods:
            if self.mname == method.name \
              and (method.inclass == current_class or method.visibility == 'public')\
              and ((basetype == 'class' and method.storage == 'instance') \
                or (basetype == 'class-literal' and method.storage == 'static')):
              #check arguments
              method_params = method.vars.get_params()
              params_match = True
              exact_match = True
              
              if len(method_params) == len(self.args):
                for i in range(0, len(method_params)):
                  valid_arg = self.args[i].check() 
                  #check if arg type is exactly the same as method's curr param type
                  if not valid_arg \
                    or (self.args[i].type.typename != method_params[i].type.typename):
                    exact_match = False
                  #check if curr arg is compatible w/ curr method's curr param
                  if not valid_arg \
                    or not self.args[i].type.compatible(method_params[i].type):
                    params_match = False
                    break
                #check if all params had matched
                if params_match:
                  #if a previous method was found, but neither methods were exact match, flag it
                  if self.method is not None and not exact_match and not found_exact_method:
                    mult_applicable = True
                  #if a previous method was found and this was an exact match
                  elif self.method is not None and exact_match:
                    #if the prev. method was also an exact match, error
                    if found_exact_method:
                      print "{0}: There are multiple applicable methods '{1}'.".format(self.lines, self.mname)
                      self.type = Type('error')
                      self.method = None
                      return False
                    #else, reset mult_applicable, and flag found_exact_method
                    mult_applicable = False
                    found_exact_method = True
                    self.method = method
                  #found first match
                  elif self.method is None:
                    self.method = method
                    self.type = method.rtype
                    if exact_match:
                      found_exact_method = True
          if mult_applicable:
            print "{0}: There are multiple applicable methods '{1}'.".format(self.lines, self.mname)
            self.type = Type('error')
            return False
          if self.method is not None:
            return True
          cls = cls.superclass

        if self.method is None:
          print "{0}: There are no applicable methods '{1}'.".format(self.lines, self.mname)
        
      else:
        print "{0}: '{1}' is not a class type".format(self.lines, self.base.type.typename)

    self.type = Type('error')
    self.method = None
    return False
    
class NewObjectExpr(Expr):
  def __init__(self, cref, args, lines):
    self.lines = lines
    self.classref = cref
    self.args = args
  def __repr__(self):
    return "New-object({0}, {1}, {2})".format(self.classref.name, self.args, self.constructor.id)

  def generate_code(self):
    code = [("#creating a new object : " + self.constructor.name,)]
    
    #save all of caller's a registers
    num_regs_to_save = len(current_method.vars.get_params())

    # Figure out if a0 needs to be saved or not
    if isinstance(current_method, Constructor) or current_method.storage == 'instance':
      num_regs_to_save += 1
    for i in range(num_regs_to_save):
      code.append(('save', 'a' + str(i)))

    absmc.reset_argument_register('instance')
    #set up the a registers
    
    #set up $a0 here
    # Count the number of instance fields in the class
    num_instance = 0
    for field in self.classref.fields.values():
      if field.storage != 'static':
        num_instance += 1

    size_reg = absmc.generate_temporary_register()
    code.append(('move_immed_i', size_reg, str(num_instance)))
    #NOTE : we are reusing the register containing # of heap cells for halloc'ing the obj
    self.register = absmc.generate_temporary_register()
    code.append(('halloc', self.register, size_reg))
    arg_setup = []
    post_auto_args = []
    arg_setup.append(('move', 'a0', self.register))
    for arg in self.args:
      arg_code = arg.generate_code()
      if isinstance(arg, AutoExpr) and arg.when == 'post':
        post_auto_args += arg_code
      elif isinstance(arg, AutoExpr) and arg.when == 'pre':
        code = arg_code + code
      else:
        code += arg_code

      curr_reg = absmc.generate_argument_register()
      curr_value = arg.register
      #this prevents moving a register into the same register
      if curr_reg == curr_value:
        continue
      if absmc.is_prev_arg(curr_value, curr_reg):
        #save the original $a value
        temp_reg = absmc.generate_temporary_register()
        #move the prev $a register into a $t register
        code.append(('move', temp_reg, curr_value))
        curr_value = temp_reg
      arg_setup.append(('move', curr_reg, curr_value))
    #add the arg setup stuff into code
    code += arg_setup


    #save temp registers
    for t in absmc.get_live_registers():
      code.append(('save', t))

    #actually call the method
    code += absmc.call(self.constructor.get_label())
    
    #restore all of the original temp registers
    for t in reversed(absmc.get_live_registers()):
      code.append(('restore', t))
    #restore all the original arguments
    for i in reversed(range(num_regs_to_save)):
      code.append(('restore', 'a' + str(i)))

    code += post_auto_args
    #print 'NEW OBJECT INVOCATION'
    #print '\n'.join(code)

    return code

  def check(self):
    '''look for constructor that accepts args of this type'''
    self.constructor = None
    self.type = None
    
    #flag for if mult. constr. can be used
    mult_applicable = False
    #flag for if we found an exact constructor
    found_exact_construct = False
    #loop through class's constructors
    for constructor in self.classref.constructors:
      #if constructor is private and it's not used in scope of class, skip constr.
      if current_class.name != self.classref.name \
        and constructor.visibility == 'private':
        continue
      #loop through arguments
      exact_match = True
      args_match = True
      curr_args = constructor.vars.get_params()
      if len(curr_args) != len(self.args):
        continue
      for i in range(0, len(self.args)):
        valid_arg = self.args[i].check() 
        #check if arg type is exactly the same as method's curr param type
        if not valid_arg \
          or (self.args[i].type.typename != curr_args[i].type.typename):
          exact_match = False
        #check if curr arg is compatible w/ curr method's curr param
        if not valid_arg \
          or not self.args[i].type.compatible(curr_args[i].type):
          args_match = False
          break
      #check if all params had matched
      if args_match:
        #if a previous constr. was found, but neither constr. were exact match, flag it
        if self.constructor is not None and not exact_match and not found_exact_constructor:
          mult_applicable = True
        #if a previous constr. was found and this was an exact match
        elif self.constructor is not None and exact_match:
          #if the prev. constructor was also an exact match, error
          if found_exact_constructor:
            print "{0}: Multiple applicable constructors for class '{1}' found.".format(self.lines, self.classref.name)
            self.type = Type('error')
            self.constructor = None
            return False
          #else, reset mult_applicable, and flag found_exact_constructor
          mult_applicable = False
          found_exact_constructor = True
          self.constructor = constructor
        #first time we find a match
        elif self.constructor is None:
          self.constructor = constructor
          self.type = Type(self.classref.name)
          if exact_match:
            found_exact_constructor = True
    if mult_applicable:
      print "{0}: Multiple applicable constructors for class '{1}' found.".format(self.lines, self.classref.name)
    elif self.constructor is not None:
      self.type = Type(self.classref.name)
      return True
    elif self.constructor is None:
      print "{0}: No applicable constructor for class '{1}' found.".format(self.lines, self.classref.name)
    self.constructor = None
    self.type = Type('error')
    return False

class ThisExpr(Expr):
  def __init__(self, lines):
    self.lines = lines
  def __repr__(self):
    return "This"
  
  def generate_code(self):
    self.register = "a0"
    code = [("#this expr",)]
    return code

  def check(self):
    if is_constructor or current_method.storage != 'static':
      self.type = Type(current_class.name)
      return True
    print "{0}: Cannot use this in a static context".format(self.lines)
    self.type = Type('error')
    return False

class SuperExpr(Expr):
  def __init__(self, lines):
    self.lines = lines
  def __repr__(self):
    return "Super"

  def generate_code(self):
    code = [('# super expr',)]
    self.register = "a0"
    return code

  def check(self):
    #check if current class has a super class
    if current_class.superclass is not None and (is_constructor or current_method.storage != 'static'):
      self.type = Type(current_class.superclass.name)
      return True
    elif (not is_constructor) and current_method.storage == 'static':
      print "{0}: Cannot use super in a static context".format(self.lines)
    else:
      print "{0}: There is no superclass for this class".format(self.lines)

    self.type = Type('error')
    return False
    
class ClassReferenceExpr(Expr):
  def __init__(self, cref, lines):
    self.lines = lines
    self.classref = cref
  def __repr__(self):
    return "ClassReference({0})".format(self.classref.name)

  def generate_code(self):
    code = []
    return code

  def check(self):
    self.type = Type(self.classref.name, True)
    return True
    
class ArrayAccessExpr(Expr):
  def __init__(self, base, index, lines):
    self.lines = lines
    self.base = base
    self.index = index
  def __repr__(self):
    return "Array-access({0}, {1})".format(self.base, self.index)
    
class NewArrayExpr(Expr):
  def __init__(self, basetype, args, lines):
    self.lines = lines
    self.basetype = basetype
    self.args = args
  def __repr__(self):
    return "New-array({0}, {1})".format(self.basetype, self.args)

