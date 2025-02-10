#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Abstract syntax tree for ChironLang

class AST(object):
    pass


# --Instruction Classes-----------------------------------------------

class Instruction(AST):
    def __init__(self):
        self.writeVariables = set()
        self.readVariables = set()

    def renameReadVariable(self, oldname, newname):
        pass

    def renameWriteVariable(self, oldname, newname):
        pass

    def getWriteVariables(self):
        return self.writeVariables
    
    def getReadVariables(self):
        return self.readVariables


class AssignmentCommand(Instruction):
    def __init__(self, leftvar, rexpr):
        super().__init__()
        self.lvar = leftvar
        self.rexpr = rexpr
        self.writeVariables.update(self.lvar.getVariables())
        self.readVariables.update(self.rexpr.getVariables())

    def renameWriteVariable(self, oldname, newname):
        if oldname in self.lvar.variables:
            self.lvar = Var(newname)
            self.lvar.variables = set([newname])
            self.writeVariables = set([newname])

    def renameReadVariable(self, oldname, newname):
        if oldname in self.rexpr.variables:
            self.rexpr.renameVariable(oldname, newname)
            self.readVariables = self.rexpr.getVariables()

    def __str__(self):
        return self.lvar.__str__() + " = " + self.rexpr.__str__()


class ConditionCommand(Instruction):
    def __init__(self, condition):
        super().__init__()
        self.cond = condition
        self.readVariables.update(self.cond.getVariables())

    def renameWriteVariable(self, oldname, newname):
        return

    def renameReadVariable(self, oldname, newname):
        if oldname in self.cond.variables:
            self.cond.renameVariable(oldname, newname)
            self.readVariables = self.cond.getVariables()

    def __str__(self):
        return self.cond.__str__()


class AssertCommand(Instruction):
    def __init__(self, condition):
        super().__init__()
        self.cond = condition
        self.readVariables.update(self.cond.getVariables())

    def renameWriteVariable(self, oldname, newname):
        return

    def renameReadVariable(self, oldname, newname):
        if oldname in self.cond.variables:
            self.cond.renameVariable(oldname, newname)
            self.readVariables = self.cond.getVariables

    def __str__(self):
        return "assert: " + self.cond.__str__()

class MoveCommand(Instruction):
    def __init__(self, motion, expr):
        super().__init__()
        self.direction = motion
        self.expr = expr
        self.readVariables.update(self.expr.getVariables())

    def renameWriteVariable(self, oldname, newname):
        return

    def renameReadVariable(self, oldname, newname):
        print("renameReadVariable: " + oldname + " to " + newname + " in " + self.__str__())
        self.expr.renameVariable(oldname, newname)
        self.readVariables = self.expr.getVariables()

    def __str__(self):
        return self.direction + " " + self.expr.__str__()


class PenCommand(Instruction):
    def __init__(self, penstat):
        super().__init__()
        self.status = penstat

    def __str__(self):
        return self.status

class GotoCommand(Instruction):
    def __init__(self, x, y):
        super().__init__()
        self.xcor = x
        self.ycor = y
        self.readVariables.update(self.xcor.getVariables())
        self.readVariables.update(self.ycor.getVariables())

    def renameWriteVariable(self, oldname, newname):
        return

    def renameReadVariable(self, oldname, newname):
        self.readVariables = set()
        if oldname in self.xcor.variables:
            self.xcor.renameVariable(oldname, newname)
            self.readVariables.update(self.xcor.getVariables())
        if oldname in self.ycor.variables:
            self.ycor.renameVariable(oldname, newname)
            self.readVariables.update(self.ycor.getVariables())

    def __str__(self):
        return "goto " + str(self.xcor) + " " + str(self.ycor)

class NoOpCommand(Instruction):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "NOP"

class PauseCommand(Instruction):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "pause"

# Phi function for SSA form
class PhiAssignmentCommand(Instruction):
    def __init__(self, lvar, varlist):
        super().__init__()
        self.lvar = lvar
        self.varlist = varlist
        self.writeVariables.update(self.lvar.getVariables())
        self.readVariables.update(set(self.varlist))
    
    def renameWriteVariable(self, oldname, newname):
        raise NotImplementedError
    
    def renameReadVariable(self, oldname, newname):
        raise NotImplementedError

    def __str__(self):
        output = self.lvar.__str__() + " = PHI("
        for var in self.varlist:
            output += var.__str__() + ", "
        return output + ")"
    
        
class Expression(AST):
    def __init__(self):
        self.variables = set()

    def renameVariable(self, oldname, newname):
        pass

    def getVariables(self):
        return self.variables


# --Arithmetic Expressions--------------------------------------------

class ArithExpr(Expression):
    def __init__(self):
        super().__init__()


