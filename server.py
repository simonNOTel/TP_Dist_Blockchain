from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from contextlib import asynccontextmanager
import uvicorn
import traceback
import json
import os

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
    Обработчик жизненного цикла приложения.
    Запускается при старте сервера и инициализирует блокчейн.
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

        # --- BOOT SEQUENCE ---
        print("[Server] Booting VM memory...")
        main_addr = cg.func_addresses.get("main")

        # Прокручиваем VM до начала main(), чтобы инициализировать глобальные переменные
        if main_addr is not None:
            safety_limit = 50000
            while vm.pc < main_addr and vm.running and safety_limit > 0:
                vm.step()
                safety_limit -= 1

        # 3. Попытка восстановить состояние из chain.json
        addr_load_state = cg.func_addresses.get("bc_load_state")
        state_loaded = False
        if addr_load_state:
            res = vm.execute_function(addr_load_state, [])
            if res == 1:
                state_loaded = True

        # Если файла нет или он пуст, инициализируем новую цепочку
        if not state_loaded:
            print("[Server] Initializing new chain...")
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


# Создаем приложение
app = FastAPI(title="Gem Blockchain API Node", lifespan=lifespan)


# --- Схемы данных API ---

class CreateWalletRequest(BaseModel):
    role: int


class NFTRequest(BaseModel):
    nft_id: int
    owner: int
    creator: int
    private_key: int
    doc_hash: List[int]


class TransferRequest(BaseModel):
    nft_id: int
    new_owner: int
    private_key: int


# --- Вспомогательные функции ---

def check_nft_exists(nft_id):
    """Проверяет, существует ли уже NFT с таким ID в файле chain.json"""
    if not os.path.exists("chain.json"):
        return False
    try:
        with open("chain.json", "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content: return False
            data = json.loads(content)

            for block in data:
                # Тип 2 = NFT Creation
                if block.get("type") == 2:
                    payload = block.get("payload", {})
                    if payload.get("nft_id") == nft_id:
                        return True
    except Exception:
        # Если ошибка чтения JSON, считаем, что дубликатов нет (или файл битый)
        pass
    return False


# --- Эндпоинты ---

@app.post("/create_wallet")
def create_wallet(req: CreateWalletRequest):
    if not vm or not cg:
        raise HTTPException(status_code=503, detail="Node not initialized")

    addr = cg.func_addresses.get("action_create_wallet")
    if addr is None:
        raise HTTPException(status_code=500, detail="Function not found")

    # Вызываем функцию VM. Она сама сгенерирует ключи.
    # Возвращает адрес массива в памяти [pub, priv]
    keys_ptr = vm.execute_function(addr, [req.role])

    # Считываем ключи из памяти VM
    pub_key = vm.heap[keys_ptr]
    priv_key = vm.heap[keys_ptr + 1]

    # Получаем текущий индекс блока
    idx_addr = cg.globals.get('block_index')
    current_idx = vm.memory[idx_addr] if idx_addr is not None else -1

    return {
        "status": "success",
        "block_index": current_idx,
        "wallet": {
            "public_key": pub_key,
            "private_key": priv_key
        }
    }


@app.post("/mint_nft")
def mint_nft(req: NFTRequest):
    if not vm or not cg:
        raise HTTPException(status_code=503, detail="Node not initialized")

    if len(req.doc_hash) != 8:
        raise HTTPException(status_code=400, detail="doc_hash must be 8 integers")

    # --- ПРОВЕРКА НА ДУБЛИКАТЫ ---
    if check_nft_exists(req.nft_id):
        raise HTTPException(status_code=400, detail=f"NFT ID {req.nft_id} already exists!")
    # -----------------------------

    # Записываем хеш документа в память VM
    hash_ptr = vm.hp
    for i, val in enumerate(req.doc_hash):
        vm.heap[hash_ptr + i] = val
    vm.hp += 8

    addr = cg.func_addresses.get("action_nft_create")
    # Передаем: ID, Владелец, Создатель, Указатель на хеш, Приватный ключ
    result = vm.execute_function(addr, [req.nft_id, req.owner, req.creator, hash_ptr, req.private_key])

    if result == 0:
        return {"status": "error", "message": "Unauthorized or system error"}
    return {"status": "success"}


@app.post("/transfer_nft")
def transfer_nft(req: TransferRequest):
    if not vm or not cg:
        raise HTTPException(status_code=503, detail="Node not initialized")

    addr = cg.func_addresses.get("action_nft_transfer")

    result = vm.execute_function(addr, [req.nft_id, req.new_owner, req.private_key])

    return {"status": "success" if result else "error"}


@app.get("/verify")
def verify_integrity():
    if not vm or not cg:
        raise HTTPException(status_code=503, detail="Node not initialized")

    addr = cg.func_addresses.get("bc_verify_full_integrity")
    result = vm.execute_function(addr, [])

    return {"is_valid": True if result == 1 else False}


if __name__ == "__main__":
    # Запускаем сервер на всех интерфейсах
    uvicorn.run(app, host="0.0.0.0", port=8000)