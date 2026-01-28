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

    def _mask64(self, v): return v & 0xFFFFFFFFFFFFFFFF

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
        op, arg = self.code[self.pc], self.code[self.pc+1]
        self.pc += 2

        if op == 1: self.stack.append(arg)
        elif op == 2: (self.stack.pop() if self.stack else None)
        elif op == 3: self.stack.append(self.memory[arg])
        elif op == 4: self.memory[arg] = self.stack.pop()
        elif op == 5:
            idx = self.fp - arg - 1
            self.stack.append(self.stack[idx] if 0 <= idx < len(self.stack) else 0)
        elif op == 6:
            idx = self.fp - arg - 1
            if 0 <= idx < len(self.stack): self.stack[idx] = self.stack.pop()
        elif op == 10: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a+b))
        elif op == 11: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a-b))
        elif op == 12: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(self._mask64(a*b))
        elif op == 14: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(1 if a==b else 0)
        elif op == 9: b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a ^ b)
        elif op == 21: # CALL
            self.call_stack.append((self.pc, self.fp))
            self.fp = len(self.stack)
            self.pc = arg
        elif op == 22: # RET
            val = self.stack.pop() if self.stack else 0
            if not self.call_stack: self.running = False
            else:
                ret_pc, prev_fp = self.call_stack.pop()
                while len(self.stack) > prev_fp: self.stack.pop()
                self.pc, self.fp = ret_pc, prev_fp
                self.stack.append(val)
                if self.pc == -1: self.running = False
        elif op == 30: # JZ
            if self.stack.pop() == 0: self.pc = arg
        elif op == 41: # NEW
            size = self.stack.pop(); self.stack.append(self.hp); self.hp += int(size)
        elif op == 42: idx, base = self.stack.pop(), self.stack.pop(); self.stack.append(self.heap[int(base+idx)])
        elif op == 43: v, i, b = self.stack.pop(), self.stack.pop(), self.stack.pop(); self.heap[int(b+i)] = v
        elif op == 45: print(self._read_str(self.stack.pop()), flush=True); self.stack.append(0)
        elif op == 46: print(f"0x{self.stack.pop():016x}", flush=True); self.stack.append(0)
        elif op == 50: d, n = self._read_str(self.stack.pop()), self._read_str(self.stack.pop()); open(n,"w").write(d); self.stack.append(1)
        elif op == 51: d, n = self._read_str(self.stack.pop()), self._read_str(self.stack.pop()); open(n,"a").write(d); self.stack.append(1)
        elif op == 52:
            try:
                name = self._read_str(self.stack.pop())
                c = open(name,"r").read(); addr = self.hp
                for i, char in enumerate(c): self.heap[addr+i] = ord(char)
                self.heap[addr+len(c)] = 0; self.hp += len(c)+1; self.stack.append(addr)
            except: self.stack.append(0)
        elif op == 53: v, n = self.stack.pop(), self._read_str(self.stack.pop()); open(n,"a").write(str(int(v))); self.stack.append(1)
        elif op == 61: # json_get_hash
            k_a, idx_v, j_a = self.stack.pop(), self.stack.pop(), self.stack.pop()
            key, json_str, idx = self._read_str(k_a), self._read_str(j_a), int(idx_v) - 1
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