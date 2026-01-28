import re
from collections import namedtuple

Token = namedtuple("Token", ["type", "value", "line", "column"])
KEYWORDS = {"var", "func", "if", "else", "while", "return", "new", "for", "import"}

TOKEN_SPEC = [
    ("COMMENT", r"//.*"),
    ("SKIP", r"[ \t\r]+"),
    ("NEWLINE", r"\n"),
    ("STRING", r'"(?:\\.|[^"\\])*"'), # ИСПРАВЛЕНО
    ("NUMBER", r"0x[0-9A-Fa-f]+|\d+"),
    ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"&&|\|\||==|!=|>=|<=|>>>|>>|<<|[\+\-\*/><=\^&|]"),
    ("LPAREN", r"\("), ("RPAREN", r"\)"),
    ("LBRACE", r"\{"), ("RBRACE", r"\}"),
    ("LBRACKET", r"\["), ("RBRACKET", r"\]"),
    ("SEMICOL", r";"), ("COMMA", r",")
]

def tokenize(code):
    tokens = []
    line, line_start = 1, 0
    reg = "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)
    for mo in re.finditer(reg, code):
        kind, value = mo.lastgroup, mo.group()
        if kind == "NEWLINE": line_start, line = mo.end(), line + 1
        elif kind not in ["SKIP", "COMMENT"]:
            if kind == "ID" and value in KEYWORDS: kind = value.upper()
            tokens.append(Token(kind, value, line, mo.start() - line_start))
    return tokens