# src/entities/pokemon/animation.py
import pygame


class PokemonAnimation:
    """Gerencia animações e sprites do Pokémon"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

    def load_sprites(self, pokemon_id, shiny):
        """Carrega sprites com cache"""
        from src.entities.pokemon.pokemon import _SPRITE_CACHE

        cache_key = f"{pokemon_id}_{shiny}"

        if cache_key in _SPRITE_CACHE:
            cached = _SPRITE_CACHE[cache_key]
            self.pokemon.ui_sprite = cached["ui"]
            self.pokemon.battle_sprite = cached["battle"]
            self.pokemon.inmap_frames = cached["inmap"]
            self.pokemon.inmap_animations = cached.get("animations", {})
        else:
            self.pokemon.ui_sprite = self.pokemon.pokedex.get_sprite(pokemon_id, "front", shiny)
            self.pokemon.battle_sprite = self.pokemon.pokedex.get_sprite(pokemon_id, "back", shiny)
            self.pokemon.inmap_frames = self.pokemon.pokedex.get_inmap_animation(pokemon_id, shiny)

            self.pokemon.inmap_animations = {}
            if hasattr(self.pokemon.pokedex, 'get_raw_inmap_data'):
                try:
                    raw_data = self.pokemon.pokedex.get_raw_inmap_data(pokemon_id, shiny)
                    self.pokemon.inmap_animations = raw_data.get("animations", {})
                    self.pokemon.raw_animations = raw_data
                except Exception as e:
                    print(f"[ERRO] Falha ao carregar dados brutos: {e}")

            _SPRITE_CACHE[cache_key] = {
                "ui": self.pokemon.ui_sprite,
                "battle": self.pokemon.battle_sprite,
                "inmap": self.pokemon.inmap_frames,
                "animations": self.pokemon.inmap_animations
            }

        self.pokemon.current_direction = "down"
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        self.pokemon.animation_speed = 0.1

        self._load_animation_timings()

    def _load_animation_timings(self):
        """Carrega os tempos de duração dos frames"""
        if not hasattr(self.pokemon, 'raw_animations') or not self.pokemon.raw_animations:
            self.pokemon.walk_frame_durations = [8, 8, 8, 8]
            self.pokemon.idle_frame_durations = [10, 10, 10, 10]
            self.pokemon.frame_durations = self.pokemon.idle_frame_durations
            return

        anim_data = self.pokemon.raw_animations.get("anim_data", {})

        walk_info = anim_data.get("Walk", {})
        if "durations" in walk_info and walk_info["durations"]:
            self.pokemon.walk_frame_durations = walk_info["durations"]
        else:
            self.pokemon.walk_frame_durations = [8, 8, 8, 8]

        idle_info = anim_data.get("Idle", {})
        if "durations" in idle_info and idle_info["durations"]:
            self.pokemon.idle_frame_durations = idle_info["durations"]
        else:
            self.pokemon.idle_frame_durations = [10, 10, 10, 10]

        self._update_current_durations()

    def _update_current_durations(self):
        """Atualiza as durações dos frames baseado na animação atual"""
        if hasattr(self.pokemon, 'current_animation'):
            if self.pokemon.current_animation == "walk" and hasattr(self.pokemon, 'walk_frame_durations'):
                self.pokemon.frame_durations = self.pokemon.walk_frame_durations
            elif hasattr(self.pokemon, 'idle_frame_durations'):
                self.pokemon.frame_durations = self.pokemon.idle_frame_durations
            else:
                self.pokemon.frame_durations = [8, 8, 8, 8]

            if hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame >= len(
                    self.pokemon.frame_durations):
                self.pokemon.current_frame = 0

    def set_animation(self, animation_name: str):
        """Troca a animação atual"""
        if not hasattr(self.pokemon, 'current_animation'):
            return

        if animation_name == self.pokemon.current_animation:
            return

        self.pokemon.current_animation = animation_name
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        self._update_current_durations()
        self._update_sprite_from_current_animation()

    def _update_sprite_from_current_animation(self):
        """Atualiza o sprite baseado na animação atual"""
        if hasattr(self.pokemon,
                   'inmap_animations') and self.pokemon.current_animation in self.pokemon.inmap_animations:
            anim_frames = self.pokemon.inmap_animations[self.pokemon.current_animation]

            if self.pokemon.current_direction in anim_frames:
                frames = anim_frames[self.pokemon.current_direction]
                if frames and hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame < len(frames):
                    self.pokemon.sprite = frames[self.pokemon.current_frame]
                    return

            dir_mapping = {
                "down": ["down", "down-left", "down-right"],
                "left": ["left", "down-left", "up-left"],
                "right": ["right", "down-right", "up-right"],
                "up": ["up", "up-left", "up-right"]
            }

            for src_dir in dir_mapping.get(self.pokemon.current_direction, [self.pokemon.current_direction]):
                if src_dir in anim_frames:
                    frames = anim_frames[src_dir]
                    if frames and hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame < len(frames):
                        self.pokemon.sprite = frames[self.pokemon.current_frame]
                        return

        if hasattr(self.pokemon, 'inmap_frames') and self.pokemon.current_direction in self.pokemon.inmap_frames:
            frames_list = self.pokemon.inmap_frames[self.pokemon.current_direction]
            if frames_list and hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame < len(frames_list):
                self.pokemon.sprite = frames_list[self.pokemon.current_frame]

    def _get_current_animation_frame_count(self) -> int:
        """Retorna o número de frames da animação atual"""
        if hasattr(self.pokemon,
                   'inmap_animations') and self.pokemon.current_animation in self.pokemon.inmap_animations:
            anim_frames = self.pokemon.inmap_animations[self.pokemon.current_animation]

            if self.pokemon.current_direction in anim_frames:
                return len(anim_frames[self.pokemon.current_direction])

            dir_mapping = {
                "down": ["down", "down-left", "down-right"],
                "left": ["left", "down-left", "up-left"],
                "right": ["right", "down-right", "up-right"],
                "up": ["up", "up-left", "up-right"]
            }

            for src_dir in dir_mapping.get(self.pokemon.current_direction, [self.pokemon.current_direction]):
                if src_dir in anim_frames:
                    return len(anim_frames[src_dir])

        if hasattr(self.pokemon, 'inmap_frames') and self.pokemon.current_direction in self.pokemon.inmap_frames:
            return len(self.pokemon.inmap_frames[self.pokemon.current_direction])

        return 1

    def _is_moving(self) -> bool:
        """Verifica se o Pokémon está em movimento"""
        if hasattr(self.pokemon, 'last_x') and hasattr(self.pokemon, 'last_y'):
            dx = abs(self.pokemon.x - self.pokemon.last_x)
            dy = abs(self.pokemon.y - self.pokemon.last_y)
            return (dx + dy) > 0.5
        return False

    def update_animation(self, dt):
        """Atualiza animação do sprite baseado no movimento"""
        is_moving_now = self._is_moving()

        if is_moving_now and not self.pokemon.is_moving:
            self.pokemon.is_moving = True
            self.set_animation("walk")
        elif not is_moving_now and self.pokemon.is_moving:
            self.pokemon.is_moving = False
            self.set_animation("idle")

        self.pokemon.animation_timer += dt

        frame_time = self.pokemon.animation_speed
        if hasattr(self.pokemon, 'frame_durations') and self.pokemon.frame_durations and hasattr(self.pokemon,
                                                                                                 'current_frame') and self.pokemon.current_frame < len(
                self.pokemon.frame_durations):
            frame_time = self.pokemon.frame_durations[self.pokemon.current_frame] / 60.0

        if self.pokemon.animation_timer >= frame_time:
            self.pokemon.animation_timer = 0

            max_frames = self._get_current_animation_frame_count()
            if max_frames > 0:
                self.pokemon.current_frame = (self.pokemon.current_frame + 1) % max_frames
                self._update_sprite_from_current_animation()