# src/managers/notification_manager.py
"""
Sistema de gerenciamento de notificações estilo toast COM SCROLL
"""
import pygame
from typing import List, Optional, Callable
from collections import deque

from src.ui.notification import Notification, NotificationType


class NotificationManager:
    """
    Gerencia fila de notificações com suporte a scroll e portraits
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Fila de notificações
        self._notifications: deque = deque()
        self._active_notifications: List[Notification] = []

        # Configurações
        self.max_visible = 3
        self.toast_height = 70
        self.toast_width = 380
        self.toast_padding = 8
        self.scroll_offset = 0

        # Posição
        self.position = "top-right"
        self.offset_x = 20
        self.offset_y = 20

        # Cache
        self._font_cache = {}
        self._portrait_cache = {}

        # Callbacks
        self._on_notification_callbacks: List[Callable] = []

        # Scroll
        self._hovering_notifications = False

        # Cores do overlay
        self.colors = {
            'bg_dark': (20, 25, 45),
            'bg_medium': (30, 35, 55),
            'bg_card': (38, 43, 68),
            'border': (80, 100, 140),
            'text': (255, 255, 255),
            'text_dim': (200, 200, 220),
            'text_muted': (150, 155, 180),
        }

    def _get_font(self, size=15, bold=False):
        """Obtém fonte com cache"""
        key = (size, bold)
        if key in self._font_cache:
            return self._font_cache[key]

        font = pygame.font.Font(None, size)
        if bold:
            font.set_bold(True)

        self._font_cache[key] = font
        return font

    def notify(
            self,
            message: str,
            type: NotificationType = NotificationType.INFO,
            duration: float = 3.0,
            data: Optional[dict] = None,
            pokemon=None,
            portrait_expression: str = "normal"
    ):
        """
        Adiciona uma nova notificação

        Args:
            message: Mensagem a ser exibida
            type: Tipo da notificação
            duration: Duração em segundos
            data: Dados extras para callbacks
            pokemon: Objeto Pokémon (opcional)
            portrait_expression: Expressão do portrait ("normal", "happy", "angry", etc)
        """
        notification = Notification(
            message=message,
            type=type,
            duration=duration,
            data=data
        )

        # Adiciona dados do Pokémon e carrega o portrait
        if pokemon is not None:
            notification.pokemon = pokemon
            notification.pokemon_id = pokemon.id
            notification.is_shiny = pokemon.is_shiny
            notification.pokemon_name = pokemon.name
            notification.portrait_expression = portrait_expression

            # Carrega o portrait com a expressão solicitada
            notification.portrait = pokemon.get_portrait(portrait_expression, (48, 48))

            if notification.portrait:
                print(f"[NOTIFICATION] Portrait '{portrait_expression}' carregado para {pokemon.name}")
            else:
                print(f"[NOTIFICATION] Portrait não encontrado para {pokemon.name} (expressão: {portrait_expression})")

        self._notifications.append(notification)

        for callback in self._on_notification_callbacks:
            callback(notification)

        self._update_visible()

    def _get_portrait_from_pokemon(self, pokemon):
        """Carrega portrait a partir do objeto Pokémon"""
        cache_key = (pokemon.id, pokemon.is_shiny)

        if cache_key in self._portrait_cache:
            return self._portrait_cache[cache_key]

        try:
            if hasattr(pokemon, 'get_portrait'):
                portrait = pokemon.get_portrait()
            else:
                # Tenta acessar via pokedex global
                from src.data.pokedex import pokedex
                portrait = pokedex.get_portrait(pokemon.id, "normal", pokemon.is_shiny)

            if portrait:
                portrait = pygame.transform.scale(portrait, (48, 48))

                if pokemon.is_shiny:
                    shiny_overlay = pygame.Surface((48, 48), pygame.SRCALPHA)
                    shiny_overlay.fill((255, 215, 0, 60))
                    portrait.blit(shiny_overlay, (0, 0))

                self._portrait_cache[cache_key] = portrait
                return portrait
            else:
                print(f"[NOTIFICATION] Portrait não encontrado para {pokemon.name} (ID: {pokemon.id})")
                return None

        except Exception as e:
            print(f"[NOTIFICATION] Erro ao carregar portrait para {pokemon.name}: {e}")
            return None

    def _update_visible(self):
        """Atualiza a lista de notificações visíveis"""
        start_idx = self.scroll_offset
        end_idx = start_idx + self.max_visible

        all_notifications = list(self._active_notifications) + list(self._notifications)
        self._visible_notifications = all_notifications[start_idx:end_idx]

    def update(self, dt: float):
        """Atualiza notificações"""
        current_time = pygame.time.get_ticks() / 1000.0

        still_active = []
        for notification in self._active_notifications:
            if notification.update(current_time):
                still_active.append(notification)

        self._active_notifications = still_active

        while len(self._active_notifications) < self.max_visible and self._notifications:
            next_notif = self._notifications.popleft()
            self._active_notifications.append(next_notif)

        total_count = len(self._active_notifications)
        if total_count <= self.max_visible:
            self.scroll_offset = 0
        elif self.scroll_offset > total_count - self.max_visible:
            self.scroll_offset = max(0, total_count - self.max_visible)

        self._update_visible()

    def scroll_up(self):
        """Rola para cima"""
        if self.scroll_offset > 0:
            self.scroll_offset -= 1
            self._update_visible()

    def scroll_down(self):
        """Rola para baixo"""
        max_offset = max(0, len(self._active_notifications) - self.max_visible)
        if self.scroll_offset < max_offset:
            self.scroll_offset += 1
            self._update_visible()

    def clear_all(self):
        """Limpa todas as notificações"""
        self._notifications.clear()
        self._active_notifications.clear()
        self.scroll_offset = 0
        self._update_visible()

    def on_notification(self, callback: Callable):
        self._on_notification_callbacks.append(callback)

    def handle_event(self, event):
        """Processa eventos de scroll"""
        if event.type == pygame.MOUSEWHEEL and self._hovering_notifications:
            if event.y > 0:
                self.scroll_up()
            elif event.y < 0:
                self.scroll_down()
            return True
        return False

    def render(self, screen: pygame.Surface, viewport: Optional[pygame.Rect] = None):
        """Renderiza notificações"""
        if not self._active_notifications:
            return

        screen_width = screen.get_width()
        screen_height = screen.get_height()

        if viewport:
            if "right" in self.position:
                base_x = viewport.x + viewport.width - self.toast_width - self.offset_x
            else:
                base_x = viewport.x + self.offset_x

            if "bottom" in self.position:
                base_y = viewport.y + viewport.height - self.offset_y
            else:
                base_y = viewport.y + self.offset_y
        else:
            if "right" in self.position:
                base_x = screen_width - self.toast_width - self.offset_x
            else:
                base_x = self.offset_x
            if "bottom" in self.position:
                base_y = screen_height - self.offset_y
            else:
                base_y = self.offset_y

        mouse_pos = pygame.mouse.get_pos()
        self._hovering_notifications = False

        for i, notification in enumerate(self._visible_notifications):
            if "bottom" in self.position:
                y_offset = - (i + 1) * (self.toast_height + self.toast_padding)
                y_pos = base_y + y_offset
            else:
                y_pos = base_y + i * (self.toast_height + self.toast_padding)

            toast_rect = pygame.Rect(base_x, y_pos, self.toast_width, self.toast_height)
            if toast_rect.collidepoint(mouse_pos):
                self._hovering_notifications = True

            self._render_single_notification(screen, notification, base_x, y_pos)

        total = len(self._active_notifications)
        if total > self.max_visible:
            self._render_scroll_indicator(screen, base_x, base_y, viewport)

    def _render_single_notification(self, screen, notification, x, y):
        """Renderiza uma notificação"""
        toast_surface = pygame.Surface((self.toast_width, self.toast_height), pygame.SRCALPHA)

        type_color = notification.type.value
        bg_color = (*self.colors['bg_card'], 220)

        # Fundo
        pygame.draw.rect(
            toast_surface,
            bg_color,
            (0, 0, self.toast_width, self.toast_height),
            border_radius=12
        )

        # Borda lateral colorida
        pygame.draw.rect(
            toast_surface,
            type_color,
            (0, 0, 6, self.toast_height),
            border_top_left_radius=12,
            border_bottom_left_radius=12
        )

        # Borda externa
        pygame.draw.rect(
            toast_surface,
            (*self.colors['border'], 200),
            (0, 0, self.toast_width, self.toast_height),
            width=2,
            border_radius=12
        )

        # Portrait
        portrait_x = 12
        portrait_y = (self.toast_height - 48) // 2

        if hasattr(notification, 'portrait') and notification.portrait:
            toast_surface.blit(notification.portrait, (portrait_x, portrait_y))
            text_start_x = 72
        else:
            text_start_x = 15

        # Título
        font_bold = self._get_font(15, True)
        type_names = {
            NotificationType.INFO: "INFO",
            NotificationType.SUCCESS: "SUCESSO",
            NotificationType.WARNING: "AVISO",
            NotificationType.ERROR: "ERRO",
            NotificationType.ACHIEVEMENT: "CONQUISTA",
            NotificationType.BATTLE: "BATALHA"
        }

        title = type_names.get(notification.type, "NOTIFICAÇÃO")
        title_surf = font_bold.render(title, True, type_color)
        toast_surface.blit(title_surf, (text_start_x, 8))

        # Mensagem
        font = self._get_font(14)
        max_chars = int((self.toast_width - text_start_x) / 7)

        if hasattr(notification, 'portrait') and notification.portrait:
            max_chars -= 4

        message = notification.message

        if len(message) > max_chars:
            split_point = message[:max_chars].rfind(' ')
            if split_point == -1:
                split_point = max_chars

            line1 = message[:split_point]
            line2 = message[split_point + 1:] if split_point + 1 < len(message) else ""

            text1 = font.render(line1, True, self.colors['text'])
            toast_surface.blit(text1, (text_start_x, 28))

            if line2:
                text2 = font.render(line2, True, self.colors['text'])
                toast_surface.blit(text2, (text_start_x, 46))
        else:
            text = font.render(message, True, self.colors['text'])
            text_y = (self.toast_height - text.get_height()) // 2
            toast_surface.blit(text, (text_start_x, text_y))

        # Barra de progresso
        if notification.duration > 0:
            life_ratio = notification._life / notification.duration
            bar_width = int((self.toast_width - 24) * life_ratio)
            bar_y = self.toast_height - 6

            pygame.draw.rect(
                toast_surface,
                type_color,
                (12, bar_y, bar_width, 3),
                border_radius=2
            )

        screen.blit(toast_surface, (x, y))

    def _render_scroll_indicator(self, screen, base_x, base_y, viewport):
        """Indicador de scroll"""
        total = len(self._active_notifications)
        visible = self.max_visible

        if total <= visible:
            return

        indicator_x = base_x + self.toast_width - 20
        indicator_y = base_y + (self.toast_height * visible) - 10

        dot_size = 4
        dot_spacing = 8

        for i in range(min(3, total - visible)):
            dot_y = indicator_y - i * dot_spacing
            alpha = 255 if i == 0 else 100
            pygame.draw.circle(
                screen,
                (*self.colors['text_muted'], alpha),
                (indicator_x, dot_y),
                dot_size // 2
            )


notification_manager = NotificationManager()