import re
from collections import namedtuple

Token = namedtuple("Token", ["type", "value", "line", "column"])
KEYWORDS = {"var", "func", "if", "else", "while", "return", "new", "for", "import"}

TOKEN_SPEC = [
    ("COMMENT", r"//.*"),
    ("SKIP", r"[ \t\r]+"),
    ("NEWLINE", r"\n"),
    ("STRING", r'"[^"]*"'),
    ("NUMBER", r"0x[0-9A-Fa-f]+|\d+"),
    ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"&&|\|\||==|!=|>=|<=|>>>|>>|[\+\-\*/><=\^&|]"),
    ("LPAREN", r"\("), ("RPAREN", r"\)"),
    ("LBRACE", r"\{"), ("RBRACE", r"\}"),
    ("LBRACKET", r"\["), ("RBRACKET", r"\]"),
    ("SEMICOL", r";"), ("COMMA", r",")
]

def tokenize(code):
    tokens = []
    line = 1
    line_start = 0
    reg = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)
    for mo in re.finditer(reg, code):
        kind = mo.lastgroup
        value = mo.group()
        column = mo.start() - line_start
        if kind == "NEWLINE":
            line_start = mo.end()
            line += 1
            continue
        elif kind in ("SKIP", "COMMENT"):
            continue
        elif kind == "ID" and value in KEYWORDS:
            kind = value.upper()
        tokens.append(Token(kind, value, line, column))
    return tokens