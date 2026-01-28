from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from contextlib import asynccontextmanager
import uvicorn
import traceback

# Импортируем компоненты компилятора
from xlang_codegen import CodeGen
from xvm import XVM
from main import load_program

# Глобальные переменные
vm = None
cg = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Обработчик жизненного цикла.
    Инициализирует VM и, что важно, выполняет код инициализации глобальных переменных.
    """
    global vm, cg
    print("[Server] Compiling blockchain logic...")
    try:
        # 1. Загрузка и компиляция
        vars_, funcs = load_program("main.xl")
        cg = CodeGen()
        bytecode = cg.gen(vars_, funcs)

        # 2. Инициализация VM
        vm = XVM(bytecode)
        vm.load_strings(cg.string_pool)
        vm.hp = cg.next_string_addr

        # --- BOOT SEQUENCE (КРИТИЧЕСКИ ВАЖНО) ---
        # Нужно выполнить код от начала (0) до входа в main,
        # чтобы проинициализировать глобальные переменные (chain_file и др.)
        print("[Server] Booting VM memory (initializing globals)...")
        main_addr = cg.func_addresses.get("main")

        if main_addr is not None:
            # Шагаем VM, пока не дойдем до адреса функции main
            # Это выполнит все присваивания var x = ... в глобальной области
            safety_limit = 50000
            while vm.pc < main_addr and vm.running and safety_limit > 0:
                vm.step()
                safety_limit -= 1

            if safety_limit <= 0:
                print("[Server] Warning: Boot sequence timed out, memory might be incomplete.")
        else:
            print("[Server] Warning: 'main' function not found, skipping boot sequence.")
        # ----------------------------------------

        # 3. Восстановление состояния из chain.json
        addr_load_state = cg.func_addresses.get("bc_load_state")

        # Попытка загрузить состояние
        state_loaded = False
        if addr_load_state:
            # Возвращает 1 если загружено, 0 если файл не найден/пуст
            res = vm.execute_function(addr_load_state, [])
            if res == 1:
                state_loaded = True

        if not state_loaded:
            print("[Server] Chain file not found or empty. Initializing new chain...")
            addr_init = cg.func_addresses.get("bc_init")
            if addr_init:
                vm.execute_function(addr_init, [])

        # Инициализация базы организаций
        addr_base_init = cg.func_addresses.get("base_init")
        if addr_base_init:
            vm.execute_function(addr_base_init, [])

        print("[Server] Node started successfully. Ready for requests.")

    except Exception as e:
        print(f"[Critical Startup Error] {e}")
        traceback.print_exc()

    yield

    print("[Server] Shutting down...")


# Создаем приложение с lifespan
app = FastAPI(title="Gem Blockchain API Node", lifespan=lifespan)


# --- Схемы данных API ---
class WalletRequest(BaseModel):
    pub_key: int
    role: int


class NFTRequest(BaseModel):
    nft_id: int
    owner: int
    creator: int
    doc_hash: List[int]


class TransferRequest(BaseModel):
    nft_id: int
    new_owner: int


# --- Эндпоинты ---

@app.post("/create_wallet")
def create_wallet(req: WalletRequest):
    if not vm or not cg:
        raise HTTPException(status_code=503, detail="Blockchain node not initialized")

    addr = cg.func_addresses.get("action_create_wallet")
    if addr is None:
        raise HTTPException(status_code=500, detail="Function 'action_create_wallet' not found")

    result = vm.execute_function(addr, [req.pub_key, req.role])

    # Получаем текущий индекс блока для ответа
    idx_addr = cg.globals.get('block_index')
    current_idx = vm.memory[idx_addr] if idx_addr is not None else -1

    return {
        "status": "success" if result else "error",
        "block_index": current_idx
    }


@app.post("/mint_nft")
def mint_nft(req: NFTRequest):
    if not vm or not cg:
        raise HTTPException(status_code=503, detail="Blockchain node not initialized")

    if len(req.doc_hash) != 8:
        raise HTTPException(status_code=400, detail="doc_hash must be 8 integers")

    # Выделяем память под хеш
    hash_ptr = vm.hp
    for i, val in enumerate(req.doc_hash):
        vm.heap[hash_ptr + i] = val
    vm.hp += 8

    addr = cg.func_addresses.get("action_nft_create")
    if addr is None:
        raise HTTPException(status_code=500, detail="Function 'action_nft_create' not found")

    result = vm.execute_function(addr, [req.nft_id, req.owner, req.creator, hash_ptr])

    if result == 0:
        return {"status": "error", "message": "Unauthorized creator or system error"}
    return {"status": "success"}


@app.post("/transfer_nft")
def transfer_nft(req: TransferRequest):
    if not vm or not cg:
        raise HTTPException(status_code=503, detail="Blockchain node not initialized")

    addr = cg.func_addresses.get("action_nft_transfer")
    if addr is None:
        raise HTTPException(status_code=500, detail="Function 'action_nft_transfer' not found")

    result = vm.execute_function(addr, [req.nft_id, req.new_owner])
    return {"status": "success" if result else "error"}


@app.get("/verify")
def verify_integrity():
    if not vm or not cg:
        raise HTTPException(status_code=503, detail="Blockchain node not initialized")

    addr = cg.func_addresses.get("bc_verify_full_integrity")
    if addr is None:
        return {"error": "Verification function missing"}

    result = vm.execute_function(addr, [])
    return {"is_valid": True if result == 1 else False}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)