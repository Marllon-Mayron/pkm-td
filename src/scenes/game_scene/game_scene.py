# src/scenes/game_scene.py (versão modificada)

"""
Cena principal do jogo - Carrega fases reais com waves
"""
import pygame, os

from src.config.paths import PROJECT_ROOT, RES_PATH, ALL_TILES_PATH
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

        # CARREGA OS DADOS DA FASE PRIMEIRO (inclui phase_rewards)
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

        # Configurações da grid
        self.show_grid = True
        self.grid_size = 16
        self.grid_color = (60, 60, 80)
        self.grid_alpha = 100

        # Debug
        self.show_debug = False

        # Controle de arrasto da câmera
        self.dragging_camera = False
        self.last_mouse_pos = None

        # Inicia automaticamente a primeira wave
        self._start_game()

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
        """Inicia o jogo - AGORA INICIA TODAS AS WAVES DE TODOS OS PATHS"""
        if self.wave_manager.has_more_waves():
            self.game_state = "in_wave"
            # Inicia todas as waves de todos os paths simultaneamente
            self.wave_manager.start_all_waves()
        else:
            self.game_state = "completed"
            print("Fase não tem waves configuradas!")

    def _load_phase_info(self):
        """Carrega informações da fase do catálogo usando chapter_id e phase_number"""
        # Tenta pegar do catálogo usando chapter_id e phase_number
        self.phase_info = phase_catalog.get_phase_info(self.chapter_id, self.phase_number)

        # Se não encontrar, cria um fallback
        if not self.phase_info:
            self.phase_info = {
                "name": f"Fase {self.chapter_id}-{self.phase_number}",
                "number": self.phase_number,
                "chapter": self.chapter_id
            }
            print(f"Fase {self.phase_id} não encontrada no catálogo, usando fallback")

    def _load_phase_data(self):
        """Carrega os dados da fase do disco usando chapter_id e phase_number"""
        print(f"\n=== CARREGANDO DADOS DA FASE {self.chapter_id}-{self.phase_number} ===")

        data = phase_loader.load_phase(self.chapter_id, self.phase_number)

        if not data:
            print(f"ERRO: Não foi possível carregar a fase {self.phase_id}")
            # Cria recompensas padrão em caso de erro
            self.phase_rewards = {"money": 0, "experience": 0}
            return

        # USA A CONSTANTE GLOBAL
        base_path = PROJECT_ROOT
        print(f"Usando PROJECT_ROOT: {base_path}")

        # Verifica se a pasta res existe
        print(f"Pasta RES_PATH: {RES_PATH}")
        print(f"Existe? {os.path.exists(RES_PATH)}")

        print(f"Pasta ALL_TILES_PATH: {ALL_TILES_PATH}")
        print(f"Existe? {os.path.exists(ALL_TILES_PATH)}")

        # Lista arquivos na pasta AllTiles
        if os.path.exists(ALL_TILES_PATH):
            files = os.listdir(ALL_TILES_PATH)
            print(f"Arquivos em AllTiles: {files[:5]}")

        # Carrega mapa
        map_data = phase_loader.get_map_data()
        print(f"Map data keys: {map_data.keys()}")
        self.map_renderer.load_from_data(map_data, base_path)

        # Carrega paths
        paths_data = phase_loader.get_paths_data()
        print(f"Paths data: {len(paths_data.get('paths', []))} paths")
        self.path_renderer.load_from_data(paths_data)

        # Carrega spots
        spot_data = phase_loader.get_tower_spots_data()
        print(f"Spots data: {len(spot_data.get('spots', []))} spots")
        self.spot_renderer.load_from_data(spot_data)

        # Carrega itens alvo
        items_data = data.get("target_items", {})
        print(f"Itens alvo: {len(items_data.get('items', []))} itens")
        self.target_item_manager.load_from_data(items_data)

        # Carrega recompensas - CRIA ANTES DE QUALQUER OUTRA COISA
        rewards = data.get("rewards", {})
        self.phase_rewards = {
            "money": rewards.get("money", 0),
            "experience": rewards.get("experience", 0)
        }
        print(f"✓ Recompensas carregadas: ${self.phase_rewards['money']} | {self.phase_rewards['experience']} XP")

        print("=== DADOS CARREGADOS COM SUCESSO ===\n")

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

    def _on_item_use(self, target, item_data, target_type):
        """Callback quando um item é usado em um alvo"""
        print(f"[USO] Usando {item_data['name']} em {getattr(target, 'name', 'alvo')}")

        # ===== EVOLUÇÃO POR PEDRA =====
        if item_data["effect"] == "evolution":
            # Só pode usar pedra em aliados (Pokémon do time)
            if target_type == "ally":
                return self._use_evolution_stone(target, item_data)
            else:
                print(f"[PEDRA] Não pode usar pedra em inimigos!")
                return False

        # Pokebolas
        elif target_type == "enemy" and item_data["category"] == "pokeball":
            return self._attempt_capture(target, item_data)

        # Poções e remédios
        elif target_type == "ally" and item_data["category"] == "medicine":
            return self._use_medicine(target, item_data)

        return False

    def _use_evolution_stone(self, pokemon, item_data):
        """Usa pedra de evolução em um Pokémon"""
        from src.managers.evolution_manager import evolution_manager

        stone_name = item_data["id"]  # ex: "firestone", "waterstone"
        stone_display = item_data["name"]

        print(f"\n{'=' * 50}")
        print(f"[EVOLUÇÃO] Usando {stone_display} em {pokemon.name} (Lv.{pokemon.level})")
        print(f"{'=' * 50}")

        # Verifica se pode evoluir com esta pedra
        evolution = evolution_manager.check_evolution(
            pokemon.id,
            stone_name=stone_name
        )

        if not evolution:
            print(f"[EVOLUÇÃO] ❌ {pokemon.name} não pode evoluir com {stone_display}!")
            # Devolve o item para a mochila? No jogo original, o item é consumido mesmo assim
            # Vamos devolver para não punir o jogador
            self.player.bag.add_item(item_data["id"], 1)
            return False

        # Armazena o ID do Pokémon evoluído
        evolve_to_id = evolution["evolve_to"]
        evolve_method = evolution["method"]

        print(f"[EVOLUÇÃO] ✅ {pokemon.name} pode evoluir para ID {evolve_to_id}!")

        # Guarda o nome antes da evolução
        old_name = pokemon.name

        # Realiza a evolução
        pokemon._perform_evolution(evolve_to_id)

        # Log de sucesso
        print(f"[EVOLUÇÃO] ✨ {old_name} evoluiu para {pokemon.name}!")
        print(f"[EVOLUÇÃO] Método: {evolve_method}")
        print(f"{'=' * 50}\n")

        # Atualiza a Pokedex do jogador (já viu o novo Pokémon)
        self.player.caught_pokemon.add(evolve_to_id)
        self.player.register_seen(evolve_to_id)

        # Salva o jogo automaticamente após evolução
        self.player.auto_save()

        return True

    def _attempt_capture(self, enemy, item_data):
        """Tenta capturar um Pokémon selvagem (boss não pode ser capturado)"""

        # ===== VERIFICA SE É BOSS =====
        if hasattr(enemy, 'is_boss') and enemy.is_boss:
            print(f"[CAPTURA]  {enemy.name} é um BOSS e não pode ser capturado!")
            print(f"[CAPTURA] Derrote o boss para continuar!")
            return False

        # Cálculo de chance de captura simplificado
        hp_ratio = enemy.current_hp / enemy.max_hp
        base_chance = (1 - hp_ratio * 0.5)

        # Multiplicador da pokebola
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

        print(f"[CAPTURA] Chance: {chance * 100:.1f}% | Rolagem: {roll * 100:.1f}%")

        if roll < chance or item_data["id"] == "masterball":
            # SUCESSO!

            # GUARDA referência ao item ANTES de resetar
            carried_item = enemy.is_carrying
            item_name = carried_item.item_name if carried_item else "nenhum item"

            # ANTES de remover o inimigo, verifica se ele está carregando um item
            if carried_item:
                enemy.drop_item()  # Usa o método unificado
                print(f"[CAPTURA] Item {item_name} foi resetado e continua no mapa")

            # Remove o inimigo
            self.wave_manager.remove_enemy(enemy)

            # CRIA UMA CÓPIA do Pokémon capturado
            from src.entities.pokemon import Pokemon
            caught = Pokemon(
                0, 0, enemy.id,
                level=enemy.level,
                is_wild=False,
                shiny=enemy.is_shiny
            )

            # Copia atributos importantes
            caught.current_hp = enemy.current_hp
            caught.max_hp = enemy.max_hp
            caught.ivs = enemy.ivs.copy()
            caught.evs = enemy.evs.copy()
            caught.xp = enemy.xp
            caught.nature = enemy.nature

            # Tenta adicionar ao time
            if self.player.has_team_space():
                self.player.add_to_team(caught)
                print(f"[CAPTURA] {enemy.name} adicionado ao time!")
            else:
                # Se time cheio, vai para a PC Box
                self.player.add_to_box(caught)
                print(f"[CAPTURA] {enemy.name} enviado para o PC Box!")

            # Atualiza a Pokedex
            self.player.caught_pokemon.add(enemy.id)
            self.player.register_seen(enemy.id)
            # Salva data
            self.player.auto_save()

            return True
        else:
            return False

    def _use_medicine(self, pokemon, item_data):
        """Usa poção em um Pokémon aliado"""
        if not pokemon.is_alive() and "revive" not in item_data["id"]:
            print(f"[POÇÃO] {pokemon.name} está derrotado! Use um Reviver.")
            return False

        heal_amount = item_data["effect_value"]

        if heal_amount == -1:  # Cura total
            pokemon.heal()
            print(f"[POÇÃO] {pokemon.name} recuperou todo HP!")

        elif "revive" in item_data["id"]:
            if pokemon.is_alive():
                print(f"[POÇÃO] {pokemon.name} já está vivo!")
                return False

            if heal_amount == 0.5:  # Revive com 50%
                pokemon.current_hp = int(pokemon.max_hp * 0.5)
                print(f"[POÇÃO] {pokemon.name} reviveu com metade do HP!")
            else:  # Max Revive (100%)
                pokemon.heal()
                print(f"[POÇÃO] {pokemon.name} reviveu com HP total!")

        else:  # Cura normal
            old_hp = pokemon.current_hp
            pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + heal_amount)
            healed = pokemon.current_hp - old_hp
            print(f"[POÇÃO] {pokemon.name} recuperou {healed} HP!")

        return True

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

    def cleanup(self):
        """Limpa o estado da fase antes de sair"""

        # 1. Libera todos os spots (usando occupied)
        for spot in self.spot_renderer.get_spots():
            spot.occupied = False

        # 2. Limpa todas as listas de Pokémon
        self.placed_pokemon.clear()

        if hasattr(self, 'placement_manager'):
            self.placement_manager.placed_pokemon.clear()

        # 3. Remove status de colocado dos Pokémon do time
        if hasattr(self, 'player'):
            for pokemon in self.player.team:
                pokemon.is_placed = False

        # 5. Limpa inimigos
        if hasattr(self, 'wave_manager'):
            self.wave_manager.active_enemies.clear()

    def handle_event(self, event):
        """Processa eventos do jogo"""

        # ===== PRIORIDADE 0: Overlays ativos =====
        if self.overlay_manager.is_active:
            if self.overlay_manager.handle_event(event):
                return None
            # Se o overlay não processou o evento, ainda assim não propaga para o jogo
            return None

        # ===== PRIORIDADE 1: Arrasto de item (se ativo) =====
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

        # ===== PRIORIDADE 2: Eventos da UI da mochila (sempre primeiro) =====
        if hasattr(self, 'item_bag_renderer'):
            bag_handled = self.item_bag_renderer.handle_event(event)
            if bag_handled:
                return None

        # ===== PRIORIDADE 3: Eventos de teclado globais =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if hasattr(self, 'player') and hasattr(self.player, 'bag'):
                    category = self.player.bag.cycle_category()
                    print(f"[ITENS] Categoria: {category}")
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

            elif event.key == pygame.K_g:
                self.show_grid = not self.show_grid
                return None

            elif event.key == pygame.K_SPACE:
                if self.game_state == "between_waves":
                    self.game_state = "in_wave"
                    self.wave_manager.start_next_wave()
                return None

        # ===== PRIORIDADE 4: Scroll do mouse =====
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()

            # Verifica se o mouse está sobre a UI da mochila
            if (hasattr(self.item_bag_renderer, 'mouse_over_ui') and
                    self.item_bag_renderer.mouse_over_ui):

                # Scroll da lista de itens
                if event.y > 0:
                    selected = self.player.bag.prev_item()
                    if selected:
                        print(f"[ITENS] Selecionado: {selected['name']}")
                elif event.y < 0:
                    selected = self.player.bag.next_item()
                    if selected:
                        print(f"[ITENS] Selecionado: {selected['name']}")

                self.item_bag_renderer.hovered_index = self.player.bag.selected_item_index
                return None

            # Se não está na UI, faz o zoom da câmera
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

        # ===== PRIORIDADE 5: Iniciar arrasto de item =====
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
                            print(f"[ITEM] Iniciando arrasto de {item['data']['name']}")
                            self.item_drag_manager.start_drag(
                                item["id"], mouse_pos, world_pos
                            )
                return None

        # ===== PRIORIDADE 6: Eventos do team manager =====
        if hasattr(self, 'team_manager'):
            result = self.team_manager.handle_event(
                event,
                self.spot_renderer.get_spots(),
                self.camera,
                self._on_pokemon_placed
            )
            if result:
                return None

        # ===== PRIORIDADE 7: Controles da câmera =====
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            in_viewport = self.screen_manager.is_mouse_in_viewport(mouse_pos)

            if event.button == 2:  # Botão do meio
                if in_viewport:
                    self.dragging_camera = True
                    self.last_mouse_pos = mouse_pos
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return None

            elif event.button == 3:  # Botão direito (recolher Pokémon)
                if not (hasattr(self.item_bag_renderer, 'mouse_over_ui') and
                        self.item_bag_renderer.mouse_over_ui):
                    world_pos = self.screen_manager.get_mouse_world_position(event.pos, self.camera)
                    if world_pos:
                        pokemon = self.placement_manager.remove_pokemon_by_right_click(
                            world_pos[0], world_pos[1]
                        )
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

            # Atualiza hover (só se não for game over)
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
        """Update da lógica do jogo - AGORA COM MÚLTIPLOS PATHS"""

        # Se estiver pausado, não atualiza nada
        if self.paused:
            return

        # ===== PRIORIDADE 1: Atualiza overlays se ativos =====
        if self.overlay_manager.is_active:
            self.overlay_manager.update(dt)
            return  # Não atualiza o jogo enquanto overlay está ativo

        # ===== RESTO DO UPDATE =====

        # Atualiza UI da mochila
        if hasattr(self, 'item_bag_renderer'):
            self.item_bag_renderer.update(dt)

        if hasattr(self, 'team_manager'):
            self.team_manager.update(dt)

        if hasattr(self, 'placement_manager'):
            # Passa os inimigos do wave_manager
            self.placement_manager.update(dt, self.wave_manager.active_enemies)

        if hasattr(self, 'spot_renderer'):
            self.spot_renderer.update(dt)

        for pokemon in self.placed_pokemon:
            pokemon.update(dt)

        self.target_item_manager.update(dt)

        # Verifica game over por itens levados
        if self.target_item_manager.game_over:
            self.game_state = "game_over"
            self.overlay_manager.show(OverlayType.GAME_OVER)
            print("GAME OVER - Todos os itens foram levados!")
            return

        # ===== ATUALIZA WAVE MANAGER =====
        # Monta dicionário com pontos de todos os paths
        path_points_by_index = {}
        for i in range(len(self.path_renderer.paths)):
            path_points = self.path_renderer.get_path_points(i)
            if path_points:
                path_points_by_index[i] = path_points
                if self.show_debug:
                    print(f"[DEBUG] Path {i + 1} tem {len(path_points)} pontos")

        # Atualiza wave manager - processa todos os paths simultaneamente
        enemies_at_end = self.wave_manager.update(
            dt,
            path_points_by_index,
            self.screen_manager
        )

        # Processa inimigos que chegaram ao fim
        for enemy in enemies_at_end:
            if enemy.is_carrying:
                item = enemy.is_carrying
                item.is_protected = False
                path_origin = getattr(enemy, 'path_index_origin', 0) + 1
                print(f"[FIM] Path {path_origin}: {enemy.name} levou {item.item_name}!")
                enemy.clear_carrying()

        # ===== VERIFICA ESTADO DO JOGO =====
        if self.game_state == "in_wave":
            # Verifica se TODAS as waves de TODOS os paths terminaram
            if self.wave_manager.is_wave_completely_finished():
                print(f"\n{'=' * 50}")
                print(f"[GAME] 🎉 TODAS AS WAVES DE TODOS OS PATHS FORAM CONCLUÍDAS!")
                print(f"{'=' * 50}\n")

                if self.target_item_manager.items_protected > 0:
                    print(f"[GAME] 🎉 PARABÉNS! Fase concluída com sucesso!")
                    self.game_state = "completed"
                    self._complete_phase()
                else:
                    print(f"[GAME] 💀 GAME OVER - Nenhum item foi protegido!")
                    self.game_state = "game_over"
                    self.overlay_manager.show(OverlayType.GAME_OVER)
            else:
                # Log detalhado para debug (só mostra a cada 60 frames para não floodar)
                if hasattr(self, '_debug_frame_counter'):
                    self._debug_frame_counter += 1
                else:
                    self._debug_frame_counter = 0

                if self._debug_frame_counter % 60 == 0 and self.show_debug:
                    print(f"\n[DEBUG] Status das waves por path:")
                    for path_idx, waves in self.wave_manager.path_waves.items():
                        status = "ATIVA" if self.wave_manager.wave_in_progress_by_path.get(path_idx,
                                                                                           False) else "inativa"
                        current = self.wave_manager.current_wave_index_by_path.get(path_idx, 0) + 1
                        total = len(waves)
                        spawned = self.wave_manager.enemies_spawned_by_path.get(path_idx, 0)
                        remaining = self.wave_manager.enemies_remaining_by_path.get(path_idx, 0)
                        wave_data = self.wave_manager.current_wave_data_by_path.get(path_idx, {})
                        wave_name = wave_data.get('name', f'Wave {current}') if wave_data else 'Aguardando'

                        print(f"  Path {path_idx + 1}: {status} | {wave_name} ({current}/{total}) | "
                              f"Spawnados: {spawned} | Vivos: {remaining}")

        elif self.game_state == "between_waves":
            self.between_waves_timer -= dt
            if self.between_waves_timer <= 0:
                # Verifica se ainda tem waves para começar
                any_wave_started = False
                for path_idx in self.wave_manager.path_waves.keys():
                    if self.wave_manager.current_wave_index_by_path.get(path_idx, 0) < len(
                            self.wave_manager.path_waves[path_idx]):
                        self.wave_manager._start_wave_for_path(path_idx)
                        any_wave_started = True
                        print(f"[BETWEEN] Path {path_idx + 1}: Iniciando próxima wave!")

                if any_wave_started:
                    self.game_state = "in_wave"
                else:
                    print(f"[BETWEEN] Não há mais waves para começar!")

    def _complete_phase(self):
        """Marca a fase como completada e dá as recompensas"""
        from src.config.progress import progress_manager

        print(f"\n{'=' * 50}")
        print(f"🎉 FASE COMPLETADA! 🎉".center(50))
        print(f"{'=' * 50}")
        print(f"Fase: {self.phase_id} - {self.phase_info.get('name', 'Desconhecida')}")
        print(f"Itens protegidos: {self.target_item_manager.items_protected}/{len(self.target_item_manager.items)}")
        print(f"Recompensas: ${self.phase_rewards['money']} | {self.phase_rewards['experience']} XP")
        print(f"{'=' * 50}\n")

        # Dá as recompensas
        self.player.money += self.phase_rewards['money']
        self.player.score += self.phase_rewards['experience']

        # Marca a fase como completada no progresso
        # Calcula estrelas baseado em quantos itens foram protegidos
        total_items = len(self.target_item_manager.items)
        protected_items = self.target_item_manager.items_protected
        if total_items > 0:
            stars = int((protected_items / total_items) * 3)
            stars = max(1, min(3, stars))  # Entre 1 e 3 estrelas
        else:
            stars = 3  # Se não tem itens, dá 3 estrelas

        progress_manager.complete_phase(self.phase_id, stars=stars)

        # Mostra a próxima fase se houver
        next_phase = progress_manager.get_next_phase(self.phase_id)
        if next_phase:
            print(f"️ Próxima fase desbloqueada: {next_phase}")
        else:
            print(" Você completou todas as fases disponíveis!")

        print(f"Saldo atual: ${self.player.money} | Pontuação: {self.player.score}")

        # MOSTRA OVERLAY DE FASE COMPLETA (NOVO)
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

        # Renderiza inimigos DO WAVE MANAGER
        for enemy in self.wave_manager.active_enemies:
            enemy.render(screen, self.camera, show_hp=False)

        if hasattr(self, 'placement_manager'):
            self.placement_manager.render(screen, self.camera, self.screen_manager)

        self.target_item_manager.render_in_pokemon(screen, self.camera)

        #HP ACIMA DOS SPRITES
        for enemy in self.wave_manager.active_enemies:
            enemy.render_hp(screen, self.camera)

        if hasattr(self, 'placement_manager'):
            self.placement_manager.render_hp(screen, self.camera)

        # UI do jogo
        self._render_game_ui(screen)

        if hasattr(self, 'team_manager'):
            self.team_manager.render(screen, self.camera, self.spot_renderer.get_spots())

        if hasattr(self, 'item_drag_manager'):
            self.item_drag_manager.render(screen, self.camera)

        if hasattr(self, 'item_bag_renderer'):
            self.item_bag_renderer.render(screen)

        # Grid e bordas
        if self.show_grid:
            self._draw_grid_aligned(screen)

        pygame.draw.rect(screen, (80, 80, 80),
                         (self.screen_manager.viewport_x,
                          self.screen_manager.viewport_y,
                          self.screen_manager.viewport_width,
                          self.screen_manager.viewport_height), 1)

        if self.paused:
            self._render_pause_overlay(screen)

        # Renderiza overlays por cima de tudo =====
        self.overlay_manager.render(screen)

        if self.show_debug:
            self._render_debug_info(screen)

    def _render_game_ui(self, screen):
        """Renderiza a UI do jogo - ADAPTADA PARA MÚLTIPLOS PATHS"""
        font = pygame.font.Font(None, 24)
        font_small = pygame.font.Font(None, 18)

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
            # Mostra quantos paths estão ativos
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

            # Barra de progresso (consolidada)
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
        """Informações de debug detalhadas - AGORA COM DADOS DE MÚLTIPLOS PATHS"""
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

                # Verifica se está em algum path
                path_info = "Nenhum path"
                for i, path in enumerate(self.path_renderer.paths):
                    for node in path.nodes:
                        dist = ((node[0] - world_pos[0]) ** 2 + (node[1] - world_pos[1]) ** 2) ** 0.5
                        if dist < 20:  # Tolerância de 20 pixels
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

        # Linhas básicas de debug
        debug_lines = [
            "=== DEBUG INFO ===",
            f"Fase: {self.phase_info.get('name', 'Desconhecida')}",
            f"Capítulo: {self.phase_info.get('chapter', 1)} | Nº: {self.phase_number}",
            f"FPS: {self.screen_manager.get_fps():.1f}",
            f"Delta Time: {self.screen_manager.get_delta_time() * 1000:.1f}ms",
            f"Grid: {'ON' if self.show_grid else 'OFF'}",
            f"Game State: {self.game_state}",
            f"Camera Drag: {'ACTIVE' if self.dragging_camera else 'inactive'}",
            "",
            "=== WAVES (CONSOLIDADO) ===",
            f"Status: {wave_info['name']}",
            f"Inimigos totais: {wave_info['enemies_spawned']}/{wave_info['enemies_total']} spawnados",
            f"Vivos agora: {len(self.wave_manager.active_enemies)}",
            f"Progresso geral: {wave_info['progress'] * 100:.1f}%",
            "",
            "=== WAVES POR PATH ===",
        ]

        # Adiciona informações detalhadas de cada path
        if hasattr(self.wave_manager, 'path_waves'):
            total_paths = len(self.wave_manager.path_waves)
            debug_lines.append(f"Total de paths com waves: {total_paths}")
            debug_lines.append("")

            for path_idx, waves in sorted(self.wave_manager.path_waves.items()):
                # Pega o estado deste path
                current_idx = self.wave_manager.current_wave_index_by_path.get(path_idx, 0)
                total_waves = len(waves)
                in_progress = self.wave_manager.wave_in_progress_by_path.get(path_idx, False)
                spawned = self.wave_manager.enemies_spawned_by_path.get(path_idx, 0)
                remaining = self.wave_manager.enemies_remaining_by_path.get(path_idx, 0)

                # Pega dados da wave atual se existir
                wave_data = self.wave_manager.current_wave_data_by_path.get(path_idx)
                if wave_data:
                    wave_name = wave_data.get('name', f'Wave {current_idx + 1}')
                    wave_size = wave_data.get('wave_size', 10)
                    repeat = wave_data.get('repeat_wave', False)
                    repeat_count = wave_data.get('repeat_count', 1) if repeat else 0
                    delay = wave_data.get('initial_delay', 2.0)
                    interval = wave_data.get('spawn_interval', 3.0)
                else:
                    wave_name = 'Aguardando'
                    wave_size = 0
                    repeat = False
                    repeat_count = 0
                    delay = 0
                    interval = 0

                # Status do path
                status_icon = "🟢" if in_progress else "⏸️"
                if current_idx >= total_waves and total_waves > 0:
                    status_icon = "✅"  # Concluído

                debug_lines.append(f"  {status_icon} Path {path_idx + 1}:")
                debug_lines.append(
                    f"      Waves: {current_idx + 1 if current_idx < total_waves else total_waves}/{total_waves}")
                debug_lines.append(f"      Atual: {wave_name}")
                debug_lines.append(f"      Progresso: {spawned}/{wave_size if wave_size > 0 else 'N/A'}")
                debug_lines.append(f"      Vivos: {remaining}")

                if in_progress and wave_data:
                    timer = self.wave_manager.wave_timer_by_path.get(path_idx, 0)
                    if timer > 0:
                        debug_lines.append(f"      ⏳ Delay inicial: {timer:.1f}s")

                    if repeat:
                        debug_lines.append(f"      🔁 Repetições restantes: {repeat_count}")

                debug_lines.append(f"      ⚙️ Config: delay={delay:.1f}s | intervalo={interval:.1f}s")

                # Mostra composição da wave atual
                if wave_data and wave_data.get('enemies'):
                    debug_lines.append(f"      📊 Composição:")
                    for e in wave_data['enemies']:
                        from src.data.pokedex import Pokedex
                        pokedex = Pokedex()
                        name = pokedex.get_name(e['pokemon_id'])
                        debug_lines.append(f"         - {name}: {e['percentage']}%")

        debug_lines.extend([
            "",
            "=== CAMERA ===",
            f"Position: ({self.camera.x:.0f}, {self.camera.y:.0f})",
            f"Zoom: {self.camera.zoom:.2f}",
            f"Visible: {self.screen_manager.render_width / self.camera.zoom:.0f} x {self.screen_manager.render_height / self.camera.zoom:.0f}",
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
            path_info,
            "",
            "=== MAPA ===",
            f"Tiles: {self.map_renderer.layer_manager.width}x{self.map_renderer.layer_manager.height}",
            f"Pixels: {self.world_width}x{self.world_height}",
            f"Grid size: {self.grid_size}px",
            f"Paths desenhados: {len(self.path_renderer.paths)}",
        ])

        # Detalhes dos paths renderizados
        for i, path in enumerate(self.path_renderer.paths):
            debug_lines.append(f"  Path {i + 1}: {len(path.nodes)} pontos | Cor: {path.line_color}")

        debug_lines.extend([
            f"Pokémon colocados: {len(self.placement_manager.placed_pokemon) if hasattr(self, 'placement_manager') else 0}",
            f"Spots disponíveis: {len(self.spot_renderer.get_spots())}",
            f"Spots ocupados: {sum(1 for s in self.spot_renderer.get_spots() if s.occupied)}",
            "",
            "=== ITENS ALVO ===",
            f"Protegidos: {self.target_item_manager.items_protected}",
            f"Levados: {self.target_item_manager.items_stolen}",
            f"Restantes: {len([i for i in self.target_item_manager.items if not i.is_protected and not i.is_stolen])}",
        ])

        # Renderiza o debug
        y_offset = self.screen_manager.viewport_y + 40
        x_offset = self.screen_manager.viewport_x + 10
        font_small = pygame.font.Font(None, 18)

        line_height = 16
        bg_height = len(debug_lines) * line_height + 10
        bg_width = 450  # Aumentado para comportar mais informações
        bg_surface = pygame.Surface((bg_width, bg_height))
        bg_surface.set_alpha(200)  # Mais opaco para melhor legibilidade
        bg_surface.fill((0, 0, 0))
        screen.blit(bg_surface, (x_offset - 5, y_offset - 5))

        for line in debug_lines:
            if line.startswith("==="):
                color = (255, 255, 0)  # Amarelo para títulos
                font_bold = pygame.font.Font(None, 20)
                text = font_bold.render(line, True, color)
            elif "🟢" in line or "✅" in line:
                color = (100, 255, 100)  # Verde para paths ativos
                text = font_small.render(line, True, color)
            elif "⏸️" in line:
                color = (255, 255, 100)  # Amarelo para paths inativos
                text = font_small.render(line, True, color)
            elif "Path" in line and not line.startswith(" "):
                color = (100, 200, 255)  # Azul claro para cabeçalhos de path
                text = font_small.render(line, True, color)
            elif line.strip().startswith("-"):
                color = (180, 180, 180)  # Cinza claro para itens de composição
                text = font_small.render(line, True, color)
            else:
                color = (0, 255, 0)  # Verde para informações normais
                text = font_small.render(line, True, color)

            screen.blit(text, (x_offset, y_offset))
            y_offset += line_height
