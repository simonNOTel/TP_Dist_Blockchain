from xlang_parser import *

class CodeGen:
    def __init__(self):
        self.code = []
        self.globals = {}
        self.next_mem = 100
        self.locals = {}
        self.func_addresses = {}
        self.string_pool = {}
        self.next_string_addr = 100000
        self.current_func = None

    def emit(self, op, arg=0):
        self.code += [op, arg]

    def patch(self, pos, val):
        self.code[pos] = val

    def gen(self, vars_, funcs):
        for f in funcs: self.func_addresses[f.name] = 0
        for v in vars_:
            if v.name not in self.globals:
                self.globals[v.name] = self.next_mem
                self.next_mem += 1
            self.gen_expr(v.value)
            self.emit(4, self.globals[v.name])

        main_jmp = len(self.code)
        self.emit(20, 0) # Прыжок в main

        for f in funcs:
            self.current_func = f
            self.func_addresses[f.name] = len(self.code)
            self.locals = {p: i for i, p in enumerate(f.params)}
            for stmt in f.body: self.gen_stmt(stmt)
            self.emit(22) # RET

        if "main" in self.func_addresses:
            self.patch(main_jmp + 1, self.func_addresses["main"])
        return self.code

    def gen_stmt(self, s):
        if isinstance(s, VarDecl):
            name = f"{self.current_func.name}_{s.name}" if self.current_func else s.name
            if name not in self.globals:
                self.globals[name] = self.next_mem
                self.next_mem += 1
            self.gen_expr(s.value)
            self.emit(4, self.globals[name])
        elif isinstance(s, Assign):
            self.gen_expr(s.expr)
            prefixed_name = f"{self.current_func.name}_{s.name}" if self.current_func else s.name
            if s.name in self.locals: self.emit(6, self.locals[s.name])
            elif prefixed_name in self.globals: self.emit(4, self.globals[prefixed_name])
            else: self.emit(4, self.globals[s.name])
        elif isinstance(s, ArrayAssign):
            self.gen_expr(Var(s.name))
            self.gen_expr(s.index)
            self.gen_expr(s.value)
            self.emit(43)
        elif isinstance(s, If):
            self.gen_expr(s.cond)
            self.emit(30, 0)
            jz_patch = len(self.code) - 1
            for st in s.then_body: self.gen_stmt(st)
            if s.else_body:
                self.emit(20, 0)
                jmp_patch = len(self.code) - 1
                self.patch(jz_patch, len(self.code))
                for st in s.else_body: self.gen_stmt(st)
                self.patch(jmp_patch, len(self.code))
            else:
                self.patch(jz_patch, len(self.code))
        elif isinstance(s, While):
            start = len(self.code)
            self.gen_expr(s.cond)
            self.emit(30, 0) # JZ
            exit_patch = len(self.code) - 1
            for st in s.body: self.gen_stmt(st)
            self.emit(20, start) # JMP
            self.patch(exit_patch, len(self.code))
        elif isinstance(s, For):
            self.gen_stmt(s.init)
            start = len(self.code)
            self.gen_expr(s.cond)
            self.emit(30, 0)
            exit_p = len(self.code) - 1
            for st in s.body: self.gen_stmt(st)
            self.gen_stmt(s.step)
            self.emit(20, start)
            self.patch(exit_p, len(self.code))
        elif isinstance(s, Return):
            self.gen_expr(s.expr)
            self.emit(22)
        else:
            self.gen_expr(s)
            self.emit(2) # POP результата вызова/выражения

    def gen_expr(self, e):
        if isinstance(e, Number): self.emit(1, e.value)
        elif isinstance(e, StringLiteral):
            if e.value not in self.string_pool:
                addr = self.next_string_addr
                self.string_pool[addr] = e.value
                self.next_string_addr += len(e.value) + 1
            addr = [k for k, v in self.string_pool.items() if v == e.value][0]
            self.emit(1, addr)
        elif isinstance(e, Var):
            name_p = f"{self.current_func.name}_{e.name}" if self.current_func else e.name
            if e.name in self.locals: self.emit(5, self.locals[e.name])
            elif name_p in self.globals: self.emit(3, self.globals[name_p])
            else: self.emit(3, self.globals[e.name])
        elif isinstance(e, BinOp):
            self.gen_expr(e.left); self.gen_expr(e.right)
            ops = {"+": 10, "-": 11, "*": 12, "/": 13, "==": 14, "!=": 15,
                  "<": 16, ">": 17, "&&": 18, "||": 19, "&": 7, "|": 8,
                  "^": 9, ">>>": 32, "<<": 33}
            self.emit(ops[e.op])
        elif isinstance(e, ArrayAlloc): self.gen_expr(e.size); self.emit(41)
        elif isinstance(e, ArrayAccess):
            self.gen_expr(Var(e.name)); self.gen_expr(e.index); self.emit(42)
        elif isinstance(e, Call):
            if e.name == "prints": self.gen_expr(e.args[0]); self.emit(45)
            elif e.name == "printi": self.gen_expr(e.args[0]); self.emit(46)
            elif e.name == "fwrite": self.gen_expr(e.args[0]); self.gen_expr(e.args[1]); self.emit(50)
            elif e.name == "fappend": self.gen_expr(e.args[0]); self.gen_expr(e.args[1]); self.emit(51)
            elif e.name == "fappend_int": self.gen_expr(e.args[0]); self.gen_expr(e.args[1]); self.emit(53)
            elif e.name == "fread": self.gen_expr(e.args[0]); self.emit(52)
            elif e.name == "json_get_hash":
                for arg in e.args: self.gen_expr(arg)
                self.emit(61)
            else:
                for arg in reversed(e.args): self.gen_expr(arg)
                self.emit(21, self.func_addresses[e.name])