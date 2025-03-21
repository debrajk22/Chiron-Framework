'''
This file is used to convert the SSA IR to SMT-LIB format.
'''
import z3
from ChironSSA import ChironSSA
from cfg import cfgBuilder

class BMC:
    def __init__(self, cfg):
        self.solver = z3.Solver()
        self.cfg = cfg

        self.bbConditions = {} # bbConditions[bb] = condition for bb
        for bb in self.cfg:
            self.bbConditions[bb] = None

        self.buildConditions()

        self.varConditions = {} # varConditions[var] = condition for var
        for bb in self.cfg.nodes():
            for stmt, _ in bb.instrlist:
                if isinstance(stmt, (ChironSSA.PhiCommand, ChironSSA.AssignmentCommand, ChironSSA.SinCommand, ChironSSA.CosCommand, ChironSSA.DegToRadCommand)):
                    self.varConditions[stmt.lvar.name] = self.bbConditions[bb] if self.bbConditions[bb] is not None else z3.BoolVal(True)

    def buildConditions(self):
        topological_order = list(self.cfg.get_topological_order())
        start = topological_order[0]
        start.set_condition(z3.BoolVal(True))
        topological_order.pop(0)
        for node in topological_order:
            for pred in self.cfg.predecessors(node):
                instr = pred.instrlist[-1][0]
                current_cond = node.get_condition()
                if isinstance(instr, ChironSSA.ConditionCommand) and type(instr.cond) == ChironSSA.Var:
                    cond = z3.Bool(instr.cond.name)
                    label = self.cfg.get_edge_label(pred, node)
                    if label == 'Cond_True':
                        node.set_condition(z3.Or(current_cond, z3.And(pred.get_condition(), cond)))
                    elif label == 'Cond_False':
                        node.set_condition(z3.Or(current_cond, z3.And(pred.get_condition(), z3.Not(cond))))
                else:
                    node.set_condition(z3.Or(pred.get_condition(), current_cond))
            
            t = z3.Tactic('ctx-simplify').apply(node.get_condition()).as_expr()
            node.set_condition(t)
            self.bbConditions[node] = node.get_condition()

    def convertSSAtoSMT(self):
        assert_conditions = z3.BoolVal(True)
        for bb in self.cfg.nodes():
            for stmt, _ in bb.instrlist:
                if isinstance(stmt, ChironSSA.PhiCommand):
                    lvar = z3.Int(stmt.lvar.name)
                    if stmt.lvar.name.startswith((":turtleX$", ":turtleY$", ":__delta_x$", ":__delta_y$", ":turtleThetaRad$", ":__cos_theta$", ":__sin_theta$")):
                        lvar = z3.Real(stmt.lvar.name)
                    rvars = [z3.Real(rvar.name) if rvar.name.startswith((":turtleX$", ":turtleY$", ":__delta_x$", ":__delta_y$", ":turtleThetaRad$", ":__cos_theta$", ":__sin_theta$")) else z3.Int(rvar.name) for rvar in stmt.rvars]
                    
                    rhs_expr = rvars[0]
                    for i in range(1, len(stmt.rvars)):
                        rhs_expr = z3.If(self.varConditions[stmt.rvars[i].name], rvars[i], (rhs_expr))

                    if self.varConditions[stmt.lvar.name] not in (None, True, False):
                        self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == rhs_expr))
                    elif self.varConditions[stmt.lvar.name] is not False:
                        self.solver.add(lvar == rhs_expr)
    
                elif isinstance(stmt, ChironSSA.AssignmentCommand):
                    lvar = None
                    rvar1 = ChironSSA.Unused()
                    rvar2 = ChironSSA.Unused()

                    if stmt.op in ["+", "-", "*", "/", "%"]:
                        lvar = z3.Int(stmt.lvar.name)
                        if isinstance(stmt.rvar1, ChironSSA.Var):
                            rvar1 = z3.Int(stmt.rvar1.name)
                        elif isinstance(stmt.rvar1, ChironSSA.Num):
                            rvar1 = z3.IntVal(stmt.rvar1.value)
                        if isinstance(stmt.rvar2, ChironSSA.Var):
                            rvar2 = z3.Int(stmt.rvar2.name)
                        elif isinstance(stmt.rvar2, ChironSSA.Num):
                            rvar2 = z3.IntVal(stmt.rvar2.value)
                    elif stmt.op in ["<", ">", "<=", ">=", "==", "!="]:
                        lvar = z3.Bool(stmt.lvar.name)
                        if isinstance(stmt.rvar1, ChironSSA.Var):
                            rvar1 = z3.Int(stmt.rvar1.name)
                        elif isinstance(stmt.rvar1, ChironSSA.Num):
                            rvar1 = z3.IntVal(stmt.rvar1.value)
                        if isinstance(stmt.rvar2, ChironSSA.Var):
                            rvar2 = z3.Int(stmt.rvar2.name)
                        elif isinstance(stmt.rvar2, ChironSSA.Num):
                            rvar2 = z3.IntVal(stmt.rvar2.value)
                    elif stmt.op in ["and", "or"]:
                        lvar = z3.Bool(stmt.lvar.name)
                        if isinstance(stmt.rvar1, ChironSSA.Var):
                            rvar1 = z3.Bool(stmt.rvar1.name)
                        elif isinstance(stmt.rvar1, ChironSSA.BoolTrue):
                            rvar1 = z3.BoolVal(True)
                        if isinstance(stmt.rvar2, ChironSSA.Var):
                            rvar2 = z3.Bool(stmt.rvar2.name)
                        elif isinstance(stmt.rvar2, ChironSSA.BoolFalse):
                            rvar2 = z3.BoolVal(False)
                    elif stmt.op == "not":
                        lvar = z3.Bool(stmt.lvar.name)
                        if isinstance(stmt.rvar2, ChironSSA.Var):
                            rvar2 = z3.Bool(stmt.rvar2.name)
                        elif isinstance(stmt.rvar2, ChironSSA.BoolTrue):
                            rvar2 = z3.BoolVal(True)
                        elif isinstance(stmt.rvar2, ChironSSA.BoolFalse):
                            rvar2 = z3.BoolVal(False)
                    elif stmt.op == "":
                        continue
                    else:
                        raise Exception("Unknown SSA instruction")
                    
                    if isinstance(stmt.lvar, ChironSSA.Var) and stmt.lvar.name.startswith((":turtleX$", ":turtleY$", ":__delta_x$", ":__delta_y$", ":turtleThetaRad$", ":__cos_theta$", ":__sin_theta$")):
                        lvar = z3.Real(stmt.lvar.name)
                    if isinstance(stmt.rvar1, ChironSSA.Var) and stmt.rvar1.name.startswith((":turtleX$", ":turtleY$", ":__delta_x$", ":__delta_y$", ":turtleThetaRad$", ":__cos_theta$", ":__sin_theta$")):
                        rvar1 = z3.Real(stmt.rvar1.name)
                    if isinstance(stmt.rvar2, ChironSSA.Var) and stmt.rvar2.name.startswith((":turtleX$", ":turtleY$", ":__delta_x$", ":__delta_y$", ":turtleThetaRad$", ":__cos_theta$", ":__sin_theta$")):
                        rvar2 = z3.Real(stmt.rvar2.name)
    
                    if stmt.op == "+":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 + rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 + rvar2))
                    elif stmt.op == "-":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 - rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 - rvar2))
                    elif stmt.op == "*":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 * rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 * rvar2))
                    elif stmt.op == "/":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 / rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 / rvar2))
                    elif stmt.op == "%":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 % rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 % rvar2))
                    elif stmt.op == "<":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 < rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 < rvar2))
                    elif stmt.op == ">":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 > rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 > rvar2))
                    elif stmt.op == "<=":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 <= rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 <= rvar2))
                    elif stmt.op == ">=":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 >= rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 >= rvar2))
                    elif stmt.op == "==":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 == rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 == rvar2))
                    elif stmt.op == "!=":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar1 != rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == (rvar1 != rvar2))
                    elif stmt.op == "and":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == z3.And(rvar1, rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == z3.And(rvar1, rvar2))
                    elif stmt.op == "or":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == z3.Or(rvar1, rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == z3.Or(rvar1, rvar2))
                    elif stmt.op == "not":
                        if self.varConditions[stmt.lvar.name] not in (None, True, False):
                            self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == z3.Not(rvar2)))
                        elif self.varConditions[stmt.lvar.name] is not False:
                            self.solver.add(lvar == z3.Not(rvar2))
    
                elif isinstance(stmt, ChironSSA.AssertCommand):
                    cond = None
                    if isinstance(stmt.cond, ChironSSA.BoolTrue):
                        cond = z3.BoolVal(True)
                    elif isinstance(stmt.cond, ChironSSA.BoolFalse):
                        cond = z3.BoolVal(False)
                    elif isinstance(stmt.cond, ChironSSA.Var):
                        cond = z3.Bool(stmt.cond.name)
                    assert_conditions = z3.And(assert_conditions, cond)

                elif isinstance(stmt, ChironSSA.DegToRadCommand):
                    rvar = None
                    if isinstance(stmt.rvar, ChironSSA.Var):
                        rvar = z3.Real(stmt.rvar.name)
                    elif isinstance(stmt.rvar, ChironSSA.Num):
                        rvar = z3.RealVal(stmt.rvar.value)
                    lvar = z3.Real(stmt.lvar.name)
                    if self.varConditions[stmt.lvar.name] not in (None, True, False):
                        self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], lvar == (rvar * 3.14 / 180)))
                    elif self.varConditions[stmt.lvar.name] is not False:
                        self.solver.add(lvar == (rvar * 3.14 / 180))

                elif isinstance(stmt, ChironSSA.CosCommand):         # Using taylor series
                    rvar = z3.Real(stmt.rvar.name)
                    rhs_expr = 1 - (rvar ** 2) / 2 + (rvar ** 4) / 24
                    # rhs_expr = 1 - (rvar ** 2) / 2 + (rvar ** 4) / 24 - (rvar ** 6) / 720 + (rvar ** 8) / 40320 - (rvar ** 10) / 3628800 + (rvar ** 12) / 479001600 - (rvar ** 14) / 87178291200 + (rvar ** 16) / 20922789888000 - (rvar ** 18) / 6402373705728000 + (rvar ** 20) / 2432902008176640000
                    if self.varConditions[stmt.lvar.name] not in (None, True, False):
                        self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], z3.Real(stmt.lvar.name) == rhs_expr))
                    elif self.varConditions[stmt.lvar.name] is not False:
                        self.solver.add(z3.Real(stmt.lvar.name) == rhs_expr)

                elif isinstance(stmt, ChironSSA.SinCommand):
                    rvar = z3.Real(stmt.rvar.name)
                    rhs_expr = rvar - (rvar ** 3) / 6
                    # rhs_expr = rvar - (rvar ** 3) / 6 + (rvar ** 5) / 120 - (rvar ** 7) / 5040 + (rvar ** 9) / 362880 - (rvar ** 11) / 39916800 + (rvar ** 13) / 6227020800 - (rvar ** 15) / 1307674368000 + (rvar ** 17) / 355687428096000 - (rvar ** 19) / 121645100408832000 + (rvar ** 21) / 51090942171709440000
                    if self.varConditions[stmt.lvar.name] not in (None, True, False):
                        self.solver.add(z3.Implies(self.varConditions[stmt.lvar.name], z3.Real(stmt.lvar.name) == rhs_expr))
                    elif self.varConditions[stmt.lvar.name] is not False:
                        self.solver.add(z3.Real(stmt.lvar.name) == rhs_expr)

                elif isinstance(stmt, ChironSSA.MoveCommand):
                    pass
                elif isinstance(stmt, ChironSSA.PenCommand):
                    pass
                elif isinstance(stmt, ChironSSA.GotoCommand):
                    pass
                elif isinstance(stmt, ChironSSA.ConditionCommand):
                    pass
                elif isinstance(stmt, ChironSSA.NoOpCommand):
                    pass
                elif isinstance(stmt, ChironSSA.PauseCommand):
                    pass
                else:
                    raise Exception("Unknown SSA instruction")
        
        assert_conditions = z3.Tactic('ctx-simplify').apply(assert_conditions).as_expr()
        self.solver.add(z3.Not(assert_conditions))

    def solve(self, inputVars):
        print("The clauses are:")
        print(self.solver, end="\n\n")
        
        sat = self.solver.check()

        if sat == z3.sat:
            print("Condition not satisfied! Bug found for the following input:")
            model = self.solver.model()
            print(model)
            solution = {}
            for var in model:
                varname, index = str(var).split("$")
                if varname in inputVars and index == "0":
                    solution[varname] = model[var]
            for var in solution:
                    print(var + " = " + str(solution[var]))

        elif sat == z3.unsat:
            print("Condition satisfied for all inputs!")
        else:
            print("Unknown")

