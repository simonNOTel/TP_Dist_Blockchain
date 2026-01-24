import json


class XVM:
    def __init__(self, code):
        self.code = code
        self.memory = [0] * 5000
        self.heap = [0] * 500000
        self.stack = []
        self.call_stack = []
        self.hp = 10000
        self.pc = 0
        self.fp = 0
        self.running = True

    def _mask64(self, v):
        return v & 0xFFFFFFFFFFFFFFFF

    def load_strings(self, smap):
        for addr, s in smap.items():
            for i, c in enumerate(s): self.heap[addr + i] = ord(c)
            self.heap[addr + len(s)] = 0

    def _read_str(self, addr):
        res = "";
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

        if op == 1:
            self.stack.append(arg)
        elif op == 2:
            self.stack.pop()
        elif op == 3:
            self.stack.append(self.memory[arg])
        elif op == 4:
            self.memory[arg] = self.stack.pop()
        elif op == 5:
            self.stack.append(self.stack[self.fp - arg - 1])
        elif op == 6:
            self.stack[self.fp - arg - 1] = self.stack.pop()

        # --- ARITHMETIC & LOGIC ---
        elif op == 10:  # ADD
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a + b))
        elif op == 11:  # SUB
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a - b))
        elif op == 12:  # MUL
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a * b))
        elif op == 13:  # DIV
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(int(a / b) if b != 0 else 0)
        elif op == 14:  # EQ (==)
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a == b else 0)
        elif op == 15:  # NEQ (!=)
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a != b else 0)
        elif op == 16:  # GT (>)
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a > b else 0)
        elif op == 17:  # LT (<)
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a < b else 0)
        elif op == 18:  # AND (&)
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a & b)
        elif op == 19:  # OR (|)
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a | b)
        # ---------------------------

        elif op == 23:  # XOR (^)
            b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a ^ b)
        elif op == 24:  # Unsigned Right Shift (>>>)
            b, a = self.stack.pop() % 64, self.stack.pop()
            self.stack.append(self._mask64(a) >> b)
        elif op == 25:  # Right Shift (>>)
            b, a = self.stack.pop() % 64, self.stack.pop()
            self.stack.append(a >> b)

        elif op == 20:  # JMP
            self.pc = arg
        elif op == 30:  # JZ (Jump if Zero)
            if self.stack.pop() == 0: self.pc = arg
        elif op == 21:  # CALL
            self.call_stack.append((self.pc, self.fp))
            self.fp = len(self.stack)
            self.pc = arg
        elif op == 22:  # RET
            val = self.stack.pop()
            if not self.call_stack:
                self.running = False
            else:
                pc, fp = self.call_stack.pop()
                self.pc, self.fp = pc, fp
                self.stack.append(val)

        elif op == 41:  # NEW
            size = self.stack.pop()
            if size > 1000000: size = 0  # Защита от кривых индексов
            self.stack.append(self.hp)
            self.hp += int(size)
        elif op == 42:  # HLOAD
            idx, base = self.stack.pop(), self.stack.pop()
            addr = int(base + idx)
            self.stack.append(self.heap[addr] if 0 <= addr < len(self.heap) else 0)
        elif op == 43:  # HSTORE
            val, idx, base = self.stack.pop(), self.stack.pop(), self.stack.pop()
            addr = int(base + idx)
            if 0 <= addr < len(self.heap): self.heap[addr] = val

        elif op == 45:  # PRINTS
            print(self._read_str(self.stack.pop())); self.stack.append(0)
        elif op == 46:  # PRINTHEX
            print(f"0x{self.stack.pop():016x}"); self.stack.append(0)

    def run(self):
        while self.running:
            self.step()