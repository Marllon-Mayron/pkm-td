# src/scenes/menu_scene.py

"""
Cena do menu principal
"""
import pygame
import random
import os
import json

from src.scenes.base_scene import BaseScene
from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
from src.scenes.settings_scene.settings_scene import SettingsScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, callback, font):
        # Coordenadas relativas (0-1) para responsividade
        self.relative_x = x
        self.relative_y = y
        self.relative_width = width
        self.relative_height = height

        # Valores absolutos calculados
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.callback = callback
        self.is_hovered = False
        self.font = font

        # Texto pré-renderizado
        self.text_surface = None
        self.text_rect = None

        # Controle de hover para som
        self._was_hovered = False

    def update_absolute_position(self, viewport_width, viewport_height, viewport_x, viewport_y):
        """Atualiza posição absoluta baseada no tamanho do viewport"""
        # Calcula posição absoluta dentro do viewport
        abs_x = viewport_x + int(self.relative_x * viewport_width)
        abs_y = viewport_y + int(self.relative_y * viewport_height)
        abs_width = int(self.relative_width * viewport_width)
        abs_height = int(self.relative_height * viewport_height)

        self.rect = pygame.Rect(abs_x, abs_y, abs_width, abs_height)

        # Atualiza texto
        font_size = max(24, int(viewport_height * 0.05))
        self.font = pygame.font.Font(None, font_size)
        self.text_surface = self.font.render(self.text, True, (255, 255, 255))
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def handle_event(self, event):
        """Processa eventos sem precisar de viewport_offset"""
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)

            # Toca som de hover quando o mouse entra no botão
            if self.is_hovered and not was_hovered:
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                sound_manager.play_effect(SoundEffect.CLICK)
                self.callback()

    def render(self, screen):
        """Renderiza botão"""
        if not self.text_surface:
            return

        # Desenha botão
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 3)

        # Desenha texto
        screen.blit(self.text_surface, self.text_rect)


class MenuScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        # Logo
        self.logo = None
        self.create_logo()

        # ===== VERIFICA SE JÁ ESCOLHEU O INICIAL =====
        has_starter = getattr(self.game.player, 'has_chosen_starter', False)

        # Define o texto do botão baseado no status
        if has_starter:
            start_text = "Continuar Jogo"
        else:
            start_text = "Iniciar Jogo"

        # ===== ESTADO DE CONFIRMAÇÃO DE RESET =====
        self.reset_confirmation_active = False
        self.reset_confirmation_timer = 0
        self._confirm_yes_rect = None
        self._confirm_no_rect = None

        # Botões
        self.buttons = [
            Button(0.3, 0.5, 0.4, 0.08, start_text,
                   (100, 100, 0), (150, 150, 0), self.start_game, None),
            Button(0.3, 0.6, 0.4, 0.08, "Configurações",
                   (100, 100, 0), (150, 150, 0), self.open_settings, None),
            Button(0.3, 0.4, 0.4, 0.08, "Editor de Fases",
                   (100, 100, 0), (150, 150, 0), self.open_editor, None),
            Button(0.015, 0.86, 0.15, 0.06, "Mystery Gift",
                   (100, 50, 100), (150, 80, 150), self.open_mystery_gift, None),
            # ===== BOTÃO DE RESET (VERMELHO) =====
            Button(0.83, 0.86, 0.15, 0.06, "RESETAR",
                   (120, 20, 20), (180, 30, 30), self.show_reset_confirmation, None),
            Button(0.3, 0.7, 0.4, 0.08, "Sair",
                   (100, 0, 0), (150, 0, 0), self.quit_game, None)
        ]

        # Partículas
        self.particles = []
        self.create_particles()

        # Controle de música
        self._music_started = False

        # INICIA A MÚSICA DO MENU IMEDIATAMENTE
        self._start_menu_music()

    def _start_menu_music(self):
        """Inicia a música do menu"""
        if not self._music_started:
            success = sound_manager.play_menu_music("Title_Theme", loop=True)
            if success:
                self._music_started = True
                print("[MENU] Música do menu iniciada: Title_Theme")
            else:
                # Tenta tocar a música padrão se Title_Theme não existir
                print("[MENU] Tentando tocar música alternativa...")
                success = sound_manager.play_menu_music("Come_Along", loop=True)
                if success:
                    self._music_started = True
                    print("[MENU] Música do menu iniciada: Come_Along (fallback)")

    def create_logo(self):
        """Cria um logo simples"""
        self.logo = pygame.Surface((400, 100), pygame.SRCALPHA)
        pygame.draw.rect(self.logo, (255, 215, 0), (0, 0, 400, 100), border_radius=20)
        pygame.draw.rect(self.logo, (200, 0, 0), (10, 10, 380, 80), border_radius=15)

        font = pygame.font.Font(None, 48)
        text = font.render("POKEMON", True, (255, 255, 255))
        text_rect = text.get_rect(center=(200, 35))
        self.logo.blit(text, text_rect)

        text2 = font.render("TOWER DEFENSE", True, (255, 255, 255))
        text_rect2 = text2.get_rect(center=(200, 70))
        self.logo.blit(text2, text_rect2)

    def create_particles(self):
        """Cria partículas decorativas"""
        for _ in range(20):
            self.particles.append({
                'x': pygame.math.Vector2(
                    random.uniform(0, self.screen_manager.render_width),
                    random.uniform(0, self.screen_manager.render_height)
                ),
                'vel': pygame.math.Vector2(
                    random.uniform(-20, 20),
                    random.uniform(-20, 20)
                ),
                'color': (random.randint(100, 255),
                          random.randint(100, 255),
                          random.randint(100, 255)),
                'size': random.randint(2, 5)
            })

    def handle_event(self, event):
        """Processa eventos"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_RETURN:
                self.start_game()
            # Tecla ESC fecha a confirmação de reset
            elif event.key == pygame.K_ESCAPE and self.reset_confirmation_active:
                self.reset_confirmation_active = False
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

        # Se a confirmação está ativa, processa os botões de confirmação
        if self.reset_confirmation_active:
            self._handle_reset_confirmation_event(event)
            # Não processa outros eventos enquanto a confirmação está ativa
            return

        for button in self.buttons:
            button.handle_event(event)

    def _handle_reset_confirmation_event(self, event):
        """Processa eventos da confirmação de reset"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            # Verifica se o botão SIM foi clicado
            if self._confirm_yes_rect and self._confirm_yes_rect.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._execute_reset()
                return

            # Verifica se o botão NÃO foi clicado
            if self._confirm_no_rect and self._confirm_no_rect.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.reset_confirmation_active = False
                return

        # Tecla ESC também fecha
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.reset_confirmation_active = False
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def show_reset_confirmation(self):
        """Mostra o diálogo de confirmação de reset"""
        if not self.reset_confirmation_active:
            self.reset_confirmation_active = True
            self.reset_confirmation_timer = 0
            sound_manager.play_effect(SoundEffect.CLICK)

    def _execute_reset(self):
        """Executa o reset do progresso"""
        print("[MENU] === INICIANDO RESET DE PROGRESSO ===")

        try:
            # ===== 1. RESETA O JOGADOR =====
            # Limpa time e box
            self.game.player.team.clear()
            self.game.player.pc_box.clear()

            # Reseta recursos
            self.game.player.money = 100
            self.game.player.score = 0

            # Reseta Pokédex
            self.game.player.seen_pokemon.clear()
            self.game.player.caught_pokemon.clear()

            # Reseta conquistas
            self.game.player.achievements = {
                "unlocked": [],
                "counters": {},
                "unlocked_data": {}
            }

            # Reseta desfossilizadores
            self.game.player.desfossilizadores.clear()
            if hasattr(self.game.player, '_add_initial_desfossilizador'):
                self.game.player._add_initial_desfossilizador()

            # Reseta flags
            self.game.player.has_chosen_starter = False
            self.game.player.total_playtime = 0.0

            # Reseta Mystery Gift
            self.game.player.redeemed_codes = {}
            self.game.player.mystery_gift_history = []

            # Reseta posição
            self.game.player.x = 100
            self.game.player.y = 100

            # Reseta bag
            self.game.player.bag.items = {}
            if hasattr(self.game.player.bag, '_update_filtered_items'):
                self.game.player.bag._update_filtered_items()

            print("[MENU] Dados do jogador resetados em memória")

            # ===== 2. DELETA OS ARQUIVOS DE SAVE =====
            saves_dir = "saves"
            deleted_count = 0

            if os.path.exists(saves_dir):
                for i in range(1, 4):  # Slots 1-3
                    save_file = os.path.join(saves_dir, f"save_{i}.json")
                    if os.path.exists(save_file):
                        try:
                            os.remove(save_file)
                            deleted_count += 1
                            print(f"[MENU] Save {i} deletado: {save_file}")
                        except Exception as e:
                            print(f"[MENU] Erro ao deletar save {i}: {e}")

                # Também deleta arquivos pickle se existirem
                for i in range(1, 4):
                    pickle_file = os.path.join(saves_dir, f"save_{i}.pkl")
                    if os.path.exists(pickle_file):
                        try:
                            os.remove(pickle_file)
                            print(f"[MENU] Pickle {i} deletado: {pickle_file}")
                        except Exception as e:
                            pass
            else:
                print("[MENU] Pasta de saves não encontrada")

            print(f"[MENU] {deleted_count} arquivo(s) de save deletado(s)")

            # ===== 3. RESETA O SAVE_MANAGER =====
            from src.managers.save_manager import save_manager
            save_manager.current_save_file = None
            save_manager.save_data = save_manager._get_default_save_data()
            print("[MENU] SaveManager resetado")

            # ===== 4. CRIA UM NOVO SAVE INICIAL =====
            from src.config.progress import progress_manager
            game_state = {
                "current_chapter": 1,
                "current_phase": 1,
                "unlocked_chapters": [1],
                "unlocked_phases": ["1-1"],
                "completed_phases": [],
                "stars": {}
            }

            success = save_manager.save_game(
                self.game.player,
                game_state,
                save_name="Save 1",
                slot=1
            )

            if success:
                print("[MENU] Novo save inicial criado com sucesso!")
                progress_manager._load_settings_from_save()
            else:
                print("[MENU] ERRO: Não foi possível criar o novo save inicial!")

            # ===== 5. FECHA A CONFIRMAÇÃO =====
            self.reset_confirmation_active = False

            # ===== 6. ATUALIZA O MENU =====
            # Recria os botões com o novo estado
            self._refresh_buttons()

            print("[MENU] === RESET DE PROGRESSO CONCLUÍDO ===")

            # Toca som de confirmação
            sound_manager.play_effect(SoundEffect.CLICK)

        except Exception as e:
            print(f"[MENU] ERRO durante o reset: {e}")
            import traceback
            traceback.print_exc()
            self.reset_confirmation_active = False

    def _refresh_buttons(self):
        """Recria os botões com o estado atualizado do jogador"""
        has_starter = getattr(self.game.player, 'has_chosen_starter', False)

        if has_starter:
            start_text = "Continuar Jogo"
        else:
            start_text = "Iniciar Jogo"

        # Atualiza o texto do primeiro botão
        self.buttons[0].text = start_text
        # Força a re-renderização do texto
        self.buttons[0].text_surface = None

    def fixed_update(self, dt):
        """Update para animações"""
        if self.paused:
            return

        for particle in self.particles:
            particle['x'] += particle['vel'] * dt
            if particle['x'].x < 0 or particle['x'].x > self.screen_manager.render_width:
                particle['vel'].x *= -1
            if particle['x'].y < 0 or particle['x'].y > self.screen_manager.render_height:
                particle['vel'].y *= -1

        # Atualiza timer da confirmação
        if self.reset_confirmation_active:
            self.reset_confirmation_timer += dt

    def render(self, screen):
        """Renderiza o menu"""
        self._draw_gradient_background(screen)

        # Atualiza posições dos botões
        for button in self.buttons:
            button.update_absolute_position(
                self.screen_manager.viewport_width,
                self.screen_manager.viewport_height,
                self.screen_manager.viewport_x,
                self.screen_manager.viewport_y
            )

        # Desenha partículas
        for particle in self.particles:
            screen_x = self.screen_manager.viewport_x + int(particle['x'].x)
            screen_y = self.screen_manager.viewport_y + int(particle['x'].y)
            pygame.draw.circle(screen, particle['color'], (screen_x, screen_y), particle['size'])

        # Desenha logo
        logo_width = int(self.screen_manager.viewport_width * 0.4)
        logo_height = int(self.screen_manager.viewport_height * 0.15)
        logo_scaled = pygame.transform.scale(self.logo, (logo_width, logo_height))
        logo_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - logo_width) // 2
        logo_y = self.screen_manager.viewport_y + int(self.screen_manager.viewport_height * 0.2)
        screen.blit(logo_scaled, (logo_x, logo_y))

        # Desenha botões
        for button in self.buttons:
            button.render(screen)

        # Versão
        font_small = pygame.font.Font(None, 20)
        version_text = font_small.render("v" + self.game.current_version + " - Em desenvolvimento", True,
                                         (150, 150, 150))
        version_x = self.screen_manager.viewport_x + 10
        version_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height - 25
        screen.blit(version_text, (version_x, version_y))

        # ===== RENDERIZA DIÁLOGO DE CONFIRMAÇÃO DE RESET =====
        if self.reset_confirmation_active:
            self._render_reset_confirmation(screen)

        if self.paused:
            self._render_pause_overlay(screen)

    def _render_reset_confirmation(self, screen):
        """Renderiza o diálogo de confirmação de reset"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Overlay escuro
        overlay = pygame.Surface((self.screen_manager.window_width, self.screen_manager.window_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Container do diálogo
        container_width = int(vw * 0.5)
        container_height = int(vh * 0.4)
        container_x = vx + (vw - container_width) // 2
        container_y = vy + (vh - container_height) // 2 - 40

        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)

        # Fundo do container com borda vermelha
        pygame.draw.rect(screen, (30, 20, 20), container_rect, border_radius=15)
        pygame.draw.rect(screen, (200, 40, 40), container_rect, 3, border_radius=15)
        pygame.draw.rect(screen, (255, 60, 60), container_rect.inflate(-6, -6), 1, border_radius=12)

        # ===== TÍTULO =====
        title_font = pygame.font.Font(None, int(vh * 0.045))
        title_text = title_font.render("RESETAR PROGRESSO", True, (255, 80, 80))
        title_x = container_x + (container_width - title_text.get_width()) // 2
        title_y = container_y + int(container_height * 0.08)
        screen.blit(title_text, (title_x, title_y))

        # ===== MENSAGEM DE AVISO =====
        warn_font = pygame.font.Font(None, int(vh * 0.022))

        warn_lines = [
            "Voce esta prestes a APAGAR TODO o seu progresso!",
            "",
            "Isso ira:",
            "- Deletar todos os seus Pokemon",
            "- Resetar seu dinheiro e itens",
            "- Apagar todas as conquistas",
            "- Deletar todos os saves",
            "",
            "Esta acao e IRREVERSIVEL!",
        ]

        line_y = title_y + title_text.get_height() + int(container_height * 0.05)
        line_spacing = int(vh * 0.025)

        for line in warn_lines:
            if line:
                if "IRREVERSIVEL" in line:
                    color = (255, 80, 80)
                    warn_font_bold = pygame.font.Font(None, int(vh * 0.026))
                    text_surface = warn_font_bold.render(line, True, color)
                elif "APAGAR TODO" in line:
                    color = (255, 200, 100)
                    text_surface = warn_font.render(line, True, color)
                else:
                    color = (200, 200, 200)
                    text_surface = warn_font.render(line, True, color)
                text_x = container_x + (container_width - text_surface.get_width()) // 2
                screen.blit(text_surface, (text_x, line_y))
            line_y += line_spacing

        # ===== BOTÕES DE CONFIRMAÇÃO =====
        button_width = 120
        button_height = 50
        spacing = 20
        total_width = button_width * 2 + spacing
        start_x = container_x + (container_width - total_width) // 2
        button_y = container_y + container_height - button_height - int(container_height * 0.08)

        # Botão SIM (vermelho)
        yes_rect = pygame.Rect(start_x, button_y, button_width, button_height)
        mouse_pos = pygame.mouse.get_pos()
        yes_hover = yes_rect.collidepoint(mouse_pos)

        yes_color = (180, 40, 40) if yes_hover else (140, 30, 30)
        pygame.draw.rect(screen, yes_color, yes_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 80, 80) if yes_hover else (200, 60, 60), yes_rect, 2, border_radius=10)

        yes_font = pygame.font.Font(None, int(vh * 0.03))
        yes_text = yes_font.render("SIM", True, (255, 255, 255))
        yes_text_x = yes_rect.x + (yes_rect.width - yes_text.get_width()) // 2
        yes_text_y = yes_rect.y + (yes_rect.height - yes_text.get_height()) // 2
        screen.blit(yes_text, (yes_text_x, yes_text_y))

        # Botão NÃO (cinza)
        no_rect = pygame.Rect(start_x + button_width + spacing, button_y, button_width, button_height)
        no_hover = no_rect.collidepoint(mouse_pos)

        no_color = (80, 80, 80) if no_hover else (60, 60, 60)
        pygame.draw.rect(screen, no_color, no_rect, border_radius=10)
        pygame.draw.rect(screen, (120, 120, 120) if no_hover else (100, 100, 100), no_rect, 2, border_radius=10)

        no_font = pygame.font.Font(None, int(vh * 0.03))
        no_text = no_font.render("NAO", True, (255, 255, 255))
        no_text_x = no_rect.x + (no_rect.width - no_text.get_width()) // 2
        no_text_y = no_rect.y + (no_rect.height - no_text.get_height()) // 2
        screen.blit(no_text, (no_text_x, no_text_y))

        # Armazena os rects para detecção de clique
        self._confirm_yes_rect = yes_rect
        self._confirm_no_rect = no_rect

    def _draw_gradient_background(self, screen):
        """Desenha fundo com gradiente"""
        for i in range(self.screen_manager.window_height):
            color_value = int(20 + (i / self.screen_manager.window_height) * 30)
            color = (color_value, color_value, color_value + 20)
            pygame.draw.line(screen, color, (0, i), (self.screen_manager.window_width, i))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa"""
        overlay = pygame.Surface((self.screen_manager.window_width,
                                  self.screen_manager.window_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.Font(None, 74)
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = (self.screen_manager.window_width - pause_text.get_width()) // 2
        text_y = (self.screen_manager.window_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

    def start_game(self):
        """Inicia o jogo - verifica se já escolheu o inicial ou precisa escolher"""
        # Para a música do menu antes de trocar de tela
        sound_manager.stop_music(fade_ms=300)

        # ===== VERIFICA SE O JOGADOR JÁ ESCOLHEU O INICIAL =====
        has_chosen_starter = getattr(self.game.player, 'has_chosen_starter', False)

        if has_chosen_starter:
            # Já escolheu o inicial - vai direto para seleção de fases
            print("[MENU] Jogador já escolheu o inicial - indo para seleção de fases")
            print(f"  - Time: {len(self.game.player.team)} Pokémon")
            print(f"  - Último capítulo acessado: {self.game.player.chapter_page_num}")

            # Carrega as configurações do save
            from src.config.progress import progress_manager
            progress_manager._load_settings_from_save()

            self.game.current_scene = PhaseSelectScene(self.game)
        else:
            # Não escolheu o inicial - mostra tela de seleção
            from src.scenes.starter_select_scene.starter_select_scene import StarterSelectScene

            print("[MENU] Jogador ainda não escolheu o inicial - abrindo seleção")
            self.game.starter_select_scene = StarterSelectScene(self.game)
            self.game.current_scene = self.game.starter_select_scene

    def open_settings(self):
        """Abre configurações"""
        print("Abrindo configurações...")
        # Para a música do menu com fade
        sound_manager.stop_music(fade_ms=300)
        self.game.current_scene = SettingsScene(self.game)

    def open_editor(self):
        """Abre o editor de fases"""
        print("Abrindo editor de fases...")
        from src.scenes.editor.editor_scene import EditorScene
        self.game.current_scene = EditorScene(self.game)

    def open_mystery_gift(self):
        """Abre a tela de Mystery Gift"""
        print("[MENU] Abrindo Mystery Gift...")
        from src.scenes.mystery_gift_scene.mystery_gift_scene import MysteryGiftScene
        self.game.current_scene = MysteryGiftScene(self.game)

    def quit_game(self):
        """Sai do jogo"""
        print("Saindo do jogo...")
        sound_manager.stop_music(fade_ms=300)
        self.game.running = False

    def on_enter(self):
        """Chamado quando a cena é ativada - inicia a música do menu se não estiver tocando"""
        # Verifica se a música já está tocando
        if not self._music_started or not pygame.mixer.music.get_busy():
            self._start_menu_music()

    def on_exit(self):
        """Chamado quando a cena é desativada - para a música"""
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False