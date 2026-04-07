# src/scenes/game_scene.py
"""
Cena principal do jogo - COM NOVA ARQUITETURA DE WAVES
"""
import pygame

from src.battle.battle_system import BattleSystem
from src.config.paths import PROJECT_ROOT
from src.config.settings import settings
from src.core.profiler import profiler
from src.managers.sound_manager import SoundEffect, sound_manager
from src.scenes.base_scene import BaseScene
from src.config.phase_catalog import phase_catalog
from src.scenes.game_scene.components.managers.overlay_manager import OverlayType, OverlayManager
from src.scenes.game_scene.components.managers.placement_manager import PlacementManager
from src.scenes.game_scene.components.managers.item_drag_manager import ItemDragManager
from src.scenes.game_scene.components.managers.target_item_manager import TargetItemManager
from src.scenes.game_scene.components.managers.team_manager import GameTeamManager
from src.scenes.game_scene.components.managers.wave_manager import WaveManager
from src.scenes.game_scene.components.overlays.move_select_overlay import MoveSelectOverlay
from src.scenes.game_scene.components.phase_loader import phase_loader
from src.scenes.game_scene.components.renderer.item_bag_renderer import ItemBagRenderer
from src.scenes.game_scene.components.renderer.map_renderer import MapRenderer
from src.scenes.game_scene.components.renderer.path_renderer import PathRenderer
from src.scenes.game_scene.components.renderer.pokemon_spot_renderer import PokemonSpotRenderer # NOVO
from src.scenes.game_scene.components.renderer.target_item_renderer import TargetItemRenderer


