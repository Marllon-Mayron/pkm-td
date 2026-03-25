# src/scenes/game_scene.py
"""
Cena principal do jogo - OTIMIZADA
"""
import pygame

from src.battle.battle_system import BattleSystem
from src.config.paths import PROJECT_ROOT
from src.config.settings import settings
from src.scenes.base_scene import BaseScene
from src.config.phase_catalog import phase_catalog
from src.scenes.game_scene.components.managers.overlay_manager import OverlayType, OverlayManager
from src.scenes.game_scene.components.managers.placement_manager import PlacementManager
from src.scenes.game_scene.components.managers.item_drag_manager import ItemDragManager
from src.scenes.game_scene.components.managers.target_item_manager import TargetItemManager
from src.scenes.game_scene.components.managers.team_manager import GameTeamManager
from src.scenes.game_scene.components.overlays.move_select_overlay import MoveSelectOverlay
from src.scenes.game_scene.components.phase_loader import phase_loader
from src.scenes.game_scene.components.renderer.item_bag_renderer import ItemBagRenderer
from src.scenes.game_scene.components.renderer.map_renderer import MapRenderer
from src.scenes.game_scene.components.renderer.path_renderer import PathRenderer
from src.scenes.game_scene.components.renderer.pokemon_spot_renderer import PokemonSpotRenderer
from src.scenes.game_scene.components.managers.wave_manager import GameWaveManager
from src.scenes.game_scene.components.renderer.target_item_renderer import TargetItemRenderer


