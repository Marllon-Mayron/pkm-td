# src/scenes/game_scene/components/managers/item_drag_manager.py

import pygame
import math
from src.data.item_bag_catalog import item_bag_catalog
from src.data.move_data import MoveData


class ItemDragManager:
    """Gerencia o arrasto de itens da mochila para usar nos Pokémon"""

    def __init__(self, game, bag_manager):
        self.game = game
        self.bag = bag_manager
        self.catalog = item_bag_catalog
        self.move_data = MoveData()

        # Estado do arrasto
        self.is_dragging = False
        self.drag_item_id = None
        self.drag_item_data = None
        self.drag_screen_pos = (0, 0)
        self.drag_world_pos = (0, 0)

        # Preview
        self.preview_surface = None
        self.trail_positions = []
        self.trail_max_length = 8

        # Alvo sob o mouse
        self.hovered_target = None
        self.target_type = None
        self.valid_target = False
        self.cannot_capture_boss = False

        # Mensagem de erro específica
        self.error_message = None
        self.error_message_timer = 0
        self.error_message_target = None  # NOVO: guarda qual alvo gerou o erro

        # Animação
        self.animation_time = 0

        # Cursor personalizado
        self.normal_cursor = pygame.SYSTEM_CURSOR_ARROW
        self.drag_cursor = pygame.SYSTEM_CURSOR_HAND

    def start_drag(self, item_id, screen_pos, world_pos):
        """Inicia o arrasto de um item"""
        if not self.bag.has_item(item_id):
            print(f"[ITEM] Não tem {item_id}!")
            return False

        self.is_dragging = True
        self.drag_item_id = item_id
        self.drag_item_data = self.catalog.get_item(item_id)
        self.drag_screen_pos = screen_pos
        self.drag_world_pos = world_pos
        self.cannot_capture_boss = False
        self.error_message = None
        self.error_message_timer = 0
        self.error_message_target = None

        # Cria preview
        self._create_preview(item_id)

        # Inicia rastro
        self.trail_positions = [screen_pos]

        # Muda cursor
        pygame.mouse.set_cursor(self.drag_cursor)

        print(f"[ITEM] Arrastando {self.drag_item_data['name']}")
        return True

    def _create_preview(self, item_id):
        """Cria a superfície de preview do item"""
        sprite = self.catalog.get_sprite(item_id, scaled=True)
        if sprite:
            self.preview_surface = pygame.transform.scale(sprite, (48, 48))
            self._add_glow_effect()

    def _add_glow_effect(self):
        """Adiciona efeito de brilho ao preview baseado no tipo"""
        if not self.preview_surface or not self.drag_item_data:
            return

        if self.drag_item_data["category"] == "pokeball":
            color = (255, 100, 100)
        elif self.drag_item_data["category"] == "medicine":
            color = (100, 255, 100)
        else:
            color = (255, 255, 100)

        glow = pygame.Surface(self.preview_surface.get_size(), pygame.SRCALPHA)

        center = (glow.get_width() // 2, glow.get_height() // 2)
        radius = glow.get_width() // 2

        for i in range(3, 0, -1):
            alpha = 50 - i * 10
            glow_color = (*color, alpha)
            pygame.draw.circle(glow, glow_color, center, radius + i * 5, 2)

        final = self.preview_surface.copy()
        final.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.preview_surface = final

    def update_drag(self, screen_pos, world_pos, allied_pokemon, enemy_pokemon, camera):
        """Atualiza a posição do arrasto e verifica alvos"""
        if not self.is_dragging:
            return

        self.drag_screen_pos = screen_pos
        self.drag_world_pos = world_pos
        self.animation_time += 1 / 60

        # Atualiza timer da mensagem de erro
        if self.error_message_timer > 0:
            self.error_message_timer -= 1 / 60
            if self.error_message_timer <= 0:
                self.error_message = None
                self.error_message_target = None

        # Atualiza rastro
        self.trail_positions.append(screen_pos)
        if len(self.trail_positions) > self.trail_max_length:
            self.trail_positions.pop(0)

        # Guarda o alvo anterior para comparar
        previous_target = self.hovered_target
        previous_error_message = self.error_message

        # Reseta flags (mas mantém a mensagem de erro por enquanto)
        old_hovered_target = self.hovered_target
        self.hovered_target = None
        self.target_type = None
        self.valid_target = False
        self.cannot_capture_boss = False

        if not self.drag_item_data:
            return

        # ===== VERIFICA ALVOS =====
        if self.drag_item_data["category"] == "pokeball":
            self._check_pokeball_target(enemy_pokemon, screen_pos, camera)

        elif self.drag_item_data["category"] == "medicine":
            self._check_medicine_target(allied_pokemon, screen_pos, camera)

        elif self.drag_item_data["category"] == "items":
            if self.drag_item_data.get("effect") == "evolution":
                self._check_evolution_target(allied_pokemon, screen_pos, camera)

        elif self.drag_item_data["category"] == "tm":
            self._check_tm_target(allied_pokemon, screen_pos, camera)

        # ===== LIMPA MENSAGEM DE ERRO SE O ALVO MUDOU =====
        # Se não tem alvo hovered OU o alvo mudou, limpa a mensagem de erro
        if self.hovered_target is None:
            # Não está mais sobre nenhum alvo
            if self.error_message is not None:
                self.error_message = None
                self.error_message_timer = 0
                self.error_message_target = None
        elif self.error_message_target is not None and self.error_message_target != self.hovered_target:
            # Mudou de alvo, limpa mensagem de erro antiga
            self.error_message = None
            self.error_message_timer = 0
            self.error_message_target = None

    def _check_pokeball_target(self, enemies, screen_pos, camera):
        """Verifica alvo para pokebola"""
        for enemy in enemies:
            if self._is_target_valid(enemy, screen_pos, camera):
                if hasattr(enemy, 'is_boss') and enemy.is_boss:
                    self.cannot_capture_boss = True
                    self.valid_target = False
                    self.hovered_target = enemy
                    self.target_type = "enemy"
                    # Mensagem de erro para boss
                    self.error_message = f"{enemy.name} é um BOSS! Não pode ser capturado!"
                    self.error_message_timer = 0.5
                    self.error_message_target = enemy
                else:
                    self.hovered_target = enemy
                    self.target_type = "enemy"
                    self.valid_target = True
                    # Limpa erro se estava com boss
                    if self.error_message_target == enemy:
                        self.error_message = None
                        self.error_message_timer = 0
                        self.error_message_target = None
                break

    def _check_medicine_target(self, allies, screen_pos, camera):
        """Verifica alvo para poções/remédios"""
        for ally in allies:
            if self._is_target_valid(ally, screen_pos, camera):
                self.hovered_target = ally
                self.target_type = "ally"
                self.valid_target = True
                # Limpa qualquer erro anterior
                if self.error_message_target == ally:
                    self.error_message = None
                    self.error_message_timer = 0
                    self.error_message_target = None
                break

    def _check_evolution_target(self, allies, screen_pos, camera):
        """Verifica alvo para pedras de evolução"""
        for ally in allies:
            if self._is_target_valid(ally, screen_pos, camera):
                self.hovered_target = ally
                self.target_type = "ally"
                self.valid_target = True
                if self.error_message_target == ally:
                    self.error_message = None
                    self.error_message_timer = 0
                    self.error_message_target = None
                break

    def _check_tm_target(self, allies, screen_pos, camera):
        """Verifica alvo para TMs e também valida se o Pokémon pode aprender"""
        for ally in allies:
            if self._is_target_valid(ally, screen_pos, camera):
                move_name = self.drag_item_data.get("effect_value")
                if move_name:
                    # Verifica se o Pokémon pode aprender o move
                    if not self.move_data.can_learn_move(ally.id, move_name):
                        # Define mensagem de erro específica para este alvo
                        self.error_message = f"{ally.name} não pode aprender {move_name}!"
                        self.error_message_timer = 0.5
                        self.error_message_target = ally
                        self.valid_target = False
                        self.hovered_target = ally
                        self.target_type = "ally"
                        return

                    # Verifica se já sabe o move
                    for existing_move in ally.moves:
                        if existing_move.name.lower() == move_name.lower():
                            self.error_message = f"{ally.name} já sabe {move_name}!"
                            self.error_message_timer = 0.5
                            self.error_message_target = ally
                            self.valid_target = False
                            self.hovered_target = ally
                            self.target_type = "ally"
                            return

                # Alvo válido
                self.hovered_target = ally
                self.target_type = "ally"
                self.valid_target = True
                # Limpa erro se estava com este alvo
                if self.error_message_target == ally:
                    self.error_message = None
                    self.error_message_timer = 0
                    self.error_message_target = None
                break

    def _is_target_valid(self, target, screen_pos, camera, tolerance=50):
        """Verifica se um alvo é válido baseado na posição do mouse"""
        target_x, target_y = self.game.screen_manager.world_to_screen(
            target.x, target.y, camera
        )

        dist = math.sqrt(
            (screen_pos[0] - target_x) ** 2 +
            (screen_pos[1] - target_y) ** 2
        )

        return dist < tolerance

    def stop_drag(self, on_item_use_callback=None):
        """Finaliza o arrasto e tenta usar o item no alvo"""
        if not self.is_dragging:
            return None

        result = None

        # Se tem um alvo válido, tenta usar o item
        if self.valid_target and self.hovered_target and self.drag_item_id:
            valid_use = False

            # Pokebolas em inimigos
            if self.drag_item_data["category"] == "pokeball" and self.target_type == "enemy":
                valid_use = True

            # Poções e remédios em aliados
            elif self.drag_item_data["category"] == "medicine" and self.target_type == "ally":
                valid_use = True

            # Itens (pedras de evolução) em aliados
            elif self.drag_item_data["category"] == "items" and self.target_type == "ally":
                if self.drag_item_data.get("effect") == "evolution":
                    valid_use = True

            # TMs em aliados (já validado no update)
            elif self.drag_item_data["category"] == "tm" and self.target_type == "ally":
                valid_use = True

            if valid_use:
                # Remove o item da mochila
                self.bag.remove_item(self.drag_item_id, 1)

                # Chama callback de uso
                if on_item_use_callback:
                    result = on_item_use_callback(
                        self.hovered_target,
                        self.drag_item_data,
                        self.target_type
                    )

                print(f"[ITEM] Usou {self.drag_item_data['name']} em {getattr(self.hovered_target, 'name', 'alvo')}")

        # Reseta estado
        self.is_dragging = False
        self.drag_item_id = None
        self.drag_item_data = None
        self.hovered_target = None
        self.target_type = None
        self.valid_target = False
        self.cannot_capture_boss = False
        self.preview_surface = None
        self.trail_positions = []
        self.error_message = None
        self.error_message_timer = 0
        self.error_message_target = None

        # Restaura cursor
        pygame.mouse.set_cursor(self.normal_cursor)

        return result

    def cancel_drag(self):
        """Cancela o arrasto"""
        self.is_dragging = False
        self.drag_item_id = None
        self.drag_item_data = None
        self.hovered_target = None
        self.target_type = None
        self.valid_target = False
        self.cannot_capture_boss = False
        self.preview_surface = None
        self.trail_positions = []
        self.error_message = None
        self.error_message_timer = 0
        self.error_message_target = None
        pygame.mouse.set_cursor(self.normal_cursor)

    def render(self, screen, camera):
        """Renderiza o preview durante o arrasto"""
        if not self.is_dragging or not self.preview_surface:
            return

        # Desenha rastro
        self._render_trail(screen)

        # Desenha preview
        preview_rect = self.preview_surface.get_rect()
        preview_rect.center = self.drag_screen_pos

        preview_with_alpha = self.preview_surface.copy()
        preview_with_alpha.set_alpha(200)

        screen.blit(preview_with_alpha, preview_rect)

        # Se tem um alvo, mostra indicador
        if self.hovered_target:
            self._render_valid_indicator(screen, camera)

        # Se tem mensagem de erro e está no alvo atual, mostra no mouse
        if self.error_message and self.error_message_timer > 0 and self.hovered_target:
            self._render_error_message(screen)

        # Instruções
        self._render_drag_instructions(screen)

    def _render_trail(self, screen):
        """Renderiza o rastro do item"""
        if len(self.trail_positions) < 2:
            return

        for i in range(1, len(self.trail_positions)):
            alpha = int(150 * (i / len(self.trail_positions)))
            width = int(4 * (i / len(self.trail_positions)))

            if self.drag_item_data:
                if self.drag_item_data["category"] == "pokeball":
                    color = (255, 100, 100, alpha)
                elif self.drag_item_data["category"] == "medicine":
                    color = (100, 255, 100, alpha)
                else:
                    color = (255, 255, 100, alpha)
            else:
                color = (255, 255, 255, alpha)

            pygame.draw.line(
                screen,
                color[:3] + (alpha,),
                self.trail_positions[i - 1],
                self.trail_positions[i],
                max(1, width)
            )

    def _render_valid_indicator(self, screen, camera):
        """Renderiza indicador de alvo válido ou inválido"""
        if not self.hovered_target:
            return

        target_x, target_y = self.game.screen_manager.world_to_screen(
            self.hovered_target.x, self.hovered_target.y, camera
        )

        pulse = 0.5 + 0.5 * math.sin(self.animation_time * 5)
        radius = 40 + int(10 * pulse)

        indicator = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)

        # Determina cor e texto baseado no estado
        if self.cannot_capture_boss:
            color = (255, 50, 50)
            text = "BOSS NÃO PODE SER CAPTURADO!"
            valid = False
        elif self.error_message and self.error_message_target == self.hovered_target:
            # Mostra a mensagem de erro específica
            color = (255, 100, 100)
            # Limita o tamanho do texto
            error_text = self.error_message
            if len(error_text) > 28:
                error_text = error_text[:25] + "..."
            text = error_text
            valid = False
        elif self.valid_target:
            if self.target_type == "enemy":
                color = (100, 255, 100)
                text = "✓ SOLTAR PARA CAPTURAR"
            else:
                color = (100, 255, 100)
                text = "✓ SOLTAR PARA APLICAR"
            valid = True
        else:
            color = (255, 100, 100)
            text = "✗ ALVO INVÁLIDO"
            valid = False

        alpha = int(150 + 105 * pulse)
        pygame.draw.circle(indicator, (*color, alpha),
                           (radius, radius), radius, 3)

        if valid:
            pygame.draw.circle(indicator, (*color, 50),
                               (radius, radius), radius - 5)
        else:
            pygame.draw.circle(indicator, (*color, 100),
                               (radius, radius), radius - 5)

            # Desenha o X apenas se for inválido e não for mensagem de erro personalizada
            if not self.error_message or self.error_message_target != self.hovered_target:
                x_offset = radius - 15
                x_end = radius + 15
                pygame.draw.line(indicator, (*color, 200),
                                 (x_offset, x_offset), (x_end, x_end), 3)
                pygame.draw.line(indicator, (*color, 200),
                                 (x_end, x_offset), (x_offset, x_end), 3)

        screen.blit(indicator, (target_x - radius, target_y - radius))

        # Renderiza o texto do indicador
        font = pygame.font.Font(None, 20)
        text_surf = font.render(text, True, color)
        text_bg = pygame.Surface((text_surf.get_width() + 10, text_surf.get_height() + 4), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 180))

        text_x = target_x - text_surf.get_width() // 2
        text_y = target_y - radius - 25

        screen.blit(text_bg, (text_x - 5, text_y - 2))
        screen.blit(text_surf, (text_x, text_y))

    def _render_error_message(self, screen):
        """Renderiza mensagem de erro detalhada no mouse (apenas para erros específicos)"""
        if not self.error_message or not self.error_message_timer > 0 or not self.hovered_target:
            return

        # Só mostra a mensagem detalhada se for um erro específico (TM não pode aprender, etc)
        # e se ainda estiver sobre o mesmo alvo
        if self.error_message_target != self.hovered_target:
            return

        font = pygame.font.Font(None, 18)

        # Divide a mensagem em linhas se necessário
        words = self.error_message.split(' ')
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] < 280:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)

        if current_line:
            lines.append(' '.join(current_line))

        # Altura do fundo
        line_height = 22
        bg_height = len(lines) * line_height + 10
        bg_width = 300

        # Posição ao lado do mouse
        mouse_x, mouse_y = self.drag_screen_pos
        bg_x = mouse_x + 30
        bg_y = mouse_y - bg_height // 2

        # Garante que fique dentro da tela
        if bg_x + bg_width > self.game.screen_manager.window_width:
            bg_x = mouse_x - bg_width - 30
        if bg_y < 0:
            bg_y = mouse_y + 30
        if bg_y + bg_height > self.game.screen_manager.window_height:
            bg_y = mouse_y - bg_height - 30

        # Fundo vermelho escuro
        bg = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
        bg.fill((100, 30, 30, 220))
        pygame.draw.rect(bg, (200, 80, 80, 255), bg.get_rect(), 2, border_radius=5)

        screen.blit(bg, (bg_x, bg_y))

        # Desenha as linhas de texto
        y = bg_y + 5
        for line in lines:
            text_surf = font.render(line, True, (255, 200, 200))
            screen.blit(text_surf, (bg_x + 10, y))
            y += line_height

    def _render_drag_instructions(self, screen):
        """Renderiza instruções durante o arrasto"""
        font = pygame.font.Font(None, 18)

        # Determina as instruções baseado no estado
        if self.cannot_capture_boss and self.drag_item_data and self.drag_item_data["category"] == "pokeball":
            instructions = [
                f"{self.hovered_target.name} é um BOSS!",
                "BOSS NÃO PODE SER CAPTURADO!",
                "Derrote o boss para continuar!",
                "Clique DIREITO para soltar",
                "ESC para cancelar"
            ]
            color = (255, 100, 100)
        elif self.error_message and self.error_message_target == self.hovered_target:
            # Mostra instrução de erro
            instructions = [
                self.error_message[:40],
                "Clique DIREITO para cancelar",
                "ESC para cancelar"
            ]
            color = (255, 150, 150)
        elif self.drag_item_data:
            if self.drag_item_data["category"] == "pokeball":
                instructions = [
                    f"{self.drag_item_data['name']} - Arraste até um Pokémon selvagem",
                    "Clique DIREITO para soltar",
                    "ESC para cancelar"
                ]
                color = (255, 100, 100)
            elif self.drag_item_data["category"] == "medicine":
                instructions = [
                    f"{self.drag_item_data['name']} - Arraste até um Pokémon aliado",
                    "Clique DIREITO para soltar",
                    "ESC para cancelar"
                ]
                color = (100, 255, 100)
            elif self.drag_item_data.get("effect") == "evolution":
                instructions = [
                    f"{self.drag_item_data['name']} - Arraste até um Pokémon aliado para evoluir",
                    "Clique DIREITO para soltar",
                    "ESC para cancelar"
                ]
                color = (255, 215, 0)
            else:
                instructions = [
                    f"{self.drag_item_data['name']}",
                    "Clique DIREITO para soltar",
                    "ESC para cancelar"
                ]
                color = (255, 255, 255)
        else:
            instructions = ["Arraste o item", "Clique DIREITO para soltar", "ESC para cancelar"]
            color = (255, 255, 255)

        bg_height = len(instructions) * 22 + 10
        bg = pygame.Surface((280, bg_height), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))

        mouse_x, mouse_y = self.drag_screen_pos
        bg_x = mouse_x + 30
        bg_y = mouse_y - 30

        if bg_x + 280 > self.game.screen_manager.window_width:
            bg_x = mouse_x - 310
        if bg_y < 0:
            bg_y = mouse_y + 30
        if bg_y + bg_height > self.game.screen_manager.window_height:
            bg_y = mouse_y - bg_height - 30

        screen.blit(bg, (bg_x, bg_y))

        y = bg_y + 5
        for text in instructions:
            text_color = color if "BOSS" in text or "Arraste" in text or "Pokémon" in text else (200, 200, 200)
            text_surf = font.render(text, True, text_color)
            screen.blit(text_surf, (bg_x + 10, y))
            y += 22