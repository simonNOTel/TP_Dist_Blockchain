import sys
import re

class XVM:
    def __init__(self, code):
        self.code = code
        self.memory = [0] * 5000
        self.heap = [0] * 500000
        self.stack = []
        self.call_stack = []
        self.hp = 200000
        self.pc = 0
        self.fp = 0
        self.running = True

    def _mask64(self, v):
        return v & 0xFFFFFFFFFFFFFFFF

    def dump_heap(self, filename="heap_debug.log"):
        print(f"[VM] Saving heap dump to {filename}...")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"--- XVM HEAP DUMP - --\n")
            f.write(f"PC: {self.pc} | FP: {self.fp} | HP: {self.hp}\n")
            f.write("-" * 30 + "\n")
            for addr in range(100000, self.hp + 10):
                val = self.heap[addr]
                if val == 0 and addr > self.hp: continue
                char_repr = f"| '{chr(val)}'" if 32 <= val <= 126 else ""
                f.write(f"[{addr}] {val:<20} {char_repr}\n")

    def load_strings(self, smap):
        for addr, s in smap.items():
            for i, c in enumerate(s): self.heap[addr + i] = ord(c)
            self.heap[addr + len(s)] = 0

    def _read_str(self, addr):
        res = ""
        addr = int(addr)
        while addr < len(self.heap) and self.heap[addr] != 0:
            res += chr(int(self.heap[addr]))
            addr += 1
        return res

    def step(self):
        if self.pc >= len(self.code) or self.pc < 0:
            self.running = False
            return
        op = self.code[self.pc]
        arg = self.code[self.pc + 1]
        self.pc += 2

        # --- Базовые операции ---
        if op == 1: self.stack.append(arg)
        elif op == 2:
            if self.stack: self.stack.pop()
        elif op == 3: self.stack.append(self.memory[arg])
        elif op == 4:
            if self.stack: self.memory[arg] = self.stack.pop()
        elif op == 5:
            idx = self.fp - arg - 1
            self.stack.append(self.stack[idx] if 0 <= idx < len(self.stack) else 0)
        elif op == 6:
            idx = self.fp - arg - 1
            if 0 <= idx < len(self.stack) and self.stack: self.stack[idx] = self.stack.pop()

        # --- Арифметика и Логика ---
        elif op == 10: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a + b))
        elif op == 11: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a - b))
        elif op == 12: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a * b))
        elif op == 13: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a // b if b != 0 else 0)
        elif op == 14: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a == b else 0)
        elif op == 15: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a != b else 0)
        elif op == 16: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a < b else 0)
        elif op == 17: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a > b else 0)
        elif op == 18: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a and b else 0)
        elif op == 19: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a or b else 0)
        elif op == 7:  b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a & b)
        elif op == 8:  b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a | b)
        elif op == 9:  b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a ^ b)
        elif op == 32: b, a = self.stack.pop() % 64, self.stack.pop(); self.stack.append(self._mask64(a) >> b)
        elif op == 33: b, a = self.stack.pop() % 64, self.stack.pop(); self.stack.append(self._mask64(a << b))

        # --- Управление ---
        elif op == 20: self.pc = arg
        elif op == 30:
            if self.stack.pop() == 0: self.pc = arg
        elif op == 21: # CALL
            self.call_stack.append((self.pc, self.fp))
            self.fp = len(self.stack)
            self.pc = arg
        elif op == 22: # RET
            val = self.stack.pop() if len(self.stack) > 0 else 0
            if not self.call_stack: self.running = False
            else:
                ret_pc, prev_fp = self.call_stack.pop()
                while len(self.stack) > prev_fp: self.stack.pop() # Чистим кадр
                self.pc, self.fp = ret_pc, prev_fp
                self.stack.append(val)
                if self.pc == -1: self.running = False

        # --- Память и Системные вызовы ---
        elif op == 41: size = self.stack.pop(); self.stack.append(self.hp); self.hp += int(size)
        elif op == 42: idx, base = self.stack.pop(), self.stack.pop(); self.stack.append(self.heap[int(base + idx)])
        elif op == 43: v, i, b = self.stack.pop(), self.stack.pop(), self.stack.pop(); self.heap[int(b + i)] = v
        elif op == 45: print(self._read_str(self.stack.pop()), flush=True); self.stack.append(0)
        elif op == 46: print(f"0x{self.stack.pop():016x}", flush=True); self.stack.append(0)
        elif op == 50: d, n = self._read_str(self.stack.pop()), self._read_str(self.stack.pop()); open(n,"w", encoding="utf-8").write(d); self.stack.append(1)
        elif op == 51: d, n = self._read_str(self.stack.pop()), self._read_str(self.stack.pop()); open(n,"a", encoding="utf-8").write(d); self.stack.append(1)
        elif op == 52:
            try:
                name = self._read_str(self.stack.pop())
                with open(name, "r", encoding="utf-8") as f: content = f.read()
                addr = self.hp
                for i, c in enumerate(content): self.heap[addr+i] = ord(c)
                self.heap[addr+len(content)] = 0; self.hp += len(content)+1; self.stack.append(addr)
            except: self.stack.append(0)
        elif op == 53: v, n = self.stack.pop(), self._read_str(self.stack.pop()); open(n,"a", encoding="utf-8").write(str(int(v))); self.stack.append(1)
        elif op == 61:
            k_a, i_v, j_a = self.stack.pop(), self.stack.pop(), self.stack.pop()
            key, json_str, idx = self._read_str(k_a), self._read_str(j_a), int(i_v) - 1
            blocks = json_str.split("  {")
            if 1 <= idx + 1 < len(blocks):
                match = re.search(fr'"{key}":\s*"(-?\d+)"', blocks[idx+1])
                self.stack.append(int(match.group(1)) if match else 0)
            else: self.stack.append(0)

    def execute_function(self, addr, args):
        for a in reversed(args): self.stack.append(a)
        self.call_stack.append((-1, self.fp))
        self.fp = len(self.stack)
        self.pc = addr
        self.running = True
        while self.running: self.step()
        return self.stack.pop() if self.stack else 0

    def run(self):
        while self.running: self.step()