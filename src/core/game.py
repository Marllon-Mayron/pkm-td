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
        Carrega o ÚLTIMO slot usado (persistido em saves/last_slot.txt).
        Se não houver nada, cai no slot 1 (comportamento antigo).
        """
        from src.managers.save_manager import save_manager
        from src.config.progress import progress_manager

        slot = self._read_last_slot()  # <-- NOVO
        save_file = os.path.join("saves", f"save_{slot}.json")

        if os.path.exists(save_file):
            print(f"[GAME] Save existente encontrado (slot {slot}) - carregando...")
            success = save_manager.load_game(self.player, slot)
            if success:
                print(f"[GAME] Save slot {slot} carregado com sucesso!")
                progress_manager.reload_progress()
                return
            print(f"[GAME] Erro ao carregar slot {slot} - criando novo...")
        else:
            print(f"[GAME] Nenhum save no slot {slot} - criando novo...")

        self._create_initial_save(slot=slot)

    # ---------- helpers ----------
    def _last_slot_path(self):
        return os.path.join("saves", "last_slot.txt")

    def _read_last_slot(self) -> int:
        path = self._last_slot_path()
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    n = int(f.read().strip())
                if 1 <= n <= 3:
                    return n
        except Exception as e:
            print(f"[GAME] last_slot inválido, usando 1: {e}")
        return 1

    def write_last_slot(self, slot: int):
        """Persiste o slot atual para o próximo boot."""
        try:
            os.makedirs("saves", exist_ok=True)
            with open(self._last_slot_path(), "w", encoding="utf-8") as f:
                f.write(str(int(slot)))
            print(f"[GAME] last_slot = {slot}")
        except Exception as e:
            print(f"[GAME] Erro ao gravar last_slot: {e}")

    def _create_initial_save(self, slot: int = 1):
        from src.managers.save_manager import save_manager
        from src.config.progress import progress_manager

        print(f"[GAME] Criando save inicial vazio (slot {slot})...")

        if not hasattr(self.player, 'desfossilizadores') or not self.player.desfossilizadores:
            if hasattr(self.player, '_add_initial_desfossilizador'):
                self.player._add_initial_desfossilizador()

        self.player.has_chosen_starter = False

        game_state = {
            "current_region": 1,
            "current_chapter": 1,
            "current_phase": 1,
            "unlocked_chapters": [1],
            "unlocked_phases": ["1:1:1"],
            "completed_phases": [],
            "stars": {},
        }

        success = save_manager.save_game(
            self.player, game_state,
            save_name=f"Save {slot}", slot=slot,
        )

        if success:
            print(f"[GAME] Save inicial criado com sucesso no slot {slot}!")
            self.write_last_slot(slot)  # <-- NOVO
            progress_manager.reload_progress()
        else:
            print("[GAME] ERRO: Não foi possível criar o save inicial!")

    def load_save_slot(self, slot=1) -> bool:
        from src.managers.save_manager import save_manager
        from src.config.progress import progress_manager

        success = save_manager.load_game(self.player, slot)
        if success:
            self.write_last_slot(slot)  # <-- NOVO
            progress_manager.reload_progress()
            print(f"[GAME] Slot {slot} carregado com sucesso")
            return True
        print(f"[GAME] Falha ao carregar o slot {slot}")
        return False

    def start_new_game_in_slot(self, slot=1):
        from src.managers.save_manager import save_manager
        from src.config.progress import progress_manager

        self.player.reset_all_data()

        game_state = {
            "current_region": 1,
            "current_chapter": 1,
            "current_phase": 1,
            "unlocked_chapters": [1],
            "unlocked_phases": ["1:1:1"],
            "completed_phases": [],
            "stars": {},
        }
        save_manager.save_game(
            self.player, game_state,
            save_name=f"Save {slot}", slot=slot,
        )
        save_manager.current_save_file = slot  # ← ESSENCIAL
        self.write_last_slot(slot)
        progress_manager.reload_progress()
        print(f"[GAME] Novo jogo iniciado no slot {slot}")

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
                elif event.key == pygame.K_F9:
                    from src.ui.anim_editor_scene.anim_editor_scene import AnimEditorScene
                    self.current_scene = AnimEditorScene(self)
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