# src/entities/pokemon/animation.py - VERSÃO COMPLETA COM TODAS AS ANIMAÇÕES
import pygame


class PokemonAnimation:
    """Gerencia animações e sprites do Pokémon"""

    def __init__(self, pokemon):
        self.pokemon = pokemon
        self._available_animations = []  # Cache de animações disponíveis

    def load_sprites(self, pokemon_id, shiny):
        """Carrega sprites com cache e todas as animações disponíveis"""
        from src.entities.pokemon.pokemon import _SPRITE_CACHE

        cache_key = f"{pokemon_id}_{shiny}"

        if cache_key in _SPRITE_CACHE:
            cached = _SPRITE_CACHE[cache_key]
            self.pokemon.ui_sprite = cached["ui"]
            self.pokemon.battle_sprite = cached["battle"]
            self.pokemon.inmap_frames = cached["inmap"]
            self.pokemon.inmap_animations = cached.get("animations", {})
            self._available_animations = cached.get("available_animations", [])
        else:
            self.pokemon.ui_sprite = self.pokemon.pokedex.get_sprite(pokemon_id, "front", shiny)
            self.pokemon.battle_sprite = self.pokemon.pokedex.get_sprite(pokemon_id, "back", shiny)
            self.pokemon.inmap_frames = self.pokemon.pokedex.get_inmap_animation(pokemon_id, shiny)

            # Carrega informações completas de animações
            animations_info = self.pokemon.pokedex.get_pokemon_animations_info(pokemon_id, shiny)
            self._available_animations = animations_info.get("available_animations", [])

            self.pokemon.inmap_animations = {}
            if hasattr(self.pokemon.pokedex, 'get_raw_inmap_data'):
                try:
                    raw_data = self.pokemon.pokedex.get_raw_inmap_data(pokemon_id, shiny)
                    self.pokemon.inmap_animations = raw_data.get("animations", {})
                    self.pokemon.raw_animations = raw_data

                    # Imprime todas as animações disponíveis para debug
                    if self._available_animations:
                        print(f"[ANIMATION] {self.pokemon.name} possui animações: {self._available_animations}")
                except Exception as e:
                    print(f"[ERRO] Falha ao carregar dados brutos: {e}")

            _SPRITE_CACHE[cache_key] = {
                "ui": self.pokemon.ui_sprite,
                "battle": self.pokemon.battle_sprite,
                "inmap": self.pokemon.inmap_frames,
                "animations": self.pokemon.inmap_animations,
                "available_animations": self._available_animations
            }

        self.pokemon.current_direction = "down"
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        self.pokemon.animation_speed = 0.1

        self._load_all_animation_timings()

    def get_available_animations(self) -> list:
        """Retorna lista de todas as animações disponíveis para este Pokémon"""
        return self._available_animations.copy()

    def has_animation(self, animation_name: str) -> bool:
        """Verifica se uma animação específica está disponível"""
        return animation_name.lower() in [a.lower() for a in self._available_animations]

    def _load_all_animation_timings(self):
        """Carrega os tempos de duração dos frames para TODAS as animações"""
        if not hasattr(self.pokemon, 'raw_animations') or not self.pokemon.raw_animations:
            self.pokemon.walk_frame_durations = [8, 8, 8, 8]
            self.pokemon.idle_frame_durations = [10, 10, 10, 10]
            self.pokemon.frame_durations = self.pokemon.idle_frame_durations
            self.pokemon.all_animation_durations = {}
            return

        anim_data = self.pokemon.raw_animations.get("anim_data", {})

        # Armazena durações para todas as animações
        self.pokemon.all_animation_durations = {}

        for anim_name, anim_info in anim_data.items():
            durations = anim_info.get("durations", [])
            if durations:
                self.pokemon.all_animation_durations[anim_name.lower()] = durations

        # Carrega walk e idle específicos
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
            # Verifica se a animação atual tem durações específicas
            if (hasattr(self.pokemon, 'all_animation_durations') and
                    self.pokemon.current_animation in self.pokemon.all_animation_durations):
                self.pokemon.frame_durations = self.pokemon.all_animation_durations[self.pokemon.current_animation]
            elif self.pokemon.current_animation == "walk" and hasattr(self.pokemon, 'walk_frame_durations'):
                self.pokemon.frame_durations = self.pokemon.walk_frame_durations
            elif self.pokemon.current_animation == "charge" and hasattr(self.pokemon, 'all_animation_durations') and "charge" in self.pokemon.all_animation_durations:
                self.pokemon.frame_durations = self.pokemon.all_animation_durations["charge"]
            elif hasattr(self.pokemon, 'idle_frame_durations'):
                self.pokemon.frame_durations = self.pokemon.idle_frame_durations
            else:
                self.pokemon.frame_durations = [8, 8, 8, 8]

            if hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame >= len(
                    self.pokemon.frame_durations):
                self.pokemon.current_frame = 0

    def set_stun_animation(self, is_stunned: bool):
        """
        Define animação de stun (paralisia) apenas quando está atordoado

        Args:
            is_stunned: True se está atordoado (parado), False se pode se mover
        """
        if is_stunned:
            # Está atordoado - mostra animação de charge
            if self.has_animation("charge"):
                # Guarda a animação anterior se ainda não guardou
                if not hasattr(self.pokemon, '_saved_animation_for_stun'):
                    self.pokemon._saved_animation_for_stun = self.pokemon.current_animation
                self.set_animation("charge")
                print(f"[STUN_ANIM] {self.pokemon.name} entrou em stun -> animação charge")
        else:
            # Não está mais atordoado - volta para animação normal
            if hasattr(self.pokemon, '_saved_animation_for_stun'):
                saved = self.pokemon._saved_animation_for_stun
                delattr(self.pokemon, '_saved_animation_for_stun')
                self.set_animation(saved)
                print(f"[STUN_ANIM] {self.pokemon.name} saiu do stun -> volta para {saved}")
            elif self.pokemon.is_moving and self.has_animation("walk"):
                self.set_animation("walk")
            elif self.has_animation("idle"):
                self.set_animation("idle")

    def set_animation(self, animation_name: str):
        """
        Troca a animação atual se disponível

        Args:
            animation_name: Nome da animação (ex: "idle", "walk", "run", "attack", etc)
        """
        if not hasattr(self.pokemon, 'current_animation'):
            return

        # Verifica se a animação está disponível
        if not self.has_animation(animation_name):
            # Se não disponível e não é idle, tenta idle
            if animation_name != "idle" and self.has_animation("idle"):
                animation_name = "idle"
            elif not self.has_animation(animation_name):
                return

        if animation_name == self.pokemon.current_animation:
            return

        self.pokemon.current_animation = animation_name
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        self._update_current_durations()
        self._update_sprite_from_current_animation()

    def set_status_animation(self, status_type):
        """
        Define a animação apropriada baseada no status do Pokémon
        Retorna True se trocou para uma animação de status, False se voltou para normal

        NOTA: Para paralisia, NÃO trocamos animação aqui - a animação charge é controlada
        pelo estado de stun separadamente.
        """
        if status_type is None:
            # Voltou ao normal - restaura animação normal
            self._restore_normal_animation()
            return False

        # Mapeia status para nomes de animação
        status_animation_map = {
            "sleep": "sleep",
            "freeze": "charge",
        }

        anim_name = status_animation_map.get(status_type.lower())

        if anim_name and self.has_animation(anim_name):
            # Guarda a animação anterior para restaurar depois
            if not hasattr(self.pokemon, '_saved_animation'):
                self.pokemon._saved_animation = self.pokemon.current_animation
            self.set_animation(anim_name)
            # Garante que o frame comece do 0
            self.pokemon.current_frame = 0
            self.pokemon.animation_timer = 0
            return True

        return False

    def _restore_normal_animation(self):
        """Restaura a animação normal após o status terminar"""
        if hasattr(self.pokemon, '_saved_animation'):
            saved = self.pokemon._saved_animation
            # Limpa antes de trocar para evitar recursão
            delattr(self.pokemon, '_saved_animation')
            self.set_animation(saved)
            self.pokemon.current_frame = 0
            self.pokemon.animation_timer = 0
        elif self.pokemon.is_moving and self.has_animation("walk"):
            self.set_animation("walk")
        elif self.has_animation("idle"):
            self.set_animation("idle")

    def _update_sprite_from_current_animation(self):
        """Atualiza o sprite baseado na animação atual"""
        if hasattr(self.pokemon,
                   'inmap_animations') and self.pokemon.current_animation in self.pokemon.inmap_animations:
            anim_frames = self.pokemon.inmap_animations[self.pokemon.current_animation]

            # ===== VERIFICA SE A ANIMAÇÃO TEM APENAS UMA DIREÇÃO =====
            # Se tiver apenas uma chave no dicionário, é animação de direção única
            if len(anim_frames) == 1:
                # Pega a única direção disponível
                single_direction = list(anim_frames.keys())[0]
                frames = anim_frames[single_direction]
                if frames and hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame < len(frames):
                    self.pokemon.sprite = frames[self.pokemon.current_frame]
                    return

            # ===== ANIMAÇÃO NORMAL COM MÚLTIPLAS DIREÇÕES =====
            # Tenta a direção atual primeiro
            if self.pokemon.current_direction in anim_frames:
                frames = anim_frames[self.pokemon.current_direction]
                if frames and hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame < len(frames):
                    self.pokemon.sprite = frames[self.pokemon.current_frame]
                    return

            # Tenta encontrar direção alternativa (mapeamento de 8 para 4)
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

        # Fallback: usa inmap_frames (sistema antigo de 4 direções)
        if hasattr(self.pokemon, 'inmap_frames') and self.pokemon.current_direction in self.pokemon.inmap_frames:
            frames_list = self.pokemon.inmap_frames[self.pokemon.current_direction]
            if frames_list and hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame < len(frames_list):
                self.pokemon.sprite = frames_list[self.pokemon.current_frame]

    def _get_current_animation_frame_count(self) -> int:
        """Retorna o número de frames da animação atual"""
        if hasattr(self.pokemon,
                   'inmap_animations') and self.pokemon.current_animation in self.pokemon.inmap_animations:
            anim_frames = self.pokemon.inmap_animations[self.pokemon.current_animation]

            # ===== SE É DIREÇÃO ÚNICA, PEGA OS FRAMES DA ÚNICA DIREÇÃO =====
            if len(anim_frames) == 1:
                single_direction = list(anim_frames.keys())[0]
                return len(anim_frames[single_direction])

            # Tenta a direção atual primeiro
            if self.pokemon.current_direction in anim_frames:
                return len(anim_frames[self.pokemon.current_direction])

            # Tenta encontrar direção alternativa
            dir_mapping = {
                "down": ["down", "down-left", "down-right"],
                "left": ["left", "down-left", "up-left"],
                "right": ["right", "down-right", "up-right"],
                "up": ["up", "up-left", "up-right"]
            }

            for src_dir in dir_mapping.get(self.pokemon.current_direction, [self.pokemon.current_direction]):
                if src_dir in anim_frames:
                    return len(anim_frames[src_dir])

        # Fallback: usa inmap_frames
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

        # ===== PRIMEIRO: VERIFICA SE ESTÁ EM ANIMAÇÃO DE STATUS =====
        current_anim = getattr(self.pokemon, 'current_animation', 'idle')
        status_animations = ['sleep','charge']

        if current_anim in status_animations:
            # Está em animação de status - só atualiza o frame, não troca animação
            self.pokemon.animation_timer += dt * 60

            frame_time = self.pokemon.animation_speed
            if hasattr(self.pokemon, 'frame_durations') and self.pokemon.frame_durations:
                current_frame = getattr(self.pokemon, 'current_frame', 0)
                if current_frame < len(self.pokemon.frame_durations):
                    frame_time = self.pokemon.frame_durations[current_frame]

            if self.pokemon.animation_timer >= frame_time:
                self.pokemon.animation_timer = 0
                max_frames = self._get_current_animation_frame_count()

                if max_frames > 0:
                    next_frame = self.pokemon.current_frame + 1

                    # ===== TODAS AS ANIMAÇÕES DE STATUS REPETEM EM LOOP =====
                    # sleep, freeze, charge, hurt, paralysis - todas devem repetir
                    if next_frame >= max_frames:
                        # Reinicia o loop para todas as animações de status
                        self.pokemon.current_frame = 0
                    else:
                        self.pokemon.current_frame = next_frame

                    self._update_sprite_from_current_animation()
                return

        # ===== ANIMAÇÃO NORMAL (IDLE/WALK) - DETECTA MOVIMENTO =====
        is_moving_now = self._is_moving()

        if is_moving_now and not self.pokemon.is_moving:
            self.pokemon.is_moving = True
            if self.has_animation("walk"):
                self.set_animation("walk")
            elif self.has_animation("run"):
                self.set_animation("run")
            elif self._available_animations:
                self.set_animation(self._available_animations[0])

        elif not is_moving_now and self.pokemon.is_moving:
            self.pokemon.is_moving = False
            if self.has_animation("idle"):
                self.set_animation("idle")
            elif self._available_animations:
                self.set_animation(self._available_animations[0])

        # ===== ATUALIZA O FRAME DA ANIMAÇÃO ATUAL =====
        self.pokemon.animation_timer += dt * 60

        frame_time = self.pokemon.animation_speed
        if hasattr(self.pokemon, 'frame_durations') and self.pokemon.frame_durations:
            current_frame = getattr(self.pokemon, 'current_frame', 0)
            if current_frame < len(self.pokemon.frame_durations):
                frame_time = self.pokemon.frame_durations[current_frame]

        if self.pokemon.animation_timer >= frame_time:
            self.pokemon.animation_timer = 0
            max_frames = self._get_current_animation_frame_count()

            if max_frames > 0:
                next_frame = self.pokemon.current_frame + 1

                # ===== VERIFICA SE É ANIMAÇÃO DE ATAQUE =====
                is_attack_anim = hasattr(self.pokemon,
                                         '_attack_animation_active') and self.pokemon._attack_animation_active

                if next_frame >= max_frames:
                    if is_attack_anim:
                        # Ataque terminou - NÃO reinicia, mantém no último frame
                        # O update do pokemon vai lidar com o fim da animação
                        self.pokemon.current_frame = max_frames - 1
                    else:
                        # Animações normais (idle, walk) reiniciam em loop
                        self.pokemon.current_frame = 0
                else:
                    self.pokemon.current_frame = next_frame

                self._update_sprite_from_current_animation()