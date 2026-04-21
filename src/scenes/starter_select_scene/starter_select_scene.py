# src/scenes/starter_select_scene.py
"""
Cena de seleção de Pokémon inicial
"""
import pygame
from src.scenes.base_scene import BaseScene
from src.entities.pokemon import Pokemon
from src.data.pokedex import Pokedex


class StarterSelectScene(BaseScene):
    """Tela para escolher o Pokémon inicial"""

    # IDs dos Pokémon iniciais tradicionais
    STARTERS = [
        {"id": 1, "name": "Bulbasaur", "type": "grass", "color": (120, 200, 80)},
        {"id": 4, "name": "Charmander", "type": "fire", "color": (240, 128, 48)},
        {"id": 7, "name": "Squirtle", "type": "water", "color": (104, 144, 240)},
    ]

    def __init__(self, game):
        super().__init__(game)

        self.pokedex = Pokedex()
        self.selected_index = 0  # 0 = Bulbasaur, 1 = Charmander, 2 = Squirtle
        self.confirmed = False

        # Layout responsivo
        self.card_width = 200
        self.card_height = 250
        self.card_spacing = 40

        # Botão confirmar
        self.confirm_button = None
        self.confirm_hover = False

        # Animação de seleção
        self.selection_animation = 0
        self.animation_direction = 1

        # Fundo gradiente
        self.bg_gradient = None

        # Fonte
        self.title_font = None
        self.subtitle_font = None

    def enter(self):
        """Quando a cena é ativada"""
        print("[STARTER_SELECT] Escolha seu Pokémon inicial!")

    def _update_layout(self):
        """Atualiza posições baseado no tamanho da viewport"""
        vp_w = self.screen_manager.viewport_width
        vp_h = self.screen_manager.viewport_height
        vp_x = self.screen_manager.viewport_x
        vp_y = self.screen_manager.viewport_y

        # Calcula tamanho dos cards baseado na viewport
        self.card_width = int(vp_w * 0.18)
        self.card_height = int(vp_h * 0.4)
        self.card_spacing = int(vp_w * 0.03)

        # Posições dos cards (centralizados)
        total_width = (self.card_width * 3) + (self.card_spacing * 2)
        start_x = vp_x + (vp_w - total_width) // 2
        start_y = vp_y + int(vp_h * 0.35)

        self.card_positions = []
        for i in range(3):
            x = start_x + (self.card_width + self.card_spacing) * i
            y = start_y
            self.card_positions.append(pygame.Rect(x, y, self.card_width, self.card_height))

        # Botão confirmar
        confirm_width = int(vp_w * 0.15)
        confirm_height = int(vp_h * 0.07)
        confirm_x = vp_x + (vp_w - confirm_width) // 2
        confirm_y = start_y + self.card_height + int(vp_h * 0.05)
        self.confirm_button = pygame.Rect(confirm_x, confirm_y, confirm_width, confirm_height)

        # Tamanhos de fonte responsivos
        title_size = max(32, int(vp_h * 0.06))
        subtitle_size = max(20, int(vp_h * 0.03))
        self.title_font = pygame.font.Font(None, title_size)
        self.subtitle_font = pygame.font.Font(None, subtitle_size)

    def handle_event(self, event):
        """Processa eventos"""
        if self.confirmed:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.selected_index = (self.selected_index - 1) % 3
                self._play_select_sound()
            elif event.key == pygame.K_RIGHT:
                self.selected_index = (self.selected_index + 1) % 3
                self._play_select_sound()
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self._confirm_selection()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            # Verifica clique nos cards
            for i, rect in enumerate(self.card_positions):
                if rect.collidepoint(mouse_pos):
                    self.selected_index = i
                    self._play_select_sound()

            # Verifica clique no botão confirmar
            if self.confirm_button and self.confirm_button.collidepoint(mouse_pos):
                self._confirm_selection()

        elif event.type == pygame.MOUSEMOTION:
            if self.confirm_button:
                self.confirm_hover = self.confirm_button.collidepoint(event.pos)

    def _play_select_sound(self):
        """Toca som de seleção (se disponível)"""
        # TODO: Adicionar som quando implementado
        pass

    def _confirm_selection(self):
        """Confirma a escolha do Pokémon inicial"""
        if self.confirmed:
            return

        self.confirmed = True
        starter = self.STARTERS[self.selected_index]

        print(f"[STARTER_SELECT] Pokémon escolhido: {starter['name']}")

        # Adiciona ao time do jogador
        pokemon = self.game.player.add_starter(starter["id"])

        if pokemon:
            print(f"[STARTER_SELECT] {pokemon.name} adicionado ao time!")

            # Salva o progresso inicial
            self.game.player.save_game(1)

            # Avança para seleção de fases
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.current_scene = PhaseSelectScene(self.game)
        else:
            print("[STARTER_SELECT] ERRO: Não foi possível adicionar o Pokémon!")
            self.confirmed = False

    def fixed_update(self, dt):
        """Atualiza animações"""
        if self.confirmed:
            return

        # Animação pulsante do card selecionado
        self.selection_animation += dt * 3 * self.animation_direction
        if self.selection_animation >= 1:
            self.selection_animation = 1
            self.animation_direction = -1
        elif self.selection_animation <= 0:
            self.selection_animation = 0
            self.animation_direction = 1

    def render(self, screen):
        """Renderiza a tela de seleção"""
        self._draw_gradient_background(screen)

        # Atualiza layout (pode mudar com redimensionamento)
        self._update_layout()

        # Título
        title_text = self.title_font.render("ESCOLHA SEU POKÉMON INICIAL", True, (255, 255, 255))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title_text.get_width()) // 2
        title_y = self.screen_manager.viewport_y + int(self.screen_manager.viewport_height * 0.08)
        screen.blit(title_text, (title_x, title_y))

        # Subtítulo
        subtitle_text = self.subtitle_font.render("Use <- -> ou clique para escolher", True, (200, 200, 200))
        subtitle_x = self.screen_manager.viewport_x + (
                    self.screen_manager.viewport_width - subtitle_text.get_width()) // 2
        subtitle_y = title_y + title_text.get_height() + 10
        screen.blit(subtitle_text, (subtitle_x, subtitle_y))

        # Renderiza os 3 cards
        for i, starter in enumerate(self.STARTERS):
            is_selected = (i == self.selected_index)
            rect = self.card_positions[i]

            # Fundo do card
            pulse = 1.0
            if is_selected:
                pulse = 1.0 + (self.selection_animation * 0.1)
                # Borda dourada para selecionado
                border_color = (255, 215, 0)
                border_width = 4
            else:
                border_color = (100, 100, 100)
                border_width = 2

            # Fundo do card
            card_bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            card_bg.fill((30, 30, 40, 220))
            screen.blit(card_bg, rect)

            # Borda
            pygame.draw.rect(screen, border_color, rect, border_width, border_radius=10)

            # Efeito de brilho no selecionado
            if is_selected:
                glow_rect = rect.inflate(10, 10)
                pygame.draw.rect(screen, (255, 215, 0, 50), glow_rect, 2, border_radius=12)

            # Sprite do Pokémon
            sprite = self.pokedex.get_sprite(starter["id"], "front", shiny=False)
            if sprite:
                # Escala o sprite para caber no card
                max_size = min(rect.width * 0.7, rect.height * 0.5)
                sprite_scale = max_size / max(sprite.get_width(), sprite.get_height())
                new_w = int(sprite.get_width() * sprite_scale)
                new_h = int(sprite.get_height() * sprite_scale)
                scaled_sprite = pygame.transform.scale(sprite, (new_w, new_h))
                sprite_x = rect.x + (rect.width - new_w) // 2
                sprite_y = rect.y + int(rect.height * 0.15)
                screen.blit(scaled_sprite, (sprite_x, sprite_y))

            # Nome
            name_font = pygame.font.Font(None, int(rect.height * 0.08))
            name_color = (255, 255, 255) if not is_selected else (255, 215, 0)
            name_text = name_font.render(starter["name"], True, name_color)
            name_x = rect.x + (rect.width - name_text.get_width()) // 2
            name_y = rect.y + int(rect.height * 0.65)
            screen.blit(name_text, (name_x, name_y))

            # Tipo
            type_font = pygame.font.Font(None, int(rect.height * 0.06))
            type_text = type_font.render(starter["type"].upper(), True, starter["color"])
            type_x = rect.x + (rect.width - type_text.get_width()) // 2
            type_y = name_y + name_text.get_height() + 5
            screen.blit(type_text, (type_x, type_y))

            # Indicador de seleção
            if is_selected:
                indicator_size = 15
                indicator_y = rect.y + rect.height - indicator_size - 10
                pygame.draw.polygon(screen, (255, 215, 0), [
                    (rect.x + rect.width // 2, indicator_y),
                    (rect.x + rect.width // 2 - indicator_size // 2, indicator_y + indicator_size),
                    (rect.x + rect.width // 2 + indicator_size // 2, indicator_y + indicator_size)
                ])

        # Botão confirmar
        if self.confirm_button:
            btn_color = (60, 120, 60) if self.confirm_hover else (40, 80, 40)
            pygame.draw.rect(screen, btn_color, self.confirm_button, border_radius=8)
            pygame.draw.rect(screen, (100, 180, 100), self.confirm_button, 2, border_radius=8)

            btn_font = pygame.font.Font(None, int(self.confirm_button.height * 0.5))
            btn_text = btn_font.render("CONFIRMAR", True, (255, 255, 255))
            btn_x = self.confirm_button.x + (self.confirm_button.width - btn_text.get_width()) // 2
            btn_y = self.confirm_button.y + (self.confirm_button.height - btn_text.get_height()) // 2
            screen.blit(btn_text, (btn_x, btn_y))

        # Dica de teclado
        tip_font = pygame.font.Font(None, int(self.screen_manager.viewport_height * 0.02))
        tip_text = tip_font.render("<-  ->  para navegar | ENTER para confirmar", True, (150, 150, 150))
        tip_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - tip_text.get_width()) // 2
        tip_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height - 40
        screen.blit(tip_text, (tip_x, tip_y))

    def _draw_gradient_background(self, screen):
        """Desenha fundo com gradiente"""
        # Cria gradiente apenas se necessário ou se a tela mudou de tamanho
        if (self.bg_gradient is None or
                self.bg_gradient.get_width() != self.screen_manager.window_width or
                self.bg_gradient.get_height() != self.screen_manager.window_height):

            self.bg_gradient = pygame.Surface((self.screen_manager.window_width,
                                               self.screen_manager.window_height))
            for i in range(self.screen_manager.window_height):
                # Gradiente de azul escuro para roxo
                t = i / self.screen_manager.window_height
                r = int(20 + t * 60)
                g = int(20 + t * 30)
                b = int(60 + t * 100)
                pygame.draw.line(self.bg_gradient, (r, g, b), (0, i),
                                 (self.screen_manager.window_width, i))

        screen.blit(self.bg_gradient, (0, 0))