class GameScene(BaseScene):
    def __init__(self, game, chapter_id=1, phase_number=1):
        super().__init__(game)

        # Flag de debug
        self.debug_in_game = False
        self.move_select_overlay = None
        self.move_learn_overlay = None
        self.game_paused = False  # Flag para pausar o jogo


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
        self.team_manager = GameTeamManager(game)
        self.placement_manager = PlacementManager(self)
        self.target_item_manager = TargetItemManager(game)
        self.target_item_renderer = TargetItemRenderer()

        # CARREGA OS DADOS DA FASE
        self._load_phase_data()

        # Cria o overlay_manager
        self.overlay_manager = OverlayManager(self)

        # Cria o wave_manager
        self.wave_manager = GameWaveManager(phase_loader)

        self.battle_system = BattleSystem(self)

        # Vincula os itens alvo
        self.wave_manager.set_target_items(self.target_item_manager.items)
        self.wave_manager.game_scene = self

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
        # Configura battle_system para Pokémon já colocados
        for pokemon in self.placement_manager.placed_pokemon:
            pokemon.set_battle_system(self.battle_system)

        # Configura para inimigos que já possam existir
        for enemy in self.wave_manager.active_enemies:
            enemy.set_battle_system(self.battle_system)

        # Configura para Pokémon no time (por precaução)
        for pokemon in self.player.team:
            pokemon.set_battle_system(self.battle_system)
            pokemon.reset_pp()
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

    def open_move_select_overlay(self, pokemon):
        """Abre o overlay de seleção de moves para um Pokémon"""
        if not pokemon or not pokemon.moves:
            return

        self.move_select_overlay = MoveSelectOverlay(self, pokemon)
        self.move_select_overlay.active = True

        # Pausa o jogo
        self.game_paused = True
        self.paused = True  # Usa o pause existente

        # Trava as waves
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

    def close_move_select_overlay(self):
        """Fecha o overlay de seleção de moves"""
        # Se ainda existe overlay, marca como inativo
        if self.move_select_overlay:
            self.move_select_overlay.active = False
            self.move_select_overlay = None

        # Despausa o jogo
        self.game_paused = False
        self.paused = False

        # Destrava as waves
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

        # Garante que a câmera está restaurada (caso o overlay não tenha feito)
        if hasattr(self, 'camera'):
            # A câmera já foi restaurada pelo overlay, mas garantimos
            pass

        print("[MOVE_SELECT] Overlay fechado, jogo despausado")

    def open_move_learn_overlay(self, pokemon, new_move_name):
        """Abre o overlay de aprendizado de novo move"""
        from src.scenes.game_scene.components.overlays.move_learn_overlay import MoveLearnOverlay

        self.move_learn_overlay = MoveLearnOverlay(self, pokemon, new_move_name)
        self.move_learn_overlay.active = True

        # Pausa o jogo
        self.game_paused = True
        self.paused = True

        # Trava as waves
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

        print(f"[MOVE_LEARN] Abrindo overlay para {pokemon.name} aprender {new_move_name}")

    def close_move_learn_overlay(self, cancel=False):
        """Fecha o overlay de aprendizado de moves"""
        if self.move_learn_overlay:
            self.move_learn_overlay.active = False
            self.move_learn_overlay = None

        # Despausa o jogo
        self.game_paused = False
        self.paused = False

        # Destrava as waves
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

        print("[MOVE_LEARN] Overlay fechado, jogo despausado")

    def _setup_world_dimensions(self):
        """Configura dimensões do mundo baseado no mapa"""
        map_width, map_height = self.map_renderer.get_dimensions()
        if map_width > 0 and map_height > 0:
            self.world_width = map_width
            self.world_height = map_height
        else:
            self.world_width = 2000
            self.world_height = 2000

    def _on_item_use(self, target, item_data, target_type):
        """Callback quando um item é usado em um alvo"""
        effect = item_data.get("effect", "")
        category = item_data.get("category", "")

        # PP RESTORE ITEMS (restaura TODOS os moves)
        if effect == "pp_restore":
            if target_type == "ally" and hasattr(target, 'restore_pp'):
                percentage = item_data.get("effect_value", 1.0)

                # Restaura TODOS os moves com a porcentagem
                restored = target.restore_pp(percentage=percentage)

                if restored > 0:
                    item_name = item_data["name"]
                    print(f"[ITEM] {item_name} usado em {target.name}! "
                          f"{restored} PP restaurados!")
                    return True
                else:
                    print(f"[ITEM] {target.name} já está com PP máximo!")
                    return False

            return False

        # EVOLUTION STONES
        elif effect == "evolution":
            if target_type == "ally":
                return self._use_evolution_stone(target, item_data)

        # POKEBALLS
        elif target_type == "enemy" and category == "pokeball":
            return self._attempt_capture(target, item_data)

        # MEDICINE (HP)
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
            caught = Pokemon(0, 0, enemy.id, level=enemy.level, is_wild=False, shiny=enemy.is_shiny)
            caught.current_hp = enemy.current_hp
            caught.max_hp = enemy.max_hp
            caught.ivs = enemy.ivs.copy()
            caught.evs = enemy.evs.copy()
            caught.xp = enemy.xp
            caught.nature = enemy.nature

            if self.player.has_team_space():
                self.player.add_to_team(caught)
            else:
                self.player.add_to_box(caught)

            self.player.caught_pokemon.add(enemy.id)
            self.player.register_seen(enemy.id)
            self.player.auto_save()

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

    def _on_pokemon_placed(self, placement_data):
        """Callback quando um Pokémon é colocado no mapa"""
        pokemon = placement_data['pokemon']
        spot = placement_data['spot']
        self.placement_manager.add_pokemon(spot, pokemon)

    def _reset_team_pp(self):
        """Reseta os PP de todos os moves do time do jogador"""
        if not self.player or not self.player.team:
            return

        total_reset = 0
        for pokemon in self.player.team:
            total_reset += pokemon.reset_pp()

        self.game.player.auto_save()

    def cleanup(self):
        """Limpa o estado da fase antes de sair"""
        # Para a música ao sair da fase
        self._stop_battle_music(fade_ms=500)

        for spot in self.spot_renderer.get_spots():
            spot.occupied = False

        self.placed_pokemon.clear()
        self.placement_manager.placed_pokemon.clear()

        for pokemon in self.player.team:
            pokemon.is_placed = False

        self.wave_manager.active_enemies.clear()

    def handle_event(self, event):
        """Processa eventos do jogo - OTIMIZADO"""
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

        # ===== NOVO: Processa overlay de aprendizado de moves primeiro =====
        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.handle_event(event)
            return None

        # ===== Processa overlay de seleção de moves =====
        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.handle_event(event)
            return None

        if overlay_active:
            if self.overlay_manager.handle_event(event):
                return None
            return None

        # Drag manager
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

        # Item bag
        if bag_renderer and bag_renderer.handle_event(event):
            return None

        # Teclado
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if hasattr(player, 'bag'):
                    player.bag.cycle_category()
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
            elif event.key == pygame.K_SPACE:
                if self.game_state == "between_waves":
                    self.game_state = "in_wave"
                    self.wave_manager.start_next_wave()
                return None

        # Mouse wheel
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

        # Mouse button down
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
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

            # Clique em Pokémon para abrir overlay de moves
            if not self.item_drag_manager.is_dragging and not self.team_manager.is_dragging():
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        # Verifica se clicou em algum Pokémon colocado
                        clicked_pokemon = self.placement_manager.get_pokemon_at_world_pos(
                            world_pos[0], world_pos[1], tolerance=30
                        )
                        if clicked_pokemon and clicked_pokemon.moves:
                            # Abre overlay de seleção de moves
                            self.open_move_select_overlay(clicked_pokemon)
                            return None

        # Team manager
        if team_manager:
            result = team_manager.handle_event(
                event, spot_renderer.get_spots(), camera, self._on_pokemon_placed
            )
            if result:
                return None

        # Mouse buttons
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

    def fixed_update(self, dt):
        """Update da lógica do jogo - OTIMIZADO"""
        # ===== Processa overlay de aprendizado de moves =====
        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.update(dt)
            return

        if hasattr(self, 'battle_system'):
            self.battle_system.update(dt)

        # ===== Processa overlay de seleção de moves =====
        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.update(dt)
            return

        # Se o jogo está pausado por outro motivo
        if self.game_paused:
            return

        if self.paused:
            return

        if self.overlay_manager.is_active:
            self.overlay_manager.update(dt)
            return

        # Cache de referências locais para acesso mais rápido
        wave_mgr = self.wave_manager
        target_mgr = self.target_item_manager
        placement_mgr = self.placement_manager
        spot_renderer = self.spot_renderer
        team_mgr = self.team_manager
        bag_renderer = self.item_bag_renderer
        placed_pokemon = self.placed_pokemon
        screen_mgr = self.screen_manager
        path_renderer = self.path_renderer

        # Updates
        if bag_renderer:
            bag_renderer.update(dt)

        if team_mgr:
            team_mgr.update(dt)

        if placement_mgr:
            placement_mgr.update(dt, wave_mgr.active_enemies)

        if spot_renderer:
            spot_renderer.update(dt)

        for pokemon in placed_pokemon:
            pokemon.update(dt)

        target_mgr.update(dt)

        # Game over check
        if target_mgr.game_over:
            # ===== PARAR MÚSICA AO GAME OVER =====
            self._stop_battle_music(fade_ms=1000)
            self.game_state = "game_over"
            self.overlay_manager.show(OverlayType.GAME_OVER)
            # ===== RESETAR PP DOS MOVES DO TIME DO JOGADOR =====
            self._reset_team_pp()
            return

        # Build path points cache
        path_points_by_index = {}
        for i, path in enumerate(path_renderer.paths):
            path_points = path_renderer.get_path_points(i)
            if path_points:
                path_points_by_index[i] = path_points

        # Update wave manager
        enemies_at_end = wave_mgr.update(dt, path_points_by_index, screen_mgr)

        # Clean up enemies at end
        for enemy in enemies_at_end:
            if enemy.is_carrying:
                enemy.is_carrying.is_protected = False
                enemy.clear_carrying()

        # State transitions
        if self.game_state == "in_wave":
            if wave_mgr.is_wave_completely_finished():
                if target_mgr.items_protected > 0:
                    self.game_state = "completed"
                    self._complete_phase()
                else:
                    self.game_state = "game_over"
                    self.overlay_manager.show(OverlayType.GAME_OVER)

        elif self.game_state == "between_waves":
            self.between_waves_timer -= dt
            if self.between_waves_timer <= 0:
                any_wave_started = False
                for path_idx in wave_mgr.path_waves.keys():
                    if wave_mgr.current_wave_index_by_path.get(path_idx, 0) < len(wave_mgr.path_waves[path_idx]):
                        wave_mgr._start_wave_for_path(path_idx)
                        any_wave_started = True

                if any_wave_started:
                    self.game_state = "in_wave"

    def _start_battle_music(self):
        """Inicia a música de batalha aleatória"""
        if not self.music_playing:
            from src.managers.sound_manager import sound_manager
            # Verifica se o som está habilitado
            if hasattr(settings, 'music_enabled') and settings.music_enabled:
                success = sound_manager.play_random_battle_music()
                if success:
                    self.music_playing = True
                    print(f"[MUSIC] Música de batalha iniciada para fase {self.phase_id}")
                else:
                    print(f"[MUSIC] Falha ao iniciar música de batalha")
            else:
                print(f"[MUSIC] Música desabilitada nas configurações")

    def _stop_battle_music(self, fade_ms=1000):
        """Para a música de batalha"""
        if self.music_playing:
            from src.managers.sound_manager import sound_manager
            sound_manager.stop_music(fade_ms)
            self.music_playing = False
            print(f"[MUSIC] Música de batalha parada")

    def render(self, screen):
        """Renderiza o jogo - OTIMIZADO"""
        screen.fill((0, 0, 0))

        # Cache de referências
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

        # Mundo do jogo
        map_renderer.render(screen, camera, screen_mgr)

        if show_debug:
            path_renderer.render(screen, camera, screen_mgr, show_editing=False)

        if spot_renderer:
            spot_renderer.render(
                screen, camera, screen_mgr,
                show_editing=False,
                highlight_spot=self.hovered_spot if hasattr(self, 'hovered_spot') else None
            )

        target_mgr.render_in_ground(screen, camera)

        # Inimigos
        for enemy in wave_mgr.active_enemies:
            enemy.render(screen, camera, show_hp=False)


        if placement_mgr:
            placement_mgr.render(screen, camera, screen_mgr)

        if hasattr(self, 'battle_system'):
            self.battle_system.render_projectiles(screen, camera, self.screen_manager)

        target_mgr.render_in_pokemon(screen, camera)

        # HP bars
        for enemy in wave_mgr.active_enemies:
            enemy.render_hp(screen, camera)

        if placement_mgr:
            placement_mgr.render_hp(screen, camera)

        # UI
        self._render_game_ui(screen)

        if team_mgr:
            team_mgr.render(screen, camera, spot_renderer.get_spots() if spot_renderer else [])

        if drag_mgr:
            drag_mgr.render(screen, camera)

        if bag_renderer:
            bag_renderer.render(screen)

        # Borda da viewport
        pygame.draw.rect(screen, (80, 80, 80),
                         (screen_mgr.viewport_x, screen_mgr.viewport_y,
                          screen_mgr.viewport_width, screen_mgr.viewport_height), 1)

        if self.paused and not self.game_paused:  # Não mostra pause overlay se estiver em overlays
            self._render_pause_overlay(screen)

        if overlay_mgr:
            overlay_mgr.render(screen)

        # ===== Renderiza overlay de aprendizado de moves por cima de tudo =====
        if self.move_learn_overlay and self.move_learn_overlay.active:
            self.move_learn_overlay.render(screen)

        # ===== Renderiza overlay de seleção de moves =====
        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.render(screen)

        if show_debug:
            self._render_debug_info(screen)

    def _complete_phase(self):
        """Marca a fase como completada e dá as recompensas"""
        from src.config.progress import progress_manager

        # Para a música ao completar a fase
        self._stop_battle_music(fade_ms=1000)

        # ===== CALCULAR RECOMPENSAS =====
        base_reward = self.phase_rewards['money']  # Ex: 100
        gold_from_defeats = self.wave_manager.get_total_gold_earned()  # Ex: 55

        # Verificar se nenhum item foi roubado
        total_items = len(self.target_item_manager.items)
        stolen_items = self.target_item_manager.items_stolen

        bonus_multiplier = 1.0
        bonus_amount = 0

        if stolen_items == 0 and total_items > 0:
            bonus_multiplier = 1.3
            bonus_amount = int(gold_from_defeats * 0.3)  # Ex: 16 (30% de 55)
            print(f"[BONUS] Nenhum item roubado! +30% de bônus em ouro! +{bonus_amount}")

        # Calcular ouro total
        gold_total = base_reward + gold_from_defeats + bonus_amount  # Ex: 100 + 55 + 16 = 171

        # ===== APLICAR RECOMPENSAS APENAS AGORA =====
        self.player.money += gold_total
        print(
            f"[REWARD] Ouro adicionado: {gold_total} (Fase: {base_reward} + Derrotas: {gold_from_defeats} + Bônus: {bonus_amount})")
        print(f"[REWARD] Total de ouro do jogador agora: {self.player.money}")

        # Distribuir XP
        for pokemon in self.player.team:
            pokemon.gain_xp(self.phase_rewards['experience'])
        self.player.score += self.phase_rewards['experience']

        # Calcular estrelas
        if total_items > 0:
            protected_items = self.target_item_manager.items_protected
            stars = int((protected_items / total_items) * 3)
            stars = max(1, min(3, stars))
        else:
            stars = 3

        # Salvar dados para o overlay
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

    def _render_game_ui(self, screen):
        """Renderiza a UI do jogo - OTIMIZADO"""
        font = self._get_ui_font(24)
        font_small = self._get_ui_font(18)

        wave_info = self.wave_manager.get_current_wave_info()
        target_mgr = self.target_item_manager
        screen_mgr = self.screen_manager
        wave_mgr = self.wave_manager

        viewport_x = screen_mgr.viewport_x
        viewport_y = screen_mgr.viewport_y

        # Fundo semi-transparente
        ui_bg = pygame.Surface((400, 150))
        ui_bg.set_alpha(180)
        ui_bg.fill((20, 20, 30))
        screen.blit(ui_bg, (viewport_x + 10, viewport_y + 10))

        y_offset = viewport_y + 15

        # Título da fase
        phase_text = font.render(self.phase_info.get("name", f"Fase {self.phase_number}"), True, (255, 215, 0))
        screen.blit(phase_text, (viewport_x + 15, y_offset))
        y_offset += 25

        # Itens alvo
        items_color = (100, 255, 100) if target_mgr.items_protected > 0 else (255, 100, 100)
        items_text = font_small.render(
            f"Itens: {target_mgr.items_protected} protegidos | {target_mgr.items_stolen} levados",
            True, items_color
        )
        screen.blit(items_text, (viewport_x + 15, y_offset))
        y_offset += 20

        # Wave info
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

            # Barra de progresso
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

        elif self.game_state == "between_waves":
            wave_text = font_small.render(
                f"Wave concluída! Próxima em {self.between_waves_timer:.1f}s",
                True, (255, 255, 0))
            screen.blit(wave_text, (viewport_x + 15, y_offset))

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
        """Informações de debug - CORRIGIDO"""
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

                # CORREÇÃO: usa get_tile corretamente
                tile_id = 0
                for layer in self.map_renderer.layer_manager.layers:
                    if hasattr(layer, 'layer_type') and layer.layer_type == "ground":
                        tile_id = layer.get_tile(tile_x, tile_y)
                        break
                tile_value = f"Tile ID: {tile_id}"

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
                tile_value = "Tile ID: N/A"
                path_info = "N/A"
        else:
            world_text = "World: outside viewport"
            tile_info = "Tile: outside"
            tile_value = "Tile ID: N/A"
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
            tile_value,
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