class BinArithOp(ArithExpr):
    def __init__(self, expr1, expr2, opsymbol):
        super().__init__()
        self.lexpr = expr1
        self.rexpr = expr2
        self.symbol = opsymbol
        
        self.variables.update(self.lexpr.variables)
        self.variables.update(self.rexpr.variables)

    def renameVariable(self, oldname, newname):
        self.variables = set()
        if oldname in self.lexpr.variables:
            self.lexpr.renameVariable(oldname, newname)
            self.variables.update(self.lexpr.getVariables())
        if oldname in self.rexpr.variables:
            self.rexpr.renameVariable(oldname, newname)
            self.variables.update(self.rexpr.getVariables())

    def __str__(self):
        return "(" + self.lexpr.__str__() + " " + self.symbol + " " + self.rexpr.__str__() + ")"


class UnaryArithOp(ArithExpr):
    def __init__(self, expr1, opsymbol):
        super().__init__()
        self.expr = expr1
        self.symbol = opsymbol
        self.variables.update(expr1.variables)

    def renameVariable(self, oldname, newname):
        if oldname in self.expr.variables:
            self.expr.renameVariable(oldname, newname)
            self.variables = self.expr.getVariables()

    def __str__(self):
        return self.symbol + self.expr.__str__()


class UMinus(UnaryArithOp):
    def __init__(self, lexpr):
        super().__init__(lexpr, "-")


class Sum(BinArithOp):
    def __init__(self, lexpr, rexpr):
        super().__init__(lexpr, rexpr, "+")


class Diff(BinArithOp):
    def __init__(self, lexpr, rexpr):
        super().__init__(lexpr, rexpr, "-")


class Mult(BinArithOp):
    def __init__(self, lexpr, rexpr):
        super().__init__(lexpr, rexpr, "*")

class Div(BinArithOp):
    def __init__(self, lexpr, rexpr):
        super().__init__(lexpr, rexpr, "/")


# --Boolean Expressions-----------------------------------------------

class BoolExpr(Expression):
    def __init__(self):
        super().__init__()


class BinCondOp(BoolExpr):
    def __init__(self, expr1, expr2, opsymbol):
        super().__init__()
        self.lexpr = expr1
        self.rexpr = expr2
        self.symbol = opsymbol
        self.variables.update(self.lexpr.variables)
        self.variables.update(self.rexpr.variables)

    def renameVariable(self, oldname, newname):
        self.variables = set()
        print("renameVariable: " + oldname + " to " + newname + " in " + self.__str__())
        if oldname in self.lexpr.variables:
            self.lexpr.renameVariable(oldname, newname)
            self.variables.update(self.lexpr.getVariables())
        if oldname in self.rexpr.variables:
            self.rexpr.renameVariable(oldname, newname)
            self.variables.update(self.rexpr.getVariables())

    def __str__(self):
        return "(" + self.lexpr.__str__() + ' ' + self.symbol + ' ' + self.rexpr.__str__() + ")"


class AND(BinCondOp):
    def __init__(self, expr1, expr2):
        super().__init__(expr1, expr2, "and")

class OR(BinCondOp):
    def __init__(self, expr1, expr2):
        super().__init__(expr1, expr2, "or")


class LT(BinCondOp):
    def __init__(self, expr1, expr2):
        super().__init__(expr1, expr2, "<")


class GT(BinCondOp):
    def __init__(self, expr1, expr2):
        super().__init__(expr1, expr2, ">")


class LTE(BinCondOp):
    def __init__(self, expr1, expr2):
        super().__init__(expr1, expr2, "<=")


class GTE(BinCondOp):
    def __init__(self, expr1, expr2):
        super().__init__(expr1, expr2, ">=")


class EQ(BinCondOp):
    def __init__(self, expr1, expr2):
        super().__init__(expr1, expr2, "==")


class NEQ(BinCondOp):
    def __init__(self, expr1, expr2):
        super().__init__(expr1, expr2, "!=")


class NOT(BoolExpr):
    def __init__(self, uexpr):
        super().__init__()
        self.expr = uexpr
        self.symbol = "not"
        self.variables.update(self.expr.variables)

    def renameVariable(self, oldname, newname):
        if oldname in self.expr.variables:
            self.expr.renameVariable(oldname, newname)
            self.variables = self.expr.getVariables()

    def __str__(self):
        return self.symbol + self.expr.__str__()


class PenStatus(BoolExpr):
    def __init__(self):
        super().__init__()
        pass

    def __str__(self):
        return "pendown?"


class BoolTrue(BoolExpr):
    def __init__(self):
        super().__init__()
        pass

    def __str__(self):
        return "True"


class BoolFalse(BoolExpr):
    def __init__(self):
        super().__init__()
        pass

    def __str__(self):
        return "False"


class Value(Expression):
    def __init__(self):
        super().__init__()


class Num(Value):
    def __init__(self, v):
        super().__init__()
        self.val = int(v)

    def renameVariable(self, oldname, newname):
        return

    def __str__(self):
        return str(self.val)


class Var(Value):
    def __init__(self, vname):
        super().__init__()
        self.varname = vname
        self.variables.add(vname)

    def renameVariable(self, oldname, newname):
        newvar = Var(newname)
        if self.varname == oldname:
            self.__dict__.update(newvar.__dict__)

    def __str__(self):
        return self.varname
