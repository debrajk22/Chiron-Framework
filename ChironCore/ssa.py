import ChironAST.ChironAST as ChironAST
import cfg.ChironCFG as ChironCFG
import networkx as nx
import copy as cp

class SSAConverter:
    def __init__(self, ir, cfg):
        self.ir = ir
        self.cfg = cfg
        self.ssa = nx.DiGraph()

        self.globals = None
        self.varBlocks = None

        self.counter = {}
        self.stack = {}

    def convert(self):
        self.getGlobals()
        self.addPhiFunctions()

        # draw cfg with phi functions
        G = self.cfg.nxgraph
        labels = {}
        for node in self.cfg:
            labels[node] = node.name + "\n" + node.label()

        G = nx.relabel_nodes(G, labels)
        A = nx.nx_agraph.to_agraph(G)
        A.layout('dot')
        A.draw('cfg_before_renaming.png')

        self.renameVariables()

        # draw cfg after renaming
        G = self.cfg.nxgraph
        labels = {}
        for node in self.cfg:
            labels[node] = node.name + "\n" + node.label()

        G = nx.relabel_nodes(G, labels)
        A = nx.nx_agraph.to_agraph(G)
        A.layout('dot')
        A.draw('cfg_after_renaming.png')
        
    def getGlobals(self):
        self.globals = set()
        self.varBlocks = {}

        for block in self.cfg.nodes():
            varkill = set()
            for instr, _ in block.instrlist:
                for var in instr.getReadVariables():
                    if var not in varkill:
                        self.globals.add(var)
                for var in instr.getWriteVariables():
                    varkill.add(var)
                    if var not in self.varBlocks:
                        self.varBlocks[var] = set()
                    self.varBlocks[var].add(block)
        
        return self.globals
    
    def addPhiFunctions(self):
        for var in self.globals:
            if var not in self.varBlocks:
                continue
            worklist = self.varBlocks[var]
            while len(worklist) > 0:
                block = worklist.pop()
                for node in self.cfg.df[block]:
                    found = False
                    for instr, _ in node.instrlist:
                        if isinstance(instr, ChironAST.PhiAssignmentCommand) and instr.lvar.varname == var:
                            found = True
                            break

                    if not found:
                        instr = ChironAST.PhiAssignmentCommand(ChironAST.Var(var), [])
                        node.prepend((instr, 1))
                        worklist.add(node)

    def renameVariables(self):
        for var in self.globals:
            self.counter[var] = 0
            self.stack[var] = []

        for block in self.cfg.nodes():
            if block.name == "START":
                self.rename(block)

    def rename(self, block):
        newblock = cp.deepcopy(block)
        newblock.instrlist = []

        for instr, target in block.instrlist:
            if not isinstance(instr, ChironAST.PhiAssignmentCommand):
                continue
            print("old instr: " + str(instr))
            newinstr = ChironAST.PhiAssignmentCommand(ChironAST.Var(self.newName(instr.lvar.varname)), instr.varlist)
            print("new instr: " + str(newinstr))
            newblock.append((newinstr, target))
        
        for instr, _ in block.instrlist:
            if isinstance(instr, ChironAST.PhiAssignmentCommand):
                continue
            print("old instr: " + str(instr))
            newinstr = cp.deepcopy(instr)
            if isinstance(newinstr, ChironAST.AssignmentCommand):
                temp = cp.deepcopy(newinstr.rexpr)
                for var in temp.getVariables():
                    temp.renameVariable(var, self.stack[var][-1])
                newinstr.rexpr = temp
                newinstr.lvar = ChironAST.Var(self.newName(newinstr.lvar.varname))
                print("new instr: " + str(newinstr))
                continue

            for var in newinstr.getReadVariables():
                if len(self.stack[self.originalName(var)]) == 0:
                    print("stack for " + var + " is empty")
                    continue
                print("renaming " + var + " to " + self.stack[self.originalName(var)][-1] + " in " + str(type(newinstr)))
                newinstr.renameReadVariable(var, self.stack[self.originalName(var)][-1])
                
            for var in newinstr.getWriteVariables():
                newinstr.renameWriteVariable(var, self.newName(var))
            print("new instr: " + str(newinstr))
            newblock.append((newinstr, target))
            
        for succ in self.cfg.successors(block):
            for instr, _ in succ.instrlist:
                if not isinstance(instr, ChironAST.PhiAssignmentCommand):
                    continue
                if len(self.stack[self.originalName(instr.lvar.varname)]) == 0:
                    print("stack for " + instr.lvar.varname + " is empty")
                    continue
                instr.varlist.append(self.stack[self.originalName(instr.lvar.varname)][-1])

        for succ in self.cfg.successors(block):
            # succ should be in dominator tree of block
            if self.cfg.idom[succ] == block:
                self.rename(succ)

        for instr, _ in block.instrlist:
            for var in instr.getWriteVariables():
                self.stack[var].pop()

        block.instrlist = newblock.instrlist


    def newName(self, var):
        self.stack[var].append(var + "#" + str(self.counter[var]))
        self.counter[var] += 1
        return self.stack[var][-1]
    
    def originalName(self, var):
        return var.split("#")[0]
    