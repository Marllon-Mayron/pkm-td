# src/managers/sounds/sound_manager.py

"""
Sistema de gerenciamento de áudio principal
"""
import pygame
from pathlib import Path
from typing import Dict, Optional
from enum import Enum
from src.config.paths import RES_PATH
from src.managers.sounds.base_sound_manager import BaseSoundManager


class SoundEffect(Enum):
    """Enum para os efeitos sonoros do jogo"""
    SHINY = "Shiny"
    CAUGHT = "Caught"
    CLICK = "Click"
    EVOLUTION = "Evolution"
    LEVELUP = "Levelup"


class SoundManager(BaseSoundManager):
    """Gerencia todos os sons e músicas do jogo - Herda do BaseSoundManager"""

    def __init__(self):
        super().__init__()

        # Inicializa pygame mixer se necessário
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        # Caminho base dos sons
        self.sounds_path = Path(RES_PATH) / "sounds"

        # Dicionário específico para efeitos
        self.effects: Dict[SoundEffect, pygame.mixer.Sound] = {}

        # Música específica
        self.music_playing: Optional[str] = None
        self._music_volume: float = 0.5
        self._music_enabled: bool = True

        # Carrega todos os sons
        self._load_sounds()

        # Sincroniza com configurações globais
        self._sync_with_global_settings("sfx")
        self._sync_music_with_global_settings()

    def _load_sounds(self):
        """Carrega todos os sons (implementação do método abstrato)"""
        self._load_all_sounds()
        self._load_effects()

    def _sync_music_with_global_settings(self):
        """Sincroniza especificamente a música com as configurações"""
        from src.config.settings import settings

        self._music_enabled = settings.music_enabled
        self._music_volume = settings.music_volume if settings.music_enabled else 0
        pygame.mixer.music.set_volume(self._music_volume)

        print(f"[SOUND] Música sincronizada: volume={self._music_volume}, enabled={self._music_enabled}")

    def sync_all(self):
        """Sincroniza todos os sons (SFX e música) com as configurações"""
        self._sync_with_global_settings("sfx")
        self._sync_music_with_global_settings()

    def _load_effects(self):
        """Carrega os efeitos sonoros da pasta res/sounds/effects"""
        effects_path = self.sounds_path / "effects"

        if not effects_path.exists():
            print(f"[SOUND] Aviso: Pasta de efeitos não encontrada: {effects_path}")
            return

        # Carrega os efeitos
        effect_files = {
            SoundEffect.SHINY: "Shiny.mp3",
            SoundEffect.CAUGHT: "Caught.mp3",
            SoundEffect.CLICK: "Click.mp3",
            SoundEffect.EVOLUTION: "Evolution.mp3",
            SoundEffect.LEVELUP: "LevelUp.mp3"
        }

        for effect, filename in effect_files.items():
            effect_path = effects_path / filename
            if effect_path.exists():
                try:
                    self.effects[effect] = pygame.mixer.Sound(str(effect_path))
                except Exception as e:
                    print(f"[SOUND] Erro ao carregar {filename}: {e}")
            else:
                print(f"[SOUND] Aviso: {filename} não encontrado em {effects_path}")

    def _load_all_sounds(self):
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
            sound_id = file_path.stem
            self._sounds[sound_id] = sound
            # print(f"[SOUND] Carregado: {sound_id}")
        except Exception as e:
            print(f"[SOUND] Erro ao carregar {file_path}: {e}")

    def play_effect(self, effect: SoundEffect, volume: Optional[float] = None, loops: int = 0) -> bool:
        """
        Toca um efeito sonoro usando o enum SoundEffect
        """
        if not self._enabled or self._volume == 0:
            return False

        sound = self.effects.get(effect)
        if not sound:
            return False

        target_volume = volume if volume is not None else self._volume
        sound.set_volume(target_volume)

        try:
            sound.play(loops)
            return True
        except Exception as e:
            print(f"[SOUND] Erro ao tocar efeito {effect.value}: {e}")
            return False

    def play_random_battle_music(self):
        """Toca uma música de batalha aleatória"""
        if not self._music_enabled or self._music_volume == 0:
            return False

        music_path = self.sounds_path / "music" / "gameBattle"
        music_files = []

        if music_path.exists():
            for ext in ['.mp3', '.ogg', '.wav']:
                files = list(music_path.glob(f"*{ext}"))
                print(f"[MUSIC] Encontrados {len(files)} arquivos com extensão {ext}")
                music_files.extend(files)

        if not music_files:
            return False

        import random
        selected_music = random.choice(music_files)
        print(f"[MUSIC] Música selecionada: {selected_music.name}")
        self.play_music(selected_music.stem, loop=True)
        return True

    def play_music(self, music_id: str, fade_ms: int = 1000, loop: bool = True):
        """Toca música de fundo"""
        print(f"[MUSIC] play_music chamado: music_id='{music_id}'")

        if not self._music_enabled or self._music_volume == 0:
            print(f"[MUSIC] Música desabilitada (enabled={self._music_enabled}, volume={self._music_volume})")
            return

        music_file = None
        possible_paths = [
            self.sounds_path / "music" / "gameBattle" / f"{music_id}.mp3",
            self.sounds_path / "music" / "gameBattle" / f"{music_id}.ogg",
            self.sounds_path / "music" / "gameBattle" / f"{music_id}.wav",
        ]

        for path in possible_paths:
            if path.exists():
                music_file = str(path)
                break

        if not music_file:
            print(f"[MUSIC] Música não encontrada: {music_id}")
            print(f"[MUSIC] Procurado em: {possible_paths[:3]}...")
            return

        try:
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
        except Exception as e:
            print(f"[MUSIC] Erro ao tocar música: {e}")
            import traceback
            traceback.print_exc()

    def stop_music(self, fade_ms: int = 500):
        """Para a música atual"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(fade_ms)
            self.music_playing = None

    def set_sfx_volume(self, volume: float):
        """Define o volume dos efeitos sonoros"""
        self._volume = max(0.0, min(1.0, volume))
        if not self._enabled:
            self._volume = 0
        self._apply_volume_to_all()

        # Sincroniza o move_sound_manager também
        from src.managers.sounds.move_sound_manager import move_sound_manager
        move_sound_manager.sync_with_main_manager()

        print(f"[SOUND] SFX volume definido: {self._volume}")

    def set_music_volume(self, volume: float):
        """Define o volume da música"""
        self._music_volume = max(0.0, min(1.0, volume))
        if not self._music_enabled:
            self._music_volume = 0
        pygame.mixer.music.set_volume(self._music_volume)
        print(f"[SOUND] Music volume definido: {self._music_volume}")

    def set_music_enabled(self, enabled: bool):
        """Habilita/desabilita música"""
        self._music_enabled = enabled
        if not enabled:
            self.stop_music()
            pygame.mixer.music.set_volume(0)
        else:
            pygame.mixer.music.set_volume(self._music_volume)

    def set_sfx_enabled(self, enabled: bool):
        """Habilita/desabilita efeitos sonoros"""
        self._enabled = enabled
        if not enabled:
            self._volume = 0
        else:
            from src.config.settings import settings
            self._volume = settings.sfx_volume
        self._apply_volume_to_all()

        # Sincroniza o move_sound_manager
        from src.managers.sounds.move_sound_manager import move_sound_manager
        move_sound_manager.sync_with_main_manager()

    def sync_all_managers(self):
        """Sincroniza todos os gerenciadores de som com as configurações atuais"""
        from src.config.settings import settings

        # CORRIGIDO: self em vez de sound_manager
        self.set_sfx_volume(settings.sfx_volume if settings.sfx_enabled else 0)
        self.set_music_volume(settings.music_volume if settings.music_enabled else 0)

        # Sincroniza o MoveSoundManager (já é feito no set_sfx_volume, mas garantimos)
        from src.managers.sounds.move_sound_manager import move_sound_manager
        move_sound_manager.sync_with_main_manager()

        print("[SOUND] Todos os gerenciadores de som sincronizados")

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


# Instância global
sound_manager = SoundManager()