class GameScene(BaseScene):
    def __init__(self, game, chapter_id=1, phase_number=1):
        super().__init__(game)

        # Flag de debug
        self.debug_in_game = False
        self.move_select_overlay = None
        self.move_learn_overlay = None
        self.game_paused = False

        self.chapter_id = chapter_id
        self.phase_number = phase_number
        self.phase_id = f"{chapter_id}-{phase_number}"
        self.phase_info = None

        # Carrega informações da fase
        self._load_phase_info()

        # Componentes da fase
        self.map_renderer = MapRenderer()
        self.path_renderer = PathRenderer()
        self.spot_renderer = PokemonSpotRenderer()

        # Cria os gerenciadores
        self.placement_manager = PlacementManager(self)
        self.team_manager = GameTeamManager(game, self)
        self.target_item_manager = TargetItemManager(game)
        self.target_item_renderer = TargetItemRenderer()

        # CARREGA OS DADOS DA FASE
        self._load_phase_data()

        # Cria o overlay_manager
        self.overlay_manager = OverlayManager(self)

        # ===== NOVO: Wave Manager refatorado =====
        self.wave_manager = WaveManager(phase_loader, self)
        self.wave_manager.set_paths(self.path_renderer.paths)  # Define os paths

        # Vincula os itens alvo
        self.wave_manager.set_target_items(self.target_item_manager.items)

        # Battle System
        self.battle_system = BattleSystem(self)

        # Configurações de mundo
        self._setup_world_dimensions()

        self.player = game.player

        # Renderizadores
        self.item_bag_renderer = ItemBagRenderer(game, self.player.bag)
        self.item_drag_manager = ItemDragManager(game, self.player.bag)

        # Controle de música
        self.music_playing = False
        self.current_music = None
        self._start_battle_music()

        # Inicializa câmera
        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera
        self.camera.set_limits(-500, self.world_width + 500, -500, self.world_height + 500)
        self.camera.x = self.world_width / 2
        self.camera.y = self.world_height / 2

        # Estado do jogo
        self.hovered_spot = None
        self.placed_pokemon = []
        self.game_state = "waiting"
        self.between_waves_timer = 3.0
        self.show_debug = False

        # Fontes cacheadas
        self._debug_font = pygame.font.Font(None, 18)
        self._debug_font_bold = pygame.font.Font(None, 20)
        self._debug_font_small = pygame.font.Font(None, 16)
        self._ui_font = None
        self._ui_font_small = None

        # Controle de arrasto da câmera
        self.dragging_camera = False
        self.last_mouse_pos = None

        # Cache de referências para otimização
        self._cached_spot_renderer = None
        self._cached_placement_manager = None
        self._cached_team_manager = None
        self._cached_item_bag_renderer = None

        # Inicia o jogo
        self._start_game()

    def _get_ui_font(self, size=24):
        """Obtém fonte da UI com cache"""
        if size == 24:
            if self._ui_font is None:
                self._ui_font = pygame.font.Font(None, 24)
            return self._ui_font
        else:
            if self._ui_font_small is None:
                self._ui_font_small = pygame.font.Font(None, 18)
            return self._ui_font_small

    def _start_game(self):
        """Inicia o jogo"""
        # ===== RESTAURA COMPLETAMENTE TODOS OS POKÉMON =====
        # Revive e restaura Pokémon no time do jogador
        for pokemon in self.player.team:
            pokemon.full_restore()
            pokemon.set_battle_system(self.battle_system)
            self.battle_system.set_effect_manager_for_pokemon(pokemon)
            pokemon.screen_manager = self.screen_manager
            pokemon.camera = self.camera

        # Revive e restaura Pokémon já colocados no campo
        for pokemon in self.placement_manager.placed_pokemon:
            pokemon.full_restore()
            pokemon.set_battle_system(self.battle_system)
            self.battle_system.set_effect_manager_for_pokemon(pokemon)
            pokemon.screen_manager = self.screen_manager
            pokemon.camera = self.camera

        # Reseta ouro acumulado
        self.wave_manager.reset_gold()

        # Configura screen_manager para inimigos que já existam
        for enemy in self.wave_manager.active_enemies:
            enemy.set_battle_system(self.battle_system)
            self.battle_system.set_effect_manager_for_pokemon(enemy)
            enemy.screen_manager = self.screen_manager
            enemy.camera = self.camera

        # Inicia as waves
        if self.wave_manager.has_more_waves():
            self.game_state = "in_wave"
            self.wave_manager.start_all_waves()

    def _load_phase_info(self):
        """Carrega informações da fase do catálogo"""
        self.phase_info = phase_catalog.get_phase_info(self.chapter_id, self.phase_number)
        if not self.phase_info:
            self.phase_info = {
                "name": f"Fase {self.chapter_id}-{self.phase_number}",
                "number": self.phase_number,
                "chapter": self.chapter_id
            }

    def _load_phase_data(self):
        """Carrega os dados da fase do disco"""
        data = phase_loader.load_phase(self.chapter_id, self.phase_number)

        if not data:
            self.phase_rewards = {"money": 0, "experience": 0}
            return

        base_path = PROJECT_ROOT

        # Carrega componentes
        self.map_renderer.load_from_data(phase_loader.get_map_data(), base_path)
        self.path_renderer.load_from_data(phase_loader.get_paths_data())
        self.spot_renderer.load_from_data(phase_loader.get_tower_spots_data())
        self.target_item_manager.load_from_data(data.get("target_items", {}))

        # Carrega recompensas
        rewards = data.get("rewards", {})
        self.phase_rewards = {
            "money": rewards.get("money", 0),
            "experience": rewards.get("experience", 0)
        }

    def _setup_world_dimensions(self):
        """Configura dimensões do mundo baseado no mapa"""
        map_width, map_height = self.map_renderer.get_dimensions()
        if map_width > 0 and map_height > 0:
            self.world_width = map_width
            self.world_height = map_height
        else:
            self.world_width = 2000
            self.world_height = 2000

    # ===== MÉTODOS DE OVERLAY (mantidos) =====

    def open_move_select_overlay(self, pokemon):
        """Abre o overlay de seleção de moves para um Pokémon"""
        if not pokemon or not pokemon.moves:
            return

        self.move_select_overlay = MoveSelectOverlay(self, pokemon)
        self.move_select_overlay.active = True
        self.game_paused = True
        self.paused = True
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

    def close_move_select_overlay(self):
        """Fecha o overlay de seleção de moves"""
        if self.move_select_overlay:
            self.move_select_overlay.active = False
            self.move_select_overlay = None

        self.game_paused = False
        self.paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

    def open_move_learn_overlay(self, pokemon, new_move_name):
        """Abre o overlay de aprendizado de novo move"""
        from src.scenes.game_scene.components.overlays.move_learn_overlay import MoveLearnOverlay

        self.move_learn_overlay = MoveLearnOverlay(self, pokemon, new_move_name)
        self.move_learn_overlay.active = True
        self.game_paused = True
        self.paused = True
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

    def close_move_learn_overlay(self, cancel=False):
        """Fecha o overlay de aprendizado de moves"""
        if self.move_learn_overlay:
            self.move_learn_overlay.active = False
            self.move_learn_overlay = None

        self.game_paused = False
        self.paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

    def show_capture_overlay(self, pokemon, is_to_team=True):
        """Mostra o overlay de captura de Pokémon"""
        self.game_paused = True
        self.paused = True
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

        sound_manager.play_effect(SoundEffect.CAUGHT)
        self.overlay_manager.show(OverlayType.CAPTURE, pokemon=pokemon, is_to_team=is_to_team)

    def close_capture_overlay(self):
        """Fecha o overlay de captura"""
        self.game_paused = False
        self.paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False
        self.overlay_manager.hide()

    def open_evolution_overlay(self, pokemon, evolution_data):
        """Abre o overlay de evolução para um Pokémon"""
        from src.scenes.game_scene.components.overlays.evolution_overlay import EvolutionOverlay

        sound_manager.play_effect(SoundEffect.EVOLUTION)
        self.evolution_overlay = EvolutionOverlay(self, pokemon, evolution_data)
        self.evolution_overlay.active = True

        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

    def close_evolution_overlay(self, cancel=False):
        """Fecha o overlay de evolução"""
        sound_manager.stop_effect(SoundEffect.EVOLUTION)

        if hasattr(self, 'evolution_overlay'):
            self.evolution_overlay = None

        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

    # ===== MÉTODOS DE ITEM E CAPTURA =====

    def _on_item_use(self, target, item_data, target_type):
        """Callback quando um item é usado em um alvo"""
        effect = item_data.get("effect", "")
        category = item_data.get("category", "")

        if effect == "cure_status":
            if target_type == "ally":
                from src.battle.effects.status_effect import StatusType
                status_to_cure = item_data.get("effect_value")

                status_map = {
                    "paralysis": StatusType.PARALYSIS,
                    "sleep": StatusType.SLEEP,
                    "poison": StatusType.POISON,
                    "burn": StatusType.BURN,
                    "freeze": StatusType.FREEZE,
                }

                status_type = status_map.get(status_to_cure)
                if status_type:
                    current_status = self.battle_system.effect_manager.get_status(target)
                    if current_status and current_status.type == status_type:
                        self.battle_system.effect_manager.remove_status(target)
                        self.battle_system.effect_manager.add_status_text(target, f"curou {status_to_cure}!")
                        return True
                return False

        elif effect == "cure_all_status":
            if target_type == "ally":
                current_status = self.battle_system.effect_manager.get_status(target)
                if current_status and current_status.type.value != "none":
                    self.battle_system.effect_manager.remove_status(target)
                    self.battle_system.effect_manager.add_status_text(target, "todos os status curados!")
                    print(f"[ITEM] {item_data['name']} usado em {target.name}!")
                    return True
                return False

        elif effect == "pp_restore":
            if target_type == "ally" and hasattr(target, 'restore_pp'):
                percentage = item_data.get("effect_value", 1.0)
                restored = target.restore_pp(percentage=percentage)
                if restored > 0:
                    print(f"[ITEM] {item_data['name']} usado em {target.name}! {restored} PP restaurados!")
                    return True
                return False

        elif effect == "evolution":
            if target_type == "ally":
                return self._use_evolution_stone(target, item_data)

        elif effect == "teach_move":
            if target_type == "ally":
                move_to_teach = item_data.get("effect_value")
                return self._teach_move_to_pokemon(target, move_to_teach, item_data)

        elif target_type == "enemy" and category == "pokeball":
            return self._attempt_capture(target, item_data)

        elif target_type == "ally" and category == "medicine":
            return self.use_medicine(target, item_data)

        return False

    def _use_evolution_stone(self, pokemon, item_data):
        """Usa pedra de evolução em um Pokémon"""
        from src.managers.evolution_manager import evolution_manager

        stone_name = item_data["id"]
        evolution = evolution_manager.check_evolution(pokemon.id, stone_name=stone_name)

        if not evolution:
            self.player.bag.add_item(item_data["id"], 1)
            return False

        evolve_to_id = evolution["evolve_to"]
        pokemon._perform_evolution(evolve_to_id)

        self.player.caught_pokemon.add(evolve_to_id)
        self.player.register_seen(evolve_to_id)
        self.player.auto_save()
        return True

    def _teach_move_to_pokemon(self, pokemon, move_name, item_data):
        """Ensina um move a um Pokémon usando TM"""
        from src.entities.move import Move
        from src.data.move_data import MoveData

        move_data = MoveData()
        move_info = move_data.get_move_info(move_name)

        if not move_info:
            print(f"[TM] Move {move_name} não encontrado!")
            self.player.bag.add_item(item_data["id"], 1)
            return False

        if len(pokemon.moves) < 4:
            pokemon.moves.append(Move(move_name, move_info))
            print(f"[TM] {pokemon.name} aprendeu {move_name} via TM!")
            return True

        self._open_forget_move_overlay(pokemon, move_name, move_info, item_data)
        return True

    def _attempt_capture(self, enemy, item_data):
        """Tenta capturar um Pokémon selvagem"""
        if hasattr(enemy, 'is_boss') and enemy.is_boss:
            return False

        hp_ratio = enemy.current_hp / enemy.max_hp
        base_chance = (1 - hp_ratio * 0.5)

        multipliers = {
            "pokeball": 1.0,
            "greatball": 1.5,
            "ultraball": 2.0,
            "masterball": 100.0
        }
        multiplier = multipliers.get(item_data["id"], 1.0)
        chance = min(1.0, base_chance * multiplier)

        import random
        roll = random.random()

        if roll < chance or item_data["id"] == "masterball":
            carried_item = enemy.is_carrying
            if carried_item:
                enemy.drop_item()

            self.wave_manager.remove_enemy(enemy)

            from src.entities.pokemon import Pokemon
            caught = Pokemon(
                enemy.x, enemy.y,
                enemy.id,
                level=enemy.level,
                is_wild=False,
                shiny=enemy.is_shiny
            )
            caught.current_hp = enemy.current_hp
            caught.max_hp = enemy.max_hp
            caught.ivs = enemy.ivs.copy()
            caught.evs = enemy.evs.copy()
            caught.xp = enemy.xp
            caught.nature = enemy.nature

            is_to_team = self.player.has_team_space()
            if is_to_team:
                self.player.add_to_team(caught)
            else:
                self.player.add_to_box(caught)

            self.player.caught_pokemon.add(enemy.id)
            self.player.register_seen(enemy.id)
            self.player.auto_save()

            self.show_capture_overlay(caught, is_to_team)
            return True

        return False

    @staticmethod
    def use_medicine(pokemon, item_data):
        """Usa poção em um Pokémon aliado"""
        if not pokemon.is_alive() and "revive" not in item_data["id"]:
            return False

        heal_amount = item_data["effect_value"]

        if heal_amount == -1:
            pokemon.heal()
        elif "revive" in item_data["id"]:
            if pokemon.is_alive():
                return False
            if heal_amount == 0.5:
                pokemon.current_hp = int(pokemon.max_hp * 0.5)
            else:
                pokemon.heal()
        else:
            pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + heal_amount)

        return True

    # ===== MÉTODOS DE POSICIONAMENTO =====

    def _on_pokemon_placed(self, placement_data):
        """Callback quando um Pokémon é colocado no mapa OU movido"""
        action = placement_data.get('action', 'place')

        if action == 'swap':
            self._on_pokemon_swap(placement_data)
        elif action == 'move':
            self._move_pokemon_to_spot(placement_data)
        else:
            pokemon = placement_data['pokemon']
            spot = placement_data['spot']
            self.placement_manager.add_pokemon(spot, pokemon)

    def _on_pokemon_swap(self, swap_data):
        """Troca as posições de dois Pokémon"""
        pokemon_a = swap_data['pokemon_a']
        pokemon_b = swap_data['pokemon_b']
        spot_a = swap_data['spot_a']
        spot_b = swap_data['spot_b']

        # Guarda as posições originais
        pos_a_x = pokemon_a.x
        pos_a_y = pokemon_a.y
        tile_a_x = pokemon_a.placed_tile_x
        tile_a_y = pokemon_a.placed_tile_y

        # Move Pokémon A para o spot B
        tile_center_x_b = (
                                      spot_b.x // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2
        tile_center_y_b = (
                                      spot_b.y // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2

        pokemon_a.x = tile_center_x_b
        pokemon_a.y = tile_center_y_b
        pokemon_a.original_spot_x = tile_center_x_b
        pokemon_a.original_spot_y = tile_center_y_b
        pokemon_a.placed_tile_x = tile_center_x_b // self.placement_manager.tile_size
        pokemon_a.placed_tile_y = tile_center_y_b // self.placement_manager.tile_size

        # Move Pokémon B para o spot A
        tile_center_x_a = (
                                      spot_a.x // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2
        tile_center_y_a = (
                                      spot_a.y // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2

        pokemon_b.x = tile_center_x_a
        pokemon_b.y = tile_center_y_a
        pokemon_b.original_spot_x = tile_center_x_a
        pokemon_b.original_spot_y = tile_center_y_a
        pokemon_b.placed_tile_x = tile_center_x_a // self.placement_manager.tile_size
        pokemon_b.placed_tile_y = tile_center_y_a // self.placement_manager.tile_size

        print(f"[SWAP] {pokemon_a.name} ↔ {pokemon_b.name} trocaram de posição!")

    def _move_pokemon_to_spot(self, move_data):
        """Move um Pokémon para um novo spot vazio"""
        pokemon = move_data['pokemon']
        from_spot = move_data.get('from_spot')
        to_spot = move_data['to_spot']

        if from_spot:
            from_spot.occupied = False

        tile_center_x = (
                                    to_spot.x // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2
        tile_center_y = (
                                    to_spot.y // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2

        pokemon.x = tile_center_x
        pokemon.y = tile_center_y
        pokemon.original_spot_x = tile_center_x
        pokemon.original_spot_y = tile_center_y
        pokemon.placed_tile_x = tile_center_x // self.placement_manager.tile_size
        pokemon.placed_tile_y = tile_center_y // self.placement_manager.tile_size

        to_spot.occupied = True
        print(f"[MOVE] {pokemon.name} movido para novo spot ({to_spot.x}, {to_spot.y})")

    def _reset_team_pp(self):
        """Reseta os PP de todos os moves do time do jogador"""
        if not self.player or not self.player.team:
            return

        for pokemon in self.player.team:
            pokemon.reset_pp()

        self.game.player.auto_save()

    # ===== MÉTODOS DE LIMPEZA =====

    def cleanup(self):
        """Limpa o estado da fase antes de sair"""
        self._stop_battle_music(fade_ms=500)

        for spot in self.spot_renderer.get_spots():
            spot.occupied = False

        self.placed_pokemon.clear()
        self.placement_manager.placed_pokemon.clear()

        for pokemon in self.player.team:
            pokemon.is_placed = False

        self.wave_manager.active_enemies.clear()

    # ===== MÉTODOS DE MÚSICA =====

    def _start_battle_music(self):
        """Inicia a música de batalha aleatória"""
        if not self.music_playing:
            if hasattr(settings, 'music_enabled') and settings.music_enabled:
                success = sound_manager.play_random_battle_music()
                if success:
                    self.music_playing = True

    def _stop_battle_music(self, fade_ms=1000):
        """Para a música de batalha"""
        if self.music_playing:
            sound_manager.stop_music(fade_ms)
            self.music_playing = False

    # ===== MÉTODO HANDLE_EVENT (SIMPLIFICADO) =====

    def handle_event(self, event):
        """Processa eventos do jogo"""
        # Cache de referências
        overlay_active = self.overlay_manager.is_active
        drag_manager = self.item_drag_manager
        bag_renderer = self.item_bag_renderer
        team_manager = self.team_manager
        placement_mgr = self.placement_manager
        spot_renderer = self.spot_renderer
        player = self.player
        camera = self.camera
        screen_mgr = self.screen_manager

        # ===== OVERLAYS PRIORITÁRIOS =====
        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            self.evolution_overlay.handle_event(event)
            return None

        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.handle_event(event)
            return None

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.handle_event(event)
            return None

        if overlay_active:
            if self.overlay_manager.handle_event(event):
                return None
            return None

        # ===== DRAG DE ITENS =====
        if drag_manager.is_dragging:
            if event.type == pygame.MOUSEMOTION:
                world_pos = screen_mgr.get_mouse_world_position(event.pos, camera)
                if world_pos:
                    drag_manager.update_drag(
                        event.pos, world_pos,
                        placement_mgr.placed_pokemon,
                        self.wave_manager.active_enemies,
                        camera
                    )
                return None
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                drag_manager.stop_drag(self._on_item_use)
                return None
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                drag_manager.cancel_drag()
                return None

        # ===== ITEM BAG =====
        if bag_renderer and bag_renderer.handle_event(event):
            return None

        # ===== TECLADO =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if hasattr(player, 'bag'):
                    player.bag.cycle_category()
                return None
            elif event.key == pygame.K_F2:
                if not profiler.enabled:
                    profiler.start()
                else:
                    profiler.stop()
                return None
            elif event.key == pygame.K_p:
                self.toggle_pause()
                return None
            elif event.key == pygame.K_ESCAPE:
                self.cleanup()
                self.game.current_scene = self.game.menu_scene
                return None
            elif event.key == pygame.K_F1:
                self.show_debug = not self.show_debug
                return None

        # ===== MOUSE WHEEL =====
        if event.type == pygame.MOUSEWHEEL:
            if bag_renderer and hasattr(bag_renderer, 'mouse_over_ui') and bag_renderer.mouse_over_ui:
                if event.y > 0:
                    player.bag.prev_item()
                elif event.y < 0:
                    player.bag.next_item()
                bag_renderer.hovered_index = player.bag.selected_item_index
                return None
            elif not self.paused and not self.dragging_camera:
                mouse_pos = pygame.mouse.get_pos()
                if screen_mgr.is_mouse_in_viewport(mouse_pos):
                    world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)
                    if world_pos:
                        target_x, target_y = world_pos
                        camera.handle_zoom(event.y > 0)
                        new_world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)
                        if new_world_pos:
                            dx = target_x - new_world_pos[0]
                            dy = target_y - new_world_pos[1]
                            camera.x += dx
                            camera.y += dy
                            camera._clamp_position()
                return None

        # ===== MOUSE BUTTON DOWN =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            # Verifica clique na bag
            if bag_renderer and hasattr(bag_renderer, 'mouse_over_ui') and bag_renderer.mouse_over_ui:
                hovered_index = bag_renderer.hovered_index
                if hovered_index >= 0:
                    items = player.bag.get_items_for_render()
                    if hovered_index < len(items):
                        item = items[hovered_index]
                        player.bag.selected_item_index = hovered_index
                        world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)
                        if world_pos:
                            drag_manager.start_drag(item["id"], mouse_pos, world_pos)
                return None

            # Verifica clique em Pokémon colocado
            if not self.item_drag_manager.is_dragging and not team_manager.is_dragging():
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        clicked_pokemon = placement_mgr.get_pokemon_at_world_pos(
                            world_pos[0], world_pos[1], tolerance=30
                        )
                        if clicked_pokemon:
                            for spot in spot_renderer.get_spots():
                                spot_tile_x = spot.x // placement_mgr.tile_size
                                spot_tile_y = spot.y // placement_mgr.tile_size
                                if (hasattr(clicked_pokemon, 'placed_tile_x') and
                                        spot_tile_x == clicked_pokemon.placed_tile_x and
                                        spot_tile_y == clicked_pokemon.placed_tile_y):
                                    clicked_spot = spot
                                    break

                            if clicked_spot:
                                team_manager.drag_manager.start_drag_placed(
                                    clicked_pokemon,
                                    clicked_spot,
                                    mouse_pos,
                                    world_pos
                                )
                                return None
                            else:
                                if clicked_pokemon.moves:
                                    self.open_move_select_overlay(clicked_pokemon)
                                    return None

        # ===== TEAM MANAGER =====
        if team_manager:
            result = team_manager.handle_event(
                event, spot_renderer.get_spots(), camera,
                self._on_pokemon_placed,
                self._on_pokemon_swap
            )
            if result:
                return None

        # ===== CÂMERA E REMOÇÃO =====
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            in_viewport = screen_mgr.is_mouse_in_viewport(mouse_pos)

            if event.button == 2:
                if in_viewport:
                    self.dragging_camera = True
                    self.last_mouse_pos = mouse_pos
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return None
            elif event.button == 3:
                if not (bag_renderer and hasattr(bag_renderer, 'mouse_over_ui') and bag_renderer.mouse_over_ui):
                    world_pos = screen_mgr.get_mouse_world_position(event.pos, camera)
                    if world_pos:
                        placement_mgr.remove_pokemon_by_right_click(world_pos[0], world_pos[1])
                return None

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2 and self.dragging_camera:
                self.dragging_camera = False
                self.last_mouse_pos = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return None

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_camera and self.last_mouse_pos:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                camera.x -= dx / camera.zoom
                camera.y -= dy / camera.zoom
                camera._clamp_position()
                self.last_mouse_pos = event.pos
                return None

            if self.game_state != "game_over":
                if bag_renderer and hasattr(bag_renderer, 'update_hover'):
                    bag_renderer.update_hover(event.pos)

                mouse_pos = pygame.mouse.get_pos()
                if screen_mgr.is_mouse_in_viewport(mouse_pos):
                    world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)
                    if world_pos:
                        self.hovered_spot = spot_renderer.get_spot_at_world_pos(world_pos[0], world_pos[1])
            return None

        return None

    # ===== MÉTODO FIXED_UPDATE (SIMPLIFICADO) =====

    def fixed_update(self, dt):
        """Update da lógica do jogo"""

        profiler.begin_frame()

        # ===== OVERLAYS =====
        profiler.begin_section("OVERLAYS")

        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            self.evolution_overlay.update(dt)
            profiler.end_section()
            profiler.end_frame()
            return

        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.update(dt)
            profiler.end_section()
            profiler.end_frame()
            return

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.update(dt)
            profiler.end_section()
            profiler.end_frame()
            return

        if self.overlay_manager.is_active:
            self.overlay_manager.update(dt)
            profiler.end_section()
            profiler.end_frame()
            return

        profiler.end_section()

        # ===== PAUSA =====
        if self.game_paused or self.paused:
            profiler.end_frame()
            return

        # ===== ATUALIZAÇÃO NORMAL =====
        wave_mgr = self.wave_manager
        target_mgr = self.target_item_manager
        placement_mgr = self.placement_manager
        spot_renderer = self.spot_renderer
        team_mgr = self.team_manager
        bag_renderer = self.item_bag_renderer
        placed_pokemon = self.placed_pokemon
        screen_mgr = self.screen_manager
        path_renderer = self.path_renderer

        # Battle System
        profiler.begin_section("BATTLE_SYSTEM")
        if hasattr(self, 'battle_system'):
            self.battle_system.update(dt)
        profiler.end_section()

        # Bag Renderer
        profiler.begin_section("BAG_RENDERER_UPDATE")
        if bag_renderer:
            bag_renderer.update(dt)
        profiler.end_section()

        # Team Manager
        profiler.begin_section("TEAM_MANAGER_UPDATE")
        if team_mgr:
            team_mgr.update(dt)
        profiler.end_section()

        # Placement Manager
        profiler.begin_section("PLACEMENT_MANAGER_UPDATE")
        if placement_mgr:
            placement_mgr.update(dt, wave_mgr.active_enemies)
        profiler.end_section()

        # Spot Renderer
        profiler.begin_section("SPOT_RENDERER_UPDATE")
        if spot_renderer:
            spot_renderer.update(dt)
        profiler.end_section()

        # Pokémon Updates
        profiler.begin_section("POKEMON_UPDATES")
        for pokemon in placed_pokemon:
            pokemon.update(dt)
        profiler.end_section()

        # Target Items Update
        profiler.begin_section("TARGET_ITEMS_UPDATE")
        target_mgr.update(dt)
        profiler.end_section()

        # Effect Manager
        if hasattr(self, 'battle_system') and self.battle_system:
            profiler.begin_section("EFFECT_MANAGER")
            self.battle_system.effect_manager.update(dt)
            profiler.end_section()

        # Game Over Check
        if target_mgr.game_over:
            self._stop_battle_music(fade_ms=1000)
            self.game_state = "game_over"
            self.overlay_manager.show(OverlayType.GAME_OVER)
            self._reset_team_pp()
            profiler.end_frame()
            return

        # ===== Wave Manager Update =====
        profiler.begin_section("WAVE_MANAGER_UPDATE")
        enemies_at_end = wave_mgr.update(dt)
        profiler.end_section()

        # ===== TRANSIÇÕES DE ESTADO =====
        if self.game_state == "in_wave":
            # Verifica se a wave está completamente finalizada
            # (sem inimigos vivos E sem waves pendentes)
            if wave_mgr.is_wave_completely_finished():
                if target_mgr.items_protected > 0:
                    print(f"[GAME] Fase COMPLETA! Todos os inimigos foram derrotados!")
                    self.game_state = "completed"
                    self._complete_phase()
                else:
                    print(f"[GAME] GAME OVER! Todos os itens foram roubados!")
                    self.game_state = "game_over"
                    self.overlay_manager.show(OverlayType.GAME_OVER)

        profiler.end_frame()

    def _complete_phase(self):
        """Marca a fase como completada e dá as recompensas"""
        from src.config.progress import progress_manager

        self._stop_battle_music(fade_ms=1000)

        base_reward = self.phase_rewards['money']
        gold_from_defeats = self.wave_manager.get_total_gold_earned()

        total_items = len(self.target_item_manager.items)
        stolen_items = self.target_item_manager.items_stolen

        bonus_amount = 0
        if stolen_items == 0 and total_items > 0:
            bonus_amount = int(gold_from_defeats * 0.3)

        gold_total = base_reward + gold_from_defeats + bonus_amount

        self.player.money += gold_total
        print(f"[REWARD] Ouro adicionado: {gold_total}")

        for pokemon in self.player.team:
            pokemon.gain_xp(self.phase_rewards['experience'])
        self.player.score += self.phase_rewards['experience']

        if total_items > 0:
            protected_items = self.target_item_manager.items_protected
            stars = int((protected_items / total_items) * 3)
            stars = max(1, min(3, stars))
        else:
            stars = 3

        self.phase_complete_data = {
            "base_reward": base_reward,
            "gold_from_defeats": gold_from_defeats,
            "bonus_amount": bonus_amount,
            "gold_total": gold_total,
            "total_xp": self.phase_rewards['experience'],
            "perfect_run": stolen_items == 0 and total_items > 0,
            "stars": stars
        }

        progress_manager.complete_phase(self.phase_id, stars=stars)
        self.player.auto_save()
        self.overlay_manager.show(OverlayType.PHASE_COMPLETE)
        self._reset_team_pp()

    # ===== MÉTODOS DE RENDER =====

    def render(self, screen):
        """Renderiza o jogo"""
        profiler.begin_section("RENDER_CLEAR")
        screen.fill((0, 0, 0))
        profiler.end_section()

        camera = self.camera
        screen_mgr = self.screen_manager
        map_renderer = self.map_renderer
        path_renderer = self.path_renderer
        spot_renderer = self.spot_renderer
        target_mgr = self.target_item_manager
        wave_mgr = self.wave_manager
        placement_mgr = self.placement_manager
        bag_renderer = self.item_bag_renderer
        team_mgr = self.team_manager
        drag_mgr = self.item_drag_manager
        overlay_mgr = self.overlay_manager
        show_debug = self.show_debug

        # Mapa
        profiler.begin_section("RENDER_MAP")
        map_renderer.render(screen, camera, screen_mgr)
        profiler.end_section()

        # Paths (apenas debug)
        if show_debug:
            profiler.begin_section("RENDER_PATHS")
            path_renderer.render(screen, camera, screen_mgr, show_editing=False)
            profiler.end_section()

        # Spots
        profiler.begin_section("RENDER_SPOTS")
        if spot_renderer:
            spot_renderer.render(
                screen, camera, screen_mgr,
                show_editing=False,
                highlight_spot=self.hovered_spot if hasattr(self, 'hovered_spot') else None
            )
        profiler.end_section()

        # Target items (ground)
        profiler.begin_section("RENDER_TARGET_ITEMS_GROUND")
        target_mgr.render_in_ground(screen, camera)
        profiler.end_section()

        # Inimigos
        profiler.begin_section("RENDER_ENEMIES")
        for enemy in wave_mgr.active_enemies:
            enemy.render(screen, camera, show_hp=False)
        profiler.end_section()

        # Pokémon colocados
        profiler.begin_section("RENDER_PLACED_POKEMON")
        if placement_mgr:
            placement_mgr.render(screen, camera, screen_mgr)
        profiler.end_section()

        # Projéteis
        profiler.begin_section("RENDER_PROJECTILES")
        if hasattr(self, 'battle_system'):
            self.battle_system.render_projectiles(screen, camera, self.screen_manager)
        profiler.end_section()

        # Target items (on pokemon)
        profiler.begin_section("RENDER_TARGET_ITEMS_POKEMON")
        target_mgr.render_in_pokemon(screen, camera)
        profiler.end_section()

        # HP Bars - Inimigos
        profiler.begin_section("RENDER_ENEMY_HP")
        for enemy in wave_mgr.active_enemies:
            enemy.render_hp_enemy(screen, camera)
        profiler.end_section()

        # HP Bars - Pokémon
        profiler.begin_section("RENDER_POKEMON_HP")
        if placement_mgr:
            placement_mgr.render_hp(screen, camera)
        profiler.end_section()

        # UI do jogo
        profiler.begin_section("RENDER_GAME_UI")
        self._render_game_ui(screen)
        profiler.end_section()

        # Team Manager UI
        profiler.begin_section("RENDER_TEAM_MANAGER")
        if team_mgr:
            team_mgr.render(screen, camera, spot_renderer.get_spots() if spot_renderer else [])
        profiler.end_section()

        # Drag Manager
        profiler.begin_section("RENDER_DRAG_MANAGER")
        if drag_mgr:
            drag_mgr.render(screen, camera)
        profiler.end_section()

        # Item Bag
        profiler.begin_section("RENDER_ITEM_BAG")
        if bag_renderer:
            bag_renderer.render(screen)
        profiler.end_section()

        # Borda da viewport
        profiler.begin_section("RENDER_VIEWPORT_BORDER")
        pygame.draw.rect(screen, (80, 80, 80),
                         (screen_mgr.viewport_x, screen_mgr.viewport_y,
                          screen_mgr.viewport_width, screen_mgr.viewport_height), 1)
        profiler.end_section()

        # Pause overlay
        if self.paused and not self.game_paused:
            profiler.begin_section("RENDER_PAUSE_OVERLAY")
            self._render_pause_overlay(screen)
            profiler.end_section()

        # Overlay Manager
        profiler.begin_section("RENDER_OVERLAY_MANAGER")
        if overlay_mgr:
            overlay_mgr.render(screen)
        profiler.end_section()

        # Move Learn Overlay
        if self.move_learn_overlay and self.move_learn_overlay.active:
            profiler.begin_section("RENDER_MOVE_LEARN")
            self.move_learn_overlay.render(screen)
            profiler.end_section()

        # Move Select Overlay
        if self.move_select_overlay and self.move_select_overlay.active:
            profiler.begin_section("RENDER_MOVE_SELECT")
            self.move_select_overlay.render(screen)
            profiler.end_section()

        # Evolution Overlay
        if hasattr(self, 'evolution_overlay') and self.evolution_overlay and self.evolution_overlay.active:
            profiler.begin_section("RENDER_EVOLUTION")
            self.evolution_overlay.render(screen)
            profiler.end_section()

        # Debug Info
        if show_debug:
            profiler.begin_section("RENDER_DEBUG")
            self._render_debug_info(screen)
            profiler.end_section()

    def _render_game_ui(self, screen):
        """Renderiza a UI do jogo"""
        font = self._get_ui_font(24)
        font_small = self._get_ui_font(18)

        wave_info = self.wave_manager.get_current_wave_info()
        target_mgr = self.target_item_manager
        screen_mgr = self.screen_manager
        wave_mgr = self.wave_manager

        viewport_x = screen_mgr.viewport_x
        viewport_y = screen_mgr.viewport_y

        ui_bg = pygame.Surface((400, 150))
        ui_bg.set_alpha(180)
        ui_bg.fill((20, 20, 30))
        screen.blit(ui_bg, (viewport_x + 10, viewport_y + 10))

        y_offset = viewport_y + 15

        phase_text = font.render(self.phase_info.get("name", f"Fase {self.phase_number}"), True, (255, 215, 0))
        screen.blit(phase_text, (viewport_x + 15, y_offset))
        y_offset += 25

        items_color = (100, 255, 100) if target_mgr.items_protected > 0 else (255, 100, 100)
        items_text = font_small.render(
            f"Itens: {target_mgr.items_protected} protegidos | {target_mgr.items_stolen} levados",
            True, items_color
        )
        screen.blit(items_text, (viewport_x + 15, y_offset))
        y_offset += 20

        if self.game_state == "waiting":
            state_text = font_small.render("Aguardando início...", True, (200, 200, 200))
            screen.blit(state_text, (viewport_x + 15, y_offset))

        elif self.game_state == "in_wave":
            active_paths = wave_info.get('active_paths', 0)
            if active_paths > 1:
                wave_text = font_small.render(
                    f"{active_paths} paths ativos | {wave_info['name']}",
                    True, (100, 255, 100))
            else:
                wave_text = font_small.render(
                    f"Wave {wave_info['index']}/{wave_info['total']}: {wave_info['name']}",
                    True, (100, 255, 100))
            screen.blit(wave_text, (viewport_x + 15, y_offset))
            y_offset += 20

            bar_x = viewport_x + 15
            bar_y = y_offset
            bar_width = 370
            bar_height = 15

            pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_width, bar_height))
            progress_width = int(bar_width * wave_info['progress'])
            pygame.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, progress_width, bar_height))
            pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)

            progress_text = font_small.render(
                f"{wave_info['enemies_spawned']}/{wave_info['enemies_total']}",
                True, (255, 255, 255))
            text_x = bar_x + (bar_width - progress_text.get_width()) // 2
            screen.blit(progress_text, (text_x, bar_y + 2))

            y_offset += 25

            enemies_color = (255, 100, 100) if wave_mgr.active_enemies else (100, 255, 100)
            enemies_text = font_small.render(
                f"Inimigos vivos: {len(wave_mgr.active_enemies)}",
                True, enemies_color)
            screen.blit(enemies_text, (viewport_x + 15, y_offset))

        elif self.game_state == "completed":
            complete_text = font.render("FASE COMPLETA!", True, (255, 215, 0))
            screen.blit(complete_text, (viewport_x + 15, y_offset))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa do jogo"""
        screen_mgr = self.screen_manager

        overlay = pygame.Surface((screen_mgr.viewport_width, screen_mgr.viewport_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (screen_mgr.viewport_x, screen_mgr.viewport_y))

        font_large = pygame.font.Font(None, 48)
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = screen_mgr.viewport_x + (screen_mgr.viewport_width - pause_text.get_width()) // 2
        text_y = screen_mgr.viewport_y + (screen_mgr.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

        font_small = pygame.font.Font(None, 24)
        phase_display = self.phase_info.get("name", f"Fase {self.phase_number}")
        phase_text = font_small.render(phase_display, True, (200, 200, 200))
        phase_x = screen_mgr.viewport_x + (screen_mgr.viewport_width - phase_text.get_width()) // 2
        phase_y = text_y + pause_text.get_height() + 10
        screen.blit(phase_text, (phase_x, phase_y))

    def _render_debug_info(self, screen):
        """Informações de debug"""
        mouse_pos = pygame.mouse.get_pos()
        screen_mgr = self.screen_manager
        camera = self.camera

        in_viewport = screen_mgr.is_mouse_in_viewport(mouse_pos)

        if in_viewport:
            world_pos = screen_mgr.get_mouse_world_position(mouse_pos, camera)
            if world_pos:
                world_text = f"World: ({world_pos[0]:.0f}, {world_pos[1]:.0f})"
                tile_x = int(world_pos[0] // 16)
                tile_y = int(world_pos[1] // 16)
                tile_info = f"Tile: ({tile_x}, {tile_y})"

                path_info = "Nenhum path"
                for i, path in enumerate(self.path_renderer.paths):
                    for node in path.nodes:
                        dx = node[0] - world_pos[0]
                        dy = node[1] - world_pos[1]
                        if dx * dx + dy * dy < 400:
                            path_info = f"Próximo ao Path {i + 1}"
                            break
            else:
                world_text = "World: invalid position"
                tile_info = "Tile: N/A"
                path_info = "N/A"
        else:
            world_text = "World: outside viewport"
            tile_info = "Tile: outside"
            path_info = "N/A"

        wave_info = self.wave_manager.get_current_wave_info()

        debug_lines = [
            "=== DEBUG INFO ===",
            f"FPS: {screen_mgr.get_fps():.1f}",
            f"Game State: {self.game_state}",
            "",
            "=== WAVES ===",
            f"Status: {wave_info['name']}",
            f"Progresso: {wave_info['progress'] * 100:.1f}%",
            f"Vivos: {len(self.wave_manager.active_enemies)}",
            "",
            "=== CAMERA ===",
            f"Position: ({camera.x:.0f}, {camera.y:.0f})",
            f"Zoom: {camera.zoom:.2f}",
            "",
            "=== MOUSE ===",
            world_text,
            tile_info,
            path_info,
            "",
            "=== MAPA ===",
            f"Pixels: {self.world_width}x{self.world_height}",
            f"Paths: {len(self.path_renderer.paths)}",
            f"Pokémon: {len(self.placement_manager.placed_pokemon)}",
            f"Spots: {sum(1 for s in self.spot_renderer.get_spots() if s.occupied)}/{len(self.spot_renderer.get_spots())}",
        ]

        y_offset = screen_mgr.viewport_y + 40
        x_offset = screen_mgr.viewport_x + 10
        line_height = 16
        bg_height = len(debug_lines) * line_height + 10
        bg_width = 350
        bg_surface = pygame.Surface((bg_width, bg_height))
        bg_surface.set_alpha(200)
        bg_surface.fill((0, 0, 0))
        screen.blit(bg_surface, (x_offset - 5, y_offset - 5))

        for line in debug_lines:
            if line.startswith("==="):
                text = self._debug_font_bold.render(line, True, (255, 255, 0))
            else:
                text = self._debug_font.render(line, True, (0, 255, 0))
            screen.blit(text, (x_offset, y_offset))
            y_offset += line_height