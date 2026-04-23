# tools/generate_mystery_code.py

"""
Gerador de códigos Mystery Gift -
"""

import hashlib
import base64
import sys

# Chave secreta
SECRET_KEY = "PkmTD-SecretKey-2026"


def encrypt_code(code: str, length: int = 8) -> str:
    """Converte qualquer texto em um código criptografado"""
    # Cria o hash
    salted = f"{code}|{SECRET_KEY}"
    hash_bytes = hashlib.sha256(salted.encode()).digest()

    # Converte para base64 e limpa
    encoded = base64.b64encode(hash_bytes).decode('ascii')
    clean = ''.join(c for c in encoded if c.isalnum()).upper()

    # Retorna do tamanho desejado
    return clean[:length]


if __name__ == "__main__":
    print("=" * 50)
    print("GERADOR DE CÓDIGOS MYSTERY GIFT")
    print("=" * 50)

    if len(sys.argv) > 1:
        # Pega o código da linha de comando
        original = sys.argv[1].upper()
        encrypted = encrypt_code(original, 8)

        print(f"\n CÓDIGO GERADO:")
        print(f"   Original: {original}")
        print(f"   Criptografado: {encrypted}")
        print(f"\n Copie este código:")
        print(f"   {encrypted}")

    else:
        # Modo interativo
        print("\n Digite os códigos (ou 'sair' para terminar):\n")

        while True:
            code = input("Código: ").strip().upper()
            if code == 'SAIR':
                break
            if code:
                encrypted = encrypt_code(code, 8)
                print(f"   → {encrypted}\n")

    print("\n" + "=" * 50)