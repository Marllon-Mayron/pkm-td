# src/core/game.py

"""
Classe principal do jogo
"""
import pygame

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

        # Cria o jogador primeiro
        self.player = Player(100, 100)

        # Câmera
        self.camera = None

        # Acumulador para updates fixos
        self.update_accumulator = 0
        self.update_step = 1.0 / settings.game_tick_rate

        # Gerenciamento de cenas
        self.current_scene = None
        self.menu_scene = MenuScene(self)

        # Referências para cenas (serão inicializadas quando necessárias)
        self.starter_select_scene = None
        self.phase_select_scene = None
        self.team_select_scene = None
        self.game_scene = None
        self.shop_scene = None

        # Começa sempre com o menu
        self.current_scene = self.menu_scene

        print(f"Jogo inicializado - FPS alvo: {settings.target_fps}")
        print(f"Tick rate do jogo: {settings.game_tick_rate} updates/segundo")
        print(f"Cena inicial: MenuScene")

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
                print(f"Janela redimensionada para: {event.w}x{event.h}")

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.screen_manager.toggle_fullscreen()

            # Passa eventos para a cena atual
            if self.current_scene:
                self.current_scene.handle_event(event)

    def fixed_update(self, dt):
        """Update fixo para lógica do jogo"""
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