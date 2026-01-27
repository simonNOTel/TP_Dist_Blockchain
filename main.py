import os
import sys
from xlang_lexer import tokenize
from xlang_parser import Parser
from xlang_codegen import CodeGen
from xvm import XVM


def load_program(filename, visited=None):
    """Рекурсивно загружает файлы через import и собирает AST."""
    if visited is None:
        visited = set()

    abs_path = os.path.abspath(filename)
    if abs_path in visited:
        return [], []
    visited.add(abs_path)

    print(f"[Compiler] Loading: {filename}...")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Source file not found: {filename}")

    with open(filename, "r", encoding="utf-8") as f:
        source = f.read()

    # Лексический анализ
    tokens = tokenize(source)

    # Парсинг
    parser = Parser(tokens)
    imports, vars_, funcs = parser.parse()

    all_vars, all_funcs = [], []

    # Обработка импортов
    for imp in imports:
        v, f = load_program(imp.filename, visited)
        all_vars.extend(v)
        all_funcs.extend(f)

    all_vars.extend(vars_)
    all_funcs.extend(funcs)

    return all_vars, all_funcs


def run_pipeline(entry_file):
    try:
        # 1. Сбор всех исходников
        final_vars, final_funcs = load_program(entry_file)
        print(f"[Compiler] Compiled {len(final_vars)} globals, {len(final_funcs)} functions.")

        # 2. Генерация байт-кода
        cg = CodeGen()
        bytecode = cg.gen(final_vars, final_funcs)
        print(f"[Compiler] Bytecode size: {len(bytecode)} bytes.")

        # 3. Запуск в виртуальной машине
        print("--- EXECUTION START ---")
        vm = XVM(bytecode)

        # Загружаем строки в память VM
        vm.load_strings(cg.string_pool)

        # Устанавливаем указатель кучи (hp) СРАЗУ ПОСЛЕ строк,
        # чтобы новые массивы (new) не затирали имена файлов и текст
        vm.hp = cg.next_string_addr

        vm.run()
        vm.dump_heap()
        print("--- EXECUTION FINISHED ---")

    except Exception as e:
        print(f"\n[!] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Точка входа - ваш главный файл .xl
    run_pipeline("main.xl")