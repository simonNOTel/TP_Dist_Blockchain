from xlang_parser import *


class CodeGen:
    def __init__(self):
        self.code = [];
        self.globals = {};
        self.next_mem = 100
        self.locals = {};
        self.func_addresses = {};
        self.string_pool = {}
        self.next_string_addr = 100000;
        self.current_func = None

    def emit(self, op, arg=0):
        self.code += [op, arg]

    def patch(self, pos, val):
        self.code[pos] = val

    def gen(self, vars_, funcs):
        # СПИСОК ДЛЯ ЛИНКОВКИ: Сохраняем места, где нужно исправить адреса функций
        calls_to_patch = []

        # 1. Глобальные переменные
        for v in vars_:
            if v.name not in self.globals: self.globals[v.name] = self.next_mem; self.next_mem += 1
            self.gen_expr(v.value, calls_to_patch);
            self.emit(4, self.globals[v.name])

        # 2. Прыжок в main
        main_jmp = len(self.code);
        self.emit(20, 0)

        # 3. Компиляция функций
        for f in funcs:
            self.current_func = f;
            self.func_addresses[f.name] = len(self.code)
            self.locals = {p: i for i, p in enumerate(f.params)}
            for stmt in f.body: self.gen_stmt(stmt, calls_to_patch)
            self.emit(22)  # RET

        # 4. Патчинг прыжка в main
        if "main" in self.func_addresses: self.patch(main_jmp + 1, self.func_addresses["main"])

        # 5. ЛИНКЕР (Самое важное): Проставляем реальные адреса вызовов
        for pos, name in calls_to_patch:
            if name in self.func_addresses:
                self.patch(pos, self.func_addresses[name])
            else:
                print(f"[Linker Warning] Undefined function call: '{name}'")

        return self.code

    def gen_stmt(self, s, calls_to_patch=None):
        if isinstance(s, VarDecl):
            name = f"{self.current_func.name}_{s.name}" if self.current_func else s.name
            if name not in self.globals: self.globals[name] = self.next_mem; self.next_mem += 1
            self.gen_expr(s.value, calls_to_patch);
            self.emit(4, self.globals[name])
        elif isinstance(s, Assign):
            self.gen_expr(s.expr, calls_to_patch)
            pre = f"{self.current_func.name}_{s.name}" if self.current_func else s.name
            if s.name in self.locals:
                self.emit(6, self.locals[s.name])
            else:
                self.emit(4, self.globals.get(pre, self.globals.get(s.name)))
        elif isinstance(s, ArrayAssign):
            self.gen_expr(Var(s.name), calls_to_patch);
            self.gen_expr(s.index, calls_to_patch);
            self.gen_expr(s.value, calls_to_patch);
            self.emit(43)
        elif isinstance(s, If):
            self.gen_expr(s.cond, calls_to_patch);
            self.emit(30, 0);
            jz = len(self.code) - 1
            for st in s.then_body: self.gen_stmt(st, calls_to_patch)
            if s.else_body:
                self.emit(20, 0);
                jmp = len(self.code) - 1;
                self.patch(jz, len(self.code))
                for st in s.else_body: self.gen_stmt(st, calls_to_patch)
                self.patch(jmp, len(self.code))
            else:
                self.patch(jz, len(self.code))
        elif isinstance(s, While):
            start = len(self.code)
            self.gen_expr(s.cond, calls_to_patch);
            self.emit(30, 0);
            exit_p = len(self.code) - 1
            for st in s.body: self.gen_stmt(st, calls_to_patch)
            self.emit(20, start);
            self.patch(exit_p, len(self.code))
        elif isinstance(s, For):
            self.gen_stmt(s.init, calls_to_patch);
            start = len(self.code);
            self.gen_expr(s.cond, calls_to_patch);
            self.emit(30, 0);
            ex = len(self.code) - 1
            for st in s.body: self.gen_stmt(st, calls_to_patch)
            self.gen_stmt(s.step, calls_to_patch);
            self.emit(20, start);
            self.patch(ex, len(self.code))
        elif isinstance(s, Return):
            self.gen_expr(s.expr, calls_to_patch); self.emit(22)
        else:
            self.gen_expr(s, calls_to_patch); self.emit(2)

    def gen_expr(self, e, calls_to_patch=None):
        if isinstance(e, Number):
            self.emit(1, e.value)
        elif isinstance(e, StringLiteral):
            if e.value not in self.string_pool:
                addr = self.next_string_addr;
                self.string_pool[addr] = e.value;
                self.next_string_addr += len(e.value) + 1
            addr = [k for k, v in self.string_pool.items() if v == e.value][0];
            self.emit(1, addr)
        elif isinstance(e, Var):
            pre = f"{self.current_func.name}_{e.name}" if self.current_func else e.name
            if e.name in self.locals:
                self.emit(5, self.locals[e.name])
            else:
                self.emit(3, self.globals.get(pre, self.globals.get(e.name)))
        elif isinstance(e, BinOp):
            self.gen_expr(e.left, calls_to_patch);
            self.gen_expr(e.right, calls_to_patch)
            ops = {"+": 10, "-": 11, "*": 12, "/": 13, "==": 14, "!=": 15, "<": 16, ">": 17, "&&": 18, "||": 19, "&": 7,
                   "|": 8, "^": 9, ">>>": 32, "<<": 33}
            self.emit(ops[e.op])
        elif isinstance(e, ArrayAlloc):
            self.gen_expr(e.size, calls_to_patch); self.emit(41)
        elif isinstance(e, ArrayAccess):
            self.gen_expr(Var(e.name), calls_to_patch); self.gen_expr(e.index, calls_to_patch); self.emit(42)
        elif isinstance(e, Call):
            # Системные вызовы
            if e.name == "prints":
                self.gen_expr(e.args[0], calls_to_patch); self.emit(45)
            elif e.name == "printi":
                self.gen_expr(e.args[0], calls_to_patch); self.emit(46)
            elif e.name == "fwrite":
                self.gen_expr(e.args[0], calls_to_patch); self.gen_expr(e.args[1], calls_to_patch); self.emit(50)
            elif e.name == "fappend":
                self.gen_expr(e.args[0], calls_to_patch); self.gen_expr(e.args[1], calls_to_patch); self.emit(51)
            elif e.name == "fappend_int":
                self.gen_expr(e.args[0], calls_to_patch); self.gen_expr(e.args[1], calls_to_patch); self.emit(53)
            elif e.name == "fread":
                self.gen_expr(e.args[0], calls_to_patch); self.emit(52)
            elif e.name == "random":
                self.emit(60)
            elif e.name == "json_get_hash":
                for arg in e.args: self.gen_expr(arg, calls_to_patch)
                self.emit(61)
            else:
                # Обычный вызов функции
                for arg in reversed(e.args): self.gen_expr(arg, calls_to_patch)
                self.emit(21, 0)  # Записываем 0 как заглушку
                if calls_to_patch is not None:
                    # Запоминаем позицию (len-1, т.к. 0 - это последний байт) для патчинга
                    calls_to_patch.append((len(self.code) - 1, e.name))