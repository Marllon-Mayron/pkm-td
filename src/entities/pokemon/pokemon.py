# src/entities/pokemon/pokemon.py
import pygame
import uuid
import random
from typing import List, Dict, Optional

from src.entities.base import Entity
from src.data.pokedex import Pokedex
from src.data.move_data import MoveData
from .animation import PokemonAnimation

from .stats import PokemonStats
from .movement import PokemonMovement
from .combat import PokemonCombat
from .moves import PokemonMoves
from .evolution import PokemonEvolution
from .rendering import PokemonRendering
from ...battle.attack_pattern import AttackTypeCategory, AttackPattern, AttackPatternManager
from ...battle.effects import StatusType

# Cache global de sprites e fontes para reduzir recriação
_SPRITE_CACHE = {}
_FONT_CACHE = {}


class Pokemon(Entity):
    # Constantes de classe
    _MIN_MOVE_SPEED = 0.2
    _MAX_MOVE_SPEED = 4.5
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
        self.is_placed = False
        self.spot_id = None
        self.types = self.pokemon_data["types"]
        self.base_stats = self.pokemon_data["base_stats"]

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
        self.speed_bonus_not_wild = 0.3
        if is_wild:
            self.base_move_speed = self._get_cached_move_speed()
            self.move_speed = self.base_move_speed
        else:
            self.base_move_speed = self._get_cached_move_speed()
            self.move_speed = self.base_move_speed + self.speed_bonus_not_wild

        # ===== 15. COMBATE =====
        self.can_attack = True
        self.attack_cooldown = 0
        self.attack_cooldown_max = 60
        self.target = None
        self.has_no_pp = False

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

        if hasattr(self, 'show_debug') and self.show_debug and sprite_rect:
            self._render_debug(screen, screen_x, screen_y, zoom_scale, sprite_rect)

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

    def set_defeated(self, defeated: bool):
        """Define se o Pokémon está derrotado"""
        self.is_defeated = defeated
        if defeated:
            # ===== CANCELA QUALQUER CARGA DE GOLPE =====
            if hasattr(self, 'battle_system') and self.battle_system:
                if (self.battle_system.active_charge_move and
                        self.battle_system.active_charge_move['attacker'] == self):
                    print(f"[TWO_TURN] Carga de {self.name} foi cancelada devido à derrota!")
                    self.battle_system.active_charge_move = None
            # Força animação de sono
            self.set_animation_direct("sleep")
            # Reseta estado de combate
            self.combat_state = "idle"
            self.target = None
            self.charge_cooldown = 0

            if defeated and hasattr(self, 'battle_system') and self.battle_system:
                # Remove efeitos residuais quando derrotado
                if hasattr(self.battle_system, 'residual_effects'):
                    self.battle_system.residual_effects.remove_effect_on_target(self)

            print(f"[DEFEATED] {self.name} foi derrotado! Animação de sono ativada.")
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

        self.set_battle_system(game_scene.battle_system)
        self.screen_manager= game_scene.screen_manager
        self.camera= game_scene.camera