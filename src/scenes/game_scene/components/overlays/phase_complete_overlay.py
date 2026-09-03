# src/scenes/game_scene/components/overlays/phase_complete_overlay.py

import pygame
from collections import Counter
from .base_overlay import BaseOverlay
from src.config.progress import progress_manager
from src.config.phase_catalog import phase_catalog
from src.data.item_bag_catalog import item_bag_catalog


class PhaseCompleteOverlay(BaseOverlay):
    """Overlay de conclusão de fase - com grade de itens"""

    def __init__(self, game_scene):
        super().__init__(game_scene)
        self.phase_info = game_scene.phase_info
        self.phase_id = game_scene.phase_id
        self.phase_number = game_scene.phase_number
        self.music_played = False

        # Dados da conclusão
        self.complete_data = getattr(game_scene, 'phase_complete_data', {})
        self.earned_items = self.complete_data.get('earned_items', [])

        # Agrupa itens iguais com contagem
        self.item_counts = Counter(self.earned_items)

        # Botão
        self.button_rect = None
        self.button_hovered = False

        # Animações
        self.animation_timer = 0.0
        self.title_scale = 0.0
        self.fade_in = 0.0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rect and self.button_rect.collidepoint(event.pos):
                self._return_to_phase_select()
                return True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._return_to_phase_select()
            return True
        elif event.type == pygame.MOUSEMOTION:
            if self.button_rect:
                self.button_hovered = self.button_rect.collidepoint(event.pos)
        return False

    def update(self, dt):
        if not self.music_played:
            self._play_victory_music()
            self.music_played = True

        self.animation_timer += dt
        if self.title_scale < 1.0:
            self.title_scale = min(1.0, self.title_scale + dt * 2.5)
        if self.fade_in < 1.0:
            self.fade_in = min(1.0, self.fade_in + dt * 2.0)

    def _play_victory_music(self):
        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.play_victory_music()

    def _stop_music(self):
        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.stop_music(fade_ms=300)

    def render(self, screen):
        # Overlay com fade-in
        overlay, viewport = self.create_overlay_surface(int(180 * self.fade_in))
        screen.blit(overlay, (viewport.x, viewport.y))

        center_x = viewport.x + viewport.width // 2
        center_y = viewport.y + viewport.height // 2

        # Fontes responsivas
        base_size = min(viewport.width, viewport.height)
        font_large = pygame.font.Font(None, max(32, int(base_size * 0.06)))
        font_medium = pygame.font.Font(None, max(24, int(base_size * 0.045)))
        font_small = pygame.font.Font(None, max(18, int(base_size * 0.035)))
        font_tiny = pygame.font.Font(None, max(16, int(base_size * 0.03)))

        # ----- Título -----
        scale = self.title_scale
        if scale < 0.1:
            scale = 0.1
        title_text = "FASE COMPLETA!"
        title_surf = font_large.render(title_text, True, (255, 215, 0))
        shadow_surf = font_large.render(title_text, True, (0, 0, 0))
        scaled_title = pygame.transform.scale(
            title_surf,
            (int(title_surf.get_width() * scale), int(title_surf.get_height() * scale))
        )
        scaled_shadow = pygame.transform.scale(
            shadow_surf,
            (int(shadow_surf.get_width() * scale), int(shadow_surf.get_height() * scale))
        )
        title_rect = scaled_title.get_rect(center=(center_x, center_y - int(viewport.height * 0.22)))
        shadow_rect = scaled_shadow.get_rect(center=(center_x + 3, center_y - int(viewport.height * 0.22) + 3))
        screen.blit(scaled_shadow, shadow_rect)
        screen.blit(scaled_title, title_rect)

        line_y = title_rect.bottom + 10
        pygame.draw.line(screen, (255, 215, 0),
                         (center_x - int(viewport.width * 0.15), line_y),
                         (center_x + int(viewport.width * 0.15), line_y), 2)

        # ----- Nome da fase -----
        phase_name = self.phase_info.get("name", f"Fase {self.phase_number}")
        name_surf = font_medium.render(phase_name, True, (255, 255, 255))
        name_rect = name_surf.get_rect(center=(center_x, line_y + 25))
        screen.blit(name_surf, name_rect)

        # ----- Cartões de recompensas -----
        base_reward = self.complete_data.get("base_reward", 0)
        gold_from_defeats = self.complete_data.get("gold_from_defeats", 0)
        bonus_amount = self.complete_data.get("bonus_amount", 0)
        gold_total = self.complete_data.get("gold_total", 0)
        total_xp = self.complete_data.get("total_xp", 0)

        card_count = 3
        card_spacing = int(viewport.width * 0.02)
        card_width = min(180, int((viewport.width - (card_count + 1) * card_spacing) / card_count))
        card_height = min(80, int(viewport.height * 0.13))
        total_cards_width = card_count * (card_width + card_spacing) - card_spacing
        start_x = center_x - total_cards_width // 2
        card_y = name_rect.bottom + 20

        card_rect1 = pygame.Rect(start_x, card_y, card_width, card_height)
        self._draw_card(screen, card_rect1, "OURO", f"+{gold_total}", (255, 215, 0))
        if bonus_amount > 0:
            bonus_surf = font_tiny.render(f"(+{bonus_amount} bônus)", True, (200, 200, 100))
            screen.blit(bonus_surf, (card_rect1.centerx - bonus_surf.get_width()//2, card_rect1.bottom + 12))

        card_rect2 = pygame.Rect(start_x + card_width + card_spacing, card_y, card_width, card_height)
        self._draw_card(screen, card_rect2, "EXP", f"+{total_xp}", (100, 200, 255))

        item_count = len(self.item_counts)
        card_rect3 = pygame.Rect(start_x + 2*(card_width + card_spacing), card_y, card_width, card_height)
        if item_count > 0:
            self._draw_card(screen, card_rect3, "ITENS", f"{item_count}", (200, 180, 160))
        else:
            self._draw_card(screen, card_rect3, "ITENS", "0", (120, 120, 120), dim=True)

        # ----- Grade de itens (sprites) -----
        y_offset = card_rect3.bottom + 20

        if self.item_counts:
            # Área de itens expandida
            icon_size = 64
            spacing = 20
            max_per_row = 4
            total_icons = len(self.item_counts)
            cols = min(max_per_row, total_icons)
            rows = (total_icons + cols - 1) // cols

            # Largura total da grade
            total_width = cols * (icon_size + spacing) - spacing
            total_height = rows * (icon_size + spacing) - spacing
            # Área de fundo: adiciona padding
            padding = 25
            area_width = total_width + padding * 2
            area_height = total_height + padding * 2 + 30  # espaço extra para o nome
            # Limitar altura máxima (para não ocupar todo o espaço)
            area_height = min(area_height, viewport.height * 0.35)

            # Centraliza a área
            area_rect = pygame.Rect(0, 0, area_width, area_height)
            area_rect.centerx = center_x
            area_rect.y = y_offset

            # Desenha fundo
            pygame.draw.rect(screen, (30, 30, 45, 200), area_rect, border_radius=12)
            pygame.draw.rect(screen, (80, 80, 100), area_rect, 2, border_radius=12)

            # Posição inicial dos ícones (centralizada dentro da área)
            start_x_items = area_rect.centerx - total_width // 2
            start_y_items = area_rect.centery - total_height // 2

            unique_items = list(self.item_counts.items())

            for idx, (item_id, count) in enumerate(unique_items):
                row = idx // cols
                col = idx % cols
                x = start_x_items + col * (icon_size + spacing)
                y = start_y_items + row * (icon_size + spacing)

                # Fundo do ícone
                icon_rect = pygame.Rect(x, y, icon_size, icon_size)
                pygame.draw.rect(screen, (50, 50, 60), icon_rect, border_radius=8)
                pygame.draw.rect(screen, (100, 100, 120), icon_rect, 2, border_radius=8)

                # Sprite
                sprite = item_bag_catalog.get_sprite(item_id, scaled=True)
                if sprite:
                    scaled_sprite = pygame.transform.scale(sprite, (icon_size - 10, icon_size - 10))
                    sprite_rect = scaled_sprite.get_rect(center=icon_rect.center)
                    screen.blit(scaled_sprite, sprite_rect)
                else:
                    fallback = font_tiny.render(item_id[:3].upper(), True, (200, 200, 200))
                    screen.blit(fallback, fallback.get_rect(center=icon_rect.center))

                # Contador de quantidade (apenas número, sem círculo)
                if count > 1:
                    # Texto da quantidade
                    count_text = f"x{count}"
                    # Fonte um pouco maior para o contador
                    count_font = pygame.font.Font(None, int(icon_size * 0.45))
                    count_surf = count_font.render(count_text, True, (255, 255, 255))
                    # Fundo semi-transparente para o contador
                    count_bg = pygame.Surface((count_surf.get_width() + 10, count_surf.get_height() + 6))
                    count_bg.set_alpha(180)
                    count_bg.fill((0, 0, 0))
                    # Posiciona no canto inferior direito do ícone
                    bg_x = icon_rect.right - count_bg.get_width() + 20
                    bg_y = icon_rect.bottom - count_bg.get_height() - 50
                    screen.blit(count_bg, (bg_x, bg_y))
                    screen.blit(count_surf, (bg_x + 5, bg_y + 3))

                # Nome do item abaixo do ícone
                item_data = item_bag_catalog.get_item(item_id)
                item_name = item_data['name'] if item_data else item_id
                name_surf = font_tiny.render(item_name, True, (220, 220, 220))
                name_rect = name_surf.get_rect(center=(icon_rect.centerx, icon_rect.bottom + 8))
                screen.blit(name_surf, name_rect)

            y_offset = area_rect.bottom + 20
        else:
            no_items_text = font_small.render("Nenhum item recebido", True, (150, 150, 150))
            screen.blit(no_items_text, (center_x - no_items_text.get_width()//2, y_offset))
            y_offset += no_items_text.get_height() + 15

        # ----- Estrelas -----
        stars = self.complete_data.get('stars', 0)
        if stars > 0:
            y_offset += 6
            star_size = int(min(viewport.width, viewport.height) * 0.025)
            total_star_width = stars * (star_size + 6) - 6
            star_x = center_x - total_star_width // 2
            for i in range(stars):
                self._draw_star(screen, star_x + i * (star_size + 6), y_offset, star_size, (255, 215, 0))
            y_offset += star_size + 10

        # ----- Próxima fase -----
        next_phase = progress_manager.get_next_phase(self.phase_id)
        if next_phase:
            chapter, phase = map(int, next_phase.split("-"))
            next_info = phase_catalog.get_phase_info(chapter, phase)
            if next_info:
                next_text = font_tiny.render(f"Próxima fase: {next_info['name']}", True, (180, 180, 255))
                screen.blit(next_text, (center_x - next_text.get_width()//2, y_offset))
                y_offset += next_text.get_height() + 15

        # ----- Botão CONTINUAR -----
        button_width = min(220, int(viewport.width * 0.25))
        button_height = min(50, int(viewport.height * 0.08))
        button_x = center_x - button_width // 2
        self.button_rect = pygame.Rect(button_x, y_offset, button_width, button_height)

        if self.button_hovered:
            color = (80, 120, 220)
            border_color = (120, 160, 255)
            shadow_offset = 2
        else:
            color = (50, 70, 150)
            border_color = (70, 100, 200)
            shadow_offset = 4

        shadow_rect = self.button_rect.copy()
        shadow_rect.x += shadow_offset
        shadow_rect.y += shadow_offset
        pygame.draw.rect(screen, (0, 0, 0, 80), shadow_rect, border_radius=12)

        pygame.draw.rect(screen, color, self.button_rect, border_radius=12)
        pygame.draw.rect(screen, border_color, self.button_rect, 2, border_radius=12)

        button_text = font_medium.render("CONTINUAR", True, (255, 255, 255))
        text_rect = button_text.get_rect(center=self.button_rect.center)
        screen.blit(button_text, text_rect)

        y_offset = self.button_rect.bottom + 15

        # ----- Instrução ESC -----
        esc_text = font_tiny.render("Pressione ESC para continuar", True, (120, 120, 120))
        screen.blit(esc_text, (center_x - esc_text.get_width()//2, y_offset))

    def _draw_card(self, screen, rect, label, value, color, dim=False):
        bg_color = (30, 30, 40) if not dim else (25, 25, 30)
        border_color = (60, 60, 70) if not dim else (45, 45, 50)
        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)

        font_val = pygame.font.Font(None, int(rect.height * 0.5))
        val_surf = font_val.render(str(value), True, color if not dim else (100, 100, 100))
        val_rect = val_surf.get_rect(center=(rect.centerx, rect.centery - 8))
        screen.blit(val_surf, val_rect)

        font_lab = pygame.font.Font(None, int(rect.height * 0.3))
        lab_surf = font_lab.render(label, True, (200, 200, 200) if not dim else (120, 120, 120))
        lab_rect = lab_surf.get_rect(center=(rect.centerx, rect.centery + int(rect.height * 0.28)))
        screen.blit(lab_surf, lab_rect)

    def _draw_star(self, screen, x, y, size, color):
        points = []
        num_points = 5
        outer_radius = size // 2
        inner_radius = outer_radius // 2
        for i in range(num_points * 2):
            angle = -90 - i * (360 / (num_points * 2))
            radius = outer_radius if i % 2 == 0 else inner_radius
            px = x + radius * pygame.math.Vector2(1, 0).rotate(angle).x
            py = y + radius * pygame.math.Vector2(1, 0).rotate(angle).y
            points.append((px, py))
        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, (200, 170, 0), points, 1)

    def _return_to_phase_select(self):
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
        self._stop_music()
        if hasattr(self.game_scene, 'cleanup'):
            self.game_scene.cleanup()
        phase_select = PhaseSelectScene(self.game)
        phase_select.refresh_data()
        self.game.current_scene = phase_select