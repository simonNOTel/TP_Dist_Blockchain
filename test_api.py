import requests
import time

BASE_URL = "http://127.0.0.1:8000"


def run_full_test():
    print("=== STARTING FULL SYSTEM TEST ===\n")

    # --- ШАГ 1: Создание кошелька и получение ключей ---
    print("[1] Creating Wallet...")
    # Больше не отправляем pub_key, система сама его генерирует
    payload_wallet = {
        "role": 1
    }

    try:
        resp = requests.post(f"{BASE_URL}/create_wallet", json=payload_wallet)
        data = resp.json()

        if resp.status_code != 200 or data.get("status") != "success":
            print(f"❌ Wallet creation failed: {data}")
            return

        # Сохраняем полученные ключи
        my_pub_key = data["wallet"]["public_key"]
        my_priv_key = data["wallet"]["private_key"]

        print(f"✅ Wallet Created!")
        print(f"   -> Your ID (Public Key): {my_pub_key}")
        print(f"   -> Your Secret (Private Key): {my_priv_key}")
        print(f"   -> Block Index: {data.get('block_index')}\n")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    time.sleep(1)

    # --- ШАГ 2: Создание (Минтинг) NFT с подписью ---
    print("[2] Minting NFT (Signed with Private Key)...")

    # Хеш документа (8 чисел)
    doc_hash = [10, 20, 30, 40, 50, 60, 70, 80]

    payload_mint = {
        "nft_id": 777,
        "owner": my_pub_key,  # Мы владельцы
        "creator": my_pub_key,  # Мы создатели (для теста)
        "private_key": my_priv_key,  # <--- ВАЖНО: Подписываем запрос
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

    # --- ШАГ 3: Передача NFT (Трансфер) с подписью ---
    print("[3] Transferring NFT to new owner...")

    payload_transfer = {
        "nft_id": 777,
        "new_owner": 999999,  # Какой-то другой пользователь
        "private_key": my_priv_key  # <--- ВАЖНО: Подтверждаем владение
    }

    try:
        resp = requests.post(f"{BASE_URL}/transfer_nft", json=payload_transfer)
        data = resp.json()

        if data.get("status") == "success":
            print(f"✅ NFT Transferred successfully!\n")
        else:
            print(f"❌ Transfer failed: {data}\n")
    except Exception as e:
        print(f"❌ Error: {e}")

    time.sleep(1)

    # --- ШАГ 4: Проверка целостности блокчейна ---
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


if __name__ == "__main__":
    run_full_test()