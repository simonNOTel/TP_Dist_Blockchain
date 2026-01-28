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

    # --- ЗАЩИТА №1: Жесткая проверка на пустое имя файла ---
    if not filename or not isinstance(filename, str) or filename.strip() == "":
        # Просто игнорируем пустые импорты, не вызывая ошибку
        return [], []

    # Приводим к абсолютному пути
    try:
        abs_path = os.path.abspath(filename)
    except Exception:
        return [], []

    if abs_path in visited:
        return [], []
    visited.add(abs_path)

    print(f"[Compiler] Loading: {filename}...")

    if not os.path.exists(filename):
        print(f"[Compiler] Error: File not found '{filename}'")
        raise FileNotFoundError(f"Source file not found: {filename}")

    # --- ЗАЩИТА №2: Безопасное открытие файла ---
    try:
        with open(filename, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"[Compiler] Failed to open file '{filename}': {e}")
        return [], []

    # Лексический анализ
    try:
        tokens = tokenize(source)
    except Exception as e:
        print(f"[Compiler] Tokenization error in {filename}: {e}")
        raise e

    # Парсинг
    parser = Parser(tokens)
    imports, vars_, funcs = parser.parse()

    all_vars, all_funcs = [], []

    # Обработка импортов
    for imp in imports:
        # Рекурсивный вызов
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
        vm.hp = cg.next_string_addr

        vm.run()
        vm.dump_heap()
        print("--- EXECUTION FINISHED ---")

    except Exception as e:
        print(f"\n[!] COMPILER ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_pipeline("main.xl")