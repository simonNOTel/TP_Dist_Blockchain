import os
import json


class XVM:
    def __init__(self, code):
        # Память: 2000 ячеек для переменных
        self.memory = [0] * 2000
        self.stack = []
        self.call_stack = []
        # Куча: 50 000 ячеек для массивов и данных
        self.heap = [0] * 50000
        self.hp = 0
        self.pc = 0
        self.frame_base = 0
        self.code = code
        self.running = True

    def _mask64(self, v):
        return v & 0xFFFFFFFFFFFFFFFF

    def _read_string_from_heap(self, addr):
        """Безопасное извлечение строки из кучи (ASCII)."""
        s = ""
        curr = int(addr)
        while curr < len(self.heap):
            val = int(self.heap[curr]) & 0xFF
            if val == 0: break
            s += chr(val)
            curr += 1
        return s

    def run(self):
        while self.running:
            try:
                self.step()
            except Exception as e:
                print(f"Runtime Error at PC {self.pc - 2}: {e}")
                self.running = False

    def step(self):
        if self.pc >= len(self.code):
            self.running = False
            return

        op = self.code[self.pc]
        o = self.code[self.pc + 1]
        self.pc += 2

        # Управление
        if op == 0:
            self.running = False
        elif op == 1:
            self.stack.append(self._mask64(o))
        elif op == 2:
            (self.stack.pop() if self.stack else 0)

        # Переменные
        elif op == 3:
            self.stack.append(self.memory[o])  # Load Global
        elif op == 4:
            self.memory[o] = self.stack.pop()  # Store Global
        elif op == 5:
            self.stack.append(self.memory[self.frame_base + o])  # Load Local
        elif op == 6:
            self.memory[self.frame_base + o] = self.stack.pop()  # Store Local

        # Арифметика (64-бит)
        elif op == 10:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a + b))
        elif op == 11:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a - b))
        elif op == 12:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a * b))
        elif op == 14:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a == b else 0)
        elif op == 15:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a > b else 0)
        elif op == 16:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a < b else 0)

        # Переходы и функции
        elif op == 20:
            self.pc = o  # JMP
        elif op == 21:  # JZ (Jump if Zero)
            if self.stack.pop() == 0: self.pc = o
        elif op == 22:  # RET
            ret_val = self.stack.pop()
            if self.call_stack:
                self.pc, self.frame_base = self.call_stack.pop()
                self.stack.append(ret_val)
            else:
                self.running = False
        elif op == 23:  # CALL
            self.call_stack.append((self.pc, self.frame_base))
            self.frame_base += 100
            self.pc = o

        # Битовые операции (важны для криптографии)
        elif op == 25:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a & b)
        elif op == 26:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a | b)
        elif op == 27:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a ^ b)
        elif op == 28:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a >> b)
        elif op == 29:
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append((a & 0xFFFFFFFFFFFFFFFF) >> b)

        # Куча / Массивы
        elif op == 41:  # NEW
            size = int(self.stack.pop())
            self.stack.append(self.hp)
            self.hp += size
        elif op == 42:  # HLOAD
            idx, addr = int(self.stack.pop()), int(self.stack.pop())
            self.stack.append(self.heap[addr + idx])
        elif op == 43:  # HSTORE
            val, idx, addr = self.stack.pop(), int(self.stack.pop()), int(self.stack.pop())
            self.heap[addr + idx] = val

        # Ввод-вывод и Блокчейн
        elif op == 45:  # PRINTS
            print(self._read_string_from_heap(self.stack.pop()))
        elif op == 46:  # PRINTHEX
            print(f"0x{self.stack.pop():016x}")
        elif op == 50:  # FWRITE
            c_ptr, f_ptr = self.stack.pop(), self.stack.pop()
            with open(self._read_string_from_heap(f_ptr), "w") as f:
                f.write(self._read_string_from_heap(c_ptr))
        elif op == 51:  # FAPPEND
            c_ptr, f_ptr = self.stack.pop(), self.stack.pop()
            with open(self._read_string_from_heap(f_ptr), "a") as f:
                f.write(self._read_string_from_heap(c_ptr))
        elif op == 55:  # BC_SAVE
            size, addr = int(self.stack.pop()), int(self.stack.pop())
            data = [int(self.heap[addr + i]) for i in range(size)]
            chain = []
            if os.path.exists("chain.json"):
                with open("chain.json", "r") as f: chain = json.load(f)
            chain.append({"data": data, "timestamp": "2026-01-23"})
            with open("chain.json", "w") as f:
                json.dump(chain, f, indent=4)