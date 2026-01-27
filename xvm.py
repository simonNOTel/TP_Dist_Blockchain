import sys

class XVM:
    def __init__(self, code):
        self.code = code
        self.memory = [0] * 5000
        self.heap = [0] * 500000
        self.stack = []
        self.call_stack = []
        self.hp = 200000  # Сдвигаем кучу дальше, чтобы не пересекаться со строками
        self.pc = 0
        self.fp = 0
        self.running = True

    def _mask64(self, v):
        return v & 0xFFFFFFFFFFFFFFFF

    def dump_heap(self, filename="heap_debug.log"):
        print(f"[VM] Saving heap dump to {filename}...")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"--- XVM HEAP DUMP ---\n")
            f.write(f"PC: {self.pc} | FP: {self.fp} | HP: {self.hp}\n")
            f.write("-" * 30 + "\n")

            # Дампим от начала кучи (100000) до текущего указателя
            # + небольшой запас в 10 ячеек
            for addr in range(100000, self.hp + 10):
                val = self.heap[addr]
                if val == 0 and addr > self.hp: continue

                # Если значение похоже на печатный символ ASCII
                char_repr = f"| '{chr(val)}'" if 32 <= val <= 126 else ""

                f.write(f"[{addr}] {val:<20} {char_repr}\n")


    def load_strings(self, smap):
        for addr, s in smap.items():
            for i, c in enumerate(s):
                self.heap[addr + i] = ord(c)
            self.heap[addr + len(s)] = 0

    def _read_str(self, addr):
        res = ""
        addr = int(addr)
        while addr < len(self.heap) and self.heap[addr] != 0:
            res += chr(int(self.heap[addr]))
            addr += 1
        return res

    def step(self):
        if self.pc >= len(self.code):
            self.running = False
            return

        op = self.code[self.pc]
        arg = self.code[self.pc + 1]
        self.pc += 2

        # --- Базовые операции ---
        if op == 1: self.stack.append(arg)
        elif op == 2: self.stack.pop()
        elif op == 3: self.stack.append(self.memory[arg])
        elif op == 4: self.memory[arg] = self.stack.pop()
        elif op == 5: self.stack.append(self.stack[self.fp - arg - 1])
        elif op == 6: self.stack[self.fp - arg - 1] = self.stack.pop()

        # --- Арифметика и Логика (СИНХРОНИЗИРОВАНО С CODEGEN) ---
        elif op == 10: # +
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(self._mask64(a + b))
        elif op == 11: # -
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(self._mask64(a - b))
        elif op == 12: # *
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(self._mask64(a * b))
        elif op == 13: # /
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a // b if b != 0 else 0)
        elif op == 14: # ==
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(1 if a == b else 0)
        elif op == 15: # !=
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(1 if a != b else 0)
        elif op == 16: # <
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(1 if a < b else 0)
        elif op == 17: # >
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(1 if a > b else 0)
        elif op == 18: # &&
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(1 if a and b else 0)
        elif op == 19: # ||
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(1 if a or b else 0)
        elif op == 7:  # &
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a & b)
        elif op == 8:  # |
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a | b)
        elif op == 9:  # ^
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a ^ b)
        elif op == 32: # >>> (сдвиг вправо)
            b, a = self.stack.pop() % 64, self.stack.pop()
            self.stack.append(self._mask64(a) >> b)
        elif op == 33: # << (сдвиг влево)
            b, a = self.stack.pop() % 64, self.stack.pop()
            self.stack.append(self._mask64(a << b))

        # --- Управление ---
        elif op == 20: self.pc = arg
        elif op == 30: # JZ (Jump if Zero)
            cond = self.stack.pop()
            if cond == 0: self.pc = arg
        elif op == 21:
            self.call_stack.append((self.pc, self.fp))
            self.fp = len(self.stack)
            self.pc = arg
        elif op == 22:
            val = self.stack.pop()
            if not self.call_stack: self.running = False
            else:
                pc, fp = self.call_stack.pop()
                self.pc, self.fp = pc, fp
                self.stack.append(val)

        # --- Память ---
        elif op == 41: # NEW (ArrayAlloc)
            size = self.stack.pop()
            self.stack.append(self.hp)
            self.hp += int(size)
        elif op == 42: # HLOAD (ArrayAccess)
            idx, base = self.stack.pop(), self.stack.pop()
            self.stack.append(self.heap[int(base + idx)])
        elif op == 43: # HSTORE (ArrayAssign)
            val, idx, base = self.stack.pop(), self.stack.pop(), self.stack.pop()
            self.heap[int(base + idx)] = val

        # --- Системные вызовы ---
        elif op == 45: # PRINTS
            s = self._read_str(self.stack.pop())
            print(s, flush=True)
            self.stack.append(0)
        elif op == 46: # PRINTHEX
            print(f"0x{self.stack.pop():016x}", flush=True)
            self.stack.append(0)

        # --- Файлы ---
        elif op == 50: # FWRITE
            data, name = self._read_str(self.stack.pop()), self._read_str(self.stack.pop())
            with open(name, "w", encoding="utf-8") as f: f.write(data)
            self.stack.append(1)
        elif op == 51: # FAPPEND
            data, name = self._read_str(self.stack.pop()), self._read_str(self.stack.pop())
            with open(name, "a", encoding="utf-8") as f: f.write(data)
            self.stack.append(1)
        elif op == 52: # FREAD
            name = self._read_str(self.stack.pop())
            try:
                with open(name, "r", encoding="utf-8") as f: content = f.read()
                addr = self.hp
                for i, c in enumerate(content): self.heap[addr+i] = ord(c)
                self.heap[addr+len(content)] = 0
                self.hp += len(content)+1
                self.stack.append(addr)
            except: self.stack.append(0)
        elif op == 53: # FAPPEND_INT
            val, name = self.stack.pop(), self._read_str(self.stack.pop())
            with open(name, "a", encoding="utf-8") as f: f.write(str(int(val)))
            self.stack.append(1)

    def run(self):
        while self.running: self.step()