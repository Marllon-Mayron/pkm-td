# src/battle/effects/effect_manager.py
from typing import Dict, List, Optional, Tuple
from .status_effect import StatusEffect, StatusType
from .stat_modifier import StatModifier, StatType, StatStage
import pygame


class EffectManager:
    """
    Gerencia todos os efeitos aplicados aos Pokémon
    """

    def __init__(self):
        # Status effects por Pokémon
        self.status_effects: Dict[int, StatusEffect] = {}

        # Stat modifiers por Pokémon
        self.stat_modifiers: Dict[int, List[StatModifier]] = {}

        self._pokemon_refs: Dict[int, object] = {}

        # Stat stages por Pokémon
        self.stat_stages: Dict[int, StatStage] = {}

        # Feedback visual (APENAS para efeitos temporários como "MISS", "Drenou", etc)
        self.status_texts: List[Tuple[int, str, float]] = []

        # Tempo para ticks de status (a cada 2 segundos)
        self.status_timer: float = 0.0
        self.STATUS_TICK_INTERVAL = 2.0
        self.font_cache = {}

    def apply_status(self, pokemon, status: StatusEffect, source=None):
        """Aplica um efeito de status a um Pokémon"""
        pokemon_id = id(pokemon)

        if pokemon_id in self.status_effects:
            existing = self.status_effects[pokemon_id]
            if existing.type != StatusType.NONE:
                conflicting = [StatusType.PARALYSIS, StatusType.BURN, StatusType.POISON]
                if existing.type in conflicting and status.type in conflicting:
                    return False
                if existing.type in [StatusType.SLEEP, StatusType.FREEZE]:
                    self.remove_status(pokemon)
                else:
                    return False

        self.status_effects[pokemon_id] = status
        status.apply(pokemon, self)

        # REMOVIDO: add_status_text - não mostra texto temporário
        # Apenas o indicador permanente será mostrado

        return True

    def remove_status(self, pokemon):
        """Remove efeito de status do Pokémon"""
        pokemon_id = id(pokemon)

        if pokemon_id in self.status_effects:
            status = self.status_effects[pokemon_id]
            status.remove(pokemon, self)
            del self.status_effects[pokemon_id]

            # Remove modificador de velocidade da paralisia
            if status.type == StatusType.PARALYSIS:
                from .stat_modifier import StatType
                # Remove o modificador de speed (aplica +2 para compensar)
                if pokemon_id in self.stat_stages:
                    self.stat_stages[pokemon_id].modify(StatType.SPEED, 2)

            return True

        return False

    def get_status(self, pokemon) -> Optional[StatusEffect]:
        """Retorna o status atual do Pokémon"""
        return self.status_effects.get(id(pokemon))

    def register_pokemon(self, pokemon):
        """Registra um Pokémon para poder atualizá-lo quando necessário"""
        self._pokemon_refs[id(pokemon)] = pokemon
        print(f"[EFFECT] Pokémon {pokemon.name} registrado (id={id(pokemon)})")

    def unregister_pokemon(self, pokemon):
        """Remove um Pokémon do registro"""
        pokemon_id = id(pokemon)
        if pokemon_id in self._pokemon_refs:
            del self._pokemon_refs[pokemon_id]
            print(f"[EFFECT] Pokémon {pokemon.name} removido do registro")

    def add_stat_modifier(self, pokemon, stat_type: StatType, stages: int, duration: float = None):
        """Adiciona um modificador de stat a um Pokémon"""
        pokemon_id = id(pokemon)

        print(
            f"[EFFECT] Aplicando modificador em {pokemon.name}: {stat_type} {stages:+d} (duração: {duration if duration else 'permanente'})")

        # Inicializa stage se necessário
        if pokemon_id not in self.stat_stages:
            self.stat_stages[pokemon_id] = StatStage()

        # Aplica a modificação nos estágios
        old_stage = self.stat_stages[pokemon_id].get_stage(stat_type)
        new_stage = self.stat_stages[pokemon_id].modify(stat_type, stages)

        print(f"[EFFECT] {pokemon.name} - {stat_type}: {old_stage:+d} -> {new_stage:+d}")

        # Guarda o modificador para controle de duração
        if pokemon_id not in self.stat_modifiers:
            self.stat_modifiers[pokemon_id] = []

        modifier = StatModifier(stat_type, stages, duration)
        self.stat_modifiers[pokemon_id].append(modifier)

        # ===== FORÇA ATUALIZAÇÃO DA VELOCIDADE IMEDIATAMENTE =====
        if stat_type == StatType.SPEED and hasattr(pokemon, 'update_move_speed_from_effects'):
            pokemon.update_move_speed_from_effects()
            print(f"[SPEED] Velocidade de {pokemon.name} atualizada imediatamente após aplicar modificador")

    def _get_stat_name(self, stat_type: StatType) -> str:
        """Retorna o nome do stat em português (para uso interno)"""
        names = {
            StatType.ATTACK: "Ataque",
            StatType.DEFENSE: "Defesa",
            StatType.SP_ATTACK: "Ataque Especial",
            StatType.SP_DEFENSE: "Defesa Especial",
            StatType.SPEED: "Velocidade",
            StatType.ACCURACY: "Precisão",
            StatType.EVASION: "Evasão"
        }
        return names.get(stat_type, stat_type.value)

    def get_stat_multiplier(self, pokemon, stat_type: StatType) -> float:
        """Retorna o multiplicador total para um stat"""
        pokemon_id = id(pokemon)
        #print(f"[EFFECT_DEBUG] get_stat_multiplier para {pokemon.name}, stat={stat_type}")

        if pokemon_id in self.stat_stages:
            stage = self.stat_stages[pokemon_id].get_stage(stat_type)
            multiplier = self.stat_stages[pokemon_id].get_multiplier(stat_type)
            #print(f"[EFFECT_DEBUG] {pokemon.name}: stage={stage}, multiplier={multiplier:.2f}")
            return multiplier
        else:
            return 1.0

    def get_stat_stage(self, pokemon, stat_type: StatType) -> int:
        """Retorna o estágio atual de um stat"""
        pokemon_id = id(pokemon)

        if pokemon_id in self.stat_stages:
            return self.stat_stages[pokemon_id].get_stage(stat_type)

        return 0

    def get_all_modifiers(self, pokemon) -> Dict[str, int]:
        """Retorna todos os modificadores ativos para um Pokémon"""
        pokemon_id = id(pokemon)

        if pokemon_id in self.stat_stages:
            return self.stat_stages[pokemon_id].get_all_active_modifiers()

        return {}

    # src/battle/effects/effect_manager.py
    # Modifique o método update

    def update(self, dt: float):
        """Atualiza todos os efeitos - dt em segundos"""

        # Atualiza modificadores com duração limitada
        expired_modifiers = []
        pokemon_to_update = set()

        for pokemon_id, modifiers in self.stat_modifiers.items():
            for modifier in modifiers[:]:
                if not modifier.is_permanent:
                    if not modifier.update(dt):
                        expired_modifiers.append((pokemon_id, modifier))
                        modifiers.remove(modifier)
                        pokemon_to_update.add(pokemon_id)

        # Aplica a remoção de estágios
        for pokemon_id, modifier in expired_modifiers:
            if pokemon_id in self.stat_stages:
                old_stage = self.stat_stages[pokemon_id].get_stage(modifier.stat_type)
                self.stat_stages[pokemon_id].modify(modifier.stat_type, -modifier.stages)
                new_stage = self.stat_stages[pokemon_id].get_stage(modifier.stat_type)

                # Se o estágio voltou a 0, remove o StatStage se não tiver outros modificadores
                if new_stage == 0 and not any(s != 0 for s in self.stat_stages[pokemon_id].stages.values()):
                    del self.stat_stages[pokemon_id]

        # Atualiza velocidade
        self._update_speed_for_pokemon_ids(pokemon_to_update)

        # ===== ATUALIZA STATUS EFFECTS =====
        status_to_remove = []

        for pokemon_id, status in self.status_effects.items():
            if pokemon_id in self._pokemon_refs:
                pokemon = self._pokemon_refs[pokemon_id]

                # Para congelamento, o update retorna False se descongelou
                if status.type == StatusType.FREEZE:
                    is_still_frozen = status.update_freeze(dt)
                    if not is_still_frozen:
                        status_to_remove.append(pokemon_id)
                    continue

                # update retorna False se o status acabou
                if not status.update(pokemon, self, dt):
                    status_to_remove.append(pokemon_id)

        # Remove status que acabaram
        for pokemon_id in status_to_remove:
            if pokemon_id in self._pokemon_refs:
                pokemon = self._pokemon_refs[pokemon_id]
                self.remove_status(pokemon)

        # Limpa textos temporários
        novos_textos = []
        for pokemon_id, text, duration in self.status_texts:
            nova_duracao = duration - dt
            if nova_duracao > 0:
                novos_textos.append((pokemon_id, text, nova_duracao))

        self.status_texts = novos_textos

    def _update_speed_for_pokemon_ids(self, pokemon_ids: set):
        """Força atualização da velocidade para Pokémon com IDs específicos"""
        for pokemon_id in pokemon_ids:
            if pokemon_id in self._pokemon_refs:
                pokemon = self._pokemon_refs[pokemon_id]
                if hasattr(pokemon, 'update_move_speed_from_effects'):
                    old_speed = pokemon.move_speed
                    pokemon.update_move_speed_from_effects()
                    if old_speed != pokemon.move_speed:
                        print(
                            f"[SPEED] {pokemon.name} velocidade: {old_speed:.2f} -> {pokemon.move_speed:.2f} (após expiração de modificador)")

    def add_status_text(self, pokemon, text: str, duration: float = 1.5):
        """Adiciona um texto de feedback visual acima do Pokémon (APENAS para temporários)"""
        pokemon_id = id(pokemon)
        self.status_texts.append((pokemon_id, text, duration))

    def get_status_texts(self, pokemon) -> List[Tuple[str, float]]:
        """Retorna os textos ativos para um Pokémon"""
        pokemon_id = id(pokemon)
        return [(text, duration) for pid, text, duration in self.status_texts if pid == pokemon_id]

    def render_status_texts(self, screen, pokemon, sprite_rect, zoom_scale, font_cache):
        """Renderiza os textos de status temporários (MISS, Drenou, etc)"""
        texts = self.get_status_texts(pokemon)

        if not texts:
            return

        font_size = max(12, int(16 * zoom_scale))

        if font_size not in font_cache:
            try:
                font_cache[font_size] = pygame.font.Font(None, font_size)
            except:
                font_cache[font_size] = pygame.font.SysFont('Arial', font_size)

        font = font_cache[font_size]

        y_offset = sprite_rect.top - 25

        for i, (text, duration) in enumerate(texts):
            # Cor baseada no tipo de mensagem
            if "Drenou" in text or "cura" in text:
                color = (100, 255, 100)
            elif "MISS" in text:
                color = (255, 100, 100)
            else:
                color = (255, 255, 255)

            text_surf = font.render(text, True, color)
            text_rect = text_surf.get_rect()
            text_rect.centerx = sprite_rect.centerx
            text_rect.y = y_offset - (i * (font_size + 2))

            screen.blit(text_surf, text_rect)

    def render_stat_modifiers(self, screen, pokemon, sprite_rect, zoom_scale, font_cache):
        """
        Renderiza os modificadores de stat (como Atk -3, Spd -2) acima do nome do Pokémon.
        Posicionamento relativo ao tamanho do sprite.
        """
        pokemon_id = id(pokemon)

        # Obtém modificadores ativos do StatStage
        if pokemon_id not in self.stat_stages:
            return

        # Obtém lista ordenada de modificadores
        ordered_modifiers = self.stat_stages[pokemon_id].get_ordered_modifiers()

        if not ordered_modifiers:
            return

        # ===== ESCALA DA FONTE =====
        base_font_size = 12

        if hasattr(pokemon, 'screen_manager') and hasattr(pokemon, 'camera'):
            render_scale = pokemon.screen_manager.render_scale
            camera_zoom = pokemon.camera.zoom if pokemon.camera else 1.0
            total_scale = render_scale * camera_zoom
            font_size = max(10, int(base_font_size * total_scale))
        else:
            font_size = max(10, int(base_font_size * zoom_scale))

        # Usar cache de fontes
        if font_size not in font_cache:
            try:
                font_cache[font_size] = pygame.font.Font(None, font_size)
            except:
                font_cache[font_size] = pygame.font.SysFont('Arial', font_size)

        font = font_cache[font_size]

        # Cria as strings dos modificadores
        modifier_parts = []
        has_debuff = False
        has_buff = False

        for stat_name, stage in ordered_modifiers:
            if stage > 0:
                modifier_parts.append(f"{stat_name} +{stage}")
                has_buff = True
            elif stage < 0:
                modifier_parts.append(f"{stat_name} {stage}")
                has_debuff = True

        if not modifier_parts:
            return

        combined_text = " | ".join(modifier_parts)

        # Define a cor
        if has_debuff and has_buff:
            color = (255, 255, 150)
        elif has_debuff:
            color = (255, 150, 150)
        elif has_buff:
            color = (150, 255, 150)
        else:
            color = (200, 200, 200)

        # Renderiza o texto
        text_surf = font.render(combined_text, True, color)
        text_rect = text_surf.get_rect()

        # ===== POSICIONAMENTO RELATIVO AO TAMANHO DO SPRITE =====
        sprite_height = sprite_rect.height

        # A barra está em -15% do topo
        # O nome está em -30% do topo
        # Modificadores ficam em -45% do topo (acima do nome)
        relative_offset = -sprite_height * 0.95  # 80% da altura do sprite acima

        # Calcula a posição base
        base_y = sprite_rect.top + relative_offset

        # Ajusta para que o texto fique completamente acima
        text_rect.y = int(base_y - text_rect.height)
        text_rect.centerx = sprite_rect.centerx

        # Garante que não fique muito acima (limite de 80% da altura do sprite)
        min_y = sprite_rect.top - sprite_height * 0.8
        if text_rect.y < min_y:
            text_rect.y = min_y

        # Fundo semi-transparente
        bg_width = text_rect.width + 8
        bg_height = text_rect.height + 4
        bg_surf = pygame.Surface((bg_width, bg_height))
        bg_surf.set_alpha(180)
        bg_surf.fill((0, 0, 0))
        screen.blit(bg_surf, (text_rect.x - 4, text_rect.y - 2))

        screen.blit(text_surf, text_rect)

    def render_status_indicators(self, screen, pokemon, sprite_rect, zoom_scale, font_cache):
        """
        Renderiza indicadores de status permanentes (PAR, BRN, PSN, SLP, etc) acima dos modificadores
        """
        status = self.get_status(pokemon)
        if not status or status.type == StatusType.NONE:
            return

        # Fonte para o indicador de status
        base_font_size = 12
        if hasattr(pokemon, 'screen_manager') and hasattr(pokemon, 'camera'):
            render_scale = pokemon.screen_manager.render_scale
            camera_zoom = pokemon.camera.zoom if pokemon.camera else 1.0
            total_scale = render_scale * camera_zoom
            font_size = max(10, int(base_font_size * total_scale))
        else:
            font_size = max(10, int(base_font_size * zoom_scale))

        if font_size not in font_cache:
            try:
                font_cache[font_size] = pygame.font.Font(None, font_size)
            except:
                font_cache[font_size] = pygame.font.SysFont('Arial', font_size)

        font = font_cache[font_size]

        # Texto do status (ex: "PAR", "BRN", "PSN", "SLP")
        status_text = status.display_name
        color = status.color

        text_surf = font.render(status_text, True, color)
        text_rect = text_surf.get_rect()

        # Posicionamento relativo ao tamanho do sprite
        sprite_height = sprite_rect.height

        # Modificadores estão em -45% do topo
        # Status fica em -55% do topo (acima)
        relative_offset = -sprite_height * 0.55

        text_rect.y = int(sprite_rect.top + relative_offset - text_rect.height)
        text_rect.centerx = sprite_rect.centerx

        # Fundo semi-transparente
        bg_width = text_rect.width + 8
        bg_height = text_rect.height + 4
        bg_surf = pygame.Surface((bg_width, bg_height))
        bg_surf.set_alpha(180)
        bg_surf.fill((0, 0, 0))
        screen.blit(bg_surf, (text_rect.x - 4, text_rect.y - 2))

        screen.blit(text_surf, text_rect)

        # Ícone de sono adicional se estiver dormindo
        if status.type == StatusType.SLEEP and status.is_asleep():
            self._render_sleep_icon(screen, pokemon, sprite_rect, zoom_scale, font_cache, status)

        # Ícone de stun para paralisia
        if status.type == StatusType.PARALYSIS and status.is_stunned():
            self._render_stun_icon(screen, pokemon, sprite_rect, zoom_scale, font_cache, status)

        if status.type == StatusType.FREEZE:
            self._render_freeze_icon(screen, pokemon, sprite_rect, zoom_scale, font_cache, status)

    def _render_stun_icon(self, screen, pokemon, sprite_rect, zoom_scale, font_cache, status):
        """Renderiza ícone de stun quando o Pokémon está paralisado"""
        base_font_size = 14
        if hasattr(pokemon, 'screen_manager') and hasattr(pokemon, 'camera'):
            render_scale = pokemon.screen_manager.render_scale
            camera_zoom = pokemon.camera.zoom if pokemon.camera else 1.0
            total_scale = render_scale * camera_zoom
            font_size = max(12, int(base_font_size * total_scale))
        else:
            font_size = max(12, int(base_font_size * zoom_scale))

        if font_size not in font_cache:
            try:
                font_cache[font_size] = pygame.font.Font(None, font_size)
            except:
                font_cache[font_size] = pygame.font.SysFont('Arial', font_size)

        font = font_cache[font_size]

        # Ícone de stun (relâmpago com círculo)
        stun_text = "⚡ !"
        text_surf = font.render(stun_text, True, (255, 255, 100))
        text_rect = text_surf.get_rect()

        # Posiciona à direita do indicador de status
        text_rect.left = sprite_rect.centerx + 15
        text_rect.centery = sprite_rect.top - int(sprite_rect.height * 0.55)

        screen.blit(text_surf, text_rect)

    def _render_sleep_icon(self, screen, pokemon, sprite_rect, zoom_scale, font_cache, status):
        """Renderiza ícone de sono quando o Pokémon está dormindo"""
        base_font_size = 14
        if hasattr(pokemon, 'screen_manager') and hasattr(pokemon, 'camera'):
            render_scale = pokemon.screen_manager.render_scale
            camera_zoom = pokemon.camera.zoom if pokemon.camera else 1.0
            total_scale = render_scale * camera_zoom
            font_size = max(12, int(base_font_size * total_scale))
        else:
            font_size = max(12, int(base_font_size * zoom_scale))

        if font_size not in font_cache:
            try:
                font_cache[font_size] = pygame.font.Font(None, font_size)
            except:
                font_cache[font_size] = pygame.font.SysFont('Arial', font_size)

        font = font_cache[font_size]

        # Ícone de sono (ZzZ)
        sleep_text = "💤"
        text_surf = font.render(sleep_text, True, (200, 200, 255))
        text_rect = text_surf.get_rect()

        # Posiciona à direita do indicador de status
        text_rect.left = sprite_rect.centerx + 15
        text_rect.centery = sprite_rect.top - int(sprite_rect.height * 0.55)

        screen.blit(text_surf, text_rect)

        # Mostra timer de sono (opcional, para debug)
        if hasattr(self, 'show_debug') and self.show_debug:
            remaining = status.get_sleep_remaining()
            if remaining > 0:
                timer_text = font.render(f"{remaining:.1f}s", True, (200, 200, 200))
                timer_rect = timer_text.get_rect()
                timer_rect.left = text_rect.right + 5
                timer_rect.centery = text_rect.centery
                screen.blit(timer_text, timer_rect)

    def _render_freeze_icon(self, screen, pokemon, sprite_rect, zoom_scale, font_cache, status):
        """Renderiza ícone de congelamento quando o Pokémon está congelado"""
        base_font_size = 14
        if hasattr(pokemon, 'screen_manager') and hasattr(pokemon, 'camera'):
            render_scale = pokemon.screen_manager.render_scale
            camera_zoom = pokemon.camera.zoom if pokemon.camera else 1.0
            total_scale = render_scale * camera_zoom
            font_size = max(12, int(base_font_size * total_scale))
        else:
            font_size = max(12, int(base_font_size * zoom_scale))

        if font_size not in font_cache:
            try:
                font_cache[font_size] = pygame.font.Font(None, font_size)
            except:
                font_cache[font_size] = pygame.font.SysFont('Arial', font_size)

        font = font_cache[font_size]

        # Ícone de congelamento (cristal de gelo)
        freeze_text = "❄️"
        text_surf = font.render(freeze_text, True, (152, 216, 216))
        text_rect = text_surf.get_rect()

        # Posiciona à direita do indicador de status
        text_rect.left = sprite_rect.centerx + 15
        text_rect.centery = sprite_rect.top - int(sprite_rect.height * 0.55)

        screen.blit(text_surf, text_rect)

    def clear_all(self):
        """Limpa todos os efeitos"""
        self.status_effects.clear()
        self.stat_modifiers.clear()
        self.stat_stages.clear()
        self.status_texts.clear()