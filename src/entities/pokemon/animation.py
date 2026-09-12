# src/entities/pokemon/animation.py
import pygame


class PokemonAnimation:
    """Gerencia animações e sprites do Pokémon - CENTRALIZADO"""

    def __init__(self, pokemon):
        self.pokemon = pokemon
        self._available_animations = []  # Cache de animações disponíveis
        self._victory_hop_active = False
        self._victory_hop_delay_remaining = 0.0

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

            animations_info = self.pokemon.pokedex.get_pokemon_animations_info(pokemon_id, shiny)
            self._available_animations = animations_info.get("available_animations", [])

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
                "animations": self.pokemon.inmap_animations,
                "available_animations": self._available_animations
            }

        self.pokemon.current_direction = "down"
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        self.pokemon.animation_speed = 0.1

        self._load_all_animation_timings()

    # ===== MÉTODOS PÚBLICOS PRINCIPAIS =====
    def get_current_frame(self) -> int:
        """Retorna o frame atual"""
        return self.pokemon.current_frame

    def get_current_animation(self) -> str:
        """Retorna a animação atual"""
        return self.pokemon.current_animation

    def get_current_direction(self) -> str:
        """Retorna a direção atual"""
        return self.pokemon.current_direction

    def is_moving(self) -> bool:
        """Verifica se está em movimento"""
        return self.pokemon.is_moving

    def update(self, dt):
        """
        MÉTODO PRINCIPAL - Atualiza animação baseada no estado do Pokémon.
        Deve ser chamado TODO FRAME, independente do estado (vivo/morto).
        """
        # ===== PRIORIDADE 0: VICTORY HOP (COMEMORAÇÃO) =====
        if getattr(self, '_victory_hop_active', False):
            self.cancel_oneshot_animation()  # ← cancela pose se houver
            self._update_victory_hop(dt)
            return

        # ===== PRIORIDADE 1: HURT ANIMATION =====
        if hasattr(self.pokemon, '_hurt_animation_active') and self.pokemon._hurt_animation_active:
            self.cancel_oneshot_animation()  # ← cancela pose se houver
            self._update_hurt_animation_frame(dt)
            return

        # ===== PRIORIDADE 2: DERROTADO =====
        if self.pokemon.is_defeated:
            self.cancel_oneshot_animation()  # ← cancela pose se houver
            self._update_defeated_animation(dt)
            return

        # ===== PRIORIDADE 3: ANIMAÇÃO DE ATAQUE =====
        if hasattr(self.pokemon, '_attack_animation_active') and self.pokemon._attack_animation_active:
            self.cancel_oneshot_animation()  # ← cancela pose se houver
            self._update_attack_animation(dt)
            return

        # ===== PRIORIDADE 4: STATUS EFFECTS =====
        status_anim = self._get_status_animation()
        if status_anim:
            self.cancel_oneshot_animation()  # ← cancela pose se houver
            self._update_status_animation(status_anim, dt)
            return

        # ===== PRIORIDADE 5: ONESHOT ANIMATION (POSE/HOP/DANCE) =====
        if getattr(self.pokemon, '_oneshot_animation_active', False):
            self._update_oneshot_animation(dt)
            return

        # ===== PRIORIDADE 6: ANIMAÇÃO NORMAL (IDLE/WALK) =====
        self._update_normal_animation(dt)

    def _update_victory_hop(self, dt):
        """Atualiza a animação de comemoração (com delay opcional antes do loop)."""
        # ===== FASE 1: AGUARDANDO DELAY =====
        if self._victory_hop_delay_remaining > 0.0:
            self._victory_hop_delay_remaining -= dt
            if self._victory_hop_delay_remaining > 0.0:
                # Ainda esperando — continua com a animação normal
                self._update_normal_animation(dt)
                return
            # Delay acabou: inicia o hop agora
            self._start_hop_animation()

        # ===== FASE 2: LOOP DE HOP (FORÇADO) =====
        if self.pokemon.current_animation != "hop":
            self.set_animation("hop")
            self.pokemon.current_frame = 0
            self.pokemon.animation_timer = 0

        # Avança o timer
        self.pokemon.animation_timer += dt * 60

        # Determina a duração do frame atual
        frame_time = self.pokemon.animation_speed
        if hasattr(self.pokemon, 'frame_durations') and self.pokemon.frame_durations:
            current_frame = getattr(self.pokemon, 'current_frame', 0)
            if 0 <= current_frame < len(self.pokemon.frame_durations):
                frame_time = self.pokemon.frame_durations[current_frame]

        # Avançou o suficiente?
        if self.pokemon.animation_timer >= frame_time:
            self.pokemon.animation_timer = 0
            max_frames = self._get_current_animation_frame_count()

            if max_frames > 0:
                next_frame = self.pokemon.current_frame + 1
                if next_frame >= max_frames:
                    # ===== LOOP FORÇADO: volta para 0 =====
                    next_frame = 0

                self.pokemon.current_frame = next_frame
                self._update_sprite_from_current_animation()

    # ===== MÉTODOS PRIVADOS DE ATUALIZAÇÃO =====

    def _update_attack_animation(self, dt):
        """Atualiza animação de ataque e aplica dano no momento certo"""
        if not hasattr(self.pokemon, '_attack_animation_timer'):
            self.pokemon._attack_animation_timer = 0
        self.pokemon._attack_animation_timer += dt

        # Calcula duração total
        total_duration = self._get_current_animation_duration()

        # Aplica dano em % da animação
        damage_percent = getattr(self.pokemon, '_damage_frame_percent', 0.6)
        damage_trigger_time = total_duration * damage_percent

        if not getattr(self.pokemon, '_damage_applied',
                       False) and self.pokemon._attack_animation_timer >= damage_trigger_time:
            self.pokemon._damage_applied = True
            # Executa o ataque
            if hasattr(self.pokemon, '_pending_attack_target') and hasattr(self.pokemon, '_pending_attack_move'):
                target = self.pokemon._pending_attack_target
                move_name = self.pokemon._pending_attack_move

                # Encontra o move pelo nome
                move = None
                for m in self.pokemon.moves:
                    if m.name == move_name:
                        move = m
                        break

                if move and target:
                    self.pokemon.combat._execute_attack(target, move)

        # Avança ou termina animação
        if self.pokemon._attack_animation_timer >= total_duration:
            self._finish_attack_animation()
        else:
            self._advance_frame(dt)

    def _update_defeated_animation(self, dt):
        """Atualiza animação de Pokémon derrotado (sleep ou idle)"""
        target_anim = "sleep" if self.has_animation("sleep") else "idle"

        if self.pokemon.current_animation != target_anim:
            self.set_animation(target_anim)

        self._advance_frame(dt)

    def _finish_attack_animation(self):
        """Finaliza animação de ataque e restaura animação anterior"""
        # Só executa o ataque se NÃO foi aplicado ainda
        if not getattr(self.pokemon, '_damage_applied', False):
            self.pokemon._damage_applied = True
            if hasattr(self.pokemon, '_pending_attack_target') and hasattr(self.pokemon, '_pending_attack_move'):
                target = self.pokemon._pending_attack_target
                move_name = self.pokemon._pending_attack_move

                # Encontra o move pelo nome
                move = None
                for m in self.pokemon.moves:
                    if m.name == move_name:
                        move = m
                        break

                if move and target:
                    self.pokemon.combat._execute_attack(target, move)

        # Restaura animação anterior
        if hasattr(self.pokemon, '_saved_animation_before_attack'):
            self.set_animation(self.pokemon._saved_animation_before_attack)
            delattr(self.pokemon, '_saved_animation_before_attack')

        # Limpa flags
        if hasattr(self.pokemon, '_attack_animation_active'):
            delattr(self.pokemon, '_attack_animation_active')
        if hasattr(self.pokemon, '_attack_animation_timer'):
            delattr(self.pokemon, '_attack_animation_timer')
        if hasattr(self.pokemon, '_damage_applied'):
            delattr(self.pokemon, '_damage_applied')
        if hasattr(self.pokemon, '_damage_frame_percent'):
            delattr(self.pokemon, '_damage_frame_percent')
        if hasattr(self.pokemon, '_pending_attack_move'):
            delattr(self.pokemon, '_pending_attack_move')
        if hasattr(self.pokemon, '_pending_attack_target'):
            delattr(self.pokemon, '_pending_attack_target')

    def _update_status_animation(self, status_anim: str, dt):
        """Atualiza animação de status (sleep, charge, etc)"""
        if self.pokemon.current_animation != status_anim:
            # Salva animação anterior para restaurar depois
            if not hasattr(self.pokemon, '_saved_animation'):
                self.pokemon._saved_animation = self.pokemon.current_animation
            self.set_animation(status_anim)

        self._advance_frame(dt)

    def _update_normal_animation(self, dt):
        """Atualiza animação normal baseada em movimento (idle/walk)"""
        is_moving = self._is_moving()

        # Troca animação se necessário
        if is_moving and not self.pokemon.is_moving:
            self.pokemon.is_moving = True
            if self.has_animation("walk"):
                self.set_animation("walk")
            elif self.has_animation("run"):
                self.set_animation("run")
        elif not is_moving and self.pokemon.is_moving:
            self.pokemon.is_moving = False
            if self.has_animation("idle"):
                self.set_animation("idle")

        # Se está em stun por paralisia, usa charge
        if self._is_stunned_by_paralysis():
            if self.pokemon.current_animation != "charge" and self.has_animation("charge"):
                self.set_animation("charge")

        self._advance_frame(dt)

    # ===== MÉTODOS AUXILIARES =====

    def _get_status_animation(self) -> str:
        """Retorna nome da animação de status ativo, ou None"""
        if not hasattr(self.pokemon, 'effect_manager') or not self.pokemon.effect_manager:
            return None

        status = self.pokemon.effect_manager.get_status(self.pokemon)
        if not status or status.type.value == "none":
            # Restaura animação normal se tinha salva
            if hasattr(self.pokemon, '_saved_animation'):
                saved = self.pokemon._saved_animation
                delattr(self.pokemon, '_saved_animation')
                self.set_animation(saved)
            return None

        status_map = {
            "sleep": "sleep",
            "paralysis": "charge",
            "freeze": "charge",
        }
        return status_map.get(status.type.value)

    def _is_stunned_by_paralysis(self) -> bool:
        """Verifica se está atordoado pela paralisia"""
        if not hasattr(self.pokemon, 'effect_manager') or not self.pokemon.effect_manager:
            return False
        status = self.pokemon.effect_manager.get_status(self.pokemon)
        if status and status.type.value == "paralysis":
            return status.is_stunned()
        return False

    def _get_current_animation_duration(self) -> float:
        """Retorna duração total da animação atual em segundos"""
        if hasattr(self.pokemon, 'frame_durations') and self.pokemon.frame_durations:
            return sum(self.pokemon.frame_durations) / 60.0
        return 0.5  # Fallback

    def _advance_frame(self, dt):
        """Avança para o próximo frame da animação atual"""
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

                # Verifica se deve loopar ou parar
                is_attack = hasattr(self.pokemon, '_attack_animation_active') and self.pokemon._attack_animation_active

                if next_frame >= max_frames:
                    if is_attack:
                        self.pokemon.current_frame = max_frames - 1  # Mantém último frame
                    else:
                        self.pokemon.current_frame = 0  # Loop
                else:
                    self.pokemon.current_frame = next_frame

                self._update_sprite_from_current_animation()

    def _finish_attack_animation(self):
        """Finaliza animação de ataque e restaura animação anterior"""
        # Executa o ataque se ainda não foi aplicado
        if hasattr(self.pokemon, '_pending_attack_target') and not getattr(self.pokemon, '_damage_applied', False):
            self.pokemon._damage_applied = True
            if hasattr(self.pokemon, 'combat') and hasattr(self.pokemon, '_pending_attack_target'):
                move_name = getattr(self.pokemon, '_pending_attack_move', None)
                target = self.pokemon._pending_attack_target

                # Encontra o move pelo nome
                move = None
                for m in self.pokemon.moves:
                    if m.name == move_name:
                        move = m
                        break

                if move and target:
                    self.pokemon.combat._execute_attack(target, move)

        # Restaura animação anterior
        if hasattr(self.pokemon, '_saved_animation_before_attack'):
            self.set_animation(self.pokemon._saved_animation_before_attack)
            delattr(self.pokemon, '_saved_animation_before_attack')

        # Limpa flags
        if hasattr(self.pokemon, '_attack_animation_active'):
            delattr(self.pokemon, '_attack_animation_active')
        if hasattr(self.pokemon, '_attack_animation_timer'):
            delattr(self.pokemon, '_attack_animation_timer')
        if hasattr(self.pokemon, '_damage_applied'):
            delattr(self.pokemon, '_damage_applied')
        if hasattr(self.pokemon, '_damage_frame_percent'):
            delattr(self.pokemon, '_damage_frame_percent')
        if hasattr(self.pokemon, '_pending_attack_move'):
            delattr(self.pokemon, '_pending_attack_move')
        if hasattr(self.pokemon, '_pending_attack_target'):
            delattr(self.pokemon, '_pending_attack_target')

    # ===== MÉTODOS EXISTENTES (mantidos) =====

    def get_available_animations(self) -> list:
        return self._available_animations.copy()

    def has_animation(self, animation_name: str) -> bool:
        return animation_name.lower() in [a.lower() for a in self._available_animations]

    def set_animation(self, animation_name: str):
        """Troca a animação atual se disponível"""
        if not hasattr(self.pokemon, 'current_animation'):
            return

        if not self.has_animation(animation_name):
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

    def set_animation_direct(self, animation_name: str):
        """Alias para set_animation"""
        self.set_animation(animation_name)

    def play_hurt_animation(self) -> bool:
        """Toca a animação de dano (hurt)"""
        if not self.has_animation("hurt"):
            return False

        if hasattr(self.pokemon, '_hurt_animation_active') and self.pokemon._hurt_animation_active:
            return False

        self.pokemon._saved_animation_before_hurt = self.pokemon.current_animation
        self.pokemon._saved_direction_before_hurt = self.pokemon.current_direction

        self.set_animation("hurt")
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        self.pokemon._hurt_animation_active = True
        self.pokemon._hurt_animation_played_once = False

        return True

    def _finish_hurt_animation(self):
        """Finaliza a animação de hurt e restaura a animação anterior"""
        saved_anim = getattr(self.pokemon, '_saved_animation_before_hurt', 'idle')

        if hasattr(self.pokemon, '_saved_direction_before_hurt'):
            self.pokemon.current_direction = self.pokemon._saved_direction_before_hurt
            delattr(self.pokemon, '_saved_direction_before_hurt')

        self.set_animation(saved_anim)
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0

        # Limpa flags
        delattr(self.pokemon, '_hurt_animation_active')
        if hasattr(self.pokemon, '_hurt_animation_played_once'):
            delattr(self.pokemon, '_hurt_animation_played_once')
        if hasattr(self.pokemon, '_saved_animation_before_hurt'):
            delattr(self.pokemon, '_saved_animation_before_hurt')

    def _update_hurt_animation_frame(self, dt):
        """Atualiza os frames da animação de hurt e finaliza quando terminar"""
        # Avança o frame
        self._advance_frame(dt)

        # Verifica se a animação terminou
        max_frames = self._get_current_animation_frame_count()

        if max_frames > 0 and self.pokemon.current_frame >= max_frames - 1:
            # Último frame atingido, finaliza a animação
            self._finish_hurt_animation()

    # ===== MÉTODOS INTERNOS (mantidos) =====

    def _load_all_animation_timings(self):
        """Carrega os tempos de duração dos frames para TODAS as animações"""
        if not hasattr(self.pokemon, 'raw_animations') or not self.pokemon.raw_animations:
            self.pokemon.walk_frame_durations = [8, 8, 8, 8]
            self.pokemon.idle_frame_durations = [10, 10, 10, 10]
            self.pokemon.frame_durations = self.pokemon.idle_frame_durations
            self.pokemon.all_animation_durations = {}
            return

        anim_data = self.pokemon.raw_animations.get("anim_data", {})

        self.pokemon.all_animation_durations = {}
        for anim_name, anim_info in anim_data.items():
            durations = anim_info.get("durations", [])
            if durations:
                self.pokemon.all_animation_durations[anim_name.lower()] = durations

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
            if (hasattr(self.pokemon, 'all_animation_durations') and
                    self.pokemon.current_animation in self.pokemon.all_animation_durations):
                self.pokemon.frame_durations = self.pokemon.all_animation_durations[self.pokemon.current_animation]
            elif self.pokemon.current_animation == "walk" and hasattr(self.pokemon, 'walk_frame_durations'):
                self.pokemon.frame_durations = self.pokemon.walk_frame_durations
            elif hasattr(self.pokemon, 'idle_frame_durations'):
                self.pokemon.frame_durations = self.pokemon.idle_frame_durations
            else:
                self.pokemon.frame_durations = [8, 8, 8, 8]

            if hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame >= len(
                    self.pokemon.frame_durations):
                self.pokemon.current_frame = 0

    def _update_sprite_from_current_animation(self):
        """Atualiza o sprite baseado na animação atual"""
        if hasattr(self.pokemon,
                   'inmap_animations') and self.pokemon.current_animation in self.pokemon.inmap_animations:
            anim_frames = self.pokemon.inmap_animations[self.pokemon.current_animation]

            if len(anim_frames) == 1:
                single_direction = list(anim_frames.keys())[0]
                frames = anim_frames[single_direction]
                if frames and hasattr(self.pokemon, 'current_frame') and self.pokemon.current_frame < len(frames):
                    self.pokemon.sprite = frames[self.pokemon.current_frame]
                    return

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

            if len(anim_frames) == 1:
                single_direction = list(anim_frames.keys())[0]
                return len(anim_frames[single_direction])

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

    def set_status_animation(self, status_type):
        """
        Define a animação apropriada baseada no status do Pokémon
        Retorna True se trocou para uma animação de status, False se voltou para normal

        Args:
            status_type: String com o tipo do status (sleep, paralysis, freeze) ou None
        """
        if status_type is None:
            # Voltou ao normal - restaura animação normal
            self._restore_normal_animation()
            return False

        # Mapeia status para nomes de animação
        status_animation_map = {
            "sleep": "sleep",
            "freeze": "charge",
            # Paralysis NÃO troca animação aqui - é controlado pelo stun separadamente
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
        else:
            # Não está mais atordoado - volta para animação normal
            if hasattr(self.pokemon, '_saved_animation_for_stun'):
                saved = self.pokemon._saved_animation_for_stun
                delattr(self.pokemon, '_saved_animation_for_stun')
                self.set_animation(saved)
            elif self.pokemon.is_moving and self.has_animation("walk"):
                self.set_animation("walk")
            elif self.has_animation("idle"):
                self.set_animation("idle")

    def on_stun_state_changed(self, is_stunned: bool):
        """Callback para quando o estado de stun muda - compatibilidade"""
        self.set_stun_animation(is_stunned)

    def _is_moving(self) -> bool:
        """Verifica se o Pokémon está em movimento"""
        if hasattr(self.pokemon, 'last_x') and hasattr(self.pokemon, 'last_y'):
            dx = abs(self.pokemon.x - self.pokemon.last_x)
            dy = abs(self.pokemon.y - self.pokemon.last_y)
            return (dx + dy) > 0.5
        return False

    def play_victory_hop(self, delay: float = 0.0) -> bool:
        """
        Inicia a animação de comemoração (hop) quando a fase é completada.
        Só funciona se o Pokémon tiver a animação 'hop' disponível.

        Args:
            delay: tempo em segundos antes de começar a pular (para escalonar)

        Returns:
            True se a animação foi iniciada, False caso contrário.
        """
        if not self.has_animation("hop"):
            return False

        # Salva a animação anterior para restaurar depois
        if not hasattr(self.pokemon, '_saved_animation_before_victory'):
            self.pokemon._saved_animation_before_victory = self.pokemon.current_animation

        # Ativa o modo de celebração
        self._victory_hop_active = True
        self.pokemon._victory_hop_active = True
        self._victory_hop_delay_remaining = max(0.0, delay)

        if self._victory_hop_delay_remaining > 0.0:
            # Aguarda o delay antes de tocar o hop — continua na animação atual
            print(f"[VICTORY] {self.pokemon.name} vai comemorar em {delay:.2f}s...")
            return True

        # Sem delay: começa imediatamente
        self._start_hop_animation()
        return True

    def _start_hop_animation(self):
        """Inicia de fato a animação hop (chamado após o delay)."""
        self.set_animation("hop")
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        print(f"[VICTORY] {self.pokemon.name} iniciou animação de comemoração (hop)!")

    # ANIMAÇÕES PARA FOTOS
    def stop_victory_hop(self):
        """Para a animação de comemoração e restaura o estado normal."""
        if not self._victory_hop_active:
            return

        self._victory_hop_active = False
        self.pokemon._victory_hop_active = False
        self._victory_hop_delay_remaining = 0.0

        # Restaura a animação anterior
        if hasattr(self.pokemon, '_saved_animation_before_victory'):
            saved = self.pokemon._saved_animation_before_victory
            delattr(self.pokemon, '_saved_animation_before_victory')
            self.set_animation(saved)
        elif self.has_animation("idle"):
            self.set_animation("idle")

        print(f"[VICTORY] {self.pokemon.name} parou a comemoração.")

    # ===== ANIMAÇÃO ONE-SHOT (POSE / HOP / DANCE) =====

    def play_oneshot_animation(self, animation_name: str) -> bool:
        """
        Toca uma animação UMA VEZ e depois volta ao normal.
        Ideal para pose/hop/dance quando o jogador clica no pokémon.

        Args:
            animation_name: nome da animação (pose, hop, dance)

        Returns:
            True se a animação foi iniciada, False caso contrário.
        """
        if not self.has_animation(animation_name):
            return False

        # Se já tem uma oneshot ativa, não reinicia
        if getattr(self.pokemon, '_oneshot_animation_active', False):
            return False

        # Se está derrotado, não anima
        if self.pokemon.is_defeated:
            return False

        # Salva a animação atual para restaurar depois
        self.pokemon._saved_animation_before_oneshot = self.pokemon.current_animation

        # Ativa modo oneshot
        self.pokemon._oneshot_animation_active = True
        self.pokemon._oneshot_animation_name = animation_name

        self.set_animation(animation_name)
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0

        print(f"[POSE] {self.pokemon.name} iniciou animação one-shot: {animation_name}")
        return True

    def cancel_oneshot_animation(self):
        """Cancela qualquer oneshot em andamento e limpa as flags."""
        if not getattr(self.pokemon, '_oneshot_animation_active', False):
            return

        self.pokemon._oneshot_animation_active = False
        if hasattr(self.pokemon, '_oneshot_animation_name'):
            delattr(self.pokemon, '_oneshot_animation_name')
        if hasattr(self.pokemon, '_saved_animation_before_oneshot'):
            delattr(self.pokemon, '_saved_animation_before_oneshot')

        print(f"[POSE] {self.pokemon.name} oneshot cancelada por interrupção")

    def _update_oneshot_animation(self, dt):
        """Avança os frames da oneshot. Quando passa do último, finaliza."""
        max_frames = self._get_current_animation_frame_count()
        if max_frames <= 0:
            self._finish_oneshot_animation()
            return

        # ===== JÁ ESTÁ NO ÚLTIMO FRAME: SÓ ESPERA O TEMPO DELE PASSAR =====
        if self.pokemon.current_frame >= max_frames - 1:
            # Pega o tempo do último frame
            frame_time = self.pokemon.animation_speed
            if hasattr(self.pokemon, 'frame_durations') and self.pokemon.frame_durations:
                last_idx = min(len(self.pokemon.frame_durations) - 1, max_frames - 1)
                frame_time = self.pokemon.frame_durations[last_idx]

            # Acumula o tempo
            self.pokemon.animation_timer += dt * 60

            if self.pokemon.animation_timer >= frame_time:
                # Terminou o último frame → finaliza
                self._finish_oneshot_animation()
            return

        # ===== AINDA NÃO ESTÁ NO ÚLTIMO: AVANÇA NORMALMENTE =====
        self.pokemon.animation_timer += dt * 60

        frame_time = self.pokemon.animation_speed
        if hasattr(self.pokemon, 'frame_durations') and self.pokemon.frame_durations:
            current_frame = getattr(self.pokemon, 'current_frame', 0)
            if current_frame < len(self.pokemon.frame_durations):
                frame_time = self.pokemon.frame_durations[current_frame]

        if self.pokemon.animation_timer >= frame_time:
            self.pokemon.animation_timer = 0
            self.pokemon.current_frame += 1
            self._update_sprite_from_current_animation()

    def _advance_frame_oneshot(self, dt):
        """Avança o frame sem loop (para oneshot)"""
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
                if next_frame >= max_frames:
                    # Mantém no último (não loopa)
                    self.pokemon.current_frame = max_frames - 1
                else:
                    self.pokemon.current_frame = next_frame
                self._update_sprite_from_current_animation()

    def _finish_oneshot_animation(self):
        """Restaura a animação anterior depois da oneshot."""
        saved = getattr(self.pokemon, '_saved_animation_before_oneshot', 'idle')

        # ===== LIMPA TODAS AS FLAGS ANTES DE TROCAR DE ANIMAÇÃO =====
        self.pokemon._oneshot_animation_active = False
        if hasattr(self.pokemon, '_oneshot_animation_name'):
            delattr(self.pokemon, '_oneshot_animation_name')
        if hasattr(self.pokemon, '_saved_animation_before_oneshot'):
            delattr(self.pokemon, '_saved_animation_before_oneshot')

        # ===== LIMPA COOLDOWN (permite nova pose imediata) =====
        if hasattr(self.pokemon, '_pose_cooldown'):
            self.pokemon._pose_cooldown = 0.0

        # ===== FORÇA RESTAURAÇÃO DA ANIMAÇÃO ANTERIOR =====
        # Não use set_animation aqui, porque ele tem uma guarda que só troca
        # se a animação for diferente. Como pode ser a mesma (idle→idle),
        # forçamos direto:
        self.pokemon.current_animation = saved
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        self._update_current_durations()
        self._update_sprite_from_current_animation()

        print(f"[POSE] {self.pokemon.name} finalizou animação one-shot (voltou para '{saved}')")

    def is_oneshot_active(self) -> bool:
        """Retorna True se uma animação one-shot está em andamento."""
        return getattr(self.pokemon, '_oneshot_animation_active', False)