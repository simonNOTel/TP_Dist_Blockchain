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
        if expected_type and t.type != expected_type:
            raise Exception(f"Expected {expected_type} at line {t.line}, got {t.type}")
        self.pos += 1
        return t

    def parse(self):
        imports, vars_, funcs = [], [], []
        while self.pos < len(self.tokens):
            t = self.peek()
            if t.type == "IMPORT":
                self.eat()
                fname = self.eat("STRING").value.strip('"')
                imports.append(Import(fname))
            elif t.type == "VAR":
                vars_.append(self.parse_var_decl())
            elif t.type == "FUNC":
                funcs.append(self.parse_func())
            else:
                self.pos += 1
        return imports, vars_, funcs

    def parse_var_decl(self):
        self.eat("VAR")
        name = self.eat("ID").value
        self.eat("OP")  # '='
        val = self.parse_expr()
        if self.peek() and self.peek().type == "SEMICOL": self.eat()
        return VarDecl(name, val)

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

    def parse_stmt(self):
        t = self.peek()
        if t.type == "VAR": return self.parse_var_decl()
        if t.type == "RETURN":
            self.eat()
            expr = self.parse_expr()
            if self.peek().type == "SEMICOL": self.eat()
            return Return(expr)
        if t.type == "IF":
            self.eat();
            self.eat("LPAREN")
            cond = self.parse_expr()
            self.eat("RPAREN");
            self.eat("LBRACE")
            then_b = []
            while self.peek().type != "RBRACE": then_b.append(self.parse_stmt())
            self.eat("RBRACE")
            else_b = []
            if self.peek() and self.peek().type == "ELSE":
                self.eat();
                self.eat("LBRACE")
                while self.peek().type != "RBRACE": else_b.append(self.parse_stmt())
                self.eat("RBRACE")
            return If(cond, then_b, else_b)
        if t.type == "FOR":
            self.eat();
            self.eat("LPAREN")
            init = self.parse_var_decl();
            # Строку self.eat("SEMICOL") удалили, так как parse_var_decl уже съел её
            cond = self.parse_expr();
            self.eat("SEMICOL")
            step = self.parse_stmt()
            self.eat("RPAREN");
            self.eat("LBRACE")
            body = []
            while self.peek().type != "RBRACE": body.append(self.parse_stmt())
            self.eat("RBRACE")
            return For(init, cond, step, body)

        # Assignment or Call
        expr = self.parse_expr()
        if self.peek() and self.peek().type == "SEMICOL": self.eat()
        return expr

    def parse_expr(self):
        left = self.parse_primary()
        while self.peek() and self.peek().type == "OP":
            op = self.eat().value
            if op == "=":
                val = self.parse_expr()
                if isinstance(left, Var): return Assign(left.name, val)
                if isinstance(left, ArrayAccess): return ArrayAssign(left.name, left.index, val)
            left = BinOp(left, op, self.parse_primary())
        return left

    def parse_primary(self):
        t = self.eat()
        if t.type == "NUMBER":
            val = int(t.value, 16) if t.value.startswith("0x") else int(t.value)
            return Number(val)
        if t.type == "STRING": return StringLiteral(t.value.strip('"'))
        if t.type == "NEW":
            self.eat("LPAREN");
            size = self.parse_expr();
            self.eat("RPAREN")
            return ArrayAlloc(size)
        if t.type == "ID":
            name = t.value
            if name == "Int":  # Special Int(-1) handling
                self.eat("LPAREN")
                sign = 1
                if self.peek().type == "OP" and self.peek().value == "-":
                    self.eat();
                    sign = -1
                num_t = self.eat("NUMBER")
                val = int(num_t.value, 16) if num_t.value.startswith("0x") else int(num_t.value)
                self.eat("RPAREN")
                return Number(val * sign)
            if self.peek() and self.peek().type == "LPAREN":
                self.eat("LPAREN")
                args = []
                if self.peek().type != "RPAREN":
                    while True:
                        args.append(self.parse_expr())
                        if self.peek().type == "COMMA":
                            self.eat("COMMA")
                        else:
                            break
                self.eat("RPAREN")
                return Call(name, args)
            if self.peek() and self.peek().type == "LBRACKET":
                self.eat("LBRACKET");
                idx = self.parse_expr();
                self.eat("RBRACKET")
                return ArrayAccess(name, idx)
            return Var(name)
        if t.type == "LPAREN":
            e = self.parse_expr();
            self.eat("RPAREN")
            return e
        raise Exception(f"Unexpected token {t.type}")