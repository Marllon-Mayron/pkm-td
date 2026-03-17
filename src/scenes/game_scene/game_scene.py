# src/scenes/game_scene.py (versão modificada)

"""
Cena principal do jogo - Carrega fases reais com waves
"""
import pygame

from src.entities.pokemon import Pokemon
from src.scenes.base_scene import BaseScene
from src.config.phase_catalog import phase_catalog
from src.scenes.game_scene.components.managers.placement_manager import PlacementManager
from src.scenes.game_scene.components.managers.target_item_manager import TargetItemManager
from src.scenes.game_scene.components.managers.team_manager import GameTeamManager
from src.scenes.game_scene.components.phase_loader import phase_loader
from src.scenes.game_scene.components.renderer.map_renderer import MapRenderer
from src.scenes.game_scene.components.renderer.path_renderer import PathRenderer
from src.scenes.game_scene.components.renderer.pokemon_spot_renderer import PokemonSpotRenderer
from src.scenes.game_scene.components.managers.wave_manager import GameWaveManager
from src.scenes.game_scene.components.renderer.target_item_renderer import TargetItemRenderer


class GameScene(BaseScene):
    def __init__(self, game, phase_number=1):
        super().__init__(game)

        self.phase_number = phase_number
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

        # cria o wave_manager, depois de carregar os dados
        self.wave_manager = GameWaveManager(phase_loader)

        # Configurações de mundo baseadas no mapa
        self._setup_world_dimensions()

        self.player = game.player

        #Timer para game over
        self.game_over_timer = 0
        self.game_over_delay = 3.0

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

        self.team_manager.update_team()

        # Spot atualmente sob o mouse
        self.hovered_spot = None

        # Lista de Pokémon colocados no mapa
        self.placed_pokemon = []

        # Lista de inimigos ativos
        self.active_enemies = []

        # Estado do jogo
        self.game_state = "waiting"
        self.between_waves_timer = 3.0

        # Configurações da grid
        self.show_grid = True
        self.grid_size = 16
        self.grid_color = (60, 60, 80)
        self.grid_alpha = 100

        # Debug
        self.show_debug = True

        # Controle de arrasto da câmera
        self.dragging_camera = False
        self.last_mouse_pos = None

        # Inicia automaticamente a primeira wave
        self._start_game()

        print(f"\n=== FASE CARREGADA ===")
        print(f"Fase: {self.phase_info.get('name', 'Desconhecida')}")
        print(f"Capítulo: {self.phase_info.get('chapter', 1)}")
        print(f"Número: {self.phase_number}")
        print(f"Waves: {len(self.wave_manager.waves_data)}")
        print(f"Itens alvo: {len(self.target_item_manager.items)}")
        print(f"Mundo: {self.world_width}x{self.world_height}")
        print("=====================\n")

    def _start_game(self):
        """Inicia o jogo"""
        if self.wave_manager.has_more_waves():
            self.game_state = "in_wave"
            self.wave_manager.start_next_wave()
        else:
            self.game_state = "completed"
            print("Fase não tem waves configuradas!")

    def _load_phase_info(self):
        """Carrega informações da fase do catálogo"""
        # Precisa encontrar em qual capítulo está esta fase
        all_phases = phase_catalog.get_all_phases()
        for chapter, phases in all_phases.items():
            for phase in phases:
                if phase["number"] == self.phase_number:
                    self.phase_info = phase
                    return

        # Fallback se não encontrar
        self.phase_info = {
            "name": f"Fase {self.phase_number}",
            "number": self.phase_number,
            "chapter": 1
        }

    def _load_phase_data(self):
        """Carrega os dados da fase do disco"""
        chapter = self.phase_info.get("chapter", 1)
        data = phase_loader.load_phase(chapter, self.phase_number)

        if not data:
            print(f"ERRO: Não foi possível carregar a fase {self.phase_number}")
            return

        # Carrega mapa
        map_data = phase_loader.get_map_data()
        self.map_renderer.load_from_data(map_data, "data/phases")

        # Carrega paths (agora pode ser múltiplos)
        paths_data = phase_loader.get_paths_data()
        self.path_renderer.load_from_data(paths_data)

        # Carrega spots
        spot_data = phase_loader.get_tower_spots_data()
        self.spot_renderer.load_from_data(spot_data)

        # Carrega itens alvo
        items_data = data.get("target_items", {})
        self.target_item_manager.load_from_data(items_data)


    def _setup_world_dimensions(self):
        """Configura dimensões do mundo baseado no mapa"""
        map_width, map_height = self.map_renderer.get_dimensions()

        # Se o mapa foi carregado, usa suas dimensões
        if map_width > 0 and map_height > 0:
            self.world_width = map_width
            self.world_height = map_height
        else:
            # Fallback para tamanho padrão
            self.world_width = 2000
            self.world_height = 2000

    def _on_enemy_spawn(self, enemy):
        """Callback chamado quando um inimigo é spawnado"""
        print(f"\n[SPAWN] Criando inimigo:")
        print(f"  - Pokémon ID: {enemy.id}")
        print(f"  - Nome: {enemy.name}")
        print(f"  - Posição: ({enemy.x}, {enemy.y})")
        print(f"  - Path points: {len(enemy.path)}")
        print(f"  - Sprite: {'Carregado' if enemy.sprite else 'NULO!'}")
        print(f"  - Tipo sprite: {type(enemy.sprite)}")

        self.active_enemies.append(enemy)

    def _on_pokemon_placed(self, placement_data):
        """Callback quando um Pokémon é colocado no mapa"""
        pokemon = placement_data['pokemon']
        spot = placement_data['spot']
        world_pos = placement_data['world_pos']  # Já vem centralizado do drag_drop

        print(
            f"[PLACED] Pokémon {pokemon.name} colocado no spot ({spot.x}, {spot.y}) em ({world_pos[0]}, {world_pos[1]})")

        # Usa o placement manager para adicionar
        placed = self.placement_manager.add_pokemon(spot, pokemon)

        if placed:
            print(f"Pokémon colocado! Total no mapa: {len(self.placement_manager.placed_pokemon)}")

    def handle_event(self, event):
        """Processa eventos do jogo"""

        if hasattr(self, 'team_manager'):
            result = self.team_manager.handle_event(
                event,
                self.spot_renderer.get_spots(),
                self.camera,
                self._on_pokemon_placed  # Callback quando colocar Pokémon
            )

        if self.game_state == "game_over" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_team_select()
                return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
                return None
            elif event.key == pygame.K_ESCAPE:
                self.game.current_scene = self.game.menu_scene
                return None
            elif event.key == pygame.K_F1:
                self.show_debug = not self.show_debug
                return None
            elif event.key == pygame.K_g:
                self.show_grid = not self.show_grid
                print(f"[DEBUG] Grid {'ativada' if self.show_grid else 'desativada'}")
                return None
            elif event.key == pygame.K_SPACE:
                # DEBUG: Inicia próxima wave manualmente
                if self.game_state == "between_waves":
                    self.game_state = "in_wave"
                    self.wave_manager.start_next_wave()
                mouse_pos = pygame.mouse.get_pos()
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        print(f"[DEBUG] Posição do mouse no mundo: ({world_pos[0]:.0f}, {world_pos[1]:.0f})")

                        # Mostra informações do tile
                        tile_x = int(world_pos[0] // self.grid_size)
                        tile_y = int(world_pos[1] // self.grid_size)
                        print(f"[DEBUG] Tile: ({tile_x}, {tile_y})")
                        return None
                    return None
                return None
            return None

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Verifica se clicou no viewport
            in_viewport = self.screen_manager.is_mouse_in_viewport(mouse_pos)

            if event.button == 1:  # Clique esquerdo
                if in_viewport:
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        print(f"[DEBUG] Clique no mundo: ({world_pos[0]:.0f}, {world_pos[1]:.0f})")

            elif event.button == 2:  # Botão do meio/scroll - ARRASTO DA CÂMERA
                if in_viewport:
                    self.dragging_camera = True
                    self.last_mouse_pos = mouse_pos
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                    return True

            if event.button == 3:  # Botão direito
                world_pos = self.screen_manager.get_mouse_world_position(event.pos, self.camera)

                if world_pos:
                    print(f"[GAME] Clique direito em ({world_pos[0]:.1f}, {world_pos[1]:.1f})")

                    # Tenta recolher Pokémon (sem passar o spot)
                    pokemon = self.placement_manager.remove_pokemon_by_right_click(
                        world_pos[0],
                        world_pos[1]
                    )

                    if pokemon:
                        print(f"[GAME] {pokemon.name} recolhido com sucesso!")
                        # Atualiza a UI do time
                        self.team_manager.update_team()

                        # DEBUG: Verifica o estado do is_placed
                        for p in self.player.team:
                            if p.id == pokemon.id:
                                print(f"[DEBUG] {p.name} is_placed = {p.is_placed}")

                        return True
                    return None
                return None
            return None

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:  # Botão do meio/scroll
                if self.dragging_camera:
                    self.dragging_camera = False
                    self.last_mouse_pos = None
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                    return True
                return None
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
                return True

            mouse_pos = pygame.mouse.get_pos()
            if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                if world_pos:
                    # Pega o spot sob o mouse
                    hovered_spot = self.spot_renderer.get_spot_at_world_pos(world_pos[0], world_pos[1])
                    # Armazena para uso no render
                    self.hovered_spot = hovered_spot
                    return None
                return None
            return None

        elif event.type == pygame.MOUSEWHEEL:
            if not self.paused and not self.dragging_camera:
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
                        return None
                    return None
                return None
            return None
        return None

    def fixed_update(self, dt):
        """Update da lógica do jogo"""
        if self.paused:
            return

        if self.game_state == "game_over":
            self.game_over_timer += dt
            if self.game_over_timer >= self.game_over_delay:
                print("Game Over - Voltando para seleção de time...")
                # Volta para a tela de seleção de time
                from src.scenes.team_select_scene import TeamSelectScene
                self.game.current_scene = TeamSelectScene(
                    self.game,
                    self.phase_info.get("chapter", 1),
                    self.phase_number
                )
            return

        if hasattr(self, 'team_manager'):
            self.team_manager.update(dt)

        # Atualiza Pokémon colocados
        if hasattr(self, 'placement_manager'):
            self.placement_manager.update(dt, self.active_enemies)

        if hasattr(self, 'spot_renderer'):
            self.spot_renderer.update(dt)

        for pokemon in self.placed_pokemon:
            pokemon.update(dt)

        # Atualiza itens alvo
        self.target_item_manager.update(dt)

        # Verifica game over por itens
        if self.target_item_manager.game_over:
            self.game_state = "game_over"
            print("GAME OVER - Todos os itens foram levados!")

        # Atualiza inimigos
        enemies_to_remove = []
        for enemy in self.active_enemies:
            # Passa a lista de itens para o inimigo poder capturá-los
            enemy.update(dt, items=self.target_item_manager.items)

            # Verifica se chegou ao fim do path
            if hasattr(enemy, 'path') and enemy.path and enemy.path_index >= len(enemy.path):
                print(f"[GAME] {enemy.name} chegou ao fim do path! Removendo...")

                # VERIFICA SE O INIMIGO ESTÁ CARREGANDO UM ITEM
                if enemy.is_carrying:
                    item = enemy.is_carrying
                    print(f"[GAME] {enemy.name} estava carregando {item.item_name} - item será removido!")

                    # Marca o item como não protegido (para ser removido)
                    item.is_protected = False
                    # O item será removido no próximo update do target_item_manager

                enemies_to_remove.append(enemy)
                self.wave_manager.enemy_destroyed()

            # Remove inimigos que chegaram ao fim
        for enemy in enemies_to_remove:
            self.active_enemies.remove(enemy)

        # Lógica das waves (existente)...
        if self.game_state == "in_wave":
            # Obtém o path correto para esta wave
            wave_index = self.wave_manager.current_wave_index
            if wave_index < len(self.wave_manager.waves_data):
                wave_data = self.wave_manager.waves_data[wave_index]
                path_index = wave_data.get("path_index", 0)

                # Pega os pontos do path correspondente
                path_points = self.path_renderer.get_path_points(path_index)

                # Atualiza wave manager
                self.wave_manager.update(dt, path_points, self._on_enemy_spawn, self.screen_manager)

                # Verifica se a wave terminou
                if not self.wave_manager.wave_in_progress:
                    if self.wave_manager.has_more_waves():
                        self.game_state = "between_waves"
                        self.between_waves_timer = 3.0
                    else:
                        # Waves acabaram - verifica se ainda tem itens
                        if self.target_item_manager.items_protected > 0:
                            self.game_state = "completed"
                            print("PARABÉNS! Todas as waves concluídas e itens protegidos!")
                        else:
                            self.game_state = "game_over"
                            print("GAME OVER - Itens foram levados!")

        elif self.game_state == "between_waves":
            self.between_waves_timer -= dt
            if self.between_waves_timer <= 0:
                self.game_state = "in_wave"
                self.wave_manager.start_next_wave()

    def render(self, screen):
        """Renderiza o jogo"""
        # Limpa a tela
        screen.fill((0, 0, 0))

        # Renderiza o mapa
        self.map_renderer.render(screen, self.camera, self.screen_manager)

        # Renderiza os paths
        if self.show_debug:
            self.path_renderer.render(screen, self.camera, self.screen_manager, show_editing=False)

        # Renderiza itens alvo
        self.target_item_manager.render(screen, self.camera)

        if hasattr(self, 'spot_renderer'):
            self.spot_renderer.render(
                screen, self.camera, self.screen_manager,
                show_editing=False,
                highlight_spot=self.hovered_spot if hasattr(self, 'hovered_spot') else None
            )

        if hasattr(self, 'placement_manager'):
            self.placement_manager.render(screen, self.camera, self.screen_manager)

        # Renderiza Pokémon colocados no mapa
        for pokemon in self.placed_pokemon:
            pokemon.render(screen, self.camera, show_hp=True)

        # Renderiza inimigos
        for enemy in self.active_enemies:
            enemy.render(screen, self.camera, show_hp=True)

        # Desenha a grid se ativada
        if self.show_grid:
            self._draw_grid_aligned(screen)

        # Desenha borda do viewport
        pygame.draw.rect(screen, (80, 80, 80),
                         (self.screen_manager.viewport_x,
                          self.screen_manager.viewport_y,
                          self.screen_manager.viewport_width,
                          self.screen_manager.viewport_height), 1)

        # UI do jogo
        self._render_game_ui(screen)

        # Renderiza a HUD do time
        if hasattr(self, 'team_manager'):
            self.team_manager.render(screen, self.camera, self.spot_renderer.get_spots())

        # Overlay de pausa
        if self.paused:
            self._render_pause_overlay(screen)

        # Debug info
        if self.show_debug:
            self._render_debug_info(screen)

    def _render_game_ui(self, screen):
        """Renderiza a UI do jogo (modificada para incluir info dos itens)"""
        font = pygame.font.Font(None, 24)
        font_small = pygame.font.Font(None, 18)
        font_large = pygame.font.Font(None, 48)  # NOVO: Fonte grande para game over

        wave_info = self.wave_manager.get_current_wave_info()

        # Fundo semi-transparente para UI
        ui_bg = pygame.Surface((400, 150))
        ui_bg.set_alpha(180)
        ui_bg.fill((20, 20, 30))
        screen.blit(ui_bg, (self.screen_manager.viewport_x + 10, self.screen_manager.viewport_y + 10))

        y_offset = self.screen_manager.viewport_y + 15

        # Título da fase
        phase_text = font.render(self.phase_info.get("name", f"Fase {self.phase_number}"), True, (255, 215, 0))
        screen.blit(phase_text, (self.screen_manager.viewport_x + 15, y_offset))
        y_offset += 25

        # Informação dos itens alvo
        items_color = (100, 255, 100) if self.target_item_manager.items_protected > 0 else (255, 100, 100)
        items_text = font_small.render(
            f"Itens: {self.target_item_manager.items_protected} protegidos | {self.target_item_manager.items_stolen} levados",
            True, items_color
        )
        screen.blit(items_text, (self.screen_manager.viewport_x + 15, y_offset))
        y_offset += 20

        # Informação da wave
        if self.game_state == "waiting":
            state_text = font_small.render("Aguardando início...", True, (200, 200, 200))
            screen.blit(state_text, (self.screen_manager.viewport_x + 15, y_offset))
        elif self.game_state == "in_wave":
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

            # Fundo da barra
            pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_width, bar_height))

            # Progresso
            progress_width = int(bar_width * wave_info['progress'])
            pygame.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, progress_width, bar_height))

            # Borda
            pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)

            # Texto do progresso
            progress_text = font_small.render(
                f"{wave_info['enemies_spawned']}/{wave_info['enemies_total']}",
                True, (255, 255, 255))
            text_x = bar_x + (bar_width - progress_text.get_width()) // 2
            screen.blit(progress_text, (text_x, bar_y + 2))

            y_offset += 25

            # Inimigos restantes
            enemies_text = font_small.render(
                f"Inimigos vivos: {len(self.active_enemies)}",
                True, (255, 100, 100) if len(self.active_enemies) > 0 else (100, 255, 100))
            screen.blit(enemies_text, (self.screen_manager.viewport_x + 15, y_offset))

        elif self.game_state == "between_waves":
            wave_text = font_small.render(
                f"Wave {wave_info['index']} concluída! Próxima em {self.between_waves_timer:.1f}s",
                True, (255, 255, 0))
            screen.blit(wave_text, (self.screen_manager.viewport_x + 15, y_offset))

        elif self.game_state == "completed":
            complete_text = font.render("FASE COMPLETA!", True, (255, 215, 0))
            screen.blit(complete_text, (self.screen_manager.viewport_x + 15, y_offset))

        elif self.game_state == "game_over":
            # Fundo escuro no viewport
            overlay = pygame.Surface((
                self.screen_manager.viewport_width,
                self.screen_manager.viewport_height
            ))
            overlay.set_alpha(200)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

            # Texto GAME OVER
            game_over_text = font_large.render("GAME OVER", True, (255, 0, 0))
            game_over_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - game_over_text.get_width()) // 2
            game_over_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - game_over_text.get_height()) // 2 - 30
            screen.blit(game_over_text, (game_over_x, game_over_y))

            # Texto de itens levados
            items_lost_text = font.render(
                f"{self.target_item_manager.items_stolen} itens foram levados!",
                True, (255, 100, 100)
            )
            items_lost_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - items_lost_text.get_width()) // 2
            items_lost_y = game_over_y + game_over_text.get_height() + 20
            screen.blit(items_lost_text, (items_lost_x, items_lost_y))

            # Timer para voltar
            remaining = max(0, self.game_over_delay - self.game_over_timer)
            timer_text = font.render(
                f"Voltando em {remaining:.0f}...",
                True, (200, 200, 200)
            )
            timer_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - timer_text.get_width()) // 2
            timer_y = items_lost_y + items_lost_text.get_height() + 20
            screen.blit(timer_text, (timer_x, timer_y))

            # Mensagem de ESC para cancelar (opcional)
            esc_text = font_small.render(
                "Pressione ESC para voltar agora",
                True, (150, 150, 150)
            )
            esc_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - esc_text.get_width()) // 2
            esc_y = timer_y + timer_text.get_height() + 30
            screen.blit(esc_text, (esc_x, esc_y))

    def _return_to_team_select(self):
        """Volta para a tela de seleção de time"""
        from src.scenes.team_select_scene import TeamSelectScene
        self.game.current_scene = TeamSelectScene(
            self.game,
            self.phase_info.get("chapter", 1),
            self.phase_number
        )

    def _draw_grid_aligned(self, screen):
        """Desenha a grid alinhada com os tiles"""
        camera = self.camera
        sm = self.screen_manager

        # Calcula offset da câmera
        cam_offset_x = round((-camera.x * camera.zoom * sm.render_scale +
                             (sm.render_width / 2) * sm.render_scale +
                             sm.viewport_x))
        cam_offset_y = round((-camera.y * camera.zoom * sm.render_scale +
                             (sm.render_height / 2) * sm.render_scale +
                             sm.viewport_y))

        tile_size_scaled = max(1, round(self.grid_size * camera.zoom * sm.render_scale))

        # Calcula primeiro tile visível
        first_visible_x = (-cam_offset_x) // tile_size_scaled
        first_visible_y = (-cam_offset_y) // tile_size_scaled

        # Quantos tiles cabem na tela
        tiles_visible_x = (sm.viewport_width // tile_size_scaled) + 3
        tiles_visible_y = (sm.viewport_height // tile_size_scaled) + 3

        # Cria superfície para a grid
        grid_surface = pygame.Surface(
            (sm.viewport_width, sm.viewport_height),
            pygame.SRCALPHA
        )

        # Desenha linhas verticais
        for i in range(tiles_visible_x):
            tile_x = first_visible_x + i
            screen_x = tile_x * tile_size_scaled + cam_offset_x
            grid_x = screen_x - sm.viewport_x

            if -tile_size_scaled <= grid_x <= sm.viewport_width + tile_size_scaled:
                if tile_x == 0:
                    color = (100, 100, 150, 150)  # Eixo Y
                else:
                    color = (60, 60, 80, 80)  # Grid normal

                pygame.draw.line(
                    grid_surface,
                    color,
                    (grid_x, 0),
                    (grid_x, sm.viewport_height),
                    1
                )

        # Desenha linhas horizontais
        for i in range(tiles_visible_y):
            tile_y = first_visible_y + i
            screen_y = tile_y * tile_size_scaled + cam_offset_y
            grid_y = screen_y - sm.viewport_y

            if -tile_size_scaled <= grid_y <= sm.viewport_height + tile_size_scaled:
                if tile_y == 0:
                    color = (150, 100, 100, 150)  # Eixo X
                else:
                    color = (60, 60, 80, 80)  # Grid normal

                pygame.draw.line(
                    grid_surface,
                    color,
                    (0, grid_y),
                    (sm.viewport_width, grid_y),
                    1
                )

        screen.blit(grid_surface, (sm.viewport_x, sm.viewport_y))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa do jogo"""
        overlay = pygame.Surface((self.screen_manager.viewport_width,
                                 self.screen_manager.viewport_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        font_large = pygame.font.Font(None, 48)
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - pause_text.get_width()) // 2
        text_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

        # Mostra nome da fase no pause
        font_small = pygame.font.Font(None, 24)
        phase_display = self.phase_info.get("name", f"Fase {self.phase_number}")
        phase_text = font_small.render(phase_display, True, (200, 200, 200))
        phase_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - phase_text.get_width()) // 2
        phase_y = text_y + pause_text.get_height() + 10
        screen.blit(phase_text, (phase_x, phase_y))

    def _render_debug_info(self, screen):
        """Informações de debug detalhadas"""
        mouse_pos = pygame.mouse.get_pos()
        in_viewport = self.screen_manager.is_mouse_in_viewport(mouse_pos)

        if in_viewport:
            world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
            if world_pos:
                world_text = f"World: ({world_pos[0]:.0f}, {world_pos[1]:.0f})"
                tile_x = int(world_pos[0] // self.grid_size)
                tile_y = int(world_pos[1] // self.grid_size)
                tile_info = f"Tile: ({tile_x}, {tile_y})"

                # Pega o tile da layer atual (primeira layer ground)
                tile_id = 0
                for layer in self.map_renderer.layer_manager.layers:
                    if layer.layer_type.value == "ground":
                        tile_id = layer.get_tile(tile_x, tile_y)
                        break
                tile_value = f"Tile ID: {tile_id}"
            else:
                world_text = "World: invalid position"
                tile_info = "Tile: N/A"
                tile_value = "Tile ID: N/A"
        else:
            world_text = "World: outside viewport"
            tile_info = "Tile: outside"
            tile_value = "Tile ID: N/A"

        wave_info = self.wave_manager.get_current_wave_info()

        debug_lines = [
            "=== DEBUG INFO ===",
            f"Fase: {self.phase_info.get('name', 'Desconhecida')}",
            f"Capítulo: {self.phase_info.get('chapter', 1)} | Nº: {self.phase_number}",
            f"FPS: {self.screen_manager.get_fps():.1f}",
            f"Delta Time: {self.screen_manager.get_delta_time()*1000:.1f}ms",
            f"Grid: {'ON' if self.show_grid else 'OFF'}",
            f"Game State: {self.game_state}",
            f"Camera Drag: {'ACTIVE' if self.dragging_camera else 'inactive'}",
            "",
            "=== WAVES ===",
            f"Wave: {wave_info['index']}/{wave_info['total']} - {wave_info['name']}",
            f"Inimigos: {wave_info['enemies_spawned']}/{wave_info['enemies_total']} spawnados",
            f"Vivos: {len(self.active_enemies)}",
            f"Progresso: {wave_info['progress']*100:.1f}%",
            "",
            "=== CAMERA ===",
            f"Position: ({self.camera.x:.0f}, {self.camera.y:.0f})",
            f"Zoom: {self.camera.zoom:.2f}",
            f"Visible: {self.screen_manager.render_width/self.camera.zoom:.0f} x {self.screen_manager.render_height/self.camera.zoom:.0f}",
            "",
            "=== SCREEN ===",
            f"Window: {self.screen_manager.window_width}x{self.screen_manager.window_height}",
            f"Viewport: {self.screen_manager.viewport_width}x{self.screen_manager.viewport_height}",
            f"Scale: {self.screen_manager.render_scale:.2f}",
            "",
            "=== MOUSE ===",
            f"Screen: ({mouse_pos[0]}, {mouse_pos[1]})",
            f"In Viewport: {in_viewport}",
            world_text,
            tile_info,
            tile_value,
            "",
            "=== MAPA ===",
            f"Tiles: {self.map_renderer.layer_manager.width}x{self.map_renderer.layer_manager.height}",
            f"Pixels: {self.world_width}x{self.world_height}",
            f"Grid size: {self.grid_size}px",
            f"Paths: {len(self.path_renderer.paths)}",
            f"Path points: {sum(len(p.nodes) for p in self.path_renderer.paths)}",
            f"Pokémon colocados: {len(self.placement_manager.placed_pokemon) if hasattr(self, 'placement_manager') else 0}",
            f"Spots disponíveis: {len(self.spot_renderer.get_spots())}",
            f"Spots ocupados: {sum(1 for s in self.spot_renderer.get_spots() if s.occupied)}"
        ]

        y_offset = self.screen_manager.viewport_y + 40
        x_offset = self.screen_manager.viewport_x + 10
        font_small = pygame.font.Font(None, 18)

        line_height = 16
        bg_height = len(debug_lines) * line_height + 10
        bg_width = 400
        bg_surface = pygame.Surface((bg_width, bg_height))
        bg_surface.set_alpha(180)
        bg_surface.fill((0, 0, 0))
        screen.blit(bg_surface, (x_offset - 5, y_offset - 5))

        for line in debug_lines:
            if line.startswith("==="):
                color = (255, 255, 0)
                font_bold = pygame.font.Font(None, 20)
                text = font_bold.render(line, True, color)
            else:
                color = (0, 255, 0)
                text = font_small.render(line, True, color)

            screen.blit(text, (x_offset, y_offset))
            y_offset += line_height