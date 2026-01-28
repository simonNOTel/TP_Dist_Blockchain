from dataclasses import dataclass


@dataclass
class VarDecl: name: str; value: any


@dataclass
class Func: name: str; params: list; body: list


@dataclass
class Assign: name: str; expr: any


@dataclass
class BinOp: left: any; op: str; right: any


@dataclass
class Number: value: int


@dataclass
class StringLiteral: value: str


@dataclass
class Var: name: str


@dataclass
class Return: expr: any


@dataclass
class Call: name: str; args: list


@dataclass
class If: cond: any; then_body: list; else_body: list


@dataclass
class While: cond: any; body: list


@dataclass
class For: init: any; cond: any; step: any; body: list


@dataclass
class ArrayAlloc: size: any


@dataclass
class ArrayAccess: name: str; index: any


@dataclass
class ArrayAssign: name: str; index: any; value: any


@dataclass
class Import: filename: str


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, expected_type=None):
        t = self.peek()
        if not t or (expected_type and t.type != expected_type):
            raise Exception(f"Expected {expected_type} at line {t.line if t else 'EOF'}")
        self.pos += 1
        return t

    def parse(self):
        imports, vars_, funcs = [], [], []
        while self.peek():
            t = self.peek()
            if t.type == "IMPORT":
                self.eat()
                filename = self.eat("STRING").value.strip('"')
                imports.append(Import(filename))
            elif t.type == "VAR":
                vars_.append(self.parse_var_decl())
            elif t.type == "FUNC":
                funcs.append(self.parse_func())
            else:
                self.eat()
        return imports, vars_, funcs

    def parse_func(self):
        self.eat("FUNC")
        name = self.eat("ID").value
        self.eat("LPAREN")
        params = []
        if self.peek().type != "RPAREN":
            while True:
                params.append(self.eat("ID").value)
                if self.peek().type == "COMMA":
                    self.eat("COMMA")
                else:
                    break
        self.eat("RPAREN")
        self.eat("LBRACE")
        body = []
        while self.peek().type != "RBRACE":
            body.append(self.parse_stmt())
        self.eat("RBRACE")
        return Func(name, params, body)

    # ДОБАВЛЕННЫЙ МЕТОД
    def parse_var_decl(self):
        self.eat("VAR")
        name = self.eat("ID").value
        self.eat("OP")  # Ожидаем '='
        val = self.parse_expr()
        if self.peek() and self.peek().type == "SEMICOL":
            self.eat("SEMICOL")
        return VarDecl(name, val)

    def parse_stmt(self):
        t = self.peek()
        if not t: return None
        if t.type == "VAR": return self.parse_var_decl()
        if t.type == "IF":
            self.eat()
            self.eat("LPAREN")
            cond = self.parse_expr()
            self.eat("RPAREN")
            self.eat("LBRACE")
            then_body = []
            while self.peek().type != "RBRACE": then_body.append(self.parse_stmt())
            self.eat("RBRACE")
            else_body = []
            if self.peek() and self.peek().type == "ELSE":
                self.eat()
                self.eat("LBRACE")
                while self.peek().type != "RBRACE": else_body.append(self.parse_stmt())
                self.eat("RBRACE")
            return If(cond, then_body, else_body)
        if t.type == "WHILE":
            self.eat()
            self.eat("LPAREN")
            cond = self.parse_expr()
            self.eat("RPAREN")
            self.eat("LBRACE")
            body = []
            while self.peek().type != "RBRACE": body.append(self.parse_stmt())
            self.eat("RBRACE")
            return While(cond, body)
        if t.type == "FOR":
            self.eat()
            self.eat("LPAREN")
            init = self.parse_stmt()
            if self.peek().type == "SEMICOL": self.eat()
            cond = self.parse_expr()
            if self.peek().type == "SEMICOL": self.eat()
            step = self.parse_stmt()
            self.eat("RPAREN")
            self.eat("LBRACE")
            body = []
            while self.peek().type != "RBRACE": body.append(self.parse_stmt())
            self.eat("RBRACE")
            return For(init, cond, step, body)
        if t.type == "RETURN":
            self.eat()
            val = self.parse_expr()
            # ИСПРАВЛЕНИЕ: съедаем точку с запятой после return
            if self.peek() and self.peek().type == "SEMICOL":
                self.eat("SEMICOL")
            return Return(val)

        # Обработка присваиваний и вызовов
        if t.type == "ID":
            name = t.value
            # Заглядываем вперед, чтобы отличить присваивание от вызова
            next_t = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_t and next_t.type == "LBRACKET":
                self.eat()  # ID
                self.eat()  # [
                idx = self.parse_expr()
                self.eat("RBRACKET")
                self.eat("OP")  # =
                val = self.parse_expr()
                # ИСПРАВЛЕНИЕ: съедаем точку с запятой после присваивания массива
                if self.peek() and self.peek().type == "SEMICOL":
                    self.eat("SEMICOL")
                return ArrayAssign(name, idx, val)

            if next_t and next_t.type == "OP" and next_t.value == "=":
                self.eat()  # ID
                self.eat()  # =
                val = self.parse_expr()
                # ИСПРАВЛЕНИЕ: съедаем точку с запятой после обычного присваивания
                if self.peek() and self.peek().type == "SEMICOL":
                    self.eat("SEMICOL")
                return Assign(name, val)

        res = self.parse_expr()
        if self.peek() and self.peek().type == "SEMICOL": self.eat()
        return res

    def parse_expr(self):
        return self.parse_logic_or()

    def parse_logic_or(self):
        node = self.parse_logic_and()
        while self.peek() and self.peek().value == "||":
            op = self.eat().value
            node = BinOp(node, op, self.parse_logic_and())
        return node

    def parse_logic_and(self):
        node = self.parse_equality()
        while self.peek() and self.peek().value == "&&":
            op = self.eat().value
            node = BinOp(node, op, self.parse_equality())
        return node

    def parse_equality(self):
        node = self.parse_relational()
        while self.peek() and self.peek().value in ["==", "!="]:
            op = self.eat().value
            node = BinOp(node, op, self.parse_relational())
        return node

    def parse_relational(self):
        node = self.parse_bitwise()
        while self.peek() and self.peek().value in ["<", ">", "<=", ">="]:
            op = self.eat().value
            node = BinOp(node, op, self.parse_bitwise())
        return node

    def parse_bitwise(self):
        node = self.parse_term()
        while self.peek() and self.peek().value in ["&", "|", "^", ">>>", "<<"]:
            op = self.eat().value
            node = BinOp(node, op, self.parse_term())
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.peek() and self.peek().value in ["+", "-"]:
            op = self.eat().value
            node = BinOp(node, op, self.parse_factor())
        return node

    def parse_factor(self):
        node = self.parse_primary()
        while self.peek() and self.peek().value in ["*", "/"]:
            op = self.eat().value
            node = BinOp(node, op, self.parse_primary())
        return node

    def parse_primary(self):
        t = self.eat()
        if t.type == "NUMBER":
            return Number(int(t.value, 16) if t.value.startswith("0x") else int(t.value))
        if t.type == "STRING":
            return StringLiteral(t.value[1:-1].encode('utf-8').decode('unicode_escape'))
        if t.type == "NEW":
            self.eat("LPAREN")
            size = self.parse_expr()
            self.eat("RPAREN")
            return ArrayAlloc(size)
        if t.type == "ID":
            name = t.value
            # Обработка Int(...)
            if name == "Int":
                self.eat("LPAREN")
                sign = 1
                if self.peek() and self.peek().value == "-":
                    self.eat()
                    sign = -1
                num_t = self.eat("NUMBER")
                val = int(num_t.value, 16) if num_t.value.startswith("0x") else int(num_t.value)
                self.eat("RPAREN")
                return Number(val * sign)

            # Обработка вызова функции
            if self.peek() and self.peek().type == "LPAREN":
                self.eat("LPAREN")
                args = []
                if self.peek().type != "RPAREN":
                    while True:
                        args.append(self.parse_expr())
                        if self.peek().type == "COMMA":
                            self.eat()
                        else:
                            break
                self.eat("RPAREN")
                return Call(name, args)

            # Доступ к массиву
            if self.peek() and self.peek().type == "LBRACKET":
                self.eat("LBRACKET")
                idx = self.parse_expr()
                self.eat("RBRACKET")
                return ArrayAccess(name, idx)
            return Var(name)

        if t.type == "LPAREN":
            n = self.parse_expr()
            self.eat("RPAREN")
            return n

        raise Exception(f"Unexpected token {t.type} at line {t.line}")