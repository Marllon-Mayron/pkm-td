# src/scenes/game_scene.py (versão final otimizada - sem grid)

"""
Cena principal do jogo - Carrega fases reais com waves
"""
import pygame
from src.config.paths import PROJECT_ROOT
from src.scenes.base_scene import BaseScene
from src.config.phase_catalog import phase_catalog
from src.scenes.game_scene.components.managers.overlay_manager import OverlayType, OverlayManager
from src.scenes.game_scene.components.managers.placement_manager import PlacementManager
from src.scenes.game_scene.components.managers.item_drag_manager import ItemDragManager
from src.scenes.game_scene.components.managers.target_item_manager import TargetItemManager
from src.scenes.game_scene.components.managers.team_manager import GameTeamManager
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

        # Flag de debug (False para produção)
        self.debug_in_game = False

        self.chapter_id = chapter_id
        self.phase_number = phase_number
        self.phase_id = f"{chapter_id}-{phase_number}"
        self.phase_info = None

        # Carrega informações da fase do catálogo
        self._load_phase_info()

        # Componentes da fase
        self.map_renderer = MapRenderer()
        self.path_renderer = PathRenderer()
        self.spot_renderer = PokemonSpotRenderer()

        # Cria os gerenciadores básicos
        self.team_manager = GameTeamManager(game)
        self.placement_manager = PlacementManager(self)
        self.target_item_manager = TargetItemManager(game)
        self.target_item_renderer = TargetItemRenderer()

        # CARREGA OS DADOS DA FASE PRIMEIRO
        self._load_phase_data()

        # SÓ DEPOIS de carregar os dados, cria o overlay_manager
        self.overlay_manager = OverlayManager(self)

        # cria o wave_manager, depois de carregar os dados
        self.wave_manager = GameWaveManager(phase_loader)

        # Vincula os itens alvo ao wave_manager
        self.wave_manager.set_target_items(self.target_item_manager.items)
        self.wave_manager.game_scene = self

        # Configurações de mundo baseadas no mapa
        self._setup_world_dimensions()

        self.player = game.player

        # Renderizador da mochila
        self.item_bag_renderer = ItemBagRenderer(game, self.player.bag)

        # Gerenciador de arrasto de itens
        self.item_drag_manager = ItemDragManager(game, self.player.bag)

        # Inicializa câmera
        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera
        self.camera.set_limits(
            -500, self.world_width + 500,
            -500, self.world_height + 500
        )

        # Posiciona câmera no centro do mapa
        self.camera.x = self.world_width / 2
        self.camera.y = self.world_height / 2

        # Spot atualmente sob o mouse
        self.hovered_spot = None

        # Lista de Pokémon colocados no mapa
        self.placed_pokemon = []

        # Estado do jogo
        self.game_state = "waiting"
        self.between_waves_timer = 3.0

        # Debug
        self.show_debug = False

        # Fontes cacheadas para debug
        self._debug_font = pygame.font.Font(None, 18)
        self._debug_font_bold = pygame.font.Font(None, 20)
        self._debug_font_small = pygame.font.Font(None, 16)

        # Controle de arrasto da câmera
        self.dragging_camera = False
        self.last_mouse_pos = None

        # Inicia automaticamente a primeira wave
        self._start_game()

        if self.debug_in_game:
            print(f"\n=== FASE CARREGADA ===")
            print(f"Fase: {self.phase_info.get('name', 'Desconhecida')}")
            print(f"Capítulo: {self.chapter_id}")
            print(f"Número: {self.phase_number}")
            print(f"ID: {self.phase_id}")
            print(f"Waves: {len(self.wave_manager.waves_data)}")
            print(f"Itens alvo: {len(self.target_item_manager.items)}")
            print(f"Recompensas: ${self.phase_rewards['money']} | {self.phase_rewards['experience']} XP")
            print(f"Mundo: {self.world_width}x{self.world_height}")
            print("=====================\n")

    def _start_game(self):
        """Inicia o jogo"""
        if self.wave_manager.has_more_waves():
            self.game_state = "in_wave"
            self.wave_manager.start_all_waves()
        elif self.debug_in_game:
            print("Fase não tem waves configuradas!")

    def _load_phase_info(self):
        """Carrega informações da fase do catálogo"""
        self.phase_info = phase_catalog.get_phase_info(self.chapter_id, self.phase_number)

        if not self.phase_info:
            self.phase_info = {
                "name": f"Fase {self.chapter_id}-{self.phase_number}",
                "number": self.phase_number,
                "chapter": self.chapter_id
            }
            if self.debug_in_game:
                print(f"Fase {self.phase_id} não encontrada no catálogo, usando fallback")

    def _load_phase_data(self):
        """Carrega os dados da fase do disco"""
        if self.debug_in_game:
            print(f"\n=== CARREGANDO DADOS DA FASE {self.chapter_id}-{self.phase_number} ===")

        data = phase_loader.load_phase(self.chapter_id, self.phase_number)

        if not data:
            if self.debug_in_game:
                print(f"ERRO: Não foi possível carregar a fase {self.phase_id}")
            self.phase_rewards = {"money": 0, "experience": 0}
            return

        base_path = PROJECT_ROOT

        # Carrega mapa
        map_data = phase_loader.get_map_data()
        self.map_renderer.load_from_data(map_data, base_path)

        # Carrega paths
        paths_data = phase_loader.get_paths_data()
        self.path_renderer.load_from_data(paths_data)

        # Carrega spots
        spot_data = phase_loader.get_tower_spots_data()
        self.spot_renderer.load_from_data(spot_data)

        # Carrega itens alvo
        items_data = data.get("target_items", {})
        self.target_item_manager.load_from_data(items_data)

        # Carrega recompensas
        rewards = data.get("rewards", {})
        self.phase_rewards = {
            "money": rewards.get("money", 0),
            "experience": rewards.get("experience", 0)
        }

        if self.debug_in_game:
            print(f"✓ Recompensas carregadas: ${self.phase_rewards['money']} | {self.phase_rewards['experience']} XP")
            print("=== DADOS CARREGADOS COM SUCESSO ===\n")

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
        if self.debug_in_game:
            print(f"[USO] Usando {item_data['name']} em {getattr(target, 'name', 'alvo')}")

        if item_data["effect"] == "evolution":
            if target_type == "ally":
                return self._use_evolution_stone(target, item_data)
            return False

        elif target_type == "enemy" and item_data["category"] == "pokeball":
            return self._attempt_capture(target, item_data)

        elif target_type == "ally" and item_data["category"] == "medicine":
            return self._use_medicine(target, item_data)

        return False

    def _use_evolution_stone(self, pokemon, item_data):
        """Usa pedra de evolução em um Pokémon"""
        from src.managers.evolution_manager import evolution_manager

        stone_name = item_data["id"]
        stone_display = item_data["name"]

        if self.debug_in_game:
            print(f"\n{'=' * 50}")
            print(f"[EVOLUÇÃO] Usando {stone_display} em {pokemon.name} (Lv.{pokemon.level})")
            print(f"{'=' * 50}")

        evolution = evolution_manager.check_evolution(pokemon.id, stone_name=stone_name)

        if not evolution:
            if self.debug_in_game:
                print(f"[EVOLUÇÃO] ❌ {pokemon.name} não pode evoluir com {stone_display}!")
            self.player.bag.add_item(item_data["id"], 1)
            return False

        evolve_to_id = evolution["evolve_to"]

        if self.debug_in_game:
            print(f"[EVOLUÇÃO] ✅ {pokemon.name} pode evoluir para ID {evolve_to_id}!")

        old_name = pokemon.name
        pokemon._perform_evolution(evolve_to_id)

        if self.debug_in_game:
            print(f"[EVOLUÇÃO] ✨ {old_name} evoluiu para {pokemon.name}!")
            print(f"{'=' * 50}\n")

        self.player.caught_pokemon.add(evolve_to_id)
        self.player.register_seen(evolve_to_id)
        self.player.auto_save()

        return True

    def _attempt_capture(self, enemy, item_data):
        """Tenta capturar um Pokémon selvagem"""
        if hasattr(enemy, 'is_boss') and enemy.is_boss:
            if self.debug_in_game:
                print(f"[CAPTURA] {enemy.name} é um BOSS e não pode ser capturado!")
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

        if self.debug_in_game:
            print(f"[CAPTURA] Chance: {chance * 100:.1f}% | Rolagem: {roll * 100:.1f}%")

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

    def _use_medicine(self, pokemon, item_data):
        """Usa poção em um Pokémon aliado"""
        if not pokemon.is_alive() and "revive" not in item_data["id"]:
            if self.debug_in_game:
                print(f"[POÇÃO] {pokemon.name} está derrotado! Use um Reviver.")
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
            old_hp = pokemon.current_hp
            pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + heal_amount)
            healed = pokemon.current_hp - old_hp
            if self.debug_in_game:
                print(f"[POÇÃO] {pokemon.name} recuperou {healed} HP!")

        return True

    def _on_pokemon_placed(self, placement_data):
        """Callback quando um Pokémon é colocado no mapa"""
        pokemon = placement_data['pokemon']
        spot = placement_data['spot']

        placed = self.placement_manager.add_pokemon(spot, pokemon)

        if placed and self.debug_in_game:
            print(f"[PLACED] Pokémon {pokemon.name} colocado no spot ({spot.x}, {spot.y})")

    def cleanup(self):
        """Limpa o estado da fase antes de sair"""
        for spot in self.spot_renderer.get_spots():
            spot.occupied = False

        self.placed_pokemon.clear()

        if hasattr(self, 'placement_manager'):
            self.placement_manager.placed_pokemon.clear()

        if hasattr(self, 'player'):
            for pokemon in self.player.team:
                pokemon.is_placed = False

        if hasattr(self, 'wave_manager'):
            self.wave_manager.active_enemies.clear()

    def handle_event(self, event):
        """Processa eventos do jogo"""
        if self.overlay_manager.is_active:
            if self.overlay_manager.handle_event(event):
                return None
            return None

        if self.item_drag_manager.is_dragging:
            if event.type == pygame.MOUSEMOTION:
                world_pos = self.screen_manager.get_mouse_world_position(event.pos, self.camera)
                if world_pos:
                    self.item_drag_manager.update_drag(
                        event.pos, world_pos,
                        self.placement_manager.placed_pokemon,
                        self.wave_manager.active_enemies,
                        self.camera
                    )
                return None

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.item_drag_manager.stop_drag(self._on_item_use)
                return None

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.item_drag_manager.cancel_drag()
                return None

        if hasattr(self, 'item_bag_renderer'):
            bag_handled = self.item_bag_renderer.handle_event(event)
            if bag_handled:
                return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if hasattr(self, 'player') and hasattr(self.player, 'bag'):
                    self.player.bag.cycle_category()
                return None

            elif event.key == pygame.K_p:
                self.toggle_pause()
                return None

            elif event.key == pygame.K_ESCAPE:
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

        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()

            if (hasattr(self.item_bag_renderer, 'mouse_over_ui') and
                    self.item_bag_renderer.mouse_over_ui):
                if event.y > 0:
                    self.player.bag.prev_item()
                elif event.y < 0:
                    self.player.bag.next_item()
                self.item_bag_renderer.hovered_index = self.player.bag.selected_item_index
                return None

            elif not self.paused and not self.dragging_camera:
                mouse_pos = pygame.mouse.get_pos()
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        target_world_x, target_world_y = world_pos
                        self.camera.handle_zoom(event.y > 0)

                        new_world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                        if new_world_pos:
                            dx = target_world_x - new_world_pos[0]
                            dy = target_world_y - new_world_pos[1]
                            self.camera.x += dx
                            self.camera.y += dy
                            self.camera._clamp_position()
                return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            if (hasattr(self.item_bag_renderer, 'mouse_over_ui') and
                    self.item_bag_renderer.mouse_over_ui):
                hovered_index = self.item_bag_renderer.hovered_index
                if hovered_index >= 0:
                    items = self.player.bag.get_items_for_render()
                    if hovered_index < len(items):
                        item = items[hovered_index]
                        self.player.bag.selected_item_index = hovered_index
                        world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                        if world_pos:
                            self.item_drag_manager.start_drag(item["id"], mouse_pos, world_pos)
                return None

        if hasattr(self, 'team_manager'):
            result = self.team_manager.handle_event(
                event, self.spot_renderer.get_spots(), self.camera, self._on_pokemon_placed
            )
            if result:
                return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            in_viewport = self.screen_manager.is_mouse_in_viewport(mouse_pos)

            if event.button == 2:
                if in_viewport:
                    self.dragging_camera = True
                    self.last_mouse_pos = mouse_pos
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return None

            elif event.button == 3:
                if not (hasattr(self.item_bag_renderer, 'mouse_over_ui') and
                        self.item_bag_renderer.mouse_over_ui):
                    world_pos = self.screen_manager.get_mouse_world_position(event.pos, self.camera)
                    if world_pos:
                        self.placement_manager.remove_pokemon_by_right_click(world_pos[0], world_pos[1])
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
                world_dx = dx / self.camera.zoom
                world_dy = dy / self.camera.zoom
                self.camera.x -= world_dx
                self.camera.y -= world_dy
                self.camera._clamp_position()
                self.last_mouse_pos = event.pos
                return None

            if self.game_state != "game_over":
                if hasattr(self.item_bag_renderer, 'update_hover'):
                    self.item_bag_renderer.update_hover(event.pos)

                mouse_pos = pygame.mouse.get_pos()
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        self.hovered_spot = self.spot_renderer.get_spot_at_world_pos(world_pos[0], world_pos[1])

            return None

        return None

    def fixed_update(self, dt):
        """Update da lógica do jogo"""
        if self.paused:
            return

        if self.overlay_manager.is_active:
            self.overlay_manager.update(dt)
            return

        if hasattr(self, 'item_bag_renderer'):
            self.item_bag_renderer.update(dt)

        if hasattr(self, 'team_manager'):
            self.team_manager.update(dt)

        if hasattr(self, 'placement_manager'):
            self.placement_manager.update(dt, self.wave_manager.active_enemies)

        if hasattr(self, 'spot_renderer'):
            self.spot_renderer.update(dt)

        for pokemon in self.placed_pokemon:
            pokemon.update(dt)

        self.target_item_manager.update(dt)

        if self.target_item_manager.game_over:
            self.game_state = "game_over"
            self.overlay_manager.show(OverlayType.GAME_OVER)
            return

        path_points_by_index = {}
        for i in range(len(self.path_renderer.paths)):
            path_points = self.path_renderer.get_path_points(i)
            if path_points:
                path_points_by_index[i] = path_points

        enemies_at_end = self.wave_manager.update(dt, path_points_by_index, self.screen_manager)

        for enemy in enemies_at_end:
            if enemy.is_carrying:
                enemy.is_carrying.is_protected = False
                enemy.clear_carrying()

        if self.game_state == "in_wave":
            if self.wave_manager.is_wave_completely_finished():
                if self.target_item_manager.items_protected > 0:
                    self.game_state = "completed"
                    self._complete_phase()
                else:
                    self.game_state = "game_over"
                    self.overlay_manager.show(OverlayType.GAME_OVER)

        elif self.game_state == "between_waves":
            self.between_waves_timer -= dt
            if self.between_waves_timer <= 0:
                any_wave_started = False
                for path_idx in self.wave_manager.path_waves.keys():
                    if self.wave_manager.current_wave_index_by_path.get(path_idx, 0) < len(
                            self.wave_manager.path_waves[path_idx]):
                        self.wave_manager._start_wave_for_path(path_idx)
                        any_wave_started = True

                if any_wave_started:
                    self.game_state = "in_wave"

    def _complete_phase(self):
        """Marca a fase como completada e dá as recompensas"""
        from src.config.progress import progress_manager

        if self.debug_in_game:
            print(f"\n{'=' * 50}")
            print(f"🎉 FASE COMPLETADA! 🎉".center(50))
            print(f"{'=' * 50}")
            print(f"Fase: {self.phase_id} - {self.phase_info.get('name', 'Desconhecida')}")
            print(f"Itens protegidos: {self.target_item_manager.items_protected}/{len(self.target_item_manager.items)}")
            print(f"Recompensas: ${self.phase_rewards['money']} | {self.phase_rewards['experience']} XP")
            print(f"{'=' * 50}\n")

        self.player.money += self.phase_rewards['money']

        for pokemon in self.player.team:
            pokemon.gain_xp(self.phase_rewards['experience'])

        self.player.score += self.phase_rewards['experience']

        total_items = len(self.target_item_manager.items)
        protected_items = self.target_item_manager.items_protected
        if total_items > 0:
            stars = int((protected_items / total_items) * 3)
            stars = max(1, min(3, stars))
        else:
            stars = 3

        progress_manager.complete_phase(self.phase_id, stars=stars)

        self.player.auto_save()
        self.overlay_manager.show(OverlayType.PHASE_COMPLETE)

    def render(self, screen):
        """Renderiza o jogo"""
        screen.fill((0, 0, 0))

        # Mundo do jogo
        self.map_renderer.render(screen, self.camera, self.screen_manager)

        if self.show_debug:
            self.path_renderer.render(screen, self.camera, self.screen_manager, show_editing=False)

        if hasattr(self, 'spot_renderer'):
            self.spot_renderer.render(
                screen, self.camera, self.screen_manager,
                show_editing=False,
                highlight_spot=self.hovered_spot if hasattr(self, 'hovered_spot') else None
            )

        self.target_item_manager.render_in_ground(screen, self.camera)

        # Renderiza inimigos
        for enemy in self.wave_manager.active_enemies:
            enemy.render(screen, self.camera, show_hp=False)

        if hasattr(self, 'placement_manager'):
            self.placement_manager.render(screen, self.camera, self.screen_manager)

        self.target_item_manager.render_in_pokemon(screen, self.camera)

        # HP bars
        for enemy in self.wave_manager.active_enemies:
            enemy.render_hp(screen, self.camera)

        if hasattr(self, 'placement_manager'):
            self.placement_manager.render_hp(screen, self.camera)

        # UI
        self._render_game_ui(screen)

        if hasattr(self, 'team_manager'):
            self.team_manager.render(screen, self.camera, self.spot_renderer.get_spots())

        if hasattr(self, 'item_drag_manager'):
            self.item_drag_manager.render(screen, self.camera)

        if hasattr(self, 'item_bag_renderer'):
            self.item_bag_renderer.render(screen)

        # Borda da viewport
        pygame.draw.rect(screen, (80, 80, 80),
                         (self.screen_manager.viewport_x,
                          self.screen_manager.viewport_y,
                          self.screen_manager.viewport_width,
                          self.screen_manager.viewport_height), 1)

        if self.paused:
            self._render_pause_overlay(screen)

        # Overlays
        self.overlay_manager.render(screen)

        if self.show_debug:
            self._render_debug_info(screen)

    def _render_game_ui(self, screen):
        """Renderiza a UI do jogo"""
        font = pygame.font.Font(None, 24)
        font_small = pygame.font.Font(None, 18)

        wave_info = self.wave_manager.get_current_wave_info()

        # Fundo semi-transparente
        ui_bg = pygame.Surface((400, 150))
        ui_bg.set_alpha(180)
        ui_bg.fill((20, 20, 30))
        screen.blit(ui_bg, (self.screen_manager.viewport_x + 10, self.screen_manager.viewport_y + 10))

        y_offset = self.screen_manager.viewport_y + 15

        # Título da fase
        phase_text = font.render(self.phase_info.get("name", f"Fase {self.phase_number}"), True, (255, 215, 0))
        screen.blit(phase_text, (self.screen_manager.viewport_x + 15, y_offset))
        y_offset += 25

        # Itens alvo
        items_color = (100, 255, 100) if self.target_item_manager.items_protected > 0 else (255, 100, 100)
        items_text = font_small.render(
            f"Itens: {self.target_item_manager.items_protected} protegidos | {self.target_item_manager.items_stolen} levados",
            True, items_color
        )
        screen.blit(items_text, (self.screen_manager.viewport_x + 15, y_offset))
        y_offset += 20

        # Wave info
        if self.game_state == "waiting":
            state_text = font_small.render("Aguardando início...", True, (200, 200, 200))
            screen.blit(state_text, (self.screen_manager.viewport_x + 15, y_offset))

        elif self.game_state == "in_wave":
            if wave_info.get('active_paths', 0) > 1:
                wave_text = font_small.render(
                    f"{wave_info['active_paths']} paths ativos | {wave_info['name']}",
                    True, (100, 255, 100))
            else:
                wave_text = font_small.render(
                    f"Wave {wave_info['index']}/{wave_info['total']}: {wave_info['name']}",
                    True, (100, 255, 100))
            screen.blit(wave_text, (self.screen_manager.viewport_x + 15, y_offset))
            y_offset += 20

            # Barra de progresso
            bar_x = self.screen_manager.viewport_x + 15
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

            enemies_text = font_small.render(
                f"Inimigos vivos: {len(self.wave_manager.active_enemies)}",
                True, (255, 100, 100) if len(self.wave_manager.active_enemies) > 0 else (100, 255, 100))
            screen.blit(enemies_text, (self.screen_manager.viewport_x + 15, y_offset))

        elif self.game_state == "between_waves":
            wave_text = font_small.render(
                f"Wave concluída! Próxima em {self.between_waves_timer:.1f}s",
                True, (255, 255, 0))
            screen.blit(wave_text, (self.screen_manager.viewport_x + 15, y_offset))

        elif self.game_state == "completed":
            complete_text = font.render("FASE COMPLETA!", True, (255, 215, 0))
            screen.blit(complete_text, (self.screen_manager.viewport_x + 15, y_offset))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa do jogo"""
        overlay = pygame.Surface((self.screen_manager.viewport_width, self.screen_manager.viewport_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        font_large = pygame.font.Font(None, 48)
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - pause_text.get_width()) // 2
        text_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

        font_small = pygame.font.Font(None, 24)
        phase_display = self.phase_info.get("name", f"Fase {self.phase_number}")
        phase_text = font_small.render(phase_display, True, (200, 200, 200))
        phase_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - phase_text.get_width()) // 2
        phase_y = text_y + pause_text.get_height() + 10
        screen.blit(phase_text, (phase_x, phase_y))

    def _render_debug_info(self, screen):
        """Informações de debug"""
        mouse_pos = pygame.mouse.get_pos()
        in_viewport = self.screen_manager.is_mouse_in_viewport(mouse_pos)

        if in_viewport:
            world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
            if world_pos:
                world_text = f"World: ({world_pos[0]:.0f}, {world_pos[1]:.0f})"
                tile_x = int(world_pos[0] // 16)
                tile_y = int(world_pos[1] // 16)
                tile_info = f"Tile: ({tile_x}, {tile_y})"

                tile_id = 0
                for layer in self.map_renderer.layer_manager.layers:
                    if hasattr(layer, 'layer_type') and layer.layer_type.value == "ground":
                        tile_id = layer.get_tile(tile_x, tile_y)
                        break
                tile_value = f"Tile ID: {tile_id}"

                path_info = "Nenhum path"
                for i, path in enumerate(self.path_renderer.paths):
                    for node in path.nodes:
                        dist = ((node[0] - world_pos[0]) ** 2 + (node[1] - world_pos[1]) ** 2) ** 0.5
                        if dist < 20:
                            path_info = f"Próximo ao Path {i + 1} (dist: {dist:.0f}px)"
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
            f"FPS: {self.screen_manager.get_fps():.1f}",
            f"Game State: {self.game_state}",
            "",
            "=== WAVES ===",
            f"Status: {wave_info['name']}",
            f"Progresso: {wave_info['progress'] * 100:.1f}%",
            f"Vivos: {len(self.wave_manager.active_enemies)}",
            "",
            "=== CAMERA ===",
            f"Position: ({self.camera.x:.0f}, {self.camera.y:.0f})",
            f"Zoom: {self.camera.zoom:.2f}",
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

        y_offset = self.screen_manager.viewport_y + 40
        x_offset = self.screen_manager.viewport_x + 10
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