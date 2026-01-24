from xlang_parser import *


class CodeGen:
    def __init__(self):
        self.code, self.globals, self.next_mem = [], {}, 100
        self.locals, self.func_addresses = {}, {}

    def emit(self, op, arg=0):
        self.code += [op, arg]

    def patch(self, pos, val):
        self.code[pos] = val

    def gen(self, vars_, funcs):
        for f in funcs: self.func_addresses[f.name] = 0
        for v in vars_:
            self.globals[v.name] = self.next_mem
            self.next_mem += 1
            self.gen_expr(v.value)
            self.emit(4, self.globals[v.name])

        main_jmp = len(self.code)
        self.emit(20, 0)  # JMP to main

        for f in funcs:
            self.func_addresses[f.name] = len(self.code)
            self.locals = {n: i for i, n in enumerate(f.params)}
            for s in f.body: self.gen_stmt(s)
            self.emit(1, 0);
            self.emit(22)  # Default return

        if "main" in self.func_addresses:
            self.patch(main_jmp + 1, self.func_addresses["main"])
        return self.code

    def gen_stmt(self, s):
        if isinstance(s, VarDecl):
            self.locals[s.name] = len(self.locals)
            self.gen_expr(s.value)
            self.emit(6, self.locals[s.name])
        elif isinstance(s, Assign):
            self.gen_expr(s.expr)
            if s.name in self.locals:
                self.emit(6, self.locals[s.name])
            else:
                self.emit(4, self.globals[s.name])
        elif isinstance(s, ArrayAssign):
            self.gen_expr(Var(s.name))
            self.gen_expr(s.index)
            self.gen_expr(s.value)
            self.emit(43)
        elif isinstance(s, Return):
            self.gen_expr(s.expr);
            self.emit(22)
        elif isinstance(s, If):
            self.gen_expr(s.cond)
            else_label = len(self.code);
            self.emit(21, 0)
            for stmt in s.then_body: self.gen_stmt(stmt)
            end_label = len(self.code);
            self.emit(20, 0)
            self.patch(else_label + 1, len(self.code))
            for stmt in s.else_body: self.gen_stmt(stmt)
            self.patch(end_label + 1, len(self.code))
        elif isinstance(s, For):
            self.gen_stmt(s.init)
            loop_start = len(self.code)
            self.gen_expr(s.cond)
            exit_jmp = len(self.code);
            self.emit(21, 0)
            for stmt in s.body: self.gen_stmt(stmt)
            self.gen_stmt(s.step)
            self.emit(20, loop_start)
            self.patch(exit_jmp + 1, len(self.code))
        else:
            self.gen_expr(s); self.emit(2)  # Pop unused result

    def gen_expr(self, e):
        if isinstance(e, Number):
            self.emit(1, e.value)
        elif isinstance(e, StringLiteral):
            addr = self.next_mem
            self.next_mem += len(e.value) + 1
            self.emit(1, addr)  # Push constant address (simplified)
        elif isinstance(e, Var):
            if e.name in self.locals:
                self.emit(5, self.locals[e.name])
            else:
                self.emit(3, self.globals[e.name])
        elif isinstance(e, BinOp):
            self.gen_expr(e.left);
            self.gen_expr(e.right)
            ops = {"+": 10, "-": 11, "*": 12, "/": 13, "==": 14, ">": 15, "<": 16, "&": 25, "|": 26, "^": 27, ">>": 28,
                   ">>>": 29}
            self.emit(ops[e.op])
        elif isinstance(e, ArrayAlloc):
            self.gen_expr(e.size);
            self.emit(41)
        elif isinstance(e, ArrayAccess):
            self.gen_expr(Var(e.name));
            self.gen_expr(e.index);
            self.emit(42)
        elif isinstance(e, Call):
            for arg in e.args: self.gen_expr(arg)
            if e.name == "fwrite":
                self.emit(50)
            elif e.name == "fappend":
                self.emit(51)
            elif e.name == "prints":
                self.emit(45); self.emit(1, 0)
            elif e.name == "printhex":
                self.emit(46); self.emit(1, 0)
            elif e.name == "bc_save":
                self.emit(55); self.emit(1, 1)
            else:
                self.emit(23, self.func_addresses[e.name])