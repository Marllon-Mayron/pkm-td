# src/core/game.py

"""
Classe principal do jogo
"""
import pygame
import os

from src.config.settings import settings
from src.core.screen import ScreenManager
from src.core.camera import Camera
from src.entities.player import Player
from src.scenes.menu_scene import MenuScene


class Game:
    def __init__(self):
        pygame.init()
        self.screen_manager = ScreenManager()
        self.running = True
        self.current_version = ""

        # Cria o jogador
        self.player = Player(100, 100)

        # ===== CARREGA OU CRIA SAVE AUTOMATICAMENTE =====
        self._initialize_save()

        # Câmera
        self.camera = None

        # Acumulador para updates fixos
        self.update_accumulator = 0
        self.update_step = 1.0 / settings.game_tick_rate

        # Gerenciamento de cenas
        self.current_scene = None
        self.menu_scene = MenuScene(self)

        # Referências para cenas (serão inicializadas quando necessárias)
        self.pokedex_scene = None
        self.starter_select_scene = None
        self.phase_select_scene = None
        self.team_select_scene = None
        self.game_scene = None
        self.shop_scene = None

        # Começa sempre com o menu
        self.current_scene = self.menu_scene

        print(f"Jogo inicializado - FPS alvo: {settings.target_fps}")
        print(f"Tick rate do jogo: {settings.game_tick_rate} updates/segundo")

    def _initialize_save(self):
        """
        Inicializa o save automaticamente.
        - Se existir save, carrega
        - Se não existir, cria um save inicial vazio
        """
        from src.managers.save_manager import save_manager
        from src.config.progress import progress_manager

        # Verifica se existe save_1.json
        save_file = os.path.join("saves", "save_1.json")
        save_exists = os.path.exists(save_file)

        if save_exists:
            print("[GAME] Save existente encontrado - carregando...")
            success = self.player.load_game(1)
            if success:
                print("[GAME] Save carregado com sucesso!")
                # Carrega as configurações do save
                progress_manager._load_settings_from_save()
                return
            else:
                print("[GAME] Erro ao carregar save - criando novo...")
        else:
            print("[GAME] Nenhum save encontrado - criando novo...")

        # Cria um save inicial vazio
        self._create_initial_save()

    def _create_initial_save(self):
        """
        Cria um save inicial vazio.
        Isso permite que o jogador acesse configurações, mystery gift, etc.
        """
        from src.managers.save_manager import save_manager
        from src.config.progress import progress_manager

        print("[GAME] Criando save inicial vazio...")

        # Garante que o jogador tem um desfossilizador
        if not hasattr(self.player, 'desfossilizadores') or not self.player.desfossilizadores:
            if hasattr(self.player, '_add_initial_desfossilizador'):
                self.player._add_initial_desfossilizador()

        # ===== GARANTE QUE HAS_CHOSEN_STARTER É FALSE =====
        self.player.has_chosen_starter = False

        # Salva o jogo com estado inicial
        game_state = {
            "current_chapter": 1,
            "current_phase": 1,
            "unlocked_chapters": [1],
            "unlocked_phases": ["1-1"],
            "completed_phases": [],
            "stars": {}
        }

        success = save_manager.save_game(self.player, game_state, save_name="Save 1", slot=1)

        if success:
            print("[GAME] Save inicial criado com sucesso!")
            # Carrega as configurações do save
            progress_manager._load_settings_from_save()
        else:
            print("[GAME] ERRO: Não foi possível criar o save inicial!")

    def initialize_camera(self, world_width, world_height):
        """Inicializa a câmera com o tamanho do mundo"""
        from src.core.render_context import render_context
        self.camera = Camera(world_width, world_height, self.screen_manager)
        render_context.invalidate_cache()  # Invalida cache quando câmera muda

    def run(self):
        """Loop principal do jogo"""
        while self.running:
            # Processa eventos
            self.handle_events()

            # Updates fixos
            dt = self.screen_manager.get_delta_time()
            self.update_accumulator += dt

            while self.update_accumulator >= self.update_step:
                self.fixed_update(self.update_step)
                self.update_accumulator -= self.update_step

            # Renderização
            self.render()

            # Flip (atualiza a tela)
            self.screen_manager.flip()

            # Pequeno delay para não consumir CPU desnecessariamente
            pygame.time.wait(1)

    def handle_events(self):
        """Processa eventos do pygame"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.VIDEORESIZE:
                self.screen_manager.handle_resize(event.w, event.h)

                # Propaga para a cena atual
                if self.current_scene and hasattr(self.current_scene, 'on_resize'):
                    self.current_scene.on_resize()

                print(f"Janela redimensionada para: {event.w}x{event.h}")

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.screen_manager.toggle_fullscreen()

            # Passa eventos para a cena atual
            if self.current_scene:
                self.current_scene.handle_event(event)

    def fixed_update(self, dt):
        """Update fixo para lógica do jogo"""
        # Acumular tempo de jogo
        if hasattr(self.player, 'total_playtime'):
            self.player.total_playtime += dt

        # Atualiza desfossilizadores (incubadora) em segundo plano
        if hasattr(self.player, 'update_desfossilizadores'):
            self.player.update_desfossilizadores(dt)

        if self.current_scene and not self.current_scene.paused:
            self.current_scene.fixed_update(dt)

    def render(self):
        """Renderização do jogo"""
        # Limpa a tela
        self.screen_manager.clear()

        # Renderiza a cena atual
        if self.current_scene:
            self.current_scene.render(self.screen_manager.screen)

    def quit(self):
        """Finaliza o jogo"""
        # Salva as configurações atuais antes de sair
        settings.save_settings()

        # Salva o progresso atual se houver um save carregado
        from src.config.progress import progress_manager
        if progress_manager.save_manager.current_save_file:
            progress_manager._sync_with_save_manager()
            print("[GAME] Progresso salvo antes de sair")

        pygame.quit()