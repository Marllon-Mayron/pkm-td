"""
Classe principal do jogo
"""
import pygame
from src.config.settings import settings
from src.core.screen import ScreenManager
from src.core.camera import Camera
from src.entities.player import Player  # Importa a classe Player
from src.scenes.menu_scene import MenuScene
from src.managers.sound_manager import sound_manager

class Game:
    def __init__(self):
        pygame.init()
        self.screen_manager = ScreenManager()
        self.running = True

        # Cria o jogador primeiro (sem starter)
        self.player = Player(100, 100)

        # TENTA CARREGAR O SAVE AUTOMATICAMENTE
        save_loaded = self.player.load_game(1)  # Tenta carregar slot 1

        if not save_loaded:
            # Se não tinha save, cria um Pokémon inicial
            print("[GAME] Nenhum save encontrado, criando novo jogo")
            self.player.add_starter(7)  # ID 7 = Squirtle
        else:
            print("[GAME] Save carregado com sucesso!")
            print(f"  - Time: {len(self.player.team)} Pokémon")
            print(f"  - Box: {len(self.player.pc_box)} Pokémon")
            print(f"  - Itens: {self.player.bag.items}")

        # Câmera
        self.camera = None

        # Acumulador para updates fixos
        self.update_accumulator = 0
        self.update_step = 1.0 / settings.game_tick_rate

        # Gerenciamento de cenas
        self.current_scene = None
        self.menu_scene = MenuScene(self)

        # Referências para cenas (serão inicializadas quando necessárias)
        self.phase_select_scene = None
        self.team_select_scene = None
        self.game_scene = None

        # Começa com o menu
        self.current_scene = self.menu_scene

        print(f"Jogo inicializado - FPS alvo: {settings.target_fps}")
        print(f"Tick rate do jogo: {settings.game_tick_rate} updates/segundo")
        print(f"Jogador criado com time: {len(self.player.team)} Pokémon")

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
        settings.save_settings()
        pygame.quit()