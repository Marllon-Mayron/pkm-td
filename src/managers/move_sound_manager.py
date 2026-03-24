# src/managers/move_sound_manager.py
"""
Gerenciador de sons para os moves/ataques dos Pokémon
"""
import pygame
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from src.config.paths import RES_PATH


class MoveSoundManager:
    """Gerencia os sons dos moves/ataques dos Pokémon"""

    _instance = None
    _sounds: Dict[str, pygame.mixer.Sound] = {}
    _default_hit_sound: Optional[pygame.mixer.Sound] = None  # Som padrão de impacto
    _volume: float = 0.7

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._load_all_move_sounds()

    def _load_all_move_sounds(self):
        """Carrega todos os sons de moves da pasta res/sounds/moves"""
        moves_path = Path(RES_PATH) / "sounds" / "moves"

        if not moves_path.exists():
            print(f"[MOVE_SOUND] Aviso: Pasta de sons de moves não encontrada: {moves_path}")
            print(f"[MOVE_SOUND] Criando pasta...")
            moves_path.mkdir(parents=True, exist_ok=True)
            return

        # Carrega todos os arquivos .mp3, .wav e .ogg da pasta
        sound_files = list(moves_path.glob("*.mp3")) + list(moves_path.glob("*.wav")) + list(moves_path.glob("*.ogg"))

        for sound_file in sound_files:
            sound_name = sound_file.stem.lower()  # Nome do arquivo sem extensão, em minúsculo
            try:
                sound = pygame.mixer.Sound(str(sound_file))
                self._sounds[sound_name] = sound
                print(f"[MOVE_SOUND] Carregado: {sound_name} -> {sound_file.name}")
            except Exception as e:
                print(f"[MOVE_SOUND] Erro ao carregar {sound_file}: {e}")

        # Carrega o som padrão de impacto (Tackle_Target)
        self._load_default_hit_sound(moves_path)

        print(f"[MOVE_SOUND] Total de sons de moves carregados: {len(self._sounds)}")

    def _load_default_hit_sound(self, moves_path: Path):
        """Carrega o som padrão de impacto (Tackle_Target)"""
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

        # Se não encontrou nenhum, cria um som padrão simples (beep)
        print("[MOVE_SOUND] Aviso: Som padrão de impacto não encontrado, usando beep")
        self._create_default_beep()

    def _create_default_beep(self):
        """Cria um som padrão simples (beep)"""
        sample_rate = 44100
        duration = 0.1  # 100ms
        frequency = 880  # 880 Hz (agudo)

        samples = int(sample_rate * duration)
        array = []
        for i in range(samples):
            t = i / sample_rate
            # Onda quadrada
            value = 32767 if (t * frequency) % 1 < 0.5 else -32767
            array.append(value)

        import array
        sample_array = array.array('h', array)

        try:
            self._default_hit_sound = pygame.mixer.Sound(buffer=sample_array)
            print("[MOVE_SOUND] Som padrão de beep criado!")
        except:
            self._default_hit_sound = None
            print("[MOVE_SOUND] Não foi possível criar som padrão")

    def play_move_sounds(self, move_name: str, attacker_pos: Optional[Tuple[float, float]] = None,
                         target_pos: Optional[Tuple[float, float]] = None,
                         volume: Optional[float] = None) -> bool:
        """
        Toca os sons de um move (atacante e alvo)

        Args:
            move_name: Nome do move (case insensitive)
            attacker_pos: Posição do atacante (para efeito 3D, opcional)
            target_pos: Posição do alvo (para efeito 3D, opcional)
            volume: Volume específico (0.0 a 1.0), se None usa o volume global

        Returns:
            bool: True se tocou pelo menos um som
        """
        played = False

        # Normaliza o nome do move
        move_key = move_name.lower().strip().replace(" ", "").replace("-", "").replace("'", "")

        # 1. Tenta tocar o som do atacante (nome do golpe)
        attacker_sound = self._sounds.get(move_key)
        if attacker_sound:
            final_volume = volume if volume is not None else self._volume
            attacker_sound.set_volume(final_volume)
            try:
                attacker_sound.play()
                print(f"[MOVE_SOUND] Som do atacante: {move_key}")
                played = True
            except Exception as e:
                print(f"[MOVE_SOUND] Erro ao tocar som do atacante {move_key}: {e}")
        else:
            print(f"[MOVE_SOUND] Som do atacante não encontrado para: {move_key}")

        # 2. Toca o som do alvo (nome_do_golpe_target)
        target_sound_key = f"{move_key}_target"
        target_sound = self._sounds.get(target_sound_key)

        if not target_sound:
            # Fallback: usa Tackle_Target
            target_sound = self._sounds.get("tackle_target") or self._default_hit_sound

        if target_sound:
            final_volume = volume if volume is not None else self._volume
            target_sound.set_volume(final_volume)
            try:
                target_sound.play()
                print(
                    f"[MOVE_SOUND] Som do alvo: {target_sound_key if target_sound_key in self._sounds else 'tackle_target'}")
                played = True
            except Exception as e:
                print(f"[MOVE_SOUND] Erro ao tocar som do alvo: {e}")
        else:
            print(f"[MOVE_SOUND] Som do alvo não encontrado para: {target_sound_key}")

        return played

    def play_attack_sound(self, move_name: str, volume: Optional[float] = None) -> bool:
        """
        Versão simplificada: toca apenas o som do atacante
        Mantido para compatibilidade com código antigo
        """
        move_key = move_name.lower().strip().replace(" ", "").replace("-", "").replace("'", "")
        sound = self._sounds.get(move_key)

        if sound:
            final_volume = volume if volume is not None else self._volume
            sound.set_volume(final_volume)
            try:
                sound.play()
                return True
            except:
                pass
        return False

    def play_hit_sound(self, move_name: str = None, volume: Optional[float] = None) -> bool:
        """
        Toca o som de impacto (quando o alvo recebe dano)

        Args:
            move_name: Nome do move que causou o dano (opcional)
            volume: Volume específico
        """
        if move_name:
            # Tenta o som específico do golpe_target
            move_key = move_name.lower().strip().replace(" ", "").replace("-", "").replace("'", "")
            target_sound_key = f"{move_key}_target"
            sound = self._sounds.get(target_sound_key)

            if sound:
                final_volume = volume if volume is not None else self._volume
                sound.set_volume(final_volume)
                try:
                    sound.play()
                    return True
                except:
                    pass

        # Fallback: som padrão de impacto
        if self._default_hit_sound:
            final_volume = volume if volume is not None else self._volume
            self._default_hit_sound.set_volume(final_volume)
            try:
                self._default_hit_sound.play()
                return True
            except:
                pass

        return False

    def set_volume(self, volume: float):
        """Define o volume global dos sons de moves"""
        self._volume = max(0.0, min(1.0, volume))
        # Atualiza volume de todos os sons carregados
        for sound in self._sounds.values():
            sound.set_volume(self._volume)
        if self._default_hit_sound:
            self._default_hit_sound.set_volume(self._volume)
        print(f"[MOVE_SOUND] Volume definido para: {self._volume}")

    def get_volume(self) -> float:
        """Retorna o volume atual"""
        return self._volume

    def get_loaded_moves(self) -> list:
        """Retorna lista de moves com sons carregados"""
        return list(self._sounds.keys())


# Instância global
move_sound_manager = MoveSoundManager()