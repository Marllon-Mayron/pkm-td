# src/managers/sounds/move_sound_manager.py

"""
Gerenciador de sons para os moves/ataques dos Pokémon
Herda do BaseSoundManager para sincronizar automaticamente
"""
import pygame
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from src.config.paths import RES_PATH
from src.managers.sounds.base_sound_manager import BaseSoundManager


class MoveSoundManager(BaseSoundManager):
    """Gerencia os sons dos moves/ataques dos Pokémon"""

    _default_hit_sound: Optional[pygame.mixer.Sound] = None

    def __init__(self):
        super().__init__()
        self._load_sounds()
        # Sincroniza com as configurações globais
        self._sync_with_global_settings("sfx")

    def _load_sounds(self):
        """Carrega todos os sons de moves (implementação do método abstrato)"""
        self._load_all_move_sounds()

    def sync_with_main_manager(self):
        """Sincroniza com o SoundManager principal"""
        # CORRIGIDO: Usar o caminho correto do import
        from src.managers.sounds.sound_manager import sound_manager

        # Pega o volume e estado do SoundManager principal
        self._enabled = sound_manager.get_enabled()
        self._volume = sound_manager.get_volume()

        # Aplica o volume a todos os sons
        self._apply_volume_to_all()

        print(f"[MOVE_SOUND] Sincronizado com SoundManager: volume={self._volume}, enabled={self._enabled}")

    def _load_all_move_sounds(self):
        """Carrega todos os sons de moves da pasta res/sounds/moves"""
        moves_path = Path(RES_PATH) / "sounds" / "moves"

        if not moves_path.exists():
            print(f"[MOVE_SOUND] Aviso: Pasta de sons de moves não encontrada: {moves_path}")
            moves_path.mkdir(parents=True, exist_ok=True)
            return

        # Carrega todos os arquivos .mp3, .wav e .ogg da pasta
        sound_files = list(moves_path.glob("*.mp3")) + list(moves_path.glob("*.wav")) + list(moves_path.glob("*.ogg"))

        for sound_file in sound_files:
            raw_name = sound_file.stem.lower()
            sound_name = raw_name.replace(" ", "").replace("-", "").replace("'", "")

            try:
                sound = pygame.mixer.Sound(str(sound_file))
                self._sounds[sound_name] = sound
            except Exception as e:
                print(f"[MOVE_SOUND] Erro ao carregar {sound_file}: {e}")

        # Carrega o som padrão de impacto
        self._load_default_hit_sound(moves_path)

        print(f"[MOVE_SOUND] Total de sons de moves carregados: {len(self._sounds)}")

    def _load_default_hit_sound(self, moves_path: Path):
        """Carrega o som padrão de impacto"""
        default_candidates = ["tackle_target", "hit", "damage"]

        for candidate in default_candidates:
            for ext in [".mp3", ".wav", ".ogg"]:
                sound_file = moves_path / f"{candidate}{ext}"
                if sound_file.exists():
                    try:
                        self._default_hit_sound = pygame.mixer.Sound(str(sound_file))
                        print(f"[MOVE_SOUND] Som padrão de impacto carregado: {candidate}{ext}")
                        return
                    except:
                        pass

        print("[MOVE_SOUND] Som padrão de impacto não encontrado")

    def play_move_sounds(self, move_name: str, attacker_pos: Optional[Tuple[float, float]] = None,
                         target_pos: Optional[Tuple[float, float]] = None,
                         volume: Optional[float] = None) -> bool:
        """Toca os sons de um move (atacante e alvo)"""
        if not self._enabled or self._volume == 0:
            return False

        played = False
        move_key = move_name.lower().strip().replace(" ", "").replace("-", "").replace("'", "")

        # Toca o som do atacante
        attacker_sound = self._sounds.get(move_key)
        if attacker_sound:
            target_volume = volume if volume is not None else self._volume
            attacker_sound.set_volume(target_volume)
            try:
                attacker_sound.play()
                played = True
            except:
                pass

        # Toca o som do alvo
        target_sound_key = f"{move_key}_target"
        target_sound = self._sounds.get(target_sound_key)

        if not target_sound:
            target_sound = self._sounds.get("tackle_target") or self._default_hit_sound

        if target_sound:
            target_volume = volume if volume is not None else self._volume
            target_sound.set_volume(target_volume)
            try:
                target_sound.play()
                played = True
            except:
                pass

        return played

    def play_attack_sound(self, move_name: str, volume: Optional[float] = None) -> bool:

        if not self._enabled or self._volume == 0:
            return False

        move_key = move_name.lower().strip().replace(" ", "").replace("-", "").replace("'", "")

        sound = self._sounds.get(move_key)

        if sound:
            target_volume = volume if volume is not None else self._volume
            sound.set_volume(target_volume)
            sound.play()
            return True
        else:
            print(f"[MOVE_SOUND] Som NÃO encontrado para '{move_key}'")
            return False

    def play_hit_sound(self, move_name: str = None, volume: Optional[float] = None, use_fallback: bool = True) -> bool:
        """Toca o som de impacto"""
        if not self._enabled or self._volume == 0:
            return False

        if move_name:
            move_key = move_name.lower().strip().replace(" ", "").replace("-", "").replace("'", "")
            target_sound_key = f"{move_key}_target"

            if self.play_sound(target_sound_key, volume):
                return True

        if use_fallback and self._default_hit_sound:
            target_volume = volume if volume is not None else self._volume
            self._default_hit_sound.set_volume(target_volume)
            try:
                self._default_hit_sound.play()
                return True
            except:
                pass

        return False


# Instância global
move_sound_manager = MoveSoundManager()