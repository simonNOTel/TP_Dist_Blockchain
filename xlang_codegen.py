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

        # Глобальные переменные
        for v in vars_:
            if v.name not in self.globals:
                self.globals[v.name] = self.next_mem
                self.next_mem += 1
            self.gen_expr(v.value)
            self.emit(4, self.globals[v.name])

        main_jmp = len(self.code)
        self.emit(20, 0)  # Прыжок в main

        for f in funcs:
            self.current_func = f
            self.func_addresses[f.name] = len(self.code)
            # Исправленный порядок аргументов: первый аргумент в locals[0]
            self.locals = {n: len(f.params) - 1 - i for i, n in enumerate(f.params)}
            for s in f.body: self.gen_stmt(s)
            self.emit(1, 0)  # Default return
            self.emit(22)
            self.current_func = None

        if "main" in self.func_addresses:
            self.patch(main_jmp + 1, self.func_addresses["main"])
        return self.code

    def gen_expr(self, e):
        if isinstance(e, Number):
            self.emit(1, e.value)
        elif isinstance(e, StringLiteral):
            addr = self.next_string_addr
            self.string_pool[addr] = e.value
            self.next_string_addr += len(e.value) + 1
            self.emit(1, addr)
        elif isinstance(e, Var):
            # Проверяем локальную переменную (с префиксом функции) или параметр
            local_name = f"{self.current_func.name}_{e.name}" if self.current_func else e.name
            if e.name in self.locals:
                self.emit(5, self.locals[e.name])
            elif local_name in self.globals:
                self.emit(3, self.globals[local_name])
            else:
                self.emit(3, self.globals.get(e.name, 0))
        elif isinstance(e, BinOp):
            self.gen_expr(e.left)
            self.gen_expr(e.right)
            ops = {"+": 10, "-": 11, "*": 12, "/": 13, "==": 14, "!=": 15,
                   ">": 16, "<": 17, "&": 18, "|": 19, "^": 23, ">>>": 24, ">>": 25}
            self.emit(ops.get(e.op, 10))
        elif isinstance(e, ArrayAlloc):
            self.gen_expr(e.size)
            self.emit(41)
        elif isinstance(e, ArrayAccess):
            self.gen_expr(Var(e.name))  # Используем логику поиска адреса из Var
            self.gen_expr(e.index)
            self.emit(42)
        elif isinstance(e, Call):
            for arg in e.args: self.gen_expr(arg)
            if e.name == "prints":
                self.emit(45)
            elif e.name == "printhex":
                self.emit(46)
            elif e.name in self.func_addresses:
                self.emit(21, self.func_addresses[e.name])
            elif e.name == "fwrite":
                for arg in e.args: self.gen_expr(arg)
                self.emit(50)  # Назначаем код 50 для записи
            elif e.name == "fappend":
                for arg in e.args: self.gen_expr(arg)
                self.emit(51)  # Назначаем код 51 для добавления

    def gen_stmt(self, s):
        if isinstance(s, VarDecl):
            # Превращаем локальный var в уникальный глобальный, чтобы избежать конфликтов
            name = f"{self.current_func.name}_{s.name}" if self.current_func else s.name
            if name not in self.globals:
                self.globals[name] = self.next_mem
                self.next_mem += 1
            self.gen_expr(s.value)
            self.emit(4, self.globals[name])
        elif isinstance(s, Assign):
            self.gen_expr(s.expr)
            name = f"{self.current_func.name}_{s.name}" if self.current_func else s.name
            if s.name in self.locals:
                self.emit(6, self.locals[s.name])
            elif name in self.globals:
                self.emit(4, self.globals[name])
            else:
                self.emit(4, self.globals[s.name])
        elif isinstance(s, ArrayAssign):
            self.gen_expr(Var(s.name))
            self.gen_expr(s.index)
            self.gen_expr(s.value)
            self.emit(43)
        elif isinstance(s, If):
            self.gen_expr(s.cond)
            self.emit(30, 0);
            p = len(self.code) - 1
            for st in s.then_body: self.gen_stmt(st)
            self.patch(p, len(self.code))
        elif isinstance(s, For):
            self.gen_stmt(s.init)
            start = len(self.code)
            self.gen_expr(s.cond)
            self.emit(30, 0);
            exit_p = len(self.code) - 1
            for st in s.body: self.gen_stmt(st)
            self.gen_stmt(s.step)
            self.emit(20, start)
            self.patch(exit_p, len(self.code))
        elif isinstance(s, Return):
            self.gen_expr(s.expr)
            self.emit(22)
        elif isinstance(s, Call):
            self.gen_expr(s)
            self.emit(2)