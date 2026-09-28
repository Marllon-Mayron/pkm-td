# src/scenes/minigame_select_scene/minigame_select_scene.py

"""
Tela de Seleção de Minigames - Estilo Plants vs Zombies
"""
import math
import os
import json

import pygame

from src.scenes.base_scene import BaseScene
from src.config.progress import progress_manager
from src.editor.phase_exporter import PhaseExporter
from src.config.paths import PROJECT_ROOT


# =====================================================================
# CARD
# =====================================================================
class MinigameCard:
    def __init__(self, minigame_data, level_data, unlocked=False):
        self.minigame_name = minigame_data["name"]
        self.level_chapter = level_data["chapter"]
        self.level_number = level_data["level"]
        self.unlock_requirement = level_data.get(
            "unlock_requirement", {"chapter": 1, "phase": 1}
        )
        self.unlocked = unlocked

        # Nome da fase vindo do JSON (level_XX_YY.json)
        self.phase_name = level_data.get("phase_name", "") or ""

        # Requisito de Poké Flute
        self.requires_flute = bool(level_data.get("requires_flute", False))
        self.has_flute = bool(level_data.get("has_flute", True))
        self.flute_missing = self.requires_flute and not self.has_flute

        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False

        # Cores baseadas no status
        if not unlocked:
            self.bg_color = (40, 35, 45)
            self.border_color = (80, 60, 100)
            self.text_color = (120, 100, 140)
            self.name_color = (100, 80, 120)
        elif self.flute_missing:
            # Bloqueado por falta de Poké Flute — vermelho suave
            self.bg_color = (55, 35, 40)
            self.border_color = (170, 80, 90)
            self.text_color = (220, 190, 190)
            self.name_color = (240, 200, 200)
        else:
            self.bg_color = (50, 45, 55)
            self.border_color = (150, 100, 200)
            self.text_color = (220, 200, 240)
            self.name_color = (200, 180, 220)

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            return was_hovered != self.is_hovered

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                if not self.unlocked:
                    return None
                if self.flute_missing:
                    # Marcador especial pro scene emitir toast
                    return ("missing_flute",
                            self.level_chapter, self.level_number)
                return (self.level_chapter, self.level_number)
        return None

    # ------------------------------------------------------------------
    def render(self, screen, font_title, font_name, font_small):
        can_hover = self.unlocked

        # Efeito hover
        if self.is_hovered and can_hover:
            color = tuple(min(255, c + 15) for c in self.bg_color)
            border = tuple(min(255, c + 40) for c in self.border_color)
            name_color = tuple(min(255, c + 50) for c in self.name_color)
        else:
            color = self.bg_color
            border = self.border_color
            name_color = self.name_color

        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (20, 15, 25), shadow_rect, border_radius=15)

        # Card principal
        pygame.draw.rect(screen, color, self.rect, border_radius=15)
        pygame.draw.rect(screen, border, self.rect, 3, border_radius=15)

        # ===== Ícone do topo =====
        icon_center = (self.rect.centerx, self.rect.y + 32)
        if not self.unlocked:
            pygame.draw.circle(screen, (80, 70, 100), icon_center, 14)
            pygame.draw.circle(screen, (60, 50, 80), icon_center, 9)
            lock_rect = pygame.Rect(icon_center[0] - 6, icon_center[1] - 4,
                                    12, 10)
            pygame.draw.rect(screen, (150, 150, 150), lock_rect,
                             border_radius=2)
            pygame.draw.rect(screen, (150, 150, 150),
                             (icon_center[0] - 4, icon_center[1] - 2, 8, 6))
        elif self.flute_missing:
            # Ícone de aviso (triângulo)
            pygame.draw.circle(screen, (200, 80, 90), icon_center, 14)
            pygame.draw.circle(screen, (140, 40, 50), icon_center, 9)
            pygame.draw.polygon(screen, (255, 255, 255), [
                (icon_center[0], icon_center[1] - 7),
                (icon_center[0] - 7, icon_center[1] + 5),
                (icon_center[0] + 7, icon_center[1] + 5),
            ])
            pygame.draw.rect(screen, (140, 40, 50),
                             (icon_center[0] - 1, icon_center[1] - 3, 2, 5))
            pygame.draw.rect(screen, (140, 40, 50),
                             (icon_center[0] - 1, icon_center[1] + 3, 2, 2))
        else:
            pygame.draw.circle(screen, (255, 200, 0), icon_center, 14)
            pygame.draw.circle(screen, (255, 150, 0), icon_center, 9)

        # ===== Nome da fase (do JSON) — destaque =====
        display_name = self.phase_name or self.minigame_name
        self._render_wrapped_text(
            screen, display_name, font_name, name_color,
            self.rect.centerx, self.rect.centery - 25,
            self.rect.width - 20,
        )

        # ===== Minigame (subtítulo) =====
        mini_s = font_small.render(self.minigame_name, True, (150, 130, 170))
        mini_rect = mini_s.get_rect(
            center=(self.rect.centerx, self.rect.centery + 5))
        screen.blit(mini_s, mini_rect)

        # ===== Capítulo / Nível =====
        level_text = font_small.render(
            f"Cap. {self.level_chapter} · Nível {self.level_number}",
            True, self.text_color,
        )
        level_rect = level_text.get_rect(
            center=(self.rect.centerx, self.rect.centery + 28))
        screen.blit(level_text, level_rect)

        # ===== Rodapé =====
        if not self.unlocked:
            req_text = font_small.render(
                f"Requer: Cap.{self.unlock_requirement['chapter']}"
                f"-{self.unlock_requirement['phase']}",
                True, (100, 80, 120),
            )
            req_rect = req_text.get_rect(
                center=(self.rect.centerx, self.rect.bottom - 16))
            screen.blit(req_text, req_rect)
        elif self.flute_missing:
            warn_text = font_small.render(
                "PRECISA DE POKE FLUTE", True, (255, 120, 120))
            warn_rect = warn_text.get_rect(
                center=(self.rect.centerx, self.rect.bottom - 16))
            screen.blit(warn_text, warn_rect)

        # Overlay escurecendo quando bloqueado por progresso
        if not self.unlocked:
            overlay = pygame.Surface(
                (self.rect.width, self.rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, self.rect)

    # ------------------------------------------------------------------
    def _render_wrapped_text(self, screen, text, font, color,
                             center_x, center_y, max_width):
        """Renderiza texto com quebra de linha (até 2 linhas)."""
        words = text.split()
        if not words:
            return

        single = font.render(text, True, color)
        if single.get_width() <= max_width:
            rect = single.get_rect(center=(center_x, center_y))
            screen.blit(single, rect)
            return

        if len(words) == 1:
            trimmed = text
            while trimmed and font.size(trimmed + "...")[0] > max_width:
                trimmed = trimmed[:-1]
            surf = font.render(trimmed + "...", True, color)
            rect = surf.get_rect(center=(center_x, center_y))
            screen.blit(surf, rect)
            return

        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])

        while line1 and font.size(line1)[0] > max_width:
            line1 = line1[:-1]
        while line2 and font.size(line2)[0] > max_width:
            line2 = line2[:-1]

        if line1:
            surf1 = font.render(line1, True, color)
            rect1 = surf1.get_rect(center=(center_x, center_y - 12))
            screen.blit(surf1, rect1)
        if line2:
            surf2 = font.render(line2, True, color)
            rect2 = surf2.get_rect(center=(center_x, center_y + 8))
            screen.blit(surf2, rect2)


