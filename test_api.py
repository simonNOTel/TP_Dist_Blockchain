import requests
import time
import random

BASE_URL = "http://127.0.0.1:8000"


def run_full_test():
    print("=== STARTING FULL SYSTEM TEST ===\n")

    # Генерируем уникальный ID для этого теста
    TEST_NFT_ID = random.randint(1000, 999999)

    print("[1] Creating Wallet...")
    payload_wallet = {"role": 1}

    try:
        resp = requests.post(f"{BASE_URL}/create_wallet", json=payload_wallet)
        data = resp.json()
        if resp.status_code != 200 or data.get("status") != "success":
            print(f"❌ Wallet creation failed: {data}")
            return

        my_pub_key = data["wallet"]["public_key"]
        my_priv_key = data["wallet"]["private_key"]
        print(f"✅ Wallet Created! ID: {my_pub_key}")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    time.sleep(1)

    print(f"[2] Minting NFT #{TEST_NFT_ID}...")

    doc_hash = [10, 20, 30, 40, 50, 60, 70, 80]

    payload_mint = {
        "nft_id": TEST_NFT_ID,
        "owner": my_pub_key,
        "creator": my_pub_key,
        "private_key": my_priv_key,
        "doc_hash": doc_hash
    }

    try:
        resp = requests.post(f"{BASE_URL}/mint_nft", json=payload_mint)
        data = resp.json()
        if data.get("status") == "success":
            print(f"✅ NFT Minted successfully!\n")
        else:
            print(f"❌ Minting failed: {data}\n")
    except Exception as e:
        print(f"❌ Error: {e}")

    time.sleep(1)

    print(f"[3] Transferring NFT #{TEST_NFT_ID}...")

    payload_transfer = {
        "nft_id": TEST_NFT_ID,
        "new_owner": 999999,
        "private_key": my_priv_key
    }

    try:
        resp = requests.post(f"{BASE_URL}/transfer_nft", json=payload_transfer)
        if resp.json().get("status") == "success":
            print(f"✅ NFT Transferred successfully!\n")
        else:
            print(f"❌ Transfer failed\n")
    except Exception as e:
        print(f"❌ Error: {e}")

    # --- ШАГ 4: Проверка целостности ---
    print("[4] Verifying Chain Integrity...")
    try:
        resp = requests.get(f"{BASE_URL}/verify")
        data = resp.json()

        if data.get("is_valid") == True:
            print(f"✅ SYSTEM INTEGRITY CONFIRMED. All hashes are valid.")
        else:
            print(f"⛔ CRITICAL ALERT: CHAIN IS BROKEN!")
    except Exception as e:
        print(f"❌ Error: {e}")


# ОБЯЗАТЕЛЬНО: Точка входа для запуска
if __name__ == "__main__":
    run_full_test()

# & "C:\Users\InfSec-08\AppData\Local\Programs\Python\Python313\python.exe" server.py