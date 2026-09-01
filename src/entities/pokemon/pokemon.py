# src/entities/pokemon/pokemon.py
import pygame
import uuid
import random
from typing import List, Dict, Optional

from src.battle.attack_strategy import AttackPriority
from src.battle.attack_pattern import AttackPattern, AttackPatternManager, AttackTypeCategory
from src.entities.base import Entity
from src.data.pokedex import Pokedex
from src.data.move_data import MoveData
from src.entities.pokemon.animation import PokemonAnimation

from src.entities.pokemon.stats import PokemonStats
from src.entities.pokemon.movement import PokemonMovement
from src.entities.pokemon.combat import PokemonCombat
from src.entities.pokemon.moves import PokemonMoves
from src.entities.pokemon.evolution import PokemonEvolution
from src.entities.pokemon.rendering import PokemonRendering
from src.managers.notification_manager import notification_manager
from src.ui.toast_renderer import toast_battle

# Cache global de sprites e fontes para reduzir recriação
_SPRITE_CACHE = {}
_FONT_CACHE = {}


class Pokemon(Entity):
    # Constantes de classe
    _MIN_MOVE_SPEED = 0.5
    _MAX_MOVE_SPEED = 4.0
    _speed_cache = {}

    def __init__(self, x, y, pokemon_id, level=5, is_wild=False, shiny=False, is_boss=False):
        # ===== 1. DADOS BÁSICOS =====
        self.game_scene = None
        self.battle_system = None
        self.pokedex = Pokedex()
        self.unique_id = str(uuid.uuid4())
        self.pokemon_data = self.pokedex.get_pokemon(pokemon_id)
        if not self.pokemon_data:
            raise ValueError(f"Pokémon ID {pokemon_id} não encontrado")

        self.id = pokemon_id
        self.name = self.pokemon_data["name"].capitalize()
        self.base_level = level
        self.level = level
        self.is_shiny = shiny
        self.is_boss = is_boss

        # ===== 2. STATUS E ATRIBUTOS BASE =====
        self.custom_name = None
        self.is_placed = False
        self.spot_id = None
        self.types = self.pokemon_data["types"]
        self.base_stats = self.pokemon_data["base_stats"]

        # Felicidade: 0-100
        self.happiness = 0
        self._max_happiness = 255
        self._min_happiness = 0

        # Peso (kg) - com variação individual de ±10%
        base_weight = self.pokemon_data.get("weight_kg", 10.0)  # Fallback 10kg
        weight_variance = random.uniform(-0.10, 0.10)
        self.weight_kg = round(base_weight * (1 + weight_variance), 2)

        # Altura (m) - com variação individual de ±10%
        base_height = self.pokemon_data.get("height_m", 1.0)  # Fallback 1m
        height_variance = random.uniform(-0.10, 0.10)
        self.height_m = round(base_height * (1 + height_variance), 2)

        # Sexo
        gender_ratio = self.pokemon_data.get("gender_ratio", 0.5)  # Fallback 50/50
        if gender_ratio is None or gender_ratio == -1:
            self.gender = None  # Sem gênero
        else:
            self.gender = "male" if random.random() < gender_ratio else "female"

        # ===== 3. IVs E EVs =====
        self.ivs = {
            "hp": random.randint(0, 31),
            "attack": random.randint(0, 31),
            "defense": random.randint(0, 31),
            "special_attack": random.randint(0, 31),
            "special_defense": random.randint(0, 31),
            "speed": random.randint(0, 31)
        }

        self.evs = {
            "hp": 0, "attack": 0, "defense": 0,
            "special_attack": 0, "special_defense": 0, "speed": 0
        }

        # ===== 4. ATRIBUTOS DE STATS (serão preenchidos pelo stats manager) =====
        self.max_hp = 0
        self.attack = 0
        self.defense = 0
        self.sp_attack = 0
        self.sp_defense = 0
        self.speed_stat = 0

        # ===== 5. CRIAR GERENCIADORES (ANTES DE USAR) =====
        self.stats = PokemonStats(self)
        self.movement = PokemonMovement(self)
        self.combat = PokemonCombat(self)
        self.animation = PokemonAnimation(self)
        self.moves_manager = PokemonMoves(self)
        self.evolution = PokemonEvolution(self)
        self.rendering = PokemonRendering(self)
        self.camera = None
        self.notification_manager = notification_manager

        # ===== 6. NATUREZA (AGORA COM STATS JÁ CRIADO) =====
        self.nature_multipliers = self.stats.generate_nature()
        self.nature = self.nature_multipliers["name"]

        # ===== 7. CALCULAR STATS =====
        self.stats.calculate_stats()

        # ===== 8. BOSS: AUMENTA LEVEL E RECALCULA =====
        if is_boss:
            self.level = self.base_level + 3
            self.stats.calculate_stats()
            self.max_hp = int(self.max_hp * 2)
            self.current_hp = self.max_hp
            self.defense = int(self.defense * 2)
            self.sp_defense = int(self.sp_defense * 2)
            self.defense_value = self._calculate_defense()
            toast_battle(f"Um grande {self.name} chefe apareceu...", duration=4.0, pokemon=self, portrait="angry")

        # ===== 9. ESTADO ATUAL =====
        self.current_hp = self.max_hp
        self.xp = 0
        self.xp_to_next = self.stats.calculate_xp_needed()

        # ===== 10. TAMANHO DO SPRITE =====
        self.map_sprite_size = self.pokedex.get_map_sprite_size(pokemon_id, shiny)
        width = self.map_sprite_size
        height = self.map_sprite_size

        # ===== 11. ATRIBUTOS DE ANIMAÇÃO =====
        self.raw_animations = None
        self.inmap_animations = {}
        self.current_animation = "idle"
        self.is_moving = False
        self.walk_frame_durations = []
        self.idle_frame_durations = []
        self.frame_durations = []

        # ===== 12. CARREGAR SPRITES =====
        self.animation.load_sprites(pokemon_id, shiny)

        # Pega o primeiro sprite da animação idle como inicial
        sprite = None
        if self.inmap_frames and "down" in self.inmap_frames and self.inmap_frames["down"]:
            sprite = self.inmap_frames["down"][0]

        super().__init__(x, y, width, height, sprite)

        self._print_available_animations()
        # ===== 13. ATRIBUTOS DE JOGO =====
        self.is_wild = is_wild
        self.is_in_team = False
        self.is_selected = False

        # ===== 14. MOVIMENTO =====
        self.path = []
        self.path_index = 0
        self.move_speed = 2.0
        self.original_path = None
        self.path_index_origin = 0
        self.is_returning_with_item = False
        self.speed_bonus_not_wild = 0.5
        if is_wild:
            self.base_move_speed = self._get_cached_move_speed()
            self.move_speed = self.base_move_speed
        else:
            self.base_move_speed = self._get_cached_move_speed()
            self.move_speed = self.base_move_speed + self.speed_bonus_not_wild

        # ===== 15. COMBATE =====
        self.can_attack = True
        self.attack_cooldown = 0
        self.attack_cooldown_max = 1.2
        self.target = None
        self.has_no_pp = False
        self.attack_priority = AttackPriority(self)  # Só será usado para aliados

        # ===== SISTEMA DE CONTRIBUIÇÃO =====
        self.damage_contributions = {}  # id do atacante -> dano causado
        self.status_contributions = {}  # id do atacante -> status aplicados
        self.buff_contributions = {}  # id do atacante -> buffs aplicados em aliados
        self.last_attacker = None
        self._contribution_multiplier = 1.0  # Multiplicador para status/buffs

        # Atributos para efeitos
        self.effect_manager = None
        self.status_effect = None
        self.stat_stages = None

        self._original_sprite_scale = 1.0
        self._current_sprite_scale = 1.0
        self._minimize_active = False
        self._minimize_timer = 0.0

        # ===== 16. EFEITOS VISUAIS =====
        self.hp_bar_width = 48
        self.hp_bar_height = 5
        self.miss_timer = 0.0

        # ===== 17. POSIÇÃO E MOVIMENTAÇÃO =====
        self.last_x = x
        self.last_y = y

        # ===== 18. ITENS =====
        self.is_carrying = None
        self.capture_range = 20

        # ===== 19. ATRIBUTOS DE COMBATE =====
        self.attack_range = 90
        self.combat_state = "idle"
        self.original_spot_x = x
        self.original_spot_y = y

        # ===== 20. COOLDOWNS =====
        self.charge_cooldown = 0.0
        self.charge_cooldown_max = 0
        if is_wild:
            if is_boss :
                self.charge_cooldown_max = 1.2
            else:
                self.charge_cooldown_max = 3.0
        else:
            self.charge_cooldown_max = 1.2  # 1.2 segundos para aliados

        # ===== 21. STATS DE COMBATE =====
        self.attack_damage = self._calculate_attack_damage()
        self.defense_value = self._calculate_defense()

        # ===== 22. RASTREAMENTO DE DANO =====
        self.damage_contributions = {}
        self.last_attacker = None

        # ===== 23. SCREEN MANAGER =====
        self.screen_manager = None

        # ===== 24. DEBUG =====
        self.show_debug = False

        # ===== 25. MOVES =====
        self.move_data = MoveData()
        self.moves: List = []
        self.current_move_index = 0
        self.moves_manager.initialize_moves()

        # ===== 26. PADRÃO DE ATAQUE PARA INIMIGOS =====
        self.attack_pattern: Optional[AttackPattern] = None
        self.selected_category: Optional[AttackTypeCategory] = None  # Para VICIOUS_SELECTIVE
        self.vicious_move_name: Optional[str] = None  # Para VICIOUS
        self.is_defeated = False  # Estado de "derrotado"

        # Configura padrão de ataque se for wild
        if is_wild:
            self.attack_pattern = AttackPatternManager.get_pattern_for_enemy(is_boss, shiny)
            self._setup_attack_pattern()

    # ===== MÉTODOS DE DELEGAÇÃO (mantém compatibilidade) =====
    def get_portrait(self, expression: str = "normal", size: tuple = (48, 48)) -> Optional[pygame.Surface]:
        """
        Retorna o portrait do Pokémon com fallback automático.

        Args:
            expression: Expressão facial ("normal", "happy", "angry", "sad", "shocked")
            size: Tamanho desejado (largura, altura)

        Returns:
            Superfície do pygame com o portrait redimensionado
        """
        # Tenta carregar a expressão solicitada
        portrait = self.pokedex.get_portrait(self.id, expression, self.is_shiny)

        # Fallback: se não encontrou a expressão, tenta "normal"
        if portrait is None and expression != "normal":
            portrait = self.pokedex.get_portrait(self.id, "normal", self.is_shiny)
            if portrait:
                print(f"[PORTRAIT] Fallback: '{expression}' não encontrado para {self.name}, usando 'normal'")

        if portrait:
            # Redimensiona para o tamanho desejado
            if portrait.get_size() != size:
                portrait = pygame.transform.scale(portrait, size)

            # Se for shiny, adiciona efeito de brilho
            if self.is_shiny:
                overlay = pygame.Surface(size, pygame.SRCALPHA)
                overlay.fill((255, 215, 0, 60))
                portrait.blit(overlay, (0, 0))

            return portrait

        return None

    def _calculate_stats(self):
        self.stats.calculate_stats()

    def _calculate_xp_needed(self) -> int:
        return self.stats.calculate_xp_needed()

    def _generate_nature(self):
        return self.stats.generate_nature()

    def _calculate_attack_damage(self) -> float:
        return self.stats.calculate_attack_damage()

    def _calculate_defense(self) -> float:
        return self.stats.calculate_defense()

    def _calculate_wild_move_speed(self) -> float:
        return self.stats.calculate_wild_move_speed()

    def _get_cached_move_speed(self):
        return self.stats.get_cached_move_speed()

    def update_move_speed_from_effects(self):
        self.movement.update_move_speed_from_effects()

    def find_nearest_enemy(self, enemies):
        return self.combat.find_nearest_enemy(enemies)

    def _handle_returning_state(self, dt):
        self.combat.handle_returning_state(dt)

    def is_immune_to_status(self, status_type) -> bool:
        """Verifica se o Pokémon é imune a um tipo específico de status"""
        from src.battle.effects.status_effect import TypeImmunity
        return TypeImmunity.is_immune_to_status(self, status_type)

    def take_damage(self, damage, attacker=None):
        """Recebe dano e registra contribuição - delega para combat"""
        # Registra a contribuição ANTES de delegar
        if attacker and self.is_wild:
            self.register_damage(attacker, min(damage, self.current_hp))
            self.last_attacker = attacker

        # Delega o processamento do dano para o combat
        was_defeated = self.is_defeated
        result = self.combat.take_damage(damage, attacker)

        # FORÇA A VERIFICAÇÃO DE MORTE NO WAVE_MANAGER
        if not was_defeated and self.is_defeated:
            # Isso vai garantir que o wave_manager veja a morte no próximo update
            print(f"[BATTLE] {self.name} foi derrotado! (forçado)")

        return result

    def register_damage(self, attacker, damage):
        """Registra dano causado por um atacante"""
        attacker_id = id(attacker)
        self.damage_contributions[attacker_id] = self.damage_contributions.get(attacker_id, 0) + damage

    def register_status_application(self, attacker, status_name):
        """Registra aplicação de um status (veneno, queimadura, etc)"""
        attacker_id = id(attacker)
        self.status_contributions[attacker_id] = self.status_contributions.get(attacker_id, 0) + 1
        print(f"[XP] {attacker.name} aplicou {status_name} em {self.name}")

    def register_stat_modifier(self, attacker, stat_name, stages):
        """Registra aplicação de modificador de stat (buff/debuff)"""
        attacker_id = id(attacker)
        # Quanto maior o estágio, maior a contribuição
        contribution_value = abs(stages) * 0.5
        self.status_contributions[attacker_id] = self.status_contributions.get(attacker_id, 0) + contribution_value
        print(
            f"[XP] {attacker.name} aplicou {stat_name} {stages:+d} em {self.name} (contribuição: {contribution_value})")

    def register_buff_on_ally(self, attacker, ally, stat_name, stages):
        """Registra buff aplicado em aliado"""
        # Os buffs são registrados no alvo? Ou no atacante?
        # Vamos registrar no atacante para que ele ganhe XP por ajudar aliados
        attacker_id = id(attacker)
        contribution_value = abs(stages) * 0.3  # Buffs valem um pouco menos que debuffs
        self.buff_contributions[attacker_id] = self.buff_contributions.get(attacker_id, 0) + contribution_value
        print(
            f"[XP] {attacker.name} buffou {ally.name} com {stat_name} {stages:+d} (contribuição: {contribution_value})")

    def get_total_contribution(self) -> float:
        """Retorna o total de contribuição (dano + status + buffs)"""
        total_damage = sum(self.damage_contributions.values())
        total_status = sum(self.status_contributions.values())
        total_buffs = sum(self.buff_contributions.values())
        return total_damage + total_status + total_buffs

    def get_xp_contributors(self):
        """Retorna lista de contribuidores com pontuação combinada"""
        contributors = {}

        # Soma dano, status e buffs para cada atacante
        for attacker_id, damage in self.damage_contributions.items():
            contributors[attacker_id] = contributors.get(attacker_id, 0) + damage

        for attacker_id, status_value in self.status_contributions.items():
            # Status vale como se fosse dano (convertido)
            contributors[attacker_id] = contributors.get(attacker_id,
                                                         0) + status_value * 15  # Cada status vale ~15 de dano

        for attacker_id, buff_value in self.buff_contributions.items():
            # Buffs valem como se fosse dano
            contributors[attacker_id] = contributors.get(attacker_id, 0) + buff_value * 20  # Cada buff vale ~20 de dano

        # Se não houver contribuições, mas tem last_attacker, dá crédito mínimo
        if not contributors and self.last_attacker:
            return [(id(self.last_attacker), 1)]

        return [(attacker_id, contribution) for attacker_id, contribution in contributors.items()]

    def clear_damage_tracking(self):
        """Limpa todo o rastreamento de contribuições"""
        self.damage_contributions.clear()
        self.status_contributions.clear()
        self.buff_contributions.clear()
        self.last_attacker = None

    def _load_sprites(self, pokemon_id, shiny):
        self.animation.load_sprites(pokemon_id, shiny)

    def _load_animation_timings(self):
        self.animation._load_animation_timings()

    def _update_current_durations(self):
        self.animation._update_current_durations()

    def set_animation(self, animation_name: str):
        self.animation.set_animation(animation_name)

    def _update_sprite_from_current_animation(self):
        self.animation._update_sprite_from_current_animation()

    def _get_current_animation_frame_count(self) -> int:
        return self.animation._get_current_animation_frame_count()

    def _is_moving(self) -> bool:
        return self.animation._is_moving()

    def _update_animation(self, dt):
        self.animation.update(dt)

    def update_status_animation(self):
        """Atualiza a animação baseada no status atual"""
        if not hasattr(self, 'effect_manager') or not self.effect_manager:
            return

        status = self.effect_manager.get_status(self)

        if status and status.type.value != "none":
            status_name = status.type.value
            # Para paralisia, não troca animação aqui (será pelo stun)
            if status_name == "paralysis":
                return
            self.animation.set_status_animation(status_name)
        else:
            # Sem status, volta ao normal
            self.animation.set_status_animation(None)

    def get_current_move(self):
        return self.moves_manager.get_current_move()

    def _initialize_moves(self):
        self.moves_manager.initialize_moves()

    def learn_move(self, move_name: str) -> bool:
        return self.moves_manager.learn_move(move_name)

    def forget_move(self, index: int) -> bool:
        return self.moves_manager.forget_move(index)

    def replace_move(self, index: int, new_move_name: str) -> bool:
        return self.moves_manager.replace_move(index, new_move_name)

    def get_available_moves(self) -> List[str]:
        return self.moves_manager.get_available_moves()

    def get_new_moves_at_level(self, level: int) -> List[str]:
        return self.moves_manager.get_new_moves_at_level(level)

    def check_new_moves_on_level_up(self, old_level: int):
        return self.moves_manager.check_new_moves_on_level_up(old_level)

    def _learn_move_without_replacement(self, move_name: str) -> bool:
        return self.moves_manager._learn_move_without_replacement(move_name)

    def learn_move_with_selection(self, move_name: str, slot_index: int) -> bool:
        return self.moves_manager.learn_move_with_selection(move_name, slot_index)

    def check_and_evolve(self):
        return self.evolution.check_and_evolve()

    def _perform_evolution(self, new_id):
        self.evolution._perform_evolution(new_id)

    def gain_xp(self, amount):
        return self.evolution.gain_xp(amount)

    def level_up(self):
        return self.evolution.level_up()

    def _get_font(self, size):
        return self.rendering.get_font(size)

    def get_enemies_in_range(self, enemies: List) -> List['Pokemon']:
        """Retorna lista de inimigos dentro do range (delega para combat)"""
        return self.combat.get_enemies_in_range(enemies)

    def get_range_radius(self) -> float:
        """Retorna o raio atual do range de ataque"""
        return self.combat.get_range_radius()

    def _prepare_sprite(self, zoom_scale):
        return self.rendering.prepare_sprite(zoom_scale)

    def _render_sprite(self, screen, sprite, screen_x, screen_y, zoom_scale):
        return self.rendering.render_sprite(screen, sprite, screen_x, screen_y, zoom_scale)

    def _render_hp_bar(self, screen, sprite_rect, zoom_scale):
        """Renderiza barra de HP - offset relativo ao tamanho do sprite"""
        hp_percent = self.current_hp / self.max_hp

        # Tamanho da barra em pixels do mundo
        bar_width = self.hp_bar_width
        bar_height = self.hp_bar_height

        # ===== POSICIONAMENTO RELATIVO AO TAMANHO DO SPRITE =====
        # Calcula a altura do sprite na tela
        sprite_height = sprite_rect.height

        # Offset relativo: 10% da altura do sprite acima do topo
        # Isso mantém a proporção independente do zoom
        relative_offset = -sprite_height * 0.35  # 15% da altura do sprite acima

        # Escala para a tela
        if hasattr(self, 'screen_manager') and hasattr(self, 'camera'):
            render_scale = self.screen_manager.render_scale
            camera_zoom = self.camera.zoom if self.camera else 1.0
            total_scale = render_scale * camera_zoom

            # Tamanho da barra na tela
            screen_bar_width = int(bar_width * total_scale)
            screen_bar_height = max(3, int(bar_height * total_scale))

            # Posição da barra (centralizada horizontalmente, com offset relativo)
            bar_x = sprite_rect.centerx - screen_bar_width // 2
            bar_y = sprite_rect.top + relative_offset

        else:
            screen_bar_width = int(bar_width * zoom_scale)
            screen_bar_height = max(3, int(bar_height * zoom_scale))
            bar_x = sprite_rect.centerx - screen_bar_width // 2
            bar_y = sprite_rect.top + relative_offset

        # Fundo da barra
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, screen_bar_width, screen_bar_height))

        # Cor da barra
        if self.is_boss:
            color = (0, 0, 255)
        else:
            if not self.is_shiny:
                if hp_percent > 0.5:
                    color = (0, 200, 0)
                elif hp_percent > 0.25:
                    color = (255, 255, 0)
                else:
                    color = (255, 0, 0)
            else:
                color = (255, 0, 0)

        progress_width = int(screen_bar_width * hp_percent)
        if progress_width > 0:
            pygame.draw.rect(screen, color, (bar_x, bar_y, progress_width, screen_bar_height))

        # Borda da barra
        pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, screen_bar_width, screen_bar_height), 1)

    def _render_wild_text(self, screen, sprite_rect, zoom_scale):
        """
        Renderiza nome e nível do Pokémon selvagem.
        Offset relativo ao tamanho do sprite.
        """
        # ===== VERIFICAÇÃO DE SEGURANÇA =====
        has_screen_manager = hasattr(self, 'screen_manager') and self.screen_manager is not None
        has_camera = hasattr(self, 'camera') and self.camera is not None

        # ===== DADOS DO TEXTO =====
        name_text = f"{self.name} - "
        level_text = f"lv. {self.level:02d}"

        # ===== CORES =====
        text_color = (255, 255, 255)
        outline_color = (0, 0, 0)

        if self.is_shiny:
            level_color = (255, 215, 0)  # Dourado para shiny
        elif self.is_boss:
            level_color = (255, 100, 100)  # Vermelho claro para boss
            text_color = (255, 100, 100)
        else:
            level_color = (255, 255, 255)

        # ===== CALCULA ESCALA E TAMANHOS DE FONTE =====
        if has_screen_manager and has_camera:
            # Usa screen_manager e camera para escala precisa
            render_scale = self.screen_manager.render_scale
            camera_zoom = self.camera.zoom
            total_scale = render_scale * camera_zoom

            base_name_font_size = 12
            base_level_font_size = 11

            name_font_size = max(10, int(base_name_font_size * total_scale))
            level_font_size = max(9, int(base_level_font_size * total_scale))
        else:
            # Fallback: usa zoom_scale passado como parâmetro
            total_scale = zoom_scale
            name_font_size = max(10, int(12 * zoom_scale))
            level_font_size = max(9, int(11 * zoom_scale))

        # ===== CRIA FONTES =====
        name_font = self._get_font(name_font_size)
        level_font = self._get_font(level_font_size)

        # ===== RENDERIZA TEXTOS COM CONTORNO =====
        name_surface = name_font.render(name_text, True, text_color)
        level_surface = level_font.render(level_text, True, level_color)
        name_outline = name_font.render(name_text, True, outline_color)
        level_outline = level_font.render(level_text, True, outline_color)

        # ===== DIMENSÕES DOS TEXTOS =====
        name_width = name_surface.get_width()
        level_width = level_surface.get_width()
        total_width = name_width + 2 + level_width

        # ===== POSICIONAMENTO RELATIVO AO SPRITE =====
        sprite_height = sprite_rect.height

        # Offset relativo: 65% da altura do sprite acima do topo
        # Ajustado para ficar acima da barra de HP (que está em -35%)
        relative_offset = -sprite_height * 0.65

        # Posição na tela
        screen_x = sprite_rect.centerx
        screen_y = sprite_rect.top + relative_offset

        start_x = int(screen_x - total_width // 2)
        text_y = int(screen_y)

        name_x, name_y = start_x, text_y
        level_x = start_x + name_width + 2
        level_y = text_y + (name_font_size - level_font_size)

        # ===== DESENHA CONTORNO (4 direções) =====
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            screen.blit(name_outline, (name_x + dx, name_y + dy))
            screen.blit(level_outline, (level_x + dx, level_y + dy))

        # ===== DESENHA TEXTO PRINCIPAL =====
        screen.blit(name_surface, (name_x, name_y))
        screen.blit(level_surface, (level_x, level_y))

        # ===== DEBUG: Mostra offset e escala se necessário =====
        if hasattr(self, 'show_debug') and self.show_debug:
            debug_font = self._get_font(10)
            offset_info = debug_font.render(f"offset:{relative_offset:.0f}", True, (255, 255, 0))
            screen.blit(offset_info, (screen_x - 40, sprite_rect.top - 50))

            scale_info = debug_font.render(f"scale:{total_scale:.2f}", True, (255, 255, 0))
            screen.blit(scale_info, (screen_x - 40, sprite_rect.top - 65))

    def _render_miss_text(self, screen, sprite_rect, zoom_scale):
        self.rendering.render_miss_text(screen, sprite_rect, zoom_scale)

    def _render_placeholder(self, screen, screen_x, screen_y, zoom_scale):
        return self.rendering.render_placeholder(screen, screen_x, screen_y, zoom_scale)

    # ===== MÉTODOS QUE PERMANECEM NA CLASSE PRINCIPAL =====

    def get_available_animations(self) -> List[str]:
        """Retorna lista de todas as animações disponíveis para este Pokémon"""
        return self.animation.get_available_animations()

    def on_stun_state_changed(self, is_stunned: bool):
        """Chamado quando o estado de stun da paralisia muda"""
        if hasattr(self, 'animation'):
            self.animation.on_stun_state_changed(is_stunned)

    def has_animation(self, animation_name: str) -> bool:
        """Verifica se este Pokémon tem uma animação específica"""
        return self.animation.has_animation(animation_name)

    def set_animation_direct(self, animation_name: str):
        """Define a animação diretamente (ignora movimento)"""
        self.animation.set_animation(animation_name)

    def set_animation_by_status(self):
        """
        Define a animação baseada no status atual.
        Deve ser chamado quando o status muda.
        """
        if not hasattr(self, 'effect_manager') or not self.effect_manager:
            return

        status = self.effect_manager.get_status(self)

        if status and status.type.value != "none":
            status_name = status.type.value
            status_animation_map = {
                "sleep": "sleep",
                "paralysis": "charge",
                "freeze": "charge",
            }
            anim_name = status_animation_map.get(status_name)
            if anim_name and self.has_animation(anim_name):
                self.set_animation_direct(anim_name)
                return True
        return False

    def get_animation_info(self) -> Dict:
        """Retorna informações completas sobre as animações deste Pokémon"""
        return self.pokedex.get_pokemon_animations_info(self.id, self.is_shiny)

    def get_gender_symbol(self) -> str:
        """Retorna o símbolo do gênero"""
        if self.gender == "male":
            return "♂"
        elif self.gender == "female":
            return "♀"
        return ""

    def get_gender_color(self) -> tuple:
        """Retorna a cor do símbolo de gênero"""
        if self.gender == "male":
            return (70, 120, 200)  # Azul
        elif self.gender == "female":
            return (230, 80, 120)  # Rosa
        return (150, 150, 150)  # Cinza

    def get_gender_name(self) -> str:
        """Retorna nome do gênero em português"""
        if self.gender == "male":
            return "Macho"
        elif self.gender == "female":
            return "Fêmea"
        return "Sem gênero"

    def get_display_name(self) -> str:
        """Retorna o nome a ser exibido (personalizado ou padrão)"""
        if self.custom_name and len(self.custom_name.strip()) > 0:
            return self.custom_name.strip()
        return self.name

    def get_happiness(self) -> int:
        return self.happiness

    def get_happiness_percentage(self) -> float:
        return self.happiness / self._max_happiness

    def add_happiness(self, amount: int, source: str = "") -> int:
        """Adiciona ou remove felicidade do Pokémon."""
        old_happiness = self.happiness
        self.happiness = max(self._min_happiness, min(self._max_happiness, self.happiness + amount))
        gained = self.happiness - old_happiness

        if gained != 0:
            if hasattr(self, 'effect_manager') and self.effect_manager:
                if gained > 0:
                    self.effect_manager.add_status_text(self, f"Felicidade +{gained}!", duration=1.5,
                                                        color=(255, 100, 100))
                else:
                    self.effect_manager.add_status_text(self, f"Felicidade {gained}!", duration=1.5,
                                                        color=(100, 100, 255))

            # ===== VERIFICA EVOLUÇÃO POR FELICIDADE =====
            self._check_happiness_evolution()

            # Conquista: Felicidade Máxima
            if self.happiness >= 100 and old_happiness < 100:
                if hasattr(self, 'game_scene') and self.game_scene:
                    game_scene = self.game_scene
                    phase_id = f"{game_scene.chapter_id}-{game_scene.phase_number}"
                    if hasattr(game_scene, 'player') and hasattr(game_scene.player, 'achievement_manager'):
                        game_scene.player.achievement_manager.check_and_unlock("max_happiness", phase_id)

        return self.happiness

    def _check_happiness_evolution(self):
        """
        Verifica se o Pokémon pode evoluir por felicidade.
        Se puder, mostra o overlay de evolução.
        """
        from src.managers.evolution_manager import evolution_manager

        # Só verifica se tiver game_scene e não for selvagem
        if not hasattr(self, 'game_scene') or not self.game_scene:
            return

        if self.is_wild:
            return

        # Verifica evolução por felicidade
        evolution = evolution_manager.check_happiness_evolution(self)

        if evolution:
            print(f"[HAPPINESS_EVOLUTION] {self.name} pode evoluir por felicidade! "
                  f"Felicidade: {self.happiness}, Requerido: {evolution['requirement']}")

            # Abre o overlay de evolução
            self.game_scene.open_evolution_overlay(self, evolution)

    def set_happiness(self, value: int) -> int:
        """Define felicidade diretamente (0-100). Retorna o novo valor."""
        self.happiness = max(self._min_happiness, min(self._max_happiness, value))
        print(f"[HAPPINESS] {self.get_display_name()}: felicidade definida para {self.happiness}/100")
        return self.happiness

    def set_custom_name(self, new_name: str) -> bool:
        """
        Define um nome personalizado para o Pokémon.
        Retorna True se o nome foi alterado, False se inválido.
        """
        # Remove espaços extras
        new_name = new_name.strip()

        # Verifica limites
        if len(new_name) > 20:
            print(f"[NAME] Nome muito longo: {len(new_name)}/20 caracteres")
            return False

        if len(new_name) == 0:
            # Remove nome personalizado, volta ao padrão
            self.custom_name = None
            print(f"[NAME] {self.name}: nome personalizado removido")
            return True

        # Define novo nome personalizado
        old_custom = self.custom_name
        self.custom_name = new_name

        # Notifica effect_manager (se existir) para mostrar mensagem
        if hasattr(self, 'effect_manager') and self.effect_manager:
            self.effect_manager.add_status_text(self, f"Chamando {self.get_display_name()}!", duration=2.0)

        print(
            f"[NAME] {self.name} renomeado de '{old_custom}' para '{new_name}' (exibe como '{self.get_display_name()}')")
        return True

    def get_info_with_gender_weight(self) -> str:
        """Retorna string com informações incluindo peso, altura e sexo"""
        gender_text = self.get_gender_name()
        return (f"{self.name} Lv.{self.level} ({gender_text})\n"
                f"Peso: {self.weight_kg}kg | Altura: {self.height_m}m\n"
                f"HP: {self.current_hp}/{self.max_hp}\n"
                f"Tipos: {'/'.join(self.types)}\n"
                f"Natureza: {self.nature}")

    def play_hurt_animation(self):
        """Toca a animação de dano (hurt)"""
        if hasattr(self, 'animation') and self.animation:
            return self.animation.play_hurt_animation()
        return False

    def set_battle_system(self, battle_system):
        """Define o sistema de combate para este Pokémon"""
        self.battle_system = battle_system
        if battle_system and battle_system.effect_manager:
            battle_system.effect_manager.register_pokemon(self)

    def heal(self, amount=None):
        if amount is None:
            self.current_hp = self.max_hp
        else:
            self.current_hp = min(self.max_hp, self.current_hp + amount)

    def is_boss_type(self):
        return hasattr(self, 'is_boss') and self.is_boss

    def is_alive(self):
        """Verifica se o Pokémon está vivo (não derrotado e com HP > 0)"""
        return not self.is_defeated and self.current_hp > 0

    def get_hp_percentage(self):
        return self.current_hp / self.max_hp

    def drop_item(self):
        if self.is_carrying:
            self.is_carrying.reset_capture()
            self.is_carrying = None

    def calculate_damage(self, target):
        damage = max(1, int((self.attack * self.level) / (target.defense * 2) + 2))
        return int(damage * random.uniform(0.85, 1.0))

    def clear_carrying(self):
        if self.is_carrying:
            self.is_carrying = None

    def get_info_string(self):
        return (f"{self.name} Lv.{self.level}\n"
                f"HP: {self.current_hp}/{self.max_hp}\n"
                f"Tipos: {'/'.join(self.types)}\n"
                f"Natureza: {self.nature}")

    def restore_pp(self, percentage: float = 1.0) -> int:
        """Restaura PP de TODOS os moves do Pokémon."""
        restored_count = 0
        for move in self.moves:
            pp_to_restore = int(move.max_pp * percentage)
            old_pp = move.current_pp
            move.current_pp = min(move.max_pp, move.current_pp + pp_to_restore)
            restored_count += move.current_pp - old_pp

        if restored_count > 0:
            print(f"[PP_RESTORE] {self.name}: {restored_count} PP restaurados "
                  f"({int(percentage * 100)}% de cada move)")

        return restored_count

    def reset_pp(self) -> int:
        """Reseta os PP de todos os moves para o máximo (100%)"""
        return self.restore_pp(percentage=1.0)

    def restore_moves(self, moves_data: list):
        """Restaura moves a partir de dados serializados"""
        from src.data.move_data import MoveData
        from src.entities.move import Move

        move_data = MoveData()
        self.moves = []

        for move_dict in moves_data:
            move_info = move_data.get_move_info(move_dict["name"])
            if move_info is None:
                move_info = {
                    "type": "normal",
                    "power": 40,
                    "accuracy": 100,
                    "pp": move_dict.get("max_pp", 35),
                    "category": "physical",
                    "description": f"Usa {move_dict['name']}."
                }

            move = Move(move_dict["name"], move_info)
            move.current_pp = move_dict.get("current_pp", move.max_pp)
            move.max_pp = move_dict.get("max_pp", move.max_pp)
            self.moves.append(move)

        # ===== GARANTE QUE TRANSFORM NÃO SEJA PERDIDO =====
        # Se o Pokémon é Ditto (ID 132) e não tem Transform, adiciona
        if self.id == 132:  # ID do Ditto
            has_transform = any(m.name.lower() == "transform" for m in self.moves)
            if not has_transform:
                transform_info = move_data.get_move_info("transform")
                if transform_info:
                    transform_move = Move("transform", transform_info)
                    transform_move.current_pp = transform_move.max_pp
                    self.moves.insert(0, transform_move)
                    print(f"[TRANSFORM] Transform adicionado a {self.name} durante restore!")

        print(f"[LOAD] {self.name} restaurado com {len(self.moves)} moves")

    def update(self, dt, player=None, enemies=None, items=None):
        """Update do Pokémon - DELEGA ANIMAÇÃO PARA animation.py"""

        # ===== 1. SEMPRE ATUALIZA ANIMAÇÃO (centralizado em animation.py) =====
        self.last_x = self.x
        self.last_y = self.y

        # ===== ATUALIZA TIMER DO MINIMIZE =====
        if hasattr(self, '_minimize_active') and self._minimize_active:
            self._minimize_timer -= dt
            if self._minimize_timer <= 0:
                # Remove o efeito minimize
                self._minimize_active = False
                self._current_sprite_scale = self._original_sprite_scale
                self._sprite_scaled = None
                print(f"[MINIMIZE] {self.name} voltou ao tamanho normal!")

                # Mostra mensagem
                if hasattr(self, 'effect_manager') and self.effect_manager:
                    self.effect_manager.add_status_text(self, f"{self.name} voltou ao normal!", duration=1.0)

        # ===== ATUALIZA DESTINY BOND =====
        if hasattr(self, '_destiny_bond_active') and self._destiny_bond_active:
            if hasattr(self, '_destiny_bond_turns_left'):
                # A cada ~2 segundos (um turno), decrementa
                if not hasattr(self, '_destiny_bond_timer'):
                    self._destiny_bond_timer = 0.0

                self._destiny_bond_timer += dt
                if self._destiny_bond_timer >= 2.0:  # 2 segundos = 1 turno
                    self._destiny_bond_timer = 0
                    self._destiny_bond_turns_left -= 1

                    if self._destiny_bond_turns_left <= 0:
                        # Desativa Destiny Bond
                        self._destiny_bond_active = False
                        if hasattr(self, '_destiny_bond_turns_left'):
                            delattr(self, '_destiny_bond_turns_left')
                        if hasattr(self, '_destiny_bond_timer'):
                            delattr(self, '_destiny_bond_timer')

                        # Mostra mensagem (opcional)
                        if hasattr(self, 'effect_manager') and self.effect_manager:
                            self.effect_manager.add_status_text(
                                self,
                                f"O laço do destino de {self.name} se desfez!",
                                duration=1.0
                            )
                        print(f"[DESTINY_BOND] {self.name} - efeito expirou!")

        # Atualiza timer de MISS
        if hasattr(self, 'miss_timer') and self.miss_timer > 0:
            self.miss_timer -= dt
            if self.miss_timer < 0:
                self.miss_timer = 0

        # ===== 2. DELEGA TODA LÓGICA DE ANIMAÇÃO =====
        self.animation.update(dt)

        # ===== 3. SE ESTÁ DERROTADO, NÃO PROCESSA MAIS NADA =====
        if self.is_defeated:
            return

        # ===== 4. POKÉMON VIVO - ATUALIZA RESTO =====
        # Atualiza velocidade baseada nos efeitos
        if hasattr(self, 'effect_manager') and self.effect_manager and self.is_wild:
            self.update_move_speed_from_effects()

        # Atualiza item sendo carregado
        if self.is_carrying:
            self.is_carrying.update_capture(dt)

        # Atualiza cooldown de ataque
        if not self.can_attack:
            self.attack_cooldown -= 1
            if self.attack_cooldown <= 0:
                self.can_attack = True

    def update_combat(self, dt, enemies):
        """Atualiza lógica de combate - DELEGA para o sistema unificado"""
        # Se está derrotado, não combate
        if self.is_defeated:
            return

        # Se tem battle_system, usa ele
        if hasattr(self, 'battle_system') and self.battle_system:
            # Apenas garante que o effect_manager está configurado
            pass

        # Atualiza cooldown
        if self.charge_cooldown > 0:
            self.charge_cooldown -= dt

        # DELEGA para o sistema unificado de combate
        # Passa a lista de entidades (para wild: aliados; para not wild: inimigos)
        self.combat.update_combat(dt, enemies)

    def get_distance_to(self, entity):
        return self.movement.get_distance_to(entity)

    def _update_sprite_size(self):
        """Atualiza o tamanho do sprite baseado no efeito Minimize"""
        if hasattr(self, '_current_sprite_scale') and self._current_sprite_scale != 1.0:
            # Força recriação do sprite na próxima renderização
            self._sprite_scaled = None

    def render(self, screen, camera=None, show_hp=True):
        """Renderiza o Pokémon com todos os elementos visuais ajustados"""

        self.camera = camera

        if camera and hasattr(self, 'screen_manager') and self.screen_manager:
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)
            zoom_scale = camera.zoom * self.screen_manager.render_scale
        else:
            screen_x = self.x
            screen_y = self.y
            zoom_scale = 1.0

        sprite_to_render = self._prepare_sprite(zoom_scale)

        sprite_rect = None
        if sprite_to_render:
            sprite_rect = self._render_sprite(screen, sprite_to_render, screen_x, screen_y, zoom_scale)
        else:
            sprite_rect = self._render_placeholder(screen, screen_x, screen_y, zoom_scale)

        if hasattr(self, 'battle_system') and self.battle_system and self.battle_system.effect_manager:
            self.battle_system.effect_manager.render_status_texts(
                screen, self, sprite_rect, zoom_scale, _FONT_CACHE
            )
            self.battle_system.effect_manager.render_stat_modifiers(
                screen, self, sprite_rect, zoom_scale, _FONT_CACHE
            )

            self.battle_system.effect_manager.render_status_indicators(
                screen, self, sprite_rect, zoom_scale, _FONT_CACHE
            )

        if sprite_rect:
            if self.is_wild:
                self._render_wild_text(screen, sprite_rect, zoom_scale)
            if show_hp:
                self._render_hp_bar(screen, sprite_rect, zoom_scale)
            if hasattr(self, 'miss_timer') and self.miss_timer > 0:
                self._render_miss_text(screen, sprite_rect, zoom_scale)

        # ===== DEBUG DO RANGE - MOVIDO PARA DENTRO DA VERIFICAÇÃO show_debug =====
        if hasattr(self, 'show_debug') and self.show_debug:
            # Renderiza informações básicas de debug
            if sprite_rect:
                self._render_debug(screen, screen_x, screen_y, zoom_scale, sprite_rect)

            # Renderiza o range (sempre, mesmo sem sprite_rect)
            # Obtém inimigos no range
            enemies_in_range = []
            if hasattr(self, 'battle_system') and self.battle_system:
                if hasattr(self.battle_system, 'game_scene') and self.battle_system.game_scene:
                    if hasattr(self.battle_system.game_scene, 'wave_manager'):
                        enemies = self.battle_system.game_scene.wave_manager.active_enemies
                        enemies_in_range = self.get_enemies_in_range(enemies)

            # Renderiza o range usando o rendering manager
            self.rendering.render_debug_range(
                screen,
                screen_x,
                screen_y,
                zoom_scale,
                enemies_in_range
            )

    def render_hp_enemy(self, screen, camera=None):
        """Método de compatibilidade para chamar o _render_hp_bar"""
        if camera and hasattr(self, 'screen_manager') and self.screen_manager:
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)
            zoom_scale = camera.zoom * self.screen_manager.render_scale

            sprite_to_render = self._prepare_sprite(zoom_scale)
            if sprite_to_render:
                current_width, current_height = sprite_to_render.get_width(), sprite_to_render.get_height()
                final_width = max(1, int(current_width * zoom_scale))
                final_height = max(1, int(current_height * zoom_scale))

                if final_width != current_width or final_height != current_height:
                    scaled_sprite = pygame.transform.scale(sprite_to_render, (final_width, final_height))
                else:
                    scaled_sprite = sprite_to_render

                sprite_rect = scaled_sprite.get_rect()
                sprite_rect.center = (int(screen_x), int(screen_y))

                self._render_hp_bar(screen, sprite_rect, zoom_scale)
        else:
            temp_rect = pygame.Rect(0, 0, self.map_sprite_size, self.map_sprite_size)
            temp_rect.center = (int(self.x), int(self.y))
            self._render_hp_bar(screen, temp_rect, 1.0)

    def _render_debug(self, screen, screen_x, screen_y, zoom_scale, sprite_rect):
        """Renderiza informações de debug"""
        pygame.draw.circle(screen, (255, 0, 0), (sprite_rect.centerx, sprite_rect.centery), 6, 2)
        pygame.draw.rect(screen, (255, 0, 255), sprite_rect, 1)

        font = self._get_font(10)
        debug_text = f"{self.current_animation} f{self.current_frame} dir:{self.current_direction}"
        text_surf = font.render(debug_text, True, (255, 255, 255))
        screen.blit(text_surf, (sprite_rect.left, sprite_rect.top - 25))

        coord_text = f"({self.x:.0f}, {self.y:.0f})"
        coord_surf = font.render(coord_text, True, (200, 200, 200))
        screen.blit(coord_surf, (sprite_rect.left, sprite_rect.bottom + 5))

    def _print_available_animations(self):
        """Printa todas as animações disponíveis para este Pokémon"""
        if hasattr(self, 'animation') and self.animation:
            available = self.animation.get_available_animations()

            if available:
                print(f"\n{'=' * 50}")
                print(f"[ANIMAÇÕES] {self.name} (ID: {self.id}) - Shiny: {self.is_shiny}")
                print(f"{'=' * 50}")
                print(f"Total de animações disponíveis: {len(available)}")
                print(f"Animações: {', '.join(available)}")

                # Mostra detalhes de cada animação
                for anim_name in available:
                    try:
                        frames_info = self.pokedex.get_animation_frames(self.id, anim_name, "down", self.is_shiny)
                        durations = self.pokedex.get_animation_durations(self.id, anim_name, self.is_shiny)

                        # Tenta pegar metadados para saber se é direção única
                        raw_data = self.pokedex.get_raw_inmap_data(self.id, self.is_shiny)
                        animations = raw_data.get("animations", {})
                        anim_data = animations.get(anim_name.lower(), {})
                        metadata = anim_data.get('_metadata', {})

                        is_single = metadata.get('is_single_direction', False)
                        num_original_dirs = metadata.get('num_original_directions', 8)

                        if is_single:
                            dir_info = f" (originalmente 1 direção, replicado para 8)"
                        else:
                            dir_info = f" ({num_original_dirs} direções)"

                        if frames_info:
                            num_frames = len(frames_info)
                            if durations:
                                print(f"  └─ {anim_name}: {num_frames} frames, durações: {durations}{dir_info}")
                            else:
                                print(f"  └─ {anim_name}: {num_frames} frames{dir_info}")
                        else:
                            print(f"  └─ {anim_name}: [sem frames]{dir_info}")
                    except Exception as e:
                        print(f"  └─ {anim_name}: [erro - {e}]")

                print(f"{'=' * 50}\n")

    def _setup_attack_pattern(self):
        """Configura o padrão de ataque específico"""
        if self.attack_pattern == AttackPattern.VICIOUS:
            # Escolhe um golpe específico para usar até acabar PP
            if self.moves:
                self.vicious_move_name = random.choice(self.moves).name
                print(f"[ATTACK_PATTERN] {self.name} é VICIADO em {self.vicious_move_name}!")

        elif self.attack_pattern == AttackPattern.VICIOUS_SELECTIVE:
            # Escolhe uma categoria de ataque para usar
            self.selected_category = AttackPatternManager.get_attack_category_for_vicious_selective(self)
            print(f"[ATTACK_PATTERN] {self.name} é VICIADO_SELETIVO em {self.selected_category.value}!")

        elif self.attack_pattern == AttackPattern.AGGRESSIVE:
            print(f"[ATTACK_PATTERN] {self.name} é AGRESSIVO!")

        elif self.attack_pattern == AttackPattern.PASSIVE:
            print(f"[ATTACK_PATTERN] {self.name} é PASSIVO (não ataca)!")

    def get_current_move_for_pattern(self):
        """Retorna o move atual baseado no padrão de ataque"""
        if not self.moves:
            return None

        # Se está derrotado, não ataca
        if self.is_defeated:
            return None

        # Se tem padrão passivo, não ataca
        if self.attack_pattern == AttackPattern.PASSIVE:
            return None

        # Se tem um move específico para VICIOUS
        if self.attack_pattern == AttackPattern.VICIOUS and self.vicious_move_name:
            for move in self.moves:
                if move.name == self.vicious_move_name and move.current_pp > 0:
                    return move

            # Se acabou PP do golpe vicioso, tenta qualquer outro
            for move in self.moves:
                if move.current_pp > 0:
                    return move
            return None

        # Para VICIOUS_SELECTIVE
        if self.attack_pattern == AttackPattern.VICIOUS_SELECTIVE and self.selected_category:
            available_moves = [m for m in self.moves
                               if m.category == self.selected_category.value and m.current_pp > 0]
            if available_moves:
                return random.choice(available_moves)

            # Se não tem mais moves da categoria, tenta qualquer outro
            for move in self.moves:
                if move.current_pp > 0:
                    return move
            return None

        # Para RANDOM (padrão)
        if self.attack_pattern == AttackPattern.RANDOM:
            available_moves = [m for m in self.moves if m.current_pp > 0]
            if available_moves:
                return random.choice(available_moves)
            return None

        # Fallback: usa o sistema normal
        return self.get_current_move()

    def clear_all_status(self):
        """
        Remove todos os efeitos de status do Pokémon.
        Chamado quando o Pokémon é derrotado.
        """
        # ===== USA O EFFECT_MANAGER DO BATTLE_SYSTEM =====
        # O effect_manager pode estar no battle_system ou diretamente no pokemon
        effect_mgr = None

        # Tenta pegar do battle_system primeiro
        if hasattr(self, 'battle_system') and self.battle_system:
            effect_mgr = self.battle_system.effect_manager

        # Se não tem battle_system, tenta o effect_manager direto
        if not effect_mgr and hasattr(self, 'effect_manager') and self.effect_manager:
            effect_mgr = self.effect_manager

        if effect_mgr:
            # Usa o método do EffectManager para limpar tudo
            effect_mgr.clear_all_effects_for_pokemon(self)
            print(f"[STATUS_CLEAR] {self.name}: todos os efeitos limpos via EffectManager")
        else:
            print(f"[STATUS_CLEAR] {self.name}: effect_manager não disponível, pulando limpeza")

        # ===== LIMPA TIMERS E CONTADORES LOCAIS (sempre faz) =====
        if hasattr(self, '_stun_timer'):
            self._stun_timer = 0.0
        if hasattr(self, '_last_stun_check'):
            self._last_stun_check = 0.0
        if hasattr(self, '_sleep_timer'):
            self._sleep_timer = 0.0
        if hasattr(self, '_sleep_check_timer'):
            self._sleep_check_timer = 0.0
        if hasattr(self, '_freeze_timer'):
            self._freeze_timer = 0.0
        if hasattr(self, '_freeze_check_timer'):
            self._freeze_check_timer = 0.0
        if hasattr(self, '_damage_timer'):
            self._damage_timer = 0.0
        if hasattr(self, '_toxic_tick_count'):
            self._toxic_tick_count = 0

        self.clear_fury_cutter()
        self.clear_destiny_bond()
        self.clear_disable()
        self.clear_guaranteed_hit_effects()
        self.clear_rollout()
        self.clear_foresight()
        self.clear_perish_song()
        self.clear_protection_effects()

        # Remove referência local ao status_effect se existir
        if hasattr(self, 'status_effect'):
            self.status_effect = None

        # Força atualização da animação para estado normal
        if hasattr(self, 'update_status_animation'):
            self.update_status_animation()

        print(f"[STATUS_CLEAR] Todos os status de {self.name} foram removidos!")

    def clear_fury_cutter(self):
        """Reseta o contador do Fury Cutter"""
        if hasattr(self, '_fury_cutter_hits'):
            self._fury_cutter_hits = 0

    def clear_destiny_bond(self):
        """Remove Destiny Bond do Pokémon"""
        if hasattr(self, '_destiny_bond_active'):
            self._destiny_bond_active = False
        if hasattr(self, '_destiny_bond_turns_left'):
            delattr(self, '_destiny_bond_turns_left')
        if hasattr(self, '_destiny_bond_timer'):
            delattr(self, '_destiny_bond_timer')
        if hasattr(self, '_destiny_bond_source'):
            delattr(self, '_destiny_bond_source')

    def clear_disable(self):
        """Remove Destiny Bond do Pokémon"""
        # ===== LIMPA DISABLE =====
        if hasattr(self, '_disabled_move'):
            delattr(self, '_disabled_move')
        if hasattr(self, '_disabled_turns'):
            delattr(self, '_disabled_turns')
        if hasattr(self, '_disabled_original_pp'):
            delattr(self, '_disabled_original_pp')
        if hasattr(self, '_disable_timer'):
            delattr(self, '_disable_timer')

    def clear_guaranteed_hit_effects(self):
        """Remove todos os efeitos de acerto garantido (Lock-On, Mind Reader)"""
        effects = ["lock_on", "mind_reader"]

        for effect_key in effects:
            active_flag = f"_{effect_key}_active"
            target_flag = f"_{effect_key}_target"

            if hasattr(self, active_flag):
                setattr(self, active_flag, False)
            if hasattr(self, target_flag):
                setattr(self, target_flag, None)

    def clear_rollout(self):
        """Reseta o estado do Rollout"""
        if hasattr(self, '_rollout_active'):
            self._rollout_active = False
        if hasattr(self, '_rollout_turns_left'):
            self._rollout_turns_left = 0
        if hasattr(self, '_rollout_hit_count'):
            self._rollout_hit_count = 0
        if hasattr(self, '_rollout_current_power'):
            self._rollout_current_power = 0
        if hasattr(self, '_rollout_base_power'):
            self._rollout_base_power = 0
        if hasattr(self, '_defense_curl_used'):
            self._defense_curl_used = False

    def clear_foresight(self):
        """Remove o efeito Foresight do Pokémon"""
        if hasattr(self, '_foresight_active'):
            self._foresight_active = False
        if hasattr(self, '_foresight_source'):
            self._foresight_source = None

    def clear_perish_song(self):
        """Remove o efeito Perish Song do Pokémon"""
        if hasattr(self, '_perish_song_active'):
            self._perish_song_active = False
        if hasattr(self, '_perish_song_turns_left'):
            delattr(self, '_perish_song_turns_left')

    def clear_protection_effects(self):
        """Remove todos os efeitos de proteção (Protect, Detect, Safeguard)"""
        if hasattr(self, '_protected'):
            self._protected = False
        if hasattr(self, '_safeguard_active'):
            self._safeguard_active = False
        if hasattr(self, '_safeguard_turns_left'):
            delattr(self, '_safeguard_turns_left')
        if hasattr(self, '_safeguard_timer'):
            delattr(self, '_safeguard_timer')
        if hasattr(self, '_last_protect_used'):
            self._last_protect_used = False

    def set_defeated(self, defeated: bool):
        """Define se o Pokémon está derrotado"""
        self.is_defeated = defeated
        if defeated:


            # ===== LIMPA TODOS OS STATUS EFFECTS =====
            self.clear_all_status()

            self.add_happiness(-30, "Derrotado")

            # ===== CANCELA QUALQUER CARGA DE GOLPE =====
            if hasattr(self, 'battle_system') and self.battle_system:
                if (self.battle_system.active_charge_move and
                        self.battle_system.active_charge_move['attacker'] == self):
                    print(f"[TWO_TURN] Carga de {self.name} foi cancelada devido à derrota!")
                    self.battle_system.active_charge_move = None

            # ===== REMOVE EFEITOS RESIDUAIS DO BATTLE_SYSTEM (apenas se existir) =====
            if hasattr(self, 'battle_system') and self.battle_system:
                if hasattr(self.battle_system, 'residual_effects'):
                    self.battle_system.residual_effects.remove_effect_on_target(self)

            # Força animação de sono/derrota
            if hasattr(self, 'set_animation_direct'):
                self.set_animation_direct("sleep")

            # Reseta estado de combate
            self.combat_state = "idle"
            self.target = None
            self.charge_cooldown = 0

            if not self.is_wild:
                toast_battle(f"{self.name} foi derrotado!", duration=4.0, pokemon=self, portrait="dizzy")

        else:
            # Restaura animação normal
            self.update_status_animation()
            if self.current_animation == "sleep" and not self.is_defeated:
                self.set_animation_direct("idle")
            print(f"[DEFEATED] {self.name} foi revivido! Animação restaurada.")

    def revive(self, heal_percentage: float = 0.5):
        """
        Revive o Pokémon (usado por itens Revive)

        Args:
            heal_percentage: Percentual de HP para curar (0.5 = 50%)
        """
        if not self.is_defeated and self.current_hp > 0:
            print(f"[REVIVE] {self.name} já está vivo! Item não usado.")
            return False

        # Revive
        self.is_defeated = False

        # Cura HP
        heal_amount = int(self.max_hp * heal_percentage)
        self.current_hp = min(self.max_hp, heal_amount)
        if self.current_hp <= 0:
            self.current_hp = self.max_hp // 2  # Fallback: revive com 50%

        # Reseta PP de todos os moves
        self.reset_pp()

        # Remove efeitos de status
        if hasattr(self, 'effect_manager') and self.effect_manager:
            self.effect_manager.remove_status(self)

        # Reseta estado de combate
        self.combat_state = "idle"
        self.target = None
        self.charge_cooldown = 0

        # Restaura animação normal
        self.update_status_animation()
        if self.current_animation == "sleep":
            self.set_animation_direct("idle")

        print(f"[REVIVE] {self.name} revivido com {self.current_hp}/{self.max_hp} HP e PP restaurados!")
        return True

    def full_restore(self):
        """
        Restaura completamente o Pokémon (HP, PP, remove status, revive se derrotado)
        Usado no início de cada partida
        """
        # Revive se estiver derrotado
        if self.is_defeated:
            self.is_defeated = False

        # Cura HP completo
        self.current_hp = self.max_hp

        # Reseta PP de todos os moves
        self.reset_pp()

        # Remove efeitos de status
        if hasattr(self, 'effect_manager') and self.effect_manager:
            self.effect_manager.remove_status(self)

        # Reseta estágios de stat
        if hasattr(self, 'effect_manager') and self.effect_manager:
            pokemon_id = id(self)
            if pokemon_id in self.effect_manager.stat_stages:
                del self.effect_manager.stat_stages[pokemon_id]

        # Reseta estado de combate
        self.combat_state = "idle"
        self.target = None
        self.charge_cooldown = 0

        # Restaura animação normal
        self.update_status_animation()
        if self.current_animation == "sleep":
            self.set_animation_direct("idle")

        print(f"[FULL_RESTORE] {self.name} completamente restaurado! HP: {self.current_hp}/{self.max_hp}")
        return True

    def reset(self, game_scene):
        """
        Restaura completamente o Pokémon para seus stats base para começar a partida.
        """
        self.full_restore()

        self.target = None
        self.current_animation = "idle"
        self.combat_state = "idle"
        self.spot_id = None
        self.is_moving = False
        self.is_placed = False

        # ===== LIMPA FLAG DO STRUGGLE =====
        if hasattr(self, '_struggle_message_shown'):
            self._struggle_message_shown = False

        self.set_battle_system(game_scene.battle_system)
        self.screen_manager = game_scene.screen_manager
        self.camera = game_scene.camera

    def reset_transform(self):
        """
        Reseta o Ditto ao seu estado original.
        DEVE SER CHAMADO APENAS QUANDO A PARTIDA TERMINA (game over, fase completa, ESC).
        """
        # Verifica se está transformado
        if not hasattr(self, '_is_transformed') or not self._is_transformed:
            return False

        print(f"[TRANSFORM_RESET] Resetando {self.name} ao estado original...")

        # Verifica se tem dados originais
        if not hasattr(self, '_original_id'):
            print(f"[TRANSFORM_RESET] ERRO: {self.name} não tem dados originais!")
            self._is_transformed = False
            return False

        # ===== RESTAURA DADOS ORIGINAIS =====
        self.id = self._original_id
        self.name = self._original_name
        self.types = self._original_types.copy()
        self.base_stats = self._original_base_stats.copy()
        self.moves = self._original_moves.copy()

        # Restaura sprites
        self.ui_sprite = self._original_sprite_data["ui_sprite"]
        self.battle_sprite = self._original_sprite_data["battle_sprite"]
        self.inmap_frames = self._original_sprite_data["inmap_frames"]
        self.inmap_animations = self._original_sprite_data["inmap_animations"]

        if hasattr(self, 'animation'):
            self.animation._available_animations = self._original_sprite_data["available_animations"]

        # Recalcula stats
        self.stats.calculate_stats()

        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp

        # Limpa flags de transformação (mas NÃO os dados originais - eles serão sobrescritos no próximo Transform)
        self._is_transformed = False

        # Recarrega animação
        if hasattr(self, 'animation'):
            self.animation.load_sprites(self.id, self.is_shiny)

        self.set_animation("idle")

        print(f"[TRANSFORM_RESET] {self.name} resetado com sucesso!")
        return True

    def serialize_transform_state(self) -> dict:
        """
        Serializa o estado de transformação para salvar no disco.
        Retorna None se não estiver transformado.
        """
        if not hasattr(self, '_is_transformed') or not self._is_transformed:
            return None

        # Serializa apenas os dados necessários para restaurar
        transform_data = {
            "is_transformed": True,
            "transformed_id": self._transformed_id,
            "transformed_name": self._transformed_name,
            "transformed_types": self.types.copy(),  # Tipos já estão substituídos
            "transformed_base_stats": self.base_stats.copy(),
            "transformed_moves": [
                {
                    "name": move.name,
                    "current_pp": move.current_pp,
                    "max_pp": move.max_pp,
                    "type": move.type,
                    "power": move.power,
                    "accuracy": move.accuracy,
                    "category": move.category
                }
                for move in self.moves
            ],
            # Não salvamos sprites (serão recarregados via Pokedex)
            # Não salvamos IVs/EVs (são do Ditto original)
        }

        print(f"[SERIALIZE] Ditto {self.name} transformado em {self._transformed_name} - estado salvo")
        return transform_data

    def deserialize_transform_state(self, transform_data: dict):
        """
        Restaura o estado de transformação a partir de dados salvos.
        """
        if not transform_data or not transform_data.get("is_transformed"):
            return False

        from src.entities.move import Move
        from src.data.move_data import MoveData

        print(f"[DESERIALIZE] Restaurando Ditto {self.name} transformado em {transform_data['transformed_name']}...")

        # ===== SALVA O ESTADO ORIGINAL (caso não tenha) =====
        if not hasattr(self, '_original_id'):
            self._original_id = self.id
            self._original_name = self.name
            self._original_types = self.types.copy()
            self._original_moves = [move for move in self.moves]
            self._original_base_stats = self.base_stats.copy()

            # Salva sprites originais
            self._original_sprite_data = {
                "ui_sprite": self.ui_sprite,
                "battle_sprite": self.battle_sprite,
                "inmap_frames": self.inmap_frames,
                "inmap_animations": self.inmap_animations.copy() if self.inmap_animations else {},
                "available_animations": self.animation.get_available_animations().copy()
            }

        # ===== RESTAURA O ESTADO TRANSFORMADO =====
        self._is_transformed = True
        self._transformed_id = transform_data["transformed_id"]
        self._transformed_name = transform_data["transformed_name"]

        # Restaura tipos
        self.types = transform_data["transformed_types"].copy()

        # Restaura stats base
        self.base_stats = transform_data["transformed_base_stats"].copy()

        # Restaura moves
        move_data = MoveData()
        self.moves = []
        for move_dict in transform_data["transformed_moves"]:
            move_info = move_data.get_move_info(move_dict["name"])
            if move_info:
                move = Move(move_dict["name"], move_info)
                move.current_pp = move_dict["current_pp"]
                move.max_pp = move_dict["max_pp"]
                self.moves.append(move)
            else:
                # Fallback
                move = Move(move_dict["name"], move_dict)
                move.current_pp = move_dict["current_pp"]
                self.moves.append(move)

        # Garante que Transform está presente
        has_transform = any(m.name.lower() == "transform" for m in self.moves)
        if not has_transform:
            transform_info = move_data.get_move_info("transform")
            if transform_info:
                transform_move = Move("transform", transform_info)
                transform_move.current_pp = transform_move.max_pp
                self.moves.insert(0, transform_move)

        # ===== RECARREGA OS SPRITES DO ALVO =====
        # Usa a Pokedex para carregar os sprites do Pokémon alvo
        pokedex = self.pokedex
        self.ui_sprite = pokedex.get_sprite(transform_data["transformed_id"], "front", self.is_shiny)
        self.battle_sprite = pokedex.get_sprite(transform_data["transformed_id"], "back", self.is_shiny)
        self.inmap_frames = pokedex.get_inmap_animation(transform_data["transformed_id"], self.is_shiny)

        # Carrega animações
        anim_info = pokedex.get_pokemon_animations_info(transform_data["transformed_id"], self.is_shiny)
        if hasattr(self, 'animation'):
            self.animation._available_animations = anim_info.get("available_animations", [])
            self.inmap_animations = anim_info.get("raw_data", {}).get("animations", {})

        # Atualiza tamanho do sprite
        self.map_sprite_size = pokedex.get_map_sprite_size(transform_data["transformed_id"], self.is_shiny)

        # ===== RECALCULA STATS =====
        self.stats.calculate_stats()

        # Mantém o HP proporcional (se possível)
        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp

        # Atualiza sprite atual
        if self.inmap_frames and self.current_direction in self.inmap_frames:
            frames = self.inmap_frames[self.current_direction]
            if frames:
                self.sprite = frames[0]

        print(f"[DESERIALIZE] Ditto {self.name} restaurado como {self._transformed_name}!")
        print(f"[DESERIALIZE] Moves: {[m.name for m in self.moves]}")

        return True