# src/scenes/minigames/survival/survival_minigame_scene.py

"""
Cena principal do minigame Survival
Estilo Plants vs Zombies / Tower Defense com cards na esteira
"""
import pygame
import math
import json
import os
from typing import List, Optional, Dict, Any

from src.scenes.minigames.survival.components.pokemon_input_handler import PokemonInputHandler
from src.managers.notification_manager import notification_manager
from src.scenes.minigames.base_minigame_scene import BaseMinigameScene
from src.scenes.minigames.survival.components.card_deck import CardDeck
from src.scenes.minigames.survival.components.placement_manager import SurvivalPlacementManager
from src.scenes.minigames.survival.components.wave_manager import SurvivalWaveManager
from src.scenes.minigames.survival.components.ui.survival_ui import SurvivalUI
from src.battle.battle_system import BattleSystem
from src.battle.effects.status_effect import StatusType
from src.config.paths import PROJECT_ROOT
from src.data.pokedex import Pokedex
from src.data.item_bag_catalog import item_bag_catalog
from src.ui.toast_renderer import toast_battle, toast_info, toast_success, toast_warning, toast_error


class SurvivalMinigameScene(BaseMinigameScene):
    """
    Minigame de sobrevivência estilo Plants vs Zombies.
    - Esteira de cards (Pokémon e Itens)
    - Cartas vêm da direita para esquerda
    - Sistema de combate idêntico ao modo campanha
    """

    STARTING_LIVES = 5
    STARTING_ENERGY = 100
    ENERGY_REGEN_RATE = 1.0
    MAX_ENERGY = 200

    def __init__(self, game, chapter_id: int = 1, phase_number: int = 1):
        super().__init__(game, chapter_id, phase_number, minigame_folder="survival")

        # ===== POKEDEX =====
        self.pokedex = Pokedex()
        self.item_catalog = item_bag_catalog

        # ===== ESTADO DO MINIGAME =====
        self.lives = self.STARTING_LIVES
        self.energy = self.STARTING_ENERGY
        self.score = 0
        self.wave_number = 1
        self.total_waves = 20
        self.game_state = "waiting"

        # ===== DADOS CARREGADOS DO JSON =====
        self.survival_data = None
        self.available_pokemon_cards = []
        self.available_item_cards = []

        # ===== CONTROLE DE CÂMERA =====
        self.dragging_camera = False
        self.last_mouse_pos = None

        if not hasattr(self.game, 'camera') or self.game.camera is None:
            self.game.initialize_camera(self.world_width, self.world_height)

        self.camera = self.game.camera
        self.camera.set_limits(-500, self.world_width + 500, -500, self.world_height + 500)
        self.camera.x = self.world_width / 2
        self.camera.y = self.world_height / 2

        # ===== ESTADO DE PAUSA =====
        self.game_paused = False

        # ===== SISTEMA DE COMBATE =====
        self.battle_system = BattleSystem(self)

        # ===== COMPONENTES =====
        self.placement_manager = SurvivalPlacementManager(self)
        self.survival_ui = SurvivalUI(self)
        self.notification_manager = notification_manager
        self.pokemon_input_handler = PokemonInputHandler(self)
        self.move_select_overlay = None
        self.move_learn_overlay = None
        self.evolution_overlay = None
        self.card_deck = None

        # ===== CARREGA DADOS DO MINIGAME =====
        self._load_survival_data()

        # ===== WAVE MANAGER =====
        from src.scenes.minigames.survival.components.path_assignment import PathAssignmentManager
        self.path_assignment = PathAssignmentManager(self)
        self._init_survival_wave_manager()

        # ===== TIMERS =====
        self.energy_regen_timer = 0.0

        # ===== ESTADO DO CARD SELECIONADO =====
        self.selected_card = None
        self.selected_card_index = -1
        self.selected_card_type = None
        self.selected_card_sprite = None

        # ===== POKÉMON DO JOGADOR =====
        self.player_pokemon: List[Any] = []

        # ===== FONTES =====
        self._init_fonts()

        # Inicia o jogo
        self._start_game()

    def _init_fonts(self):
        """Inicializa fontes específicas"""
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        # ===== CACHE DE FONTES PARA LABELS DE POKEMON =====
        self._label_font_cache = {}

    def _get_cached_font(self, size):
        """Retorna fonte do cache (evita criar fontes a cada frame)."""
        size = max(8, int(size))
        font = self._label_font_cache.get(size)
        if font is None:
            font = pygame.font.Font(None, size)
            self._label_font_cache[size] = font
        return font

    def _load_survival_data(self):
        """Carrega os dados específicos do minigame survival"""
        data_path = os.path.join(PROJECT_ROOT, "src", "data", "minigames", "survival",
                                 f"survival_data_{self.chapter_id:02d}_{self.phase_number:02d}.json")

        if not os.path.exists(data_path):
            print(f"[Survival] ERRO: Arquivo de dados não encontrado: {data_path}")
            self._load_default_data()
            return

        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                self.survival_data = json.load(f)

            print(f"[Survival] Dados carregados: {self.survival_data.get('name', 'Sem nome')}")

            self.total_waves = self.survival_data.get("total_waves", 20)
            self.STARTING_LIVES = self.survival_data.get("starting_lives", 5)
            self.STARTING_ENERGY = self.survival_data.get("starting_energy", 100)
            self.MAX_ENERGY = self.survival_data.get("max_energy", 200)
            self.ENERGY_REGEN_RATE = self.survival_data.get("energy_regen_rate", 1.0)

            self.available_pokemon_cards = self.survival_data.get("available_pokemon", [])
            self.available_item_cards = self.survival_data.get("available_items", [])

            for pokemon in self.available_pokemon_cards:
                pokemon_id = pokemon["id"]
                pokemon["name"] = self.pokedex.get_name(pokemon_id)
                pokemon["types"] = self.pokedex.get_types(pokemon_id)
                pokemon["type"] = pokemon["types"][0] if pokemon["types"] else "normal"

            print(f"[Survival] {len(self.available_pokemon_cards)} Pokémon disponíveis")
            print(f"[Survival] {len(self.available_item_cards)} Itens disponíveis")

        except Exception as e:
            print(f"[Survival] Erro ao carregar dados: {e}")
            import traceback
            traceback.print_exc()
            self._load_default_data()

    def _load_default_data(self):
        """Carrega dados padrão (fallback)"""
        self.total_waves = 20
        self.STARTING_LIVES = 5
        self.STARTING_ENERGY = 100
        self.MAX_ENERGY = 200
        self.ENERGY_REGEN_RATE = 1.0

        self.available_pokemon_cards = [
            {"id": 10, "cost": 30, "level": 5, "name": "Caterpie", "type": "bug"},
            {"id": 13, "cost": 30, "level": 5, "name": "Weedle", "type": "bug"},
            {"id": 19, "cost": 35, "level": 5, "name": "Rattata", "type": "normal"},
            {"id": 16, "cost": 40, "level": 5, "name": "Pidgey", "type": "flying"},
            {"id": 25, "cost": 60, "level": 5, "name": "Pikachu", "type": "electric"}
        ]

        self.available_item_cards = [
            {"id": "potion", "cost": 30, "effect": "heal", "effect_value": 20},
            {"id": "antidote", "cost": 20, "effect": "cure_status", "effect_value": "poison"},
        ]

        print(f"[Survival] Usando dados padrão (fallback)")

    def _init_card_deck(self):
        """Inicializa o deck de cartas com Pokémon e Itens"""
        self.card_deck = CardDeck(self)

        pokemon_cards = []
        for pokemon in self.available_pokemon_cards:
            pokemon_cards.append({
                "id": pokemon["id"],
                "cost": pokemon["cost"],
                "level": pokemon.get("level", 5)
            })

        item_cards = []
        for item in self.available_item_cards:
            item_cards.append({
                "id": item["id"],
                "cost": item["cost"],
                "effect": item["effect"],
                "effect_value": item["effect_value"]
            })

        self.card_deck.set_card_pools(pokemon_cards, item_cards)

        print(f"[Survival] Deck inicializado com {len(self.card_deck.card_pool)} cartas no pool")

    def _init_survival_wave_manager(self):
        """Inicializa o wave manager com os dados carregados"""
        self.wave_manager = SurvivalWaveManager(self, self.chapter_id, self.phase_number, self.survival_data)
        self.wave_manager.set_paths(self.path_renderer.paths)

        if self.path_renderer and self.path_renderer.paths:
            self.path_assignment.load_paths(self.path_renderer.paths)

            if hasattr(self, 'spot_renderer') and self.spot_renderer:
                for spot in self.spot_renderer.get_spots():
                    self.path_assignment.register_spot(
                        spot.x, spot.y,
                        self.placement_manager.tile_size
                    )

    def _start_game(self):
        """Inicia o minigame"""
        print(f"[Survival] Iniciando minigame - Fase {self.chapter_id}-{self.phase_number}")
        print(f"[Survival] Total de waves: {self.total_waves}")

        self.lives = self.STARTING_LIVES
        self.energy = self.STARTING_ENERGY
        self.score = 0
        self.wave_number = 1
        self.game_state = "in_wave"

        self._clear_all_pokemon()
        self._init_card_deck()

        if hasattr(self, 'wave_manager') and self.wave_manager:
            self.wave_manager.start_waves()

    def _clear_all_pokemon(self):
        """Remove todos os Pokémon do mapa"""
        for pokemon in self.player_pokemon[:]:
            self._remove_pokemon(pokemon)
        self.player_pokemon.clear()
        self.placement_manager.clear()

    def _remove_pokemon(self, pokemon):
        """Remove um Pokémon do mapa"""
        if pokemon in self.player_pokemon:
            self.player_pokemon.remove(pokemon)

        if hasattr(pokemon, 'placed_tile_x') and hasattr(pokemon, 'placed_tile_y'):
            for spot in self.spot_renderer.get_spots():
                spot_tile_x = spot.x // self.placement_manager.tile_size
                spot_tile_y = spot.y // self.placement_manager.tile_size
                if spot_tile_x == pokemon.placed_tile_x and spot_tile_y == pokemon.placed_tile_y:
                    spot.occupied = False
                    break

        if hasattr(self, 'battle_system') and self.battle_system:
            if hasattr(self.battle_system, 'effect_manager'):
                self.battle_system.effect_manager.unregister_pokemon(pokemon)

        pokemon.is_placed = False

    def _get_pokemon_status(self, pokemon) -> Optional[StatusType]:
        """Retorna o status atual do Pokémon"""
        if pokemon and hasattr(pokemon, 'effect_manager') and pokemon.effect_manager:
            status = pokemon.effect_manager.get_status(pokemon)
            if status:
                if hasattr(status, 'type'):
                    return status.type
                elif isinstance(status, StatusType):
                    return status
        return None

    def _get_pokemon_status_name(self, pokemon) -> str:
        """Retorna o nome do status atual do Pokémon como string"""
        if self.battle_system and self.battle_system.effect_manager:
            status = self.battle_system.effect_manager.get_status(pokemon)
            if status and status.type != StatusType.NONE:
                status_map = {
                    StatusType.POISON: "poison",
                    StatusType.TOXIC_POISON: "poison",
                    StatusType.PARALYSIS: "paralysis",
                    StatusType.SLEEP: "sleep",
                    StatusType.BURN: "burn",
                    StatusType.FREEZE: "freeze",
                }
                return status_map.get(status.type, "none")

        if hasattr(pokemon, 'effect_manager') and pokemon.effect_manager:
            status = pokemon.effect_manager.get_status(pokemon)
            if status and status.type != StatusType.NONE:
                status_map = {
                    StatusType.POISON: "poison",
                    StatusType.TOXIC_POISON: "poison",
                    StatusType.PARALYSIS: "paralysis",
                    StatusType.SLEEP: "sleep",
                    StatusType.BURN: "burn",
                    StatusType.FREEZE: "freeze",
                }
                return status_map.get(status.type, "none")

        return "none"

    def try_use_item(self, spot, item_data: dict) -> bool:
        """Tenta usar um item em um Pokémon no spot"""
        if not spot.occupied:
            toast_warning("Nenhum Pokémon neste spot!", duration=1.5)
            return False

        target_pokemon = None
        for pokemon in self.player_pokemon:
            if (hasattr(pokemon, 'placed_tile_x') and hasattr(pokemon, 'placed_tile_y') and
                    pokemon.placed_tile_x == spot.x // self.placement_manager.tile_size and
                    pokemon.placed_tile_y == spot.y // self.placement_manager.tile_size):
                target_pokemon = pokemon
                break

        if not target_pokemon:
            toast_warning("Pokémon não encontrado!", duration=1.5)
            return False

        if not target_pokemon.is_alive() or target_pokemon.is_defeated:
            toast_warning(f"{target_pokemon.name} está derrotado!", duration=1.5, pokemon=target_pokemon,
                          portrait="sad")
            return False

        cost = item_data.get('cost', 30)
        if self.energy < cost:
            toast_warning(f"Energia insuficiente! ({cost} necessário)", duration=1.5)
            return False

        effect = item_data.get('effect', '')
        effect_value = item_data.get('effect_value')
        item_name = item_data.get('id', 'item').upper()

        success = False

        if effect == 'heal':
            heal_amount = effect_value
            if target_pokemon.current_hp >= target_pokemon.max_hp:
                toast_warning(f"{target_pokemon.name} já está com HP máximo!",
                              duration=1.5, pokemon=target_pokemon, portrait="normal")
                return False

            old_hp = target_pokemon.current_hp
            target_pokemon.current_hp = min(target_pokemon.max_hp, target_pokemon.current_hp + heal_amount)
            healed = target_pokemon.current_hp - old_hp
            toast_success(f"{item_name} usado! {target_pokemon.name} recuperou {healed} HP!",
                          duration=2.0, pokemon=target_pokemon, portrait="happy")
            success = True

        elif effect == 'cure_status':
            status_to_cure = effect_value

            from src.battle.effects.status_effect import StatusType
            status_map = {
                "paralysis": StatusType.PARALYSIS,
                "sleep": StatusType.SLEEP,
                "poison": StatusType.POISON,
                "burn": StatusType.BURN,
                "freeze": StatusType.FREEZE,
            }
            status_names = {
                StatusType.PARALYSIS: "paralisado",
                StatusType.SLEEP: "dormindo",
                StatusType.POISON: "envenenado",
                StatusType.BURN: "queimado",
                StatusType.FREEZE: "congelado"
            }

            status_type = status_map.get(status_to_cure.lower())

            if not status_type:
                toast_warning(f"Não foi possível usar {item_name} em {target_pokemon.name}!",
                              duration=1.5, pokemon=target_pokemon, portrait="sad")
                return False

            if self.battle_system and self.battle_system.effect_manager:
                current_status = self.battle_system.effect_manager.get_status(target_pokemon)
                if current_status and current_status.type == status_type:
                    self.battle_system.effect_manager.remove_status(target_pokemon)
                    toast_success(f"{item_name} usado! {target_pokemon.name} foi curado!",
                                  duration=2.0, pokemon=target_pokemon, portrait="happy")
                    success = True
                else:
                    if not current_status or current_status.type.value == "none":
                        needed_status_display = status_names.get(status_type, status_to_cure)
                        toast_warning(
                            f"{target_pokemon.name} não está {needed_status_display}! {item_name} não pode ser usado.",
                            duration=2.0, pokemon=target_pokemon, portrait="normal")
                    else:
                        current_name = status_names.get(current_status.type, current_status.type.value)
                        needed_name = status_names.get(status_type, status_to_cure)
                        toast_warning(
                            f"{target_pokemon.name} está {current_name}! {item_name} cura {needed_name} apenas.",
                            duration=2.0, pokemon=target_pokemon, portrait="sad")
                    return False
            else:
                if target_pokemon.effect_manager:
                    target_pokemon.effect_manager.remove_status(target_pokemon)
                    toast_success(f"{item_name} usado! {target_pokemon.name} foi curado!",
                                  duration=2.0, pokemon=target_pokemon, portrait="happy")
                    success = True
                else:
                    toast_warning(f"Não foi possível curar {target_pokemon.name}!",
                                  duration=1.5, pokemon=target_pokemon, portrait="sad")
                    return False

        elif effect == 'revive':
            if target_pokemon.is_alive():
                toast_warning(f"{target_pokemon.name} já está vivo! Não pode usar revive.",
                              duration=1.5, pokemon=target_pokemon, portrait="normal")
                return False

            revive_percent = effect_value or 0.5
            target_pokemon.revive(heal_percentage=revive_percent)
            toast_success(f"{item_name} usado! {target_pokemon.name} foi revivido!",
                          duration=2.0, pokemon=target_pokemon, portrait="happy")
            success = True

        elif effect == 'pp_restore':
            if target_pokemon.moves:
                percentage = effect_value or 1.0
                restored = target_pokemon.restore_pp(percentage=percentage)
                if restored > 0:
                    toast_success(f"{item_name} usado! PP restaurados para {target_pokemon.name}!",
                                  duration=2.0, pokemon=target_pokemon, portrait="happy")
                    success = True
                else:
                    toast_warning(f"{target_pokemon.name} já tem PP máximo!",
                                  duration=1.5, pokemon=target_pokemon, portrait="normal")
                    return False
            else:
                toast_warning(f"{target_pokemon.name} não tem moves para restaurar PP!",
                              duration=1.5, pokemon=target_pokemon)
                return False

        elif effect == 'cure_all_status':
            current_status_name = self._get_pokemon_status_name(target_pokemon)
            if current_status_name == "none":
                toast_warning(f"{target_pokemon.name} não tem nenhum status para curar!",
                              duration=1.5, pokemon=target_pokemon, portrait="normal")
                return False

            if target_pokemon.effect_manager:
                target_pokemon.effect_manager.remove_status(target_pokemon)
                toast_success(f"{item_name} usado! Todos os status de {target_pokemon.name} foram curados!",
                              duration=2.0, pokemon=target_pokemon, portrait="happy")
                success = True
            else:
                return False

        else:
            toast_warning(f"Item {item_name} não pode ser usado aqui!", duration=1.5)
            return False

        if success:
            self.energy -= cost
            if self.selected_card_index >= 0:
                self.card_deck.remove_card(self.selected_card_index)
            self.card_deck.clear_selection()
            self.selected_card = None
            self.selected_card_index = -1
            self.selected_card_type = None
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            return True

        return False

    def try_place_pokemon(self, spot, pokemon_data: dict) -> bool:
        """Tenta colocar um Pokémon no spot"""
        if spot.occupied:
            toast_warning("Spot ocupado!", duration=1.5)
            return False

        cost = pokemon_data.get('cost', 50)
        if self.energy < cost:
            toast_warning(f"Energia insuficiente! ({cost} necessário)", duration=1.5)
            return False

        from src.entities.pokemon import Pokemon

        tile_center_x = (spot.x // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2
        tile_center_y = (spot.y // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2

        pokemon = Pokemon(
            tile_center_x, tile_center_y,
            pokemon_data['id'],
            level=pokemon_data.get('level', 5),
            is_wild=False,
            shiny=False,
            is_boss=False
        )

        pokemon.is_placed = True
        pokemon.placed_tile_x = tile_center_x // self.placement_manager.tile_size
        pokemon.placed_tile_y = tile_center_y // self.placement_manager.tile_size
        pokemon.original_spot_x = tile_center_x
        pokemon.original_spot_y = tile_center_y
        pokemon.screen_manager = self.screen_manager
        pokemon.camera = self.camera
        pokemon.game_scene = self

        pokemon.set_battle_system(self.battle_system)

        self._update_pokemon_range_from_move(pokemon)

        self.placement_manager.add_pokemon(pokemon, spot)
        self.player_pokemon.append(pokemon)
        spot.occupied = True

        self.energy -= cost

        if self.selected_card_index >= 0:
            self.card_deck.remove_card(self.selected_card_index)

        self.card_deck.clear_selection()
        self.selected_card = None
        self.selected_card_index = -1
        self.selected_card_type = None
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        toast_success(f"{pokemon.name} colocado!", duration=1.5, pokemon=pokemon, portrait="happy")
        print(f"[Survival] {pokemon.name} colocado! Range: {pokemon.attack_range}")
        return True

    def can_afford(self, cost: int) -> bool:
        return self.energy >= cost

    def add_energy(self, amount: int):
        self.energy = min(self.MAX_ENERGY, self.energy + amount)

    def add_score(self, amount: int):
        self.score += amount

    def lose_life(self, amount: int = 1):
        """Perde uma vida"""
        if self.game_state == "game_over":
            return

        self.lives -= amount

        if self.lives > 0:
            toast_warning(f"Perdeu uma vida! Restam: {self.lives}",
                          duration=2.0, portrait="sad")
        else:
            self.game_over()

    def game_over(self):
        # ===== TRAVA: nao entra em game over duas vezes =====
        if self.game_state == "game_over":
            return

        self.game_state = "game_over"

        # ===== GARANTE QUE NAO ESTA PAUSADO (evita _render_pause_overlay em cima) =====
        self.paused = False

        if self.wave_manager:
            self.wave_manager.paused = True
            self.wave_manager._finished = True
            self.wave_manager.active_enemies.clear()

        # ===== LIMPA TOASTS PENDENTES (evita "Perdeu uma vida" residindo 2s) =====
        if hasattr(self, 'notification_manager') and self.notification_manager:
            try:
                # Se o notification_manager tiver um método de limpar, usa.
                # Caso não tenha, ignora silenciosamente.
                if hasattr(self.notification_manager, 'clear_all'):
                    self.notification_manager.clear_all()
                elif hasattr(self.notification_manager, 'toasts'):
                    self.notification_manager.toasts.clear()
                elif hasattr(self.notification_manager, 'notifications'):
                    self.notification_manager.notifications.clear()
            except Exception as e:
                print(f"[Survival] Aviso ao limpar notificacoes: {e}")

        print(f"[Survival] GAME OVER! Score final: {self.score}")

    def complete_game(self):
        # ===== TRAVA: nao completa duas vezes =====
        if self.game_state == "completed":
            return

        self.game_state = "completed"
        if self.wave_manager:
            self.wave_manager.paused = True
            self.wave_manager._finished = True
            self.wave_manager.active_enemies.clear()

        # ===== NOTA: toast de "FASE COMPLETA!" foi removido.
        # ===== O overlay central já comunica isso ao jogador.
        print(f"[Survival] FASE COMPLETA! Score final: {self.score}")

    # ===== MÉTODOS DE OVERLAY =====

    def open_evolution_overlay(self, pokemon, evolution_data):
        from src.scenes.game_scene.components.overlays.evolution_overlay import EvolutionOverlay

        self.evolution_overlay = EvolutionOverlay(self, pokemon, evolution_data, False)
        self.evolution_overlay.active = True
        if hasattr(self, 'wave_manager') and self.wave_manager:
            self.wave_manager.paused = True

    def close_evolution_overlay(self, cancel=False):
        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.stop_effect("evolution")

        if hasattr(self, 'evolution_overlay'):
            self.evolution_overlay.active = False
            self.evolution_overlay = None

        self.paused = False
        if hasattr(self, 'wave_manager') and self.wave_manager:
            self.wave_manager.paused = False

        if cancel:
            print(f"[EVOLUTION] Evolução cancelada")

    def open_move_learn_overlay(self, pokemon, new_move_name):
        from src.scenes.game_scene.components.overlays.move_learn_overlay import MoveLearnOverlay

        self.move_learn_overlay = MoveLearnOverlay(self, pokemon, new_move_name)
        self.move_learn_overlay.active = True
        self.paused = True
        if hasattr(self, 'wave_manager') and self.wave_manager:
            self.wave_manager.paused = True

    def close_move_learn_overlay(self, cancel=False):
        if self.move_learn_overlay:
            self.move_learn_overlay.active = False
            self.move_learn_overlay = None

        if not cancel and hasattr(self, 'pending_tm_data') and self.pending_tm_data:
            self.pending_tm_data = None

        self.paused = False
        if hasattr(self, 'wave_manager') and self.wave_manager:
            self.wave_manager.paused = False

    def open_move_select_overlay(self, pokemon):
        from src.scenes.game_scene.components.overlays.move_select_overlay import MoveSelectOverlay

        if not pokemon or not pokemon.moves:
            return

        self.move_select_overlay = MoveSelectOverlay(self, pokemon)
        self.move_select_overlay.active = True
        self.paused = True
        if hasattr(self, 'wave_manager') and self.wave_manager:
            self.wave_manager.paused = True

    def close_move_select_overlay(self):
        """Fecha o overlay de seleção de move (apenas minigame)"""
        pokemon = None
        if self.move_select_overlay:
            pokemon = self.move_select_overlay.pokemon if hasattr(self.move_select_overlay, 'pokemon') else None
            self.move_select_overlay.active = False
            self.move_select_overlay = None

            if pokemon and pokemon.is_placed and not pokemon.is_defeated:
                self._update_pokemon_range_from_move(pokemon)

        self.paused = False
        if hasattr(self, 'wave_manager') and self.wave_manager:
            self.wave_manager.paused = False

    def _update_pokemon_range_from_move(self, pokemon):
        """
        Atualiza o attack_range do Pokémon baseado no tipo do move atual.
        Physical: 150
        Special: 500
        """
        if not pokemon or pokemon.is_defeated or not pokemon.is_alive():
            return

        current_move = pokemon.get_current_move()
        if current_move:
            move_category = current_move.category.lower()
            if move_category == "physical" or move_category == "status":
                pokemon.attack_range = 150
            elif move_category == "special":
                pokemon.attack_range = 500

    # ===== MÉTODOS DE BOTÃO VOLTAR =====

    def _get_back_button_rect(self) -> pygame.Rect:
        """Retorna o rect do botão VOLTAR (usado em game_over/completed)."""
        btn_w, btn_h = 260, 55
        btn_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - btn_w) // 2
        btn_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height // 2 + 100
        return pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    def _render_back_button(self, screen) -> None:
        """Renderiza o botão VOLTAR nas telas de fim de jogo."""
        btn_rect = self._get_back_button_rect()
        mouse_pos = pygame.mouse.get_pos()
        hovered = btn_rect.collidepoint(mouse_pos)

        if hovered:
            bg_color = (60, 130, 200)
            border_color = (150, 200, 255)
        else:
            bg_color = (40, 90, 150)
            border_color = (100, 150, 200)

        # Sombra
        shadow = btn_rect.copy()
        shadow.x += 3
        shadow.y += 3
        pygame.draw.rect(screen, (0, 0, 0, 120), shadow, border_radius=10)

        pygame.draw.rect(screen, bg_color, btn_rect, border_radius=10)
        pygame.draw.rect(screen, border_color, btn_rect, 3, border_radius=10)

        font = pygame.font.Font(None, 32)
        text = font.render("VOLTAR", True, (255, 255, 255))
        text_rect = text.get_rect(center=btn_rect.center)
        screen.blit(text, text_rect)

    def _return_to_survival_select(self):
        """
        Volta para a tela de seleção de fases do minigame Survival.
        Tenta vários nomes possíveis; se não achar, cai no menu principal.
        """
        print("[Survival] Voltando para a seleção de fases do minigame...")

        # AJUSTE: adicione/remova candidatos conforme o nome real da sua cena de seleção
        candidates = [
            ("src.scenes.minigames.survival.survival_select_scene", "SurvivalSelectScene"),
            ("src.scenes.minigames.survival.survival_phase_select_scene", "SurvivalPhaseSelectScene"),
            ("src.scenes.minigames.survival_select_scene", "SurvivalSelectScene"),
            ("src.scenes.minigames.minigame_select_scene", "MinigameSelectScene"),
            ("src.scenes.minigames_scene", "MinigamesScene"),
        ]

        for module_path, class_name in candidates:
            try:
                module = __import__(module_path, fromlist=[class_name])
                scene_class = getattr(module, class_name)
                self.game.current_scene = scene_class(self.game)
                print(f"[Survival] Cena de seleção carregada: {class_name}")
                return
            except (ImportError, AttributeError, TypeError):
                continue

        # Fallback: menu principal
        print("[Survival] Cena de seleção não encontrada. Voltando ao menu principal.")
        self.game.current_scene = self.game.menu_scene

    # ===== MÉTODOS DE EVENTOS =====

    def handle_event(self, event):
        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            self.evolution_overlay.handle_event(event)
            return

        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.handle_event(event)
            return

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.handle_event(event)
            return

        # ===== BOTÃO VOLTAR NAS TELAS DE FIM DE JOGO =====
        if self.game_state in ["game_over", "completed"]:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._get_back_button_rect().collidepoint(event.pos):
                    self._return_to_survival_select()
                    return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._return_to_survival_select()
                return

        if self.survival_ui.handle_event(event):
            return

        if self.pokemon_input_handler.handle_event(event):
            return

        if event.type == pygame.MOUSEWHEEL:
            if not self.paused and not self.dragging_camera:
                mouse_pos = pygame.mouse.get_pos()
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        target_x, target_y = world_pos
                        self.camera.handle_zoom(event.y > 0)
                        new_world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                        if new_world_pos:
                            dx = target_x - new_world_pos[0]
                            dy = target_y - new_world_pos[1]
                            self.camera.x += dx
                            self.camera.y += dy
                            self.camera._clamp_position()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            mouse_pos = pygame.mouse.get_pos()
            if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                self.dragging_camera = True
                self.last_mouse_pos = mouse_pos
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            if self.dragging_camera:
                self.dragging_camera = False
                self.last_mouse_pos = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            return

        if event.type == pygame.MOUSEMOTION:
            if self.dragging_camera and self.last_mouse_pos:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                self.camera.x -= dx / self.camera.zoom
                self.camera.y -= dy / self.camera.zoom
                self.camera._clamp_position()
                self.last_mouse_pos = event.pos
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
                return
            elif event.key == pygame.K_F1:
                self.show_debug = not self.show_debug
                return
            elif event.key == pygame.K_r:
                if self.card_deck and self.card_deck.recycle_cooldown_remaining <= 0:
                    if self.card_deck.cards:
                        self.card_deck.recycle_deck()
                        self.card_deck.clear_selection()
                        self.selected_card = None
                        self.selected_card_index = -1
                        self.selected_card_type = None
                        self.selected_card_sprite = None
                        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                        if hasattr(self, 'survival_ui'):
                            self.survival_ui.show_message("DECK RECICLADO! (R)", (100, 200, 255), duration=1.0)
                    else:
                        self.card_deck.recycle_deck()
                return

        if self.card_deck:
            card_result = self.card_deck.handle_event(event)
            if card_result:
                if card_result.get('action') == 'card_selected':
                    self.selected_card = card_result
                    self.selected_card_index = card_result.get('index', -1)
                    self.selected_card_type = card_result.get('card_type', 'pokemon')

                    if self.selected_card_type == 'item':
                        item_id = self.selected_card.get('item_data', {}).get('id', '')
                        self.selected_card_sprite = self.item_catalog.get_sprite(item_id, scaled=True)
                        if self.selected_card_sprite:
                            self.selected_card_sprite = pygame.transform.scale(self.selected_card_sprite, (48, 48))
                    else:
                        self.selected_card_sprite = None

                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                return

        if self.selected_card and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                if world_pos:
                    spot = self.spot_renderer.get_spot_at_world_pos(world_pos[0], world_pos[1])
                    if spot:
                        if self.selected_card_type == 'pokemon':
                            self.try_place_pokemon(spot, self.selected_card.get('pokemon_data', {}))
                        elif self.selected_card_type == 'item':
                            self.try_use_item(spot, self.selected_card.get('item_data', {}))
                    else:
                        self.card_deck.clear_selection()
                        self.selected_card = None
                        self.selected_card_index = -1
                        self.selected_card_type = None
                        self.selected_card_sprite = None
                        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self.selected_card:
                self.card_deck.clear_selection()
                self.selected_card = None
                self.selected_card_index = -1
                self.selected_card_type = None
                self.selected_card_sprite = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.selected_card:
                self.card_deck.clear_selection()
                self.selected_card = None
                self.selected_card_index = -1
                self.selected_card_type = None
                self.selected_card_sprite = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            elif self.move_select_overlay and self.move_select_overlay.active:
                self.close_move_select_overlay()
            elif self.move_learn_overlay and self.move_learn_overlay.active:
                self.close_move_learn_overlay(cancel=True)
            elif hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
                self.close_evolution_overlay(cancel=True)
            else:
                # ESC durante o jogo normal: volta para a seleção de fases do minigame
                self._return_to_survival_select()

        super().handle_event(event)

    # ===== MÉTODOS DE UPDATE =====

    def fixed_update(self, dt):
        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            self.evolution_overlay.update(dt)
            return

        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.update(dt)
            return

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.update(dt)
            return

        if self.paused:
            return

        # ===== TRAVA DURA: nao atualiza mais nada apos fim =====
        if self.game_state in ["game_over", "completed"]:
            if hasattr(self, 'survival_ui'):
                self.survival_ui.update(dt)
            return

        # ===== TRAVA EXTRA: se wave_manager tambem esta pausado =====
        if self.wave_manager and self.wave_manager.paused:
            if hasattr(self, 'survival_ui'):
                self.survival_ui.update(dt)
            return

        if hasattr(self, 'survival_ui'):
            self.survival_ui.update(dt)

        # ===== REGENERAÇÃO DE ENERGIA =====
        self.energy_regen_timer += dt
        if self.energy_regen_timer >= 1.0:
            regen_amount = int(self.energy_regen_timer * self.ENERGY_REGEN_RATE)
            if regen_amount > 0:
                self.energy = min(self.MAX_ENERGY, self.energy + regen_amount)
                self.energy_regen_timer -= regen_amount / self.ENERGY_REGEN_RATE

        # ===== ATUALIZA DECK DE CARTAS =====
        if self.card_deck:
            self.card_deck.update(dt)

        # ===== ATUALIZA WAVES =====
        if self.wave_manager:
            enemies_at_end = self.wave_manager.update(dt)

            for enemy in enemies_at_end:
                if enemy.is_alive() and not enemy.is_defeated:
                    if not hasattr(enemy, '_escaped_counted') or not enemy._escaped_counted:
                        self.lose_life(1)
                        enemy._escaped_counted = True

        # ===== LIMPA ALVOS INVÁLIDOS DOS ALIADOS =====
        for ally in self.player_pokemon:
            if ally.target and (not ally.target.is_alive() or ally.target.is_defeated):
                ally.target = None
                ally.combat_state = "returning"
                if hasattr(ally, 'has_animation') and ally.has_animation("walk"):
                    ally.set_animation("walk")

        # ===== COLETA INIMIGOS VIVOS =====
        active_enemies = []
        if self.wave_manager:
            active_enemies = [e for e in self.wave_manager.active_enemies if e.is_alive() and not e.is_defeated]

        # ===== ATUALIZA TODOS OS ALIADOS =====
        old_levels = {id(pokemon): pokemon.level for pokemon in self.player_pokemon}

        for pokemon in self.player_pokemon[:]:
            if not pokemon.is_alive() or pokemon.is_defeated:
                self._remove_pokemon(pokemon)
                continue

            pokemon.update(dt)

            if active_enemies:
                pokemon._temp_path_assignment = self.path_assignment
                pokemon.update_combat(dt, active_enemies)
                pokemon._temp_path_assignment = None
            else:
                if pokemon.combat_state != "returning":
                    if pokemon.target:
                        pokemon.target = None

                    if hasattr(pokemon, 'original_spot_x') and hasattr(pokemon, 'original_spot_y'):
                        dx = pokemon.original_spot_x - pokemon.x
                        dy = pokemon.original_spot_y - pokemon.y
                        distance = math.hypot(dx, dy)

                        if distance > 5:
                            pokemon.combat_state = "returning"
                            if pokemon.has_animation("walk"):
                                pokemon.set_animation("walk")
                        else:
                            if pokemon.combat_state != "idle":
                                pokemon.combat_state = "idle"
                                if pokemon.has_animation("idle"):
                                    pokemon.set_animation("idle")
                    else:
                        if pokemon.combat_state != "idle":
                            pokemon.combat_state = "idle"
                            if pokemon.has_animation("idle"):
                                pokemon.set_animation("idle")
                else:
                    pokemon._temp_path_assignment = self.path_assignment
                    pokemon.update_combat(dt, [])
                    pokemon._temp_path_assignment = None

            pokemon.animation.update(dt)

        # ===== ATUALIZA COMBATE DOS INIMIGOS =====
        if self.wave_manager and self.wave_manager.active_enemies:
            for enemy in self.wave_manager.active_enemies[:]:
                if not enemy.is_alive() or enemy.is_defeated:
                    continue

                enemy._temp_path_assignment = self.path_assignment
                enemy.update_combat(dt, self.player_pokemon)
                enemy._temp_path_assignment = None

                enemy.animation.update(dt)

        # ===== ATUALIZA SISTEMA DE COMBATE =====
        if hasattr(self, 'battle_system'):
            self.battle_system.update(dt)

        if hasattr(self, 'battle_system') and self.battle_system:
            effect_mgr = self.battle_system.effect_manager
            if effect_mgr:
                effect_mgr.update(dt)

        # ===== VERIFICA EVOLUÇÕES =====
        from src.managers.evolution_manager import evolution_manager

        for pokemon in self.player_pokemon[:]:
            old_level = old_levels.get(id(pokemon), pokemon.level)

            if pokemon.level > old_level:
                print(f"[SURVIVAL] {pokemon.name} subiu do nível {old_level} para {pokemon.level}!")

                evolution = evolution_manager.check_evolution(pokemon.id, current_level=pokemon.level)
                if evolution:
                    print(f"[SURVIVAL] {pokemon.name} pode evoluir! Abrindo overlay...")
                    self.open_evolution_overlay(pokemon, evolution)
                    return

        # ===== ATUALIZA NOTIFICAÇÕES =====
        if hasattr(self, 'notification_manager'):
            self.notification_manager.update(dt)

    def force_allies_return_to_spots(self):
        """Força todos os aliados a voltarem para seus spots"""
        for ally in self.player_pokemon:
            if not ally.is_alive() or ally.is_defeated:
                continue

            ally.target = None

            if hasattr(ally, 'original_spot_x') and hasattr(ally, 'original_spot_y'):
                dx = ally.original_spot_x - ally.x
                dy = ally.original_spot_y - ally.y
                distance = math.hypot(dx, dy)

                if distance > 5:
                    ally.combat_state = "returning"
                    if hasattr(ally, 'has_animation') and ally.has_animation("walk"):
                        ally.set_animation("walk")
                else:
                    ally.combat_state = "idle"
                    if hasattr(ally, 'has_animation') and ally.has_animation("idle"):
                        ally.set_animation("idle")
            else:
                ally.combat_state = "idle"
                if hasattr(ally, 'has_animation') and ally.has_animation("idle"):
                    ally.set_animation("idle")

    def toggle_pause(self):
        self.paused = not self.paused
        if self.wave_manager:
            self.wave_manager.paused = self.paused

    # ===== MÉTODOS DE RENDER =====

    def render(self, screen):
        self.map_renderer.render(screen, self.camera, self.screen_manager)

        self.spot_renderer.render(
            screen, self.camera, self.screen_manager,
            highlight_spot=self._get_hovered_spot() if self.selected_card else None
        )

        if self.wave_manager:
            for enemy in self.wave_manager.active_enemies:
                enemy.render(screen, self.camera, show_hp=True)

        for pokemon in self.player_pokemon:
            pokemon.render(screen, self.camera, show_hp=True)
            self._render_ally_pp_and_xp(screen, pokemon)

        if hasattr(self, 'battle_system'):
            self.battle_system.render_projectiles(screen, self.camera, self.screen_manager)

        self.survival_ui.render(screen)
        if self.card_deck:
            self.card_deck.render(screen)

        if self.selected_card:
            self._render_selected_card_preview(screen)

        if self.game_state == "game_over":
            self._render_game_over(screen)
        elif self.game_state == "completed":
            self._render_completed(screen)

        if self.paused:
            self._render_pause_overlay(screen)

        pygame.draw.rect(screen, (80, 80, 80),
                         (self.screen_manager.viewport_x, self.screen_manager.viewport_y,
                          self.screen_manager.viewport_width, self.screen_manager.viewport_height), 2)

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.render(screen)

        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.render(screen)

        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            self.evolution_overlay.render(screen)

    def _get_hovered_spot(self):
        mouse_pos = pygame.mouse.get_pos()
        if self.screen_manager.is_mouse_in_viewport(mouse_pos):
            world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
            if world_pos:
                return self.spot_renderer.get_spot_at_world_pos(world_pos[0], world_pos[1])
        return None

    def _render_ally_pp_and_xp(self, screen, pokemon):
        """
        Renderiza level + PP e barra de XP acima do Pokémon.
        Formato: 'lvl: 8 - PP: 10/20'
        """
        if not pokemon or pokemon.is_defeated or not pokemon.is_alive():
            return

        if hasattr(self, 'camera') and self.camera:
            screen_x, screen_y = self.screen_manager.world_to_screen(
                pokemon.x, pokemon.y, self.camera
            )
            zoom_scale = self.camera.zoom * self.screen_manager.render_scale
        else:
            screen_x, screen_y = pokemon.x, pokemon.y
            zoom_scale = 1.0

        sprite_to_render = None
        if hasattr(pokemon, 'sprite') and pokemon.sprite:
            if pokemon.is_boss:
                ow, oh = pokemon.sprite.get_width(), pokemon.sprite.get_height()
                sprite_to_render = pygame.transform.scale(pokemon.sprite, (ow * 2, oh * 2))
            else:
                sprite_to_render = pokemon.sprite

        if sprite_to_render:
            cw, ch = sprite_to_render.get_width(), sprite_to_render.get_height()
            fw = max(1, int(cw * zoom_scale))
            fh = max(1, int(ch * zoom_scale))
            if fw != cw or fh != ch:
                scaled_sprite = pygame.transform.scale(sprite_to_render, (fw, fh))
            else:
                scaled_sprite = sprite_to_render
            sprite_rect = scaled_sprite.get_rect()
            sprite_rect.center = (int(screen_x), int(screen_y))
        else:
            size = int((64 if pokemon.is_boss else pokemon.map_sprite_size) * zoom_scale)
            sprite_rect = pygame.Rect(0, 0, size, size)
            sprite_rect.center = (int(screen_x), int(screen_y))

        # ===== MONTA TEXTO: 'lvl: 8 - PP: 10/20' =====
        level_text = f"lvl: {pokemon.level}"

        current_move = pokemon.get_current_move()
        if current_move:
            pp_current = current_move.current_pp
            pp_max = current_move.max_pp
            pp_text = f"PP: {pp_current:02d}/{pp_max:02d}"

            pp_percent = pp_current / pp_max if pp_max > 0 else 0
            if pp_percent <= 0.25:
                pp_color = (255, 100, 100)
            elif pp_percent <= 0.5:
                pp_color = (255, 200, 100)
            else:
                pp_color = (100, 255, 100)
        else:
            pp_text = "PP: --"
            pp_color = (150, 150, 150)

        # Cor do level (shiny = dourado, level alto = vermelho, normal = verde)
        if pokemon.is_shiny:
            level_color = (255, 215, 0)
        elif pokemon.level >= 30:
            level_color = (255, 100, 100)
        else:
            level_color = (100, 255, 100)

        separator = " - "
        separator_color = (200, 200, 200)

        font_size = max(8, int(11 * zoom_scale))
        font = self._get_cached_font(font_size)

        # Renderiza cada parte
        level_surf = font.render(level_text, True, level_color)
        sep_surf = font.render(separator, True, separator_color)
        pp_surf = font.render(pp_text, True, pp_color)

        level_outline = font.render(level_text, True, (0, 0, 0))
        sep_outline = font.render(separator, True, (0, 0, 0))
        pp_outline = font.render(pp_text, True, (0, 0, 0))

        # Largura total
        total_w = level_surf.get_width() + sep_surf.get_width() + pp_surf.get_width()

        # Posicao (acima do sprite)
        sprite_height = sprite_rect.height
        relative_offset = -sprite_height * 0.85

        base_x = sprite_rect.centerx - total_w // 2
        base_y = int(sprite_rect.top + relative_offset)

        # Desenha cada parte com contorno
        cur_x = base_x
        for surf, outline in [(level_surf, level_outline),
                              (sep_surf, sep_outline),
                              (pp_surf, pp_outline)]:
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                screen.blit(outline, (cur_x + dx, base_y + dy))
            screen.blit(surf, (cur_x, base_y))
            cur_x += surf.get_width()

        # Barra de XP
        self._render_ally_xp_bar(screen, sprite_rect, pokemon, zoom_scale)

    def _render_ally_xp_bar(self, screen, sprite_rect, pokemon, zoom_scale):
        sprite_height = sprite_rect.height
        hp_bar_y = sprite_rect.top + (-sprite_height * 0.35)
        hp_bar_width = 48

        bar_width = int(hp_bar_width * zoom_scale)
        bar_width = max(30, min(100, bar_width))

        bar_x = sprite_rect.centerx - bar_width // 2
        xp_bar_height = max(3, int(4 * zoom_scale))
        xp_bar_y = int(hp_bar_y + (6 * zoom_scale) + 2)

        if pokemon.is_defeated or not pokemon.is_alive():
            return

        xp_percent = pokemon.xp / pokemon.xp_to_next if pokemon.xp_to_next > 0 else 0

        pygame.draw.rect(screen, (30, 30, 40), (bar_x, xp_bar_y, bar_width, xp_bar_height), border_radius=2)

        if xp_percent > 0:
            xp_width = max(2, int(bar_width * xp_percent))
            xp_color = (100, 150, 255)
            pygame.draw.rect(screen, xp_color, (bar_x, xp_bar_y, xp_width, xp_bar_height), border_radius=2)

        pygame.draw.rect(screen, (100, 100, 120), (bar_x, xp_bar_y, bar_width, xp_bar_height), 1, border_radius=2)

    def _render_selected_card_preview(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        if not self.screen_manager.is_mouse_in_viewport(mouse_pos):
            return

        if self.selected_card_type == 'pokemon':
            pokemon_data = self.selected_card.get('pokemon_data', {})
            cost = pokemon_data.get('cost', 50)
            can_afford = self.energy >= cost

            sprite_to_draw = None
            try:
                pokedex = self.game.player.pokedex if self.game.player else None
                if pokedex and pokemon_data:
                    sprite = pokedex.get_sprite(pokemon_data['id'], "front", False)
                    if sprite:
                        sprite_to_draw = pygame.transform.scale(sprite, (48, 48))
            except:
                pass
        else:
            item_data = self.selected_card.get('item_data', {})
            cost = item_data.get('cost', 30)
            can_afford = self.energy >= cost
            sprite_to_draw = self.selected_card_sprite

        preview_size = 64
        half = preview_size // 2

        preview_bg = pygame.Surface((preview_size, preview_size), pygame.SRCALPHA)

        if can_afford:
            preview_bg.fill((100, 200, 100, 200))
            border_color = (0, 255, 0)
        else:
            preview_bg.fill((200, 100, 100, 200))
            border_color = (255, 0, 0)

        pygame.draw.rect(preview_bg, border_color, (0, 0, preview_size, preview_size), 3, border_radius=8)

        if sprite_to_draw:
            sprite_x = (preview_size - sprite_to_draw.get_width()) // 2
            sprite_y = (preview_size - sprite_to_draw.get_height()) // 2
            preview_bg.blit(sprite_to_draw, (sprite_x, sprite_y))

        cost_text = self.font_small.render(f"{cost}", True, (255, 255, 255))
        cost_bg = pygame.Surface((cost_text.get_width() + 6, 18), pygame.SRCALPHA)
        cost_bg.fill((0, 0, 0, 180))

        screen.blit(preview_bg, (mouse_pos[0] - half, mouse_pos[1] - half))

        pygame.draw.circle(screen, (255, 200, 50), (mouse_pos[0] + half - 15, mouse_pos[1] - half + 15), 14)
        screen.blit(cost_bg, (mouse_pos[0] + half - 15 - cost_text.get_width() // 2 - 3, mouse_pos[1] - half + 10))
        screen.blit(cost_text, (mouse_pos[0] + half - 15 - cost_text.get_width() // 2, mouse_pos[1] - half + 11))

    def _render_game_over(self, screen):
        overlay = pygame.Surface((self.screen_manager.viewport_width, self.screen_manager.viewport_height))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        title = self.font_large.render("GAME OVER", True, (255, 80, 80))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title.get_width()) // 2
        title_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height // 2 - 60
        screen.blit(title, (title_x, title_y))

        score_text = self.font_medium.render(f"Score Final: {self.score}", True, (255, 215, 0))
        score_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - score_text.get_width()) // 2
        score_y = title_y + 50
        screen.blit(score_text, (score_x, score_y))

        wave_text = self.font_small.render(f"Waves completadas: {self.wave_number - 1}", True, (200, 200, 200))
        wave_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - wave_text.get_width()) // 2
        wave_y = score_y + 35
        screen.blit(wave_text, (wave_x, wave_y))

        inst_text = self.font_small.render("Pressione ESC para voltar a selecao", True, (150, 150, 150))
        inst_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - inst_text.get_width()) // 2
        inst_y = wave_y + 30
        screen.blit(inst_text, (inst_x, inst_y))

        # ===== BOTAO VOLTAR =====
        self._render_back_button(screen)

    def _render_completed(self, screen):
        overlay = pygame.Surface((self.screen_manager.viewport_width, self.screen_manager.viewport_height))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        title = self.font_large.render("FASE COMPLETA!", True, (100, 255, 100))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title.get_width()) // 2
        title_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height // 2 - 60
        screen.blit(title, (title_x, title_y))

        score_text = self.font_medium.render(f"Score Final: {self.score}", True, (255, 215, 0))
        score_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - score_text.get_width()) // 2
        score_y = title_y + 50
        screen.blit(score_text, (score_x, score_y))

        lives_text = self.font_small.render(f"Vidas restantes: {self.lives}", True, (200, 200, 200))
        lives_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - lives_text.get_width()) // 2
        lives_y = score_y + 35
        screen.blit(lives_text, (lives_x, lives_y))

        inst_text = self.font_small.render("Pressione ESC para voltar a selecao", True, (150, 150, 150))
        inst_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - inst_text.get_width()) // 2
        inst_y = lives_y + 30
        screen.blit(inst_text, (inst_x, inst_y))

        # ===== BOTAO VOLTAR =====
        self._render_back_button(screen)

    def _render_pause_overlay(self, screen):
        overlay = pygame.Surface((self.screen_manager.viewport_width, self.screen_manager.viewport_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        pause_text = self.font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - pause_text.get_width()) // 2
        text_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

    def on_resize(self):
        """Chamado quando a tela é redimensionada"""
        if self.card_deck:
            self.card_deck.on_resize()