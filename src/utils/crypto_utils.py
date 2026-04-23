# src/utils/crypto_utils.py

"""
Utilitários de criptografia para Mystery Gift
"""

import hashlib
import base64
SECRET_KEY = "PkmTD-SecretKey-2026"


class MysteryGiftCrypto:
    """Sistema de criptografia para códigos Mystery Gift"""

    @staticmethod
    def encrypt_code(code: str, length: int = 8) -> str:
        """
        Criptografa um código - MESMO ALGORITMO DO GERADOR!
        """
        # Cria o hash (MESMO FORMATO do gerador)
        salted = f"{code}|{SECRET_KEY}"
        hash_bytes = hashlib.sha256(salted.encode()).digest()

        # Converte para base64 e limpa
        encoded = base64.b64encode(hash_bytes).decode('ascii')
        clean = ''.join(c for c in encoded if c.isalnum()).upper()

        # Retorna do tamanho desejado
        return clean[:length]

    @staticmethod
    def verify_code(original_code: str, encrypted_code: str) -> bool:
        """Verifica se o código original corresponde ao código criptografado"""
        length = len(encrypted_code)
        expected = MysteryGiftCrypto.encrypt_code(original_code, length)
        return expected == encrypted_code


# Instância global
mystery_crypto = MysteryGiftCrypto()