# src/network/firewall_utils.py

import subprocess
import sys
import os

def request_firewall_permission(port=12345, description="Pokemon TD Multiplayer"):
    """
    Tenta adicionar uma regra no firewall do Windows para liberar a porta.
    Retorna True se bem-sucedido ou já existir, False em caso de erro.
    """
    if sys.platform != 'win32':
        print("[FIREWALL] Sistema não é Windows, pulando configuração.")
        return True

    try:
        # Verifica se já existe uma regra
        check_cmd = f'netsh advfirewall firewall show rule name="{description}"'
        result = subprocess.run(check_cmd, capture_output=True, text=True, shell=True)
        if "No rules match" not in result.stdout and "No rules match" not in result.stderr:
            print(f"[FIREWALL] Regra '{description}' já existe.")
            return True

        # Adiciona regra de entrada
        add_cmd = f'netsh advfirewall firewall add rule name="{description}" dir=in action=allow protocol=TCP localport={port}'
        subprocess.run(add_cmd, shell=True, check=True)
        print(f"[FIREWALL] Porta {port} liberada com sucesso.")
        return True
    except Exception as e:
        print(f"[FIREWALL] Falha ao configurar firewall: {e}")
        return False