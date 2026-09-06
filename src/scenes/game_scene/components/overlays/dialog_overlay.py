# src/scenes/game_scene/components/overlays/dialog_overlay.py

import pygame
import math


class DialogOverlay:
    """Overlay de diálogo com layout moderno: imagem do falante separada, texto em painel e botão elegante."""

    # Cores do tema escuro suave
    COLORS = {
        'overlay_bg': (0, 0, 0, 180),
        'dialog_bg': (45, 45, 60),
        'dialog_border': (120, 130, 160),
        'speaker_frame': (70, 80, 110),
        'speaker_bg': (30, 30, 45),
        'text_primary': (255, 255, 255),
        'text_secondary': (200, 210, 230),
        'text_speaker': (180, 210, 255),
        'button_bg': (80, 140, 220),
        'button_hover': (100, 170, 255),
        'button_text': (255, 255, 255),
        'button_border': (200, 220, 255),
        'shadow': (0, 0, 0, 80),
    }

    def __init__(self, game_scene, text, speaker="", sprite_path="", action_label="OK", action_callback=None):
        self.game_scene = game_scene
        self.text = text
        self.speaker = speaker
        self.sprite = None
        if sprite_path:
            try:
                self.sprite = pygame.image.load(sprite_path).convert_alpha()
            except Exception:
                pass
        self.action_label = action_label
        self.action_callback = action_callback
        self.active = True

        # Referências para UI
        sm = self.game_scene.screen_manager
        self.viewport = pygame.Rect(sm.viewport_x, sm.viewport_y,
                                    sm.viewport_width, sm.viewport_height)

        # Dimensões do diálogo – adaptável ao tamanho da viewport
        self.dialog_width = min(700, self.viewport.width - 80)
        self.dialog_height = min(280, self.viewport.height - 120)
        self.dialog_x = self.viewport.x + (self.viewport.width - self.dialog_width) // 2
        self.dialog_y = self.viewport.y + (self.viewport.height - self.dialog_height) // 2
        self.rect = pygame.Rect(self.dialog_x, self.dialog_y,
                                self.dialog_width, self.dialog_height)

        # Layout interno (margens e proporções)
        self.margin = 20
        self.sprite_size = 80  # tamanho do quadrado da imagem
        self.sprite_radius = 12  # arredondamento da moldura

        # Área do sprite (à esquerda)
        self.sprite_area = pygame.Rect(
            self.dialog_x + self.margin,
            self.dialog_y + self.margin,
            self.sprite_size,
            self.sprite_size
        )

        # Área do texto (à direita da imagem)
        text_area_x = self.sprite_area.right + self.margin
        text_area_width = self.dialog_width - text_area_x - self.margin
        self.text_area = pygame.Rect(
            text_area_x,
            self.dialog_y + self.margin + 10,
            text_area_width,
            self.dialog_height - 2 * self.margin - 60  # reserva para botão
        )

        # Área do botão (inferior central)
        button_width = 120
        button_height = 36
        self.button_rect = pygame.Rect(
            self.dialog_x + (self.dialog_width - button_width) // 2,
            self.dialog_y + self.dialog_height - self.margin - button_height,
            button_width,
            button_height
        )

        # Fontes
        self.font_speaker = pygame.font.Font(None, 22)
        self.font_text = pygame.font.Font(None, 20)
        self.font_button = pygame.font.Font(None, 20)

        # Estado do botão (para hover)
        self.button_hovered = False

    def handle_event(self, event):
        if not self.active:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.button_hovered = self.button_rect.collidepoint(event.pos)
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rect.collidepoint(event.pos):
                if self.action_callback:
                    self.action_callback()
                self.active = False
                return True
        return False

    def update(self, dt):
        pass

    def render(self, screen):
        if not self.active:
            return

        # 1. Overlay escuro com transparência
        overlay = pygame.Surface((self.viewport.width, self.viewport.height), pygame.SRCALPHA)
        overlay.fill(self.COLORS['overlay_bg'])
        screen.blit(overlay, (self.viewport.x, self.viewport.y))

        # 2. Sombra do diálogo (deslocada)
        shadow_rect = self.rect.copy()
        shadow_rect.x += 8
        shadow_rect.y += 8
        shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        shadow_surf.fill(self.COLORS['shadow'])
        screen.blit(shadow_surf, shadow_rect)

        # 3. Fundo do diálogo com bordas arredondadas
        pygame.draw.rect(screen, self.COLORS['dialog_bg'], self.rect, border_radius=16)
        pygame.draw.rect(screen, self.COLORS['dialog_border'], self.rect, 2, border_radius=16)

        # 4. Painel do sprite (moldura)
        # Desenha um fundo para a imagem com borda arredondada
        sprite_bg_rect = self.sprite_area.inflate(8, 8)
        pygame.draw.rect(screen, self.COLORS['speaker_bg'], sprite_bg_rect, border_radius=self.sprite_radius + 4)
        pygame.draw.rect(screen, self.COLORS['speaker_frame'], sprite_bg_rect, 2, border_radius=self.sprite_radius + 4)

        # Desenha o sprite dentro da área, com clipping para arredondar (se quisermos um círculo)
        if self.sprite:
            # Escala a imagem para caber no quadrado mantendo proporção
            sprite_scaled = self._scale_image_to_fit(self.sprite, self.sprite_size, self.sprite_size)
            # Recorta a imagem para formato circular (opcional, aqui usamos retangular arredondado)
            # Criamos uma máscara para cantos arredondados
            mask = pygame.Surface((self.sprite_size, self.sprite_size), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, self.sprite_size, self.sprite_size),
                             border_radius=self.sprite_radius)
            # Aplica a máscara
            sprite_final = sprite_scaled.copy()
            sprite_final.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(sprite_final, self.sprite_area)
        else:
            # Placeholder se não houver sprite: um ícone simples (círculo com iniciais)
            placeholder_color = (100, 120, 160)
            pygame.draw.circle(screen, placeholder_color,
                               self.sprite_area.center, self.sprite_size // 2 - 4)
            if self.speaker:
                initial = self.speaker[0].upper()
                font_initial = pygame.font.Font(None, 36)
                init_surf = font_initial.render(initial, True, (220, 230, 250))
                init_rect = init_surf.get_rect(center=self.sprite_area.center)
                screen.blit(init_surf, init_rect)

        # 5. Nome do falante
        if self.speaker:
            speaker_surf = self.font_speaker.render(self.speaker, True, self.COLORS['text_speaker'])
            speaker_rect = speaker_surf.get_rect(topleft=(self.text_area.x, self.text_area.y - 5))
            screen.blit(speaker_surf, speaker_rect)

        # 6. Texto (com quebra de linha)
        text_y_start = self.text_area.y + 25 if self.speaker else self.text_area.y
        lines = self._wrap_text(self.text, self.text_area.width)
        for i, line in enumerate(lines):
            if i >= 6:  # limite de linhas para não estourar
                break
            line_surf = self.font_text.render(line, True, self.COLORS['text_primary'])
            line_y = text_y_start + i * 26
            screen.blit(line_surf, (self.text_area.x, line_y))

        # 7. Botão de ação com efeito de hover
        button_color = self.COLORS['button_hover'] if self.button_hovered else self.COLORS['button_bg']
        pygame.draw.rect(screen, button_color, self.button_rect, border_radius=8)
        pygame.draw.rect(screen, self.COLORS['button_border'], self.button_rect, 1, border_radius=8)
        btn_text = self.font_button.render(self.action_label, True, self.COLORS['button_text'])
        btn_x = self.button_rect.centerx - btn_text.get_width() // 2
        btn_y = self.button_rect.centery - btn_text.get_height() // 2
        screen.blit(btn_text, (btn_x, btn_y))

    def _wrap_text(self, text, max_width):
        """Quebra o texto em linhas que caibam na largura máxima."""
        words = text.split(' ')
        lines = []
        current_line = []
        for word in words:
            # Se a palavra for muito longa, força quebra
            if self.font_text.size(word)[0] > max_width:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = []
                # Quebra a palavra em caracteres
                for char in word:
                    test_line = ''.join(current_line + [char])
                    if self.font_text.size(test_line)[0] <= max_width:
                        current_line.append(char)
                    else:
                        if current_line:
                            lines.append(''.join(current_line))
                        current_line = [char]
                if current_line:
                    lines.append(''.join(current_line))
                    current_line = []
                continue

            test_line = ' '.join(current_line + [word])
            if self.font_text.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        return lines

    def _scale_image_to_fit(self, image, target_w, target_h):
        """Redimensiona a imagem mantendo proporção para caber no quadrado."""
        orig_w, orig_h = image.get_size()
        scale = min(target_w / orig_w, target_h / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        scaled = pygame.transform.smoothscale(image, (new_w, new_h))
        # Centraliza a imagem em um fundo transparente do tamanho alvo
        result = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        result.blit(scaled, ((target_w - new_w) // 2, (target_h - new_h) // 2))
        return result