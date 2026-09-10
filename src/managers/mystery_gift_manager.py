# src/managers/mystery_gift_manager.py

"""
Gerenciador do sistema Mystery Gift
Controla códigos resgatados e distribuição de Pokémon
Com suporte para histórico e códigos inválidos
Toca o som de item raro ao resgatar com sucesso
"""

from datetime import datetime
from src.utils.crypto_utils import mystery_crypto
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class MysteryGiftManager:
    """Gerencia os códigos resgatados pelo jogador"""

    def __init__(self, player):
        self.player = player

        # Inicializa o registro de códigos resgatados no player se não existir
        if not hasattr(self.player, 'redeemed_codes'):
            self.player.redeemed_codes = {}
            print("[MYSTERY_GIFT] Registro de códigos resgatados inicializado")

        # Inicializa histórico de gifts
        if not hasattr(self.player, 'mystery_gift_history'):
            self.player.mystery_gift_history = []
            print("[MYSTERY_GIFT] Histórico de gifts inicializado")

    def can_redeem_code(self, raw_code):
        """
        Verifica se o código pode ser resgatado
        raw_code é o código que o jogador DIGITOU (ex: 0BR1G4D0P0RJ0G4R)
        Retorna: (bool, str, dict) -> (pode_resgatar, mensagem, info_codigo)
        """
        from src.data.mystery_gift_data import get_code_info

        # ===== CRIPTOGRAFA O CÓDIGO QUE O JOGADOR DIGITOU =====
        encrypted_code = mystery_crypto.encrypt_code(raw_code, length=8)

        print(f"[MYSTERY_GIFT] Código digitado: {raw_code}")
        print(f"[MYSTERY_GIFT] Código criptografado: {encrypted_code}")

        # ===== BUSCA O CÓDIGO CRIPTOGRAFADO NO BANCO =====
        code_info = get_code_info(encrypted_code)
        if not code_info:
            return False, "Código inválido! Este código não existe.", None

        # Verifica se o código está inválido (evento encerrado)
        if code_info.get("invalid", False):
            event_name = code_info.get("event_name", "Evento")
            return False, f"Este evento ({event_name}) já foi encerrado! Código não está mais disponível.", code_info

        # Verifica se já foi resgatado neste save (usa o código criptografado como chave)
        if encrypted_code in self.player.redeemed_codes:
            redeemed_date = self.player.redeemed_codes[encrypted_code]["date"]
            return False, f"Você já resgatou este código em {redeemed_date}", code_info

        return True, "Código válido!", code_info

    def redeem_code(self, raw_code):
        """
        Resgata um código e adiciona o Pokémon ao time/box
        raw_code é o código que o jogador DIGITOU (ex: 0BR1G4D0P0RJ0G4R)
        Retorna: (bool, str, Pokemon) -> (sucesso, mensagem, pokemon)

        IMPORTANTE: Toca o som de item raro automaticamente ao resgatar com sucesso.
        """
        from src.entities.pokemon import Pokemon

        # ===== CRIPTOGRAFA O CÓDIGO QUE O JOGADOR DIGITOU =====
        encrypted_code = mystery_crypto.encrypt_code(raw_code, length=8)

        # Verifica se pode resgatar (já usa o código criptografado)
        can_redeem, message, code_info = self.can_redeem_code(raw_code)
        if not can_redeem:
            return False, message, None

        # Obtém informações do código
        pokemon_id = code_info["pokemon_id"]
        pokemon_name = code_info["pokemon_name"]
        is_shiny = code_info.get("is_shiny", False)
        event_name = code_info.get("event_name", "Evento Especial")

        # Recarrega o save antes de modificar
        current_slot = getattr(self.player.save_manager, 'current_save_file', 1)
        if current_slot:
            self.player.load_game(current_slot)

        # ===== MOMENTO ÚNICO PARA CONSISTÊNCIA =====
        now = datetime.now()

        # ===== CRIA O POKÉMON NÍVEL 5 =====
        new_pokemon = Pokemon(
            0, 0,
            pokemon_id=pokemon_id,
            level=5,
            is_wild=False,
            shiny=is_shiny,
            is_boss=False
        )

        # ===== DEFINE A ORIGEM DO POKÉMON (ANTES DE add_to_team/add_to_box) =====
        # Isso é crucial: add_to_box chama pokemon.to_dict(), que serializa
        # capture_method/capture_date no momento da chamada.
        new_pokemon.capture_method = "event"  # Mystery Gift
        new_pokemon.capture_date = now.isoformat()  # Data/hora exata do resgate
        print(f"[MYSTERY_GIFT] Origem definida: capture_method='event' para {new_pokemon.name}")

        # Garante que o Pokémon está configurado corretamente
        new_pokemon.is_in_team = False
        new_pokemon.is_placed = False
        new_pokemon.is_wild = False

        # ===== ADICIONA À PC BOX (OU TIME SE TIVER ESPAÇO) =====
        if self.player.has_team_space():
            self.player.add_to_team(new_pokemon)
            message = f"{new_pokemon.name} foi adicionado ao seu time!"
        else:
            self.player.add_to_box(new_pokemon)
            message = f"{new_pokemon.name} foi adicionado à sua PC Box!"

        # ===== REGISTRA O CÓDIGO COMO RESGATADO =====
        # (usa o código criptografado como chave)
        self.player.redeemed_codes[encrypted_code] = {
            "pokemon_id": pokemon_id,
            "pokemon_name": pokemon_name,
            "date": now.strftime("%d/%m/%Y %H:%M"),
            "timestamp": now.timestamp(),
            "event_name": event_name,
            "is_shiny": is_shiny,
            "raw_code": raw_code
        }

        # ===== ADICIONA AO HISTÓRICO =====
        history_entry = {
            "code": encrypted_code,
            "raw_code": raw_code,
            "pokemon_id": pokemon_id,
            "pokemon_name": pokemon_name,
            "pokemon_level": 5,
            "pokemon_unique_id": new_pokemon.unique_id,
            "date": now.strftime("%d/%m/%Y %H:%M"),
            "timestamp": now.timestamp(),
            "event_name": event_name,
            "is_shiny": is_shiny
        }
        self.player.mystery_gift_history.append(history_entry)

        # ===== ADICIONA À POKÉDEX =====
        self.player.caught_pokemon.add(pokemon_id)
        self.player.register_seen(pokemon_id)

        # ===== SALVA AUTOMATICAMENTE APÓS O RESGATE =====
        self.player.save_game()

        # ===== TOCA O SOM DE ITEM RARO OBTIDO =====
        # (usa o volume global de SFX das configurações automaticamente)
        sound_manager.play_effect(SoundEffect.OBTAINED_RARE_ITEM)
        print("[MYSTERY_GIFT] Som tocado: ObtainedARareItem")

        print(f"[MYSTERY_GIFT] Código {raw_code} -> {encrypted_code} resgatado!")
        print(f"[MYSTERY_GIFT] Pokémon: {new_pokemon.name} (origem: {new_pokemon.capture_method})")
        print(f"[MYSTERY_GIFT] Histórico atualizado. Total de gifts: {len(self.player.mystery_gift_history)}")

        return True, message, new_pokemon

    def get_redeemed_codes_info(self):
        """Retorna informações detalhadas sobre códigos já resgatados"""
        if not hasattr(self.player, 'redeemed_codes'):
            return []

        info = []
        for code, data in self.player.redeemed_codes.items():
            info.append({
                "code": code,
                "date": data["date"],
                "pokemon": data["pokemon_name"],
                "pokemon_id": data["pokemon_id"],
                "event_name": data.get("event_name", "Evento Especial"),
                "is_shiny": data.get("is_shiny", False)
            })
        return info

    def get_gift_history(self):
        """Retorna o histórico completo de gifts resgatados"""
        if not hasattr(self.player, 'mystery_gift_history'):
            return []
        return self.player.mystery_gift_history.copy()

    def get_available_codes(self):
        """
        Retorna todos os códigos válidos que o jogador AINDA NÃO resgatou
        """
        from src.data.mystery_gift_data import MYSTERY_GIFT_CODES

        available = []
        for code, info in MYSTERY_GIFT_CODES.items():
            # Pula códigos inválidos
            if info.get("invalid", False):
                continue

            # Verifica se já foi resgatado
            if code not in self.player.redeemed_codes:
                available.append({
                    "code": code,
                    "pokemon_name": info["pokemon_name"],
                    "description": info["description"],
                    "event_name": info.get("event_name", "Evento Especial")
                })

        return available

    def get_unavailable_codes_info(self):
        """
        Retorna informações sobre códigos que NÃO estão disponíveis (já resgatados ou inválidos)
        """
        from src.data.mystery_gift_data import MYSTERY_GIFT_CODES

        unavailable = []
        for code, info in MYSTERY_GIFT_CODES.items():
            is_invalid = info.get("invalid", False)
            is_redeemed = code in self.player.redeemed_codes

            if is_invalid or is_redeemed:
                unavailable.append({
                    "code": code,
                    "pokemon_name": info["pokemon_name"],
                    "reason": "Evento encerrado" if is_invalid else "Já resgatado",
                    "redeemed_date": self.player.redeemed_codes[code]["date"] if is_redeemed else None,
                    "event_name": info.get("event_name", "Evento Especial")
                })

        return unavailable

    def get_statistics(self):
        """
        Retorna estatísticas do sistema Mystery Gift
        """
        from src.data.mystery_gift_data import MYSTERY_GIFT_CODES

        total_codes = len(MYSTERY_GIFT_CODES)
        invalid_codes = sum(1 for info in MYSTERY_GIFT_CODES.values() if info.get("invalid", False))
        valid_codes = total_codes - invalid_codes
        redeemed_count = len(self.player.redeemed_codes)
        available_count = valid_codes - redeemed_count

        return {
            "total_codes": total_codes,
            "invalid_codes": invalid_codes,
            "valid_codes": valid_codes,
            "redeemed_count": redeemed_count,
            "available_count": available_count,
            "total_gifts_received": len(getattr(self.player, 'mystery_gift_history', []))
        }