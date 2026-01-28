from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn

# Импортируем твои исправленные компоненты
from xlang_lexer import tokenize
from xlang_parser import Parser
from xlang_codegen import CodeGen
from xvm import XVM
from main import load_program

app = FastAPI(title="Gem Blockchain API Node")

# Глобальные объекты для работы системы
vm = None
cg = None


# Схемы данных для API
class WalletRequest(BaseModel):
    pub_key: int
    role: int


class NFTRequest(BaseModel):
    nft_id: int
    owner: int
    creator: int
    doc_hash: List[int]  # Массив из 8 чисел


class TransferRequest(BaseModel):
    nft_id: int
    new_owner: int


@app.on_event("startup")
def startup_event():
    global vm, cg
    print("[Server] Compiling blockchain logic...")
    try:
        # 1. Загрузка и компиляция всех .xl файлов
        vars_, funcs = load_program("main.xl")
        cg = CodeGen()
        bytecode = cg.gen(vars_, funcs)

        # 2. Инициализация VM
        vm = XVM(bytecode)
        vm.load_strings(cg.string_pool)
        vm.hp = cg.next_string_addr

        # 3. Восстановление состояния из chain.json
        # Вызываем bc_load_state вместо bc_init, чтобы не затереть файл
        addr_load_state = cg.func_addresses.get("bc_load_state")
        if addr_load_state:
            vm.execute_function(addr_load_state, [])
        else:
            # Если функции восстановления нет, инициализируем с нуля
            addr_init = cg.func_addresses.get("bc_init")
            vm.execute_function(addr_init, [])

        # Также инициализируем базу организаций
        addr_base_init = cg.func_addresses.get("base_init")
        vm.execute_function(addr_base_init, [])

        print("[Server] Node started successfully.")
    except Exception as e:
        print(f"[Critical Error] {e}")


# --- Эндпоинты API ---

@app.post("/create_wallet")
def create_wallet(req: WalletRequest):
    addr = cg.func_addresses.get("action_create_wallet")
    # Вызываем функцию в VM: action_create_wallet(pub_key, role)
    result = vm.execute_function(addr, [req.pub_key, req.role])
    return {"status": "success" if result else "error", "block_index": vm.memory[cg.globals['block_index']]}


@app.post("/mint_nft")
def mint_nft(req: NFTRequest):
    if len(req.doc_hash) != 8:
        raise HTTPException(status_code=400, detail="doc_hash must be 8 integers")

    # 1. Выделяем память в куче VM под хеш документа
    hash_ptr = vm.hp
    for i, val in enumerate(req.doc_hash):
        vm.heap[hash_ptr + i] = val
    vm.hp += 8

    addr = cg.func_addresses.get("action_nft_create")
    # action_nft_create(nft_id, owner, creator, doc_hash_ptr)
    result = vm.execute_function(addr, [req.nft_id, req.owner, req.creator, hash_ptr])

    if result == 0:
        return {"status": "error", "message": "Unauthorized creator or system error"}
    return {"status": "success"}


@app.post("/transfer_nft")
def transfer_nft(req: TransferRequest):
    addr = cg.func_addresses.get("action_nft_transfer")
    result = vm.execute_function(addr, [req.nft_id, req.new_owner])
    return {"status": "success" if result else "error"}


@app.get("/verify")
def verify_integrity():
    addr = cg.func_addresses.get("bc_verify_full_integrity")
    result = vm.execute_function(addr, [])
    return {"is_valid": True if result == 1 else False}


if __name__ == "__main__":
    # Запуск сервера на всех интерфейсах (0.0.0.0) для доступа из локальной сети
    uvicorn.run(app, host="0.0.0.0", port=8000)