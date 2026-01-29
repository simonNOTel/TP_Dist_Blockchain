import hashlib
import nacl.signing
import nacl.encoding


# Функция для превращения байтов в список 64-битных чисел (для VM)
def bytes_to_vm_words(data_bytes):
    words = []
    # Разбиваем по 8 байт (64 бита)
    for i in range(0, len(data_bytes), 8):
        chunk = data_bytes[i:i + 8]
        # Дополняем нулями, если кусок меньше 8 байт
        if len(chunk) < 8:
            chunk = chunk.ljust(8, b'\x00')
        val = int.from_bytes(chunk, byteorder='big')
        words.append(val)
    return words


def get_sha512_hash(data_bytes):
    """
    Возвращает хеш как список из 8 целых чисел (8 x 64 бит = 512 бит).
    Это соответствует структуре h0-h7 в chain.json.
    """
    digest = hashlib.sha512(data_bytes).digest()
    return bytes_to_vm_words(digest)


def generate_ed25519_keys():
    """
    Генерирует пару ключей.
    Возвращает кортеж (список слов публичного ключа, список слов приватного ключа).
    Ключ Ed25519 — это 32 байта, то есть 4 числа по 64 бита.
    """
    signing_key = nacl.signing.SigningKey.generate()
    verify_key = signing_key.verify_key

    priv_bytes = signing_key.encode()
    pub_bytes = verify_key.encode()

    return bytes_to_vm_words(pub_bytes), bytes_to_vm_words(priv_bytes)


def sign_data(message_bytes, priv_key_words):
    """
    Подписывает сообщение.
    На вход принимает сообщение и приватный ключ (в формате списка чисел VM).
    """
    # Восстанавливаем байты ключа из чисел VM
    priv_bytes = b''.join([val.to_bytes(8, 'big') for val in priv_key_words])

    signing_key = nacl.signing.SigningKey(priv_bytes)
    signed = signing_key.sign(message_bytes)

    # Возвращаем подпись (64 байта -> 8 слов)
    return bytes_to_vm_words(signed.signature)