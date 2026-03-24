# src/entities/move.py (atualizado)
from typing import Dict, Optional


class Move:
    """Representa um move que um Pokémon pode usar"""

    def __init__(self, name: str, move_data: Dict):
        self.name = name
        self.type = move_data.get("type", "normal")
        self.power = move_data.get("power", 0)
        self.accuracy = move_data.get("accuracy", 100)
        self.max_pp = move_data.get("pp", 35)
        self.current_pp = self.max_pp
        self.category = move_data.get("category", "physical")  # physical, special, status
        self.description = move_data.get("description", f"Usa {name}.")

        self.sound_name = move_data.get("sound_name", name.lower())

        # Efeitos especiais (para futura implementação)
        self.effect = move_data.get("effect", None)
        self.effect_chance = move_data.get("effect_chance", 0)

    def use(self) -> bool:
        """Usa o move, retorna True se foi bem sucedido"""
        if self.current_pp <= 0:
            return False
        self.current_pp -= 1
        return True

    def restore_pp(self, amount: Optional[int] = None):
        """Restaura PP do move"""
        if amount is None:
            self.current_pp = self.max_pp
        else:
            self.current_pp = min(self.max_pp, self.current_pp + amount)

    def get_pp_percentage(self) -> float:
        """Retorna porcentagem de PP restante"""
        return self.current_pp / self.max_pp if self.max_pp > 0 else 0

    def to_dict(self) -> Dict:
        """Converte para dicionário para serialização"""
        return {
            "name": self.name,
            "type": self.type,
            "power": self.power,
            "accuracy": self.accuracy,
            "max_pp": self.max_pp,
            "current_pp": self.current_pp,
            "category": self.category,
            "description": self.description,
            "sound_name": self.sound_name  # NOVO
        }

    @classmethod
    def from_dict(cls, data: Dict, move_info: Optional[Dict] = None):
        """Cria Move a partir de dicionário"""
        if move_info is None:
            move_info = {
                "type": data.get("type", "normal"),
                "power": data.get("power", 0),
                "accuracy": data.get("accuracy", 100),
                "pp": data.get("max_pp", 35),
                "category": data.get("category", "physical"),
                "description": data.get("description", ""),
                "sound_name": data.get("sound_name", data.get("name", "").lower())
            }

        move = cls(data["name"], move_info)
        move.current_pp = data.get("current_pp", move.max_pp)
        return move