# =====================================================================
# SCENE
# =====================================================================
class MinigameSelectScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        self.exporter = PhaseExporter()
        self.progress = progress_manager

        # Dados dos minigames
        self.minigames = []
        self.current_minigame_cards = []
        self.selected_minigame_folder = None
        self.selected_minigame_data = None

        # Estados
        self.state = "select_minigame"  # ou "select_level"

        # Scroll
        self.scroll_y = 0
        self.scroll_target = 0
        self.max_scroll = 0
        self.dragging_scroll = False
        self.last_mouse_y = 0

        # UI
        self.back_button = None
        self.title_font = pygame.font.Font(None, 48)
        self.card_title_font = pygame.font.Font(None, 28)
        self.card_name_font = pygame.font.Font(None, 22)
        self.card_small_font = pygame.font.Font(None, 16)
        self.button_font = pygame.font.Font(None, 24)

        # Layout
        self.layout_initialized = False
        self.last_window_size = (
            self.screen_manager.window_width,
            self.screen_manager.window_height,
        )

        # Carrega minigames
        self._load_minigames()

    # ------------------------------------------------------------------
    # CARREGAMENTO
    # ------------------------------------------------------------------
    def _load_minigames(self):
        """Carrega todos os minigames disponíveis."""
        folders = self.exporter.list_minigame_folders()
        self.minigames = []

        # ===== BLOQUEIO: pastas terminadas em "_maps" =====
        # São mapas multijogador / rascunhos — não entram na seleção.
        blocked_suffix = "_maps"

        for folder in folders:
            folder_l = (folder or "").lower()

            if folder_l.endswith(blocked_suffix):
                print(f"[MINIGAME_SELECT] Ignorando pasta bloqueada: "
                      f"{folder}")
                continue

            index_path = self.exporter.minigames_path / folder / "index.json"
            if index_path.exists():
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        index_data = json.load(f)
                except Exception as e:
                    print(f"[MINIGAME_SELECT] Erro ao ler {index_path}: {e}")
                    continue

                self.minigames.append({
                    "folder": folder,
                    "name": index_data.get("name", folder),
                    "levels": index_data.get("levels", []),
                })

        print(f"Carregados {len(self.minigames)} minigames")

    def _select_minigame(self, folder):
        """Seleciona um minigame para mostrar seus níveis."""
        for mg in self.minigames:
            if mg["folder"] == folder:
                self.selected_minigame_folder = folder
                self.selected_minigame_data = mg
                self.state = "select_level"
                self._create_level_cards()
                self.scroll_y = 0
                self.scroll_target = 0
                break

    # ------------------------------------------------------------------
    # HELPERS DE FASE
    # ------------------------------------------------------------------
    def _get_phase_name(self, folder, level):
        """
        Lê o campo 'name' do JSON da fase (level_XX_YY.json).
        Retorna "" se não achar — o card usa o nome do minigame como fallback.
        """
        try:
            path = os.path.join(
                PROJECT_ROOT, "src", "data", "minigames", folder,
                f"level_{int(level['chapter']):02d}_"
                f"{int(level['level']):02d}.json",
            )
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                name = (data.get("name") or "").strip()
                if name:
                    return name
        except Exception as e:
            print(f"[MINIGAME_SELECT] Erro lendo nome da fase "
                  f"({folder}): {e}")
        return ""

    # ------------------------------------------------------------------
    # CRIAÇÃO DE CARDS
    # ------------------------------------------------------------------
    def _create_level_cards(self):
        """Cria cards para os níveis do minigame selecionado."""
        if not self.selected_minigame_data:
            return

        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        levels = self.selected_minigame_data["levels"]

        # Configuração do grid
        card_width = 180
        card_height = 200
        card_margin = 25
        cols = max(2, min(4,
                          (viewport_width - 100) // (card_width + card_margin)))

        # Posições
        grid_width = cols * card_width + (cols - 1) * card_margin
        grid_start_x = viewport_x + (viewport_width - grid_width) // 2
        grid_start_y = viewport_y + 150

        rows = math.ceil(len(levels) / cols)
        grid_height = rows * (card_height + card_margin)
        visible_height = viewport_height - (grid_start_y - viewport_y) - 80
        self.max_scroll = max(0, grid_height - visible_height)

        # ===== FLUTE POR NÍVEL =====
        # Cada card verifica seu próprio `requires_flute` no JSON.

        # Cria cards
        self.current_minigame_cards = []
        for i, level in enumerate(levels):
            row = i // cols
            col = i % cols

            card_x = grid_start_x + col * (card_width + card_margin)
            card_y = (grid_start_y
                      + row * (card_height + card_margin)
                      - self.scroll_y)

            # Desbloqueio por progresso
            unlock_req = level.get(
                "unlock_requirement", {"chapter": 1, "phase": 1}
            )
            required_phase_id = (
                f"{unlock_req['chapter']}-{unlock_req['phase']}"
            )
            unlocked = self.progress.is_phase_completed(required_phase_id)

            # Nome da fase (lido do JSON)
            phase_name = self._get_phase_name(
                self.selected_minigame_folder, level
            )

            # ===== FLUTE POR NÍVEL =====
            requires_flute = bool(level.get("requires_flute", False))
            has_flute = True
            if requires_flute:
                try:
                    has_flute = (
                        self.game.player.bag.get_quantity("pokeflute") > 0
                    )
                except Exception:
                    has_flute = False

            # Dict enriquecido pro card
            level_info = dict(level)
            level_info["phase_name"] = phase_name
            level_info["requires_flute"] = requires_flute
            level_info["has_flute"] = has_flute

            card = MinigameCard(
                self.selected_minigame_data, level_info, unlocked
            )
            card.update_position(card_x, card_y, card_width, card_height)
            self.current_minigame_cards.append(card)

        print(f"[MINIGAME_SELECT] {len(self.current_minigame_cards)} card(s) "
              f"criado(s) | pasta='{self.selected_minigame_folder}'")

    # ------------------------------------------------------------------
    # INICIAR NÍVEL  (ÚNICA VERSÃO — a correta)
    # ------------------------------------------------------------------
    def _start_minigame_level(self, chapter_and_level):
        """
        Inicia um nível de minigame.

        Roteamento:
          - survival              → SurvivalMinigameScene
          - desafios + level 1    → DojoSelectScene  → DojoMinigameScene
          - desafios + level 2    → DesafiosMinigameScene (Snorlax)
        """
        chapter_val, level_val = chapter_and_level
        folder_l = (self.selected_minigame_folder or "").lower()

        print(f"Iniciando minigame {self.selected_minigame_folder} - "
              f"Capítulo {chapter_val}, Nível {level_val}")

        # ---------- SURVIVAL ----------
        if folder_l == "survival":
            from src.scenes.minigames.survival import SurvivalMinigameScene
            self.game.current_scene = SurvivalMinigameScene(
                self.game,
                chapter_id=chapter_val,
                phase_number=level_val,
            )
            return

        # ---------- DESAFIOS (Dojo + Snorlax na MESMA pasta) ----------
        if folder_l == "desafios":
            # Nível 1 → DOJO
            if level_val == 1:
                from src.scenes.minigames.dojo.dojo_select_scene import (
                    DojoSelectScene,
                )
                self.game.current_scene = DojoSelectScene(
                    self.game,
                    chapter_id=chapter_val,
                    phase_number=level_val,
                )
                return

            # Nível 2 → SNORLAX (precisa de Poké Flute)
            if level_val == 2:
                has_flute = False
                try:
                    has_flute = (
                        self.game.player.bag.get_quantity("pokeflute") > 0
                    )
                except Exception:
                    has_flute = False

                if not has_flute:
                    try:
                        from src.ui.toast_renderer import toast_warning
                        toast_warning(
                            "Você precisa de uma POKE FLUTE para entrar!",
                            duration=3.5,
                        )
                    except Exception:
                        pass
                    print("[DESAFIOS] Bloqueado: jogador sem Poké Flute.")
                    return

                from src.scenes.minigames.desafios.desafios_minigame_scene import (
                    DesafiosMinigameScene,
                )
                self.game.current_scene = DesafiosMinigameScene(
                    self.game,
                    chapter_id=chapter_val,
                    phase_number=level_val,
                )
                return

        # ---------- FALLBACK ----------
        phase_data = self.exporter.load_phase(
            chapter_val,
            level_val,
            localization_type="custom",
            custom_folder=self.selected_minigame_folder,
        )
        if phase_data:
            print(f"Minigame carregado: "
                  f"{phase_data.get('name', 'Sem nome')}")
        else:
            print(f"Erro ao carregar nível {chapter_val}-{level_val}")

    # ------------------------------------------------------------------
    # LAYOUT / RESIZE
    # ------------------------------------------------------------------
    def _check_resize(self):
        current_size = (self.screen_manager.window_width,
                        self.screen_manager.window_height)
        if current_size != self.last_window_size:
            self.last_window_size = current_size
            self.layout_initialized = False
            return True
        return False

    def _create_layout(self):
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        back_size = 45
        self.back_button = pygame.Rect(
            viewport_x + 30,
            viewport_y + 25,
            back_size,
            back_size,
        )

        self.layout_initialized = True

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        """Processa eventos."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                if self.state == "select_level":
                    self.state = "select_minigame"
                    self.selected_minigame_folder = None
                    self.selected_minigame_data = None
                    self.current_minigame_cards = []
                else:
                    self.game.current_scene = self.game.menu_scene

        elif event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False

        elif event.type == pygame.MOUSEWHEEL:
            if (self.state == "select_level"
                    and self.current_minigame_cards
                    and self.max_scroll > 0):
                self.scroll_target += event.y * -30
                self.scroll_target = max(
                    0, min(self.max_scroll, self.scroll_target))

        elif event.type == pygame.MOUSEMOTION:
            if self.state == "select_level":
                for card in self.current_minigame_cards:
                    card.handle_event(event)

            if self.dragging_scroll:
                dy = event.pos[1] - self.last_mouse_y
                self.scroll_target += dy * 5
                self.scroll_target = max(
                    0, min(self.max_scroll, self.scroll_target))
                self.last_mouse_y = event.pos[1]

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                # Botão voltar
                if (self.back_button
                        and self.back_button.collidepoint(event.pos)):
                    if self.state == "select_level":
                        self.state = "select_minigame"
                        self.selected_minigame_folder = None
                        self.selected_minigame_data = None
                        self.current_minigame_cards = []
                    else:
                        from src.scenes.phase_selector.phase_select_scene import (
                            PhaseSelectScene,
                        )
                        self.game.current_scene = PhaseSelectScene(self.game)
                    return

                if self.state == "select_minigame":
                    pass

                elif self.state == "select_level":
                    # Scroll dragging
                    if self.max_scroll > 0:
                        scroll_bar_rect = self._get_scroll_bar_rect()
                        if (scroll_bar_rect
                                and scroll_bar_rect.collidepoint(event.pos)):
                            self.dragging_scroll = True
                            self.last_mouse_y = event.pos[1]
                            return

                    # ===== Clique nos cards de nível =====
                    for card in self.current_minigame_cards:
                        result = card.handle_event(event)
                        if not result:
                            continue

                        # Card respondeu "missing_flute"
                        if (isinstance(result, tuple) and len(result) == 3
                                and result[0] == "missing_flute"):
                            try:
                                from src.ui.toast_renderer import toast_warning
                                toast_warning(
                                    "Você precisa de uma POKE FLUTE para "
                                    "entrar neste desafio!",
                                    duration=4.0,
                                )
                            except Exception:
                                pass
                            return

                        self._start_minigame_level(result)
                        return

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging_scroll = False

    # ==================================================================
    # SCROLL
    # ==================================================================
    def _get_scroll_bar_rect(self):
        if self.max_scroll <= 0 or not self.current_minigame_cards:
            return None

        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_height = self.screen_manager.viewport_height

        x = viewport_x + self.screen_manager.viewport_width - 20
        y = viewport_y + 150
        width = 10
        height = viewport_height - 230

        scroll_height = max(
            30, height * (height / (height + self.max_scroll)))
        scroll_pos = (y
                      + (self.scroll_y / self.max_scroll)
                      * (height - scroll_height))

        return pygame.Rect(x, scroll_pos, width, scroll_height)

    def _render_scroll_bar(self, screen):
        if self.max_scroll <= 0 or not self.current_minigame_cards:
            return

        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_height = self.screen_manager.viewport_height

        x = viewport_x + self.screen_manager.viewport_width - 20
        y = viewport_y + 150
        width = 10
        height = viewport_height - 230

        # Fundo
        pygame.draw.rect(screen, (40, 40, 45),
                         (x, y, width, height), border_radius=5)

        # Barra
        scroll_height = max(
            30, height * (height / (height + self.max_scroll)))
        scroll_pos = (y
                      + (self.scroll_y / self.max_scroll)
                      * (height - scroll_height))

        color = (120, 80, 160) if self.dragging_scroll else (90, 60, 120)
        pygame.draw.rect(screen, color,
                         (x, scroll_pos, width, scroll_height),
                         border_radius=5)
        pygame.draw.rect(screen, (150, 100, 200),
                         (x, scroll_pos, width, scroll_height),
                         1, border_radius=5)

    def fixed_update(self, dt):
        """Update suave do scroll."""
        if abs(self.scroll_y - self.scroll_target) > 0.5:
            self.scroll_y += (
                (self.scroll_target - self.scroll_y) * min(1, dt * 10)
            )
            if self.state == "select_level" and self.current_minigame_cards:
                self._update_cards_position()

    def _update_cards_position(self):
        if not self.selected_minigame_data:
            return

        viewport_width = self.screen_manager.viewport_width
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        card_width = 180
        card_height = 200
        card_margin = 25
        cols = max(2, min(4,
                          (viewport_width - 100) // (card_width + card_margin)))

        grid_width = cols * card_width + (cols - 1) * card_margin
        grid_start_x = viewport_x + (viewport_width - grid_width) // 2
        grid_start_y = viewport_y + 150

        for i, card in enumerate(self.current_minigame_cards):
            row = i // cols
            col = i % cols
            card.rect.x = grid_start_x + col * (card_width + card_margin)
            card.rect.y = (grid_start_y
                           + row * (card_height + card_margin)
                           - self.scroll_y)

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        self._check_resize()
        self._draw_gradient_background(screen)

        if not self.layout_initialized:
            self._create_layout()

        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height

        # Título
        if self.state == "select_minigame":
            title = self.title_font.render(
                "MINIGAMES", True, (220, 180, 255))
        else:
            title = self.title_font.render(
                self.selected_minigame_data["name"],
                True, (220, 180, 255),
            )

        title_x = viewport_x + (viewport_width - title.get_width()) // 2
        screen.blit(title, (title_x, viewport_y + 25))

        # Botão voltar
        if self.back_button:
            pygame.draw.rect(screen, (50, 45, 60),
                             self.back_button, border_radius=8)
            pygame.draw.rect(screen, (100, 80, 130),
                             self.back_button, 2, border_radius=8)
            back_text = pygame.font.Font(None, 40).render(
                "<", True, (200, 180, 220))
            back_rect = back_text.get_rect(
                center=self.back_button.center)
            screen.blit(back_text, back_rect)

        if self.state == "select_minigame":
            self._render_minigame_grid(screen)
        else:
            self._render_level_grid(screen)

        # Instruções
        inst_font = pygame.font.Font(None, 16)
        if self.state == "select_minigame":
            inst_text = "CLIQUE NO MINIGAME  |  ESC  VOLTAR"
        else:
            inst_text = "CLIQUE NO NÍVEL  |  ESC  VOLTAR"

        inst = inst_font.render(inst_text, True, (100, 80, 120))
        inst_x = viewport_x + (viewport_width - inst.get_width()) // 2
        screen.blit(inst, (inst_x, viewport_y + viewport_height - 30))

        if self.paused:
            self._render_pause_overlay(screen)

    # ------------------------------------------------------------------
    def _render_minigame_grid(self, screen):
        """Renderiza grade de minigames."""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_width = self.screen_manager.viewport_width

        if not self.minigames:
            font = pygame.font.Font(None, 28)
            msg = font.render(
                "Nenhum minigame disponível ainda!", True, (150, 150, 150))
            msg_x = viewport_x + (viewport_width - msg.get_width()) // 2
            msg_y = viewport_y + 300
            screen.blit(msg, (msg_x, msg_y))
            return

        card_width = 200
        card_height = 150
        card_margin = 30
        cols = max(2, min(3,
                          (viewport_width - 100) // (card_width + card_margin)))

        grid_width = cols * card_width + (cols - 1) * card_margin
        grid_start_x = viewport_x + (viewport_width - grid_width) // 2
        grid_start_y = viewport_y + 150

        mouse_pos = pygame.mouse.get_pos()

        for i, mg in enumerate(self.minigames):
            row = i // cols
            col = i % cols

            card_x = grid_start_x + col * (card_width + card_margin)
            card_y = grid_start_y + row * (card_height + card_margin)
            card_rect = pygame.Rect(card_x, card_y, card_width, card_height)

            is_hovered = card_rect.collidepoint(mouse_pos)

            if is_hovered:
                bg_color = (60, 55, 70)
                border_color = (200, 150, 255)
            else:
                bg_color = (45, 40, 55)
                border_color = (100, 80, 130)

            # Sombra
            shadow_rect = card_rect.copy()
            shadow_rect.x += 3
            shadow_rect.y += 3
            pygame.draw.rect(screen, (25, 20, 35),
                             shadow_rect, border_radius=10)

            # Card
            pygame.draw.rect(screen, bg_color, card_rect, border_radius=10)
            pygame.draw.rect(screen, border_color, card_rect,
                             2, border_radius=10)

            # Nome
            name = self.card_name_font.render(
                mg["name"], True, (220, 200, 240))
            name_rect = name.get_rect(
                center=(card_rect.centerx, card_rect.centery - 15))
            screen.blit(name, name_rect)

            # Contador de níveis
            level_count = len(mg["levels"])
            count_text = self.card_small_font.render(
                f"{level_count} nível(níveis)", True, (150, 130, 170))
            count_rect = count_text.get_rect(
                center=(card_rect.centerx, card_rect.centery + 20))
            screen.blit(count_text, count_rect)

            # Botão jogar
            play_btn = pygame.Rect(
                card_rect.centerx - 40, card_rect.bottom - 35, 80, 25)
            if is_hovered:
                pygame.draw.rect(screen, (100, 150, 100),
                                 play_btn, border_radius=5)
                pygame.draw.rect(screen, (150, 200, 150),
                                 play_btn, 1, border_radius=5)
            else:
                pygame.draw.rect(screen, (80, 100, 80),
                                 play_btn, border_radius=5)

            play_text = self.card_small_font.render(
                "JOGAR", True, (255, 255, 255))
            play_text_rect = play_text.get_rect(center=play_btn.center)
            screen.blit(play_text, play_text_rect)

        # Clique pelo estado do mouse (mesmo padrão do original)
        if pygame.mouse.get_pressed()[0]:
            for i, mg in enumerate(self.minigames):
                row = i // cols
                col = i % cols
                card_x = grid_start_x + col * (card_width + card_margin)
                card_y = grid_start_y + row * (card_height + card_margin)
                card_rect = pygame.Rect(
                    card_x, card_y, card_width, card_height)
                if card_rect.collidepoint(mouse_pos):
                    self._select_minigame(mg["folder"])
                    return

    # ------------------------------------------------------------------
    def _render_level_grid(self, screen):
        """Renderiza grade de níveis com clipping."""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height

        clip_rect = pygame.Rect(
            viewport_x, viewport_y + 130,
            viewport_width, viewport_height - 180,
        )
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for card in self.current_minigame_cards:
            if (card.rect.bottom > clip_rect.top
                    and card.rect.top < clip_rect.bottom):
                card.render(
                    screen,
                    self.card_title_font,
                    self.card_name_font,
                    self.card_small_font,
                )

        screen.set_clip(old_clip)

        if self.max_scroll > 0:
            self._render_scroll_bar(screen)

    # ------------------------------------------------------------------
    def _draw_gradient_background(self, screen):
        for i in range(self.screen_manager.window_height):
            value = int(15 + (i / self.screen_manager.window_height) * 25)
            color = (value, value - 5, value + 10)
            pygame.draw.line(
                screen, color,
                (0, i), (self.screen_manager.window_width, i))

    def _render_pause_overlay(self, screen):
        overlay = pygame.Surface(
            (self.screen_manager.window_width,
             self.screen_manager.window_height))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 15))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.Font(None, 74)
        pause_text = font_large.render("PAUSADO", True, (200, 180, 220))
        text_x = (self.screen_manager.window_width
                  - pause_text.get_width()) // 2
        text_y = (self.screen_manager.window_height
                  - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))