# src/managers/sound_manager.py
"""
Sistema de gerenciamento de áudio
"""
import pygame
import os
from pathlib import Path
from typing import Dict, Optional, List
from enum import Enum, auto
from src.config.paths import RES_PATH


class SoundEffect(Enum):
    """Enum para os efeitos sonoros do jogo"""
    SHINY = "Shiny"
    CAUGHT = "Caught"
    CLICK = "Click"
    EVOLUTION = "Evolution"


class SoundManager:
    """Gerencia todos os sons e músicas do jogo"""

    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        # Caminho base dos sons
        self.sounds_path = Path(RES_PATH) / "sounds"

        # Dicionários para armazenar os sons
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_playing: Optional[str] = None

        # Dicionário específico para efeitos
        self.effects: Dict[SoundEffect, pygame.mixer.Sound] = {}

        # Volumes (0.0 a 1.0)
        self._sfx_volume = 0.7
        self._music_volume = 0.5

        # Configura o volume inicial
        self.set_sfx_volume(self._sfx_volume)
        self.set_music_volume(self._music_volume)

        # Carrega todos os sons
        self.load_all_sounds()
        self.load_effects()

        print("[SOUND] SoundManager inicializado")
        print(f"[SOUND] Pasta de sons: {self.sounds_path}")
        print(f"[SOUND] Sons carregados: {len(self.sounds)}")
        print(f"[SOUND] Efeitos carregados: {len(self.effects)}")

    def load_effects(self):
        """Carrega os efeitos sonoros da pasta res/sounds/effects"""
        effects_path = self.sounds_path / "effects"

        if not effects_path.exists():
            print(f"[SOUND] Aviso: Pasta de efeitos não encontrada: {effects_path}")
            return

        # Carrega o Shiny.mp3
        shiny_path = effects_path / "Shiny.mp3"
        if shiny_path.exists():
            try:
                self.effects[SoundEffect.SHINY] = pygame.mixer.Sound(str(shiny_path))
                print(f"[SOUND] Efeito carregado: Shiny")
            except Exception as e:
                print(f"[SOUND] Erro ao carregar Shiny.mp3: {e}")
        else:
            print(f"[SOUND] Aviso: Shiny.mp3 não encontrado em {effects_path}")

        # Carrega o Caught.mp3
        caught_path = effects_path / "Caught.mp3"
        if caught_path.exists():
            try:
                self.effects[SoundEffect.CAUGHT] = pygame.mixer.Sound(str(caught_path))
                print(f"[SOUND] Efeito carregado: Caught")
            except Exception as e:
                print(f"[SOUND] Erro ao carregar Caught.mp3: {e}")
        else:
            print(f"[SOUND] Aviso: Caught.mp3 não encontrado em {effects_path}")

        click_path = effects_path / "Click.mp3"
        if click_path.exists():
            try:
                self.effects[SoundEffect.CLICK] = pygame.mixer.Sound(str(click_path))
                print(f"[SOUND] Efeito carregado: Click")
            except Exception as e:
                print(f"[SOUND] Erro ao carregar Click.mp3: {e}")
        else:
            print(f"[SOUND] Aviso: Click.mp3 não encontrado em {effects_path}")

        evolution_path = effects_path / "Evolution.mp3"
        if evolution_path.exists():
            try:
                self.effects[SoundEffect.EVOLUTION] = pygame.mixer.Sound(str(evolution_path))
                print(f"[SOUND] Efeito carregado: Evolution")
            except Exception as e:
                print(f"[SOUND] Erro ao carregar Evolution.mp3: {e}")
        else:
            print(f"[SOUND] Aviso: Evolution.mp3 não encontrado em {effects_path}")

    def load_all_sounds(self):
        """Carrega todos os sons da pasta res/sounds"""
        if not self.sounds_path.exists():
            print(f"[SOUND] Aviso: Pasta de sons não encontrada: {self.sounds_path}")
            return

        # Mapeamento de categorias de sons
        sound_categories = {
            "menu": ["click", "hover", "confirm", "cancel"],
            "game": ["tower_place", "tower_upgrade", "enemy_spawn", "enemy_death",
                     "wave_start", "wave_end", "game_over", "victory"],
            "battle": ["attack", "critical", "skill", "heal", "faint"],
            "ui": ["button", "shop", "unlock", "error"],
            "pokemon": ["evolution", "catch", "level_up"]
        }

        # Carrega sons por categoria
        for category, sound_names in sound_categories.items():
            for sound_name in sound_names:
                self._load_sound(category, sound_name)

        # Também carrega qualquer arquivo .wav ou .ogg diretamente na pasta
        for file_path in self.sounds_path.glob("*.wav"):
            self._load_sound_file(file_path)

        for file_path in self.sounds_path.glob("*.ogg"):
            self._load_sound_file(file_path)

    def _load_sound(self, category: str, name: str):
        """Tenta carregar um som específico"""
        possible_extensions = ['.wav', '.ogg', '.mp3']

        for ext in possible_extensions:
            sound_file = self.sounds_path / category / f"{name}{ext}"
            if sound_file.exists():
                self._load_sound_file(sound_file)
                break

            # Tenta também na raiz
            sound_file = self.sounds_path / f"{name}{ext}"
            if sound_file.exists():
                self._load_sound_file(sound_file)
                break

    def _load_sound_file(self, file_path: Path):
        """Carrega um arquivo de som individual"""
        try:
            sound = pygame.mixer.Sound(str(file_path))
            sound_id = file_path.stem  # Nome sem extensão
            self.sounds[sound_id] = sound
            print(f"[SOUND] Carregado: {sound_id} ({file_path.name})")
        except Exception as e:
            print(f"[SOUND] Erro ao carregar {file_path}: {e}")

    def play_effect(self, effect: SoundEffect, volume: Optional[float] = None, loops: int = 0) -> bool:
        """
        Toca um efeito sonoro usando o enum SoundEffect

        Args:
            effect: Enum do efeito a ser tocado (SoundEffect.SHINY ou SoundEffect.CAUGHT)
            volume: Volume específico para este efeito (0.0 a 1.0)
            loops: Número de repetições (-1 para loop infinito)

        Returns:
            True se tocou, False se não encontrou
        """
        if effect not in self.effects:
            print(f"[SOUND] Efeito não encontrado: {effect.value}")
            return False

        sound = self.effects[effect]
        if volume is not None:
            sound.set_volume(volume)
        else:
            sound.set_volume(self._sfx_volume)

        try:
            sound.play(loops)
            return True
        except Exception as e:
            print(f"[SOUND] Erro ao tocar efeito {effect.value}: {e}")
            return False

    def play_random_battle_music(self):
        """Toca uma música de batalha aleatória da pasta music/gameBattle"""
        from src.config.settings import settings

        # Verifica se música está habilitada
        if not settings.music_enabled:
            print(f"[SOUND] Música desabilitada, não tocando música aleatória")
            return False

        music_path = self.sounds_path / "music" / "gameBattle"
        music_files = []

        if music_path.exists():
            for ext in ['.mp3', '.ogg', '.wav']:
                music_files.extend(music_path.glob(f"*{ext}"))

        if not music_files:
            print(f"[SOUND] Nenhuma música de batalha encontrada em {music_path}")
            return False

        import random
        selected_music = random.choice(music_files)
        music_id = selected_music.stem

        self.play_music(music_id, fade_ms=1000, loop=True)
        print(f"[SOUND] Tocando música de batalha: {music_id}")
        return True

    def play_victory_music(self):
        """Toca a música de vitória (Victory_Wild.mp3)"""
        from src.config.settings import settings

        if not settings.music_enabled:
            print(f"[SOUND] Música desabilitada")
            return False

        # Toca a música Victory_Wild (uma vez, sem loop)
        self.play_music("Victory_Wild", fade_ms=500, loop=False)
        return True

    def play_defeat_music(self):
        """Toca a música de derrota (Defeat.mp3)"""
        from src.config.settings import settings

        if not settings.music_enabled:
            print(f"[SOUND] Música desabilitada")
            return False

        # Toca a música Defeat (uma vez, sem loop)
        self.play_music("Defeat", fade_ms=500, loop=False)
        return True

    def play_music(self, music_id: str, fade_ms: int = 1000, loop: bool = True):
        """
        Toca música de fundo

        Args:
            music_id: Identificador da música (nome do arquivo sem extensão)
            fade_ms: Tempo de fade in em milissegundos
            loop: Se deve tocar em loop
        """
        from src.config.settings import settings
        if not settings.music_enabled:
            print(f"[SOUND] Música desabilitada, não tocando {music_id}")
            return

        music_file = None

        # Procura o arquivo em várias pastas
        possible_paths = [
            self.sounds_path / "music" / "gameBattle" / f"{music_id}.mp3",
            self.sounds_path / "music" / "gameBattle" / f"{music_id}.ogg",
            self.sounds_path / "music" / "gameBattle" / f"{music_id}.wav",
            self.sounds_path / "music" / f"{music_id}.mp3",
            self.sounds_path / "music" / f"{music_id}.ogg",
            self.sounds_path / "music" / f"{music_id}.wav",
            self.sounds_path / f"{music_id}.mp3",
            self.sounds_path / f"{music_id}.ogg",
            self.sounds_path / f"{music_id}.wav",
        ]

        for path in possible_paths:
            if path.exists():
                music_file = str(path)
                break

        if music_file is None:
            print(f"[SOUND] Música não encontrada: {music_id}")
            return

        try:
            # Para a música atual com fade
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms)
                pygame.time.wait(fade_ms // 10)

            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(self._music_volume)

            if loop:
                pygame.mixer.music.play(-1, fade_ms=fade_ms)
            else:
                pygame.mixer.music.play(fade_ms=fade_ms)

            self.music_playing = music_id
            print(f"[SOUND] Tocando música: {music_id}")

        except Exception as e:
            print(f"[SOUND] Erro ao tocar música {music_id}: {e}")

    def stop_music(self, fade_ms: int = 500):
        """Para a música atual"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(fade_ms)
            self.music_playing = None

    def pause_music(self):
        """Pausa a música"""
        pygame.mixer.music.pause()

    def unpause_music(self):
        """Despausa a música"""
        pygame.mixer.music.unpause()

    def stop_effect(self, effect: SoundEffect):
        """Para um efeito sonoro específico"""
        if effect in self.effects:
            self.effects[effect].stop()

    def set_sfx_volume(self, volume: float):
        """Define o volume dos efeitos sonoros"""
        self._sfx_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self._sfx_volume)
        for effect in self.effects.values():
            effect.set_volume(self._sfx_volume)
        print(f"[SOUND] SFX volume: {self._sfx_volume}")

    def set_music_volume(self, volume: float):
        """Define o volume da música"""
        self._music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self._music_volume)
        print(f"[SOUND] Music volume: {self._music_volume}")

    def get_sfx_volume(self) -> float:
        """Retorna o volume atual dos efeitos"""
        return self._sfx_volume

    def get_music_volume(self) -> float:
        """Retorna o volume atual da música"""
        return self._music_volume


# Instância global
sound_manager = SoundManager()