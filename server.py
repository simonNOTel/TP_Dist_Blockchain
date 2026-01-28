from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from contextlib import asynccontextmanager
import uvicorn
import traceback

from xlang_codegen import CodeGen
from xvm import XVM
from main import load_program

vm = None
cg = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vm, cg
    print("[Server] Compiling blockchain logic...")
    try:
        vars_, funcs = load_program("main.xl")
        cg = CodeGen()
        bytecode = cg.gen(vars_, funcs)

        vm = XVM(bytecode)
        vm.load_strings(cg.string_pool)
        vm.hp = cg.next_string_addr

        print("[Server] Booting VM memory...")
        main_addr = cg.func_addresses.get("main")

        if main_addr is not None:
            safety_limit = 50000
            while vm.pc < main_addr and vm.running and safety_limit > 0:
                vm.step()
                safety_limit -= 1

        addr_load_state = cg.func_addresses.get("bc_load_state")
        state_loaded = False
        if addr_load_state:
            res = vm.execute_function(addr_load_state, [])
            if res == 1: state_loaded = True

        if not state_loaded:
            print("[Server] Initializing new chain...")
            addr_init = cg.func_addresses.get("bc_init")
            if addr_init: vm.execute_function(addr_init, [])

        addr_base_init = cg.func_addresses.get("base_init")
        if addr_base_init: vm.execute_function(addr_base_init, [])

        print("[Server] Node started successfully.")

    except Exception as e:
        print(f"[Critical Startup Error] {e}")
        traceback.print_exc()
    yield
    print("[Server] Shutting down...")


app = FastAPI(title="Gem Blockchain API Node", lifespan=lifespan)


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


# --- Эндпоинты ---

@app.post("/create_wallet")
def create_wallet(req: CreateWalletRequest):
    if not vm or not cg: raise HTTPException(status_code=503)

    addr = cg.func_addresses.get("action_create_wallet")
    if addr is None: raise HTTPException(status_code=500)

    # Вызываем функцию VM. Она сама сгенерирует ключи.
    # Возвращает адрес массива в памяти (куче), где лежат [pub, priv]
    keys_ptr = vm.execute_function(addr, [req.role])

    # Считываем данные из памяти VM
    # [0] = Public Key, [1] = Private Key
    pub_key = vm.heap[keys_ptr]
    priv_key = vm.heap[keys_ptr + 1]

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
    if not vm or not cg: raise HTTPException(status_code=503)
    if len(req.doc_hash) != 8: raise HTTPException(status_code=400)

    hash_ptr = vm.hp
    for i, val in enumerate(req.doc_hash): vm.heap[hash_ptr + i] = val
    vm.hp += 8

    addr = cg.func_addresses.get("action_nft_create")
    result = vm.execute_function(addr, [req.nft_id, req.owner, req.creator, hash_ptr, req.private_key])

    if result == 0: return {"status": "error", "message": "Unauthorized or system error"}
    return {"status": "success"}


@app.post("/transfer_nft")
def transfer_nft(req: TransferRequest):
    if not vm or not cg: raise HTTPException(status_code=503)
    addr = cg.func_addresses.get("action_nft_transfer")
    result = vm.execute_function(addr, [req.nft_id, req.new_owner, req.private_key])
    return {"status": "success" if result else "error"}


@app.get("/verify")
def verify_integrity():
    if not vm or not cg: raise HTTPException(status_code=503)
    addr = cg.func_addresses.get("bc_verify_full_integrity")
    result = vm.execute_function(addr, [])
    return {"is_valid": True if result == 1 else False}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)