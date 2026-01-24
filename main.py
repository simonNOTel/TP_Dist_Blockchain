import os
from xlang_lexer import tokenize
from xlang_parser import Parser
from xlang_codegen import CodeGen
from xvm import XVM

def load_program(filename, visited=None):
    if visited is None: visited = set()
    abs_path = os.path.abspath(filename)
    if abs_path in visited: return [], []
    visited.add(abs_path)

    print(f"Loading: {filename}...")
    if not os.path.exists(filename): raise FileNotFoundError(f"File not found: {filename}")
    with open(filename, "r", encoding="utf-8") as f: source = f.read()

    tokens = tokenize(source)

    parser = Parser(tokens)
    imports, vars_, funcs = parser.parse()

    all_vars, all_funcs = [], []
    for imp in imports:
        v, f = load_program(imp.filename, visited)
        all_vars.extend(v); all_funcs.extend(f)

    all_vars.extend(vars_); all_funcs.extend(funcs)
    return all_vars, all_funcs

try:
    final_vars, final_funcs = load_program("main.xl")
    print(f"Compilation: {len(final_vars)} globals, {len(final_funcs)} functions.")
    cg = CodeGen()
    bytecode = cg.gen(final_vars, final_funcs)
    vm = XVM(bytecode)
    vm.run()
    print("Execution finished.")
except Exception as e:
    print(f"Error: {e}")

