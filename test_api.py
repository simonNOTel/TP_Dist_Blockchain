import requests
import time

BASE_URL = "http://127.0.0.1:8000"


def test_create_wallet():
    print("\n--- 1. Testing Wallet Creation ---")
    payload = {
        "pub_key": 0xABCD1234,
        "role": 1
    }
    try:
        resp = requests.post(f"{BASE_URL}/create_wallet", json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Failed: {e}")


def test_mint_nft():
    print("\n--- 2. Testing NFT Minting ---")
    # Хеш документа (8 чисел)
    doc_hash = [
        0x11111111, 0x22222222, 0x33333333, 0x44444444,
        0x55555555, 0x66666666, 0x77777777, 0x88888888
    ]

    payload = {
        "nft_id": 101,
        "owner": 0xABCD1234,
        "creator": 0x375,  # 0x375 - это ID авторизованной организации в base.xl
        "doc_hash": doc_hash
    }
    try:
        resp = requests.post(f"{BASE_URL}/mint_nft", json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Failed: {e}")


def test_verify():
    print("\n--- 3. Testing Chain Integrity ---")
    try:
        resp = requests.get(f"{BASE_URL}/verify")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Failed: {e}")


if __name__ == "__main__":
    # Убедитесь, что server.py запущен в другом окне!
    test_create_wallet()
    time.sleep(1)
    test_mint_nft()
    time.sleep(1)
    test_verify()