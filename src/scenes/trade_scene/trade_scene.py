# src/scenes/trade_scene/trade_scene.py

import pygame
import uuid
from src.scenes.base_scene import BaseScene
from src.network.protocol import create_message
from src.ui.toast_renderer import toast_info, toast_warning
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class TradeScene(BaseScene):
    def __init__(self, game, is_host, network):
        super().__init__(game)
        self.network = network
        self.is_host = is_host
        self.network.current_scene_callback = self._on_network_message

        # Estado
        self.my_offer = None
        self.opponent_offer = None
        self.my_accept = False
        self.opponent_accept = False
        self.trade_completed = False

        # ===== LISTA DE POKÉMON DO TIME (TODOS) =====
        self.my_pokemon = game.player.team[:]
        self.scroll_offset = 0
        self.visible_items = 6
        self.selected_index = -1

        # UI
        self.back_btn = pygame.Rect(0, 0, 120, 40)
        self.accept_btn = pygame.Rect(0, 0, 150, 40)
        self.decline_btn = pygame.Rect(0, 0, 150, 40)
        self.confirm_btn = pygame.Rect(0, 0, 180, 40)
        self.scroll_up_btn = pygame.Rect(0, 0, 30, 30)
        self.scroll_down_btn = pygame.Rect(0, 0, 30, 30)

        self._center_ui()

    def _center_ui(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self.back_btn.topleft = (vx + 20, vy + 20)
        self.accept_btn.center = (vx + vw // 2 - 100, vy + vh - 60)
        self.decline_btn.center = (vx + vw // 2 + 100, vy + vh - 60)
        self.confirm_btn.center = (vx + vw // 2, vy + vh - 60)
        self.scroll_up_btn.topleft = (vx + 235, vy + 130)
        self.scroll_down_btn.topleft = (vx + 235, vy + 130 + self.visible_items * 40 + 5)

    def _on_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "TRADE_OFFER":
            self.opponent_offer = payload.get("pokemon_data")
            self._check_both_offered()
        elif msg_type == "TRADE_CANCEL":
            self.opponent_offer = None
            self.opponent_accept = False
            toast_info("O oponente cancelou a oferta.")
        elif msg_type == "TRADE_ACCEPT":
            self.opponent_accept = True
            self._check_both_accepted()
        elif msg_type == "TRADE_DECLINE":
            self.opponent_accept = False
            toast_info("O oponente recusou a troca.")
            self._reset_state()
        elif msg_type == "TRADE_CONFIRM":
            self.opponent_accept = True
            if self.my_accept:
                self._execute_trade()
        elif msg_type == "TRADE_COMPLETE":
            self._finalize_trade(payload.get("pokemon_data"))
        elif msg_type == "DISCONNECT":
            toast_warning("O outro jogador desconectou.")
            self._return_to_menu()

    def _check_both_offered(self):
        if self.my_offer and self.opponent_offer:
            toast_info("Ambos ofereceram! Clique em 'Aceitar' para confirmar.")

    def _check_both_accepted(self):
        if self.my_accept and self.opponent_accept:
            toast_info("Ambos aceitaram! Clique em 'Confirmar Troca' para finalizar.")

    def _execute_trade(self):
        # Envia confirmação final
        self.network.send_to_all(create_message("TRADE_CONFIRM", {}))
        # Executa a troca localmente
        self._finalize_trade(self.opponent_offer)
        toast_info("Troca realizada com sucesso!")

    def _finalize_trade(self, received_data):
        offered_unique_id = self.my_offer.get("unique_id")

        # ===== 1. REMOVE DO TIME =====
        pokemon_removed = None
        for i, p in enumerate(self.game.player.team):
            if p.unique_id == offered_unique_id:
                pokemon_removed = p
                self.game.player.team.pop(i)
                break

        # ===== 2. REMOVE DA BOX =====
        for i, data in enumerate(self.game.player.pc_box):
            if data.get("unique_id") == offered_unique_id:
                self.game.player.pc_box.pop(i)
                break

        # ===== 3. REMOVE DO CACHE =====
        if offered_unique_id in self.game.player._pokemon_cache:
            del self.game.player._pokemon_cache[offered_unique_id]

        # ===== 4. CRIA O NOVO POKEMON =====
        from src.entities.pokemon import Pokemon
        new_pokemon = Pokemon.from_dict(received_data)
        new_pokemon.unique_id = str(uuid.uuid4())
        new_pokemon.is_in_team = True

        # ===== 5. ADICIONA AO TIME OU BOX =====
        if len(self.game.player.team) < 6:
            self.game.player.team.append(new_pokemon)
        else:
            self.game.player.add_to_box(new_pokemon)

        # ===== 6. ATUALIZA CACHE =====
        self.game.player._pokemon_cache[new_pokemon.unique_id] = new_pokemon

        # ===== 7. SALVA =====
        self.game.player.auto_save()

    def _reset_state(self):
        self.my_offer = None
        self.opponent_offer = None
        self.my_accept = False
        self.opponent_accept = False
        self.selected_index = -1

    def _return_to_menu(self):
        self.network.stop()
        self.game.current_scene = self.game.menu_scene

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._center_ui()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Scroll Up
            if self.scroll_up_btn.collidepoint(event.pos) and self.scroll_offset > 0:
                self.scroll_offset -= 1
                return

            # Scroll Down
            if self.scroll_down_btn.collidepoint(event.pos) and self.scroll_offset < len(
                    self.my_pokemon) - self.visible_items:
                self.scroll_offset += 1
                return

            # Botão Voltar
            if self.back_btn.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.network.send_to_all(create_message("DISCONNECT"))
                self._return_to_menu()
                return

            # Botões de troca
            if self.my_offer and self.opponent_offer:
                if not self.my_accept:
                    if self.accept_btn.collidepoint(event.pos):
                        self.my_accept = True
                        self.network.send_to_all(create_message("TRADE_ACCEPT"))
                        self._check_both_accepted()
                        return
                    if self.decline_btn.collidepoint(event.pos):
                        self.network.send_to_all(create_message("TRADE_DECLINE"))
                        self._reset_state()
                        return
                else:
                    if self.confirm_btn.collidepoint(event.pos) and self.opponent_accept:
                        self._execute_trade()
                        return

            # ===== SELEÇÃO DE POKÉMON (COM SCROLL) =====
            list_x = self.screen_manager.viewport_x + 30
            list_y = self.screen_manager.viewport_y + 130
            item_height = 40

            for i in range(self.visible_items):
                idx = i + self.scroll_offset
                if idx >= len(self.my_pokemon):
                    break

                pokemon = self.my_pokemon[idx]
                rect = pygame.Rect(list_x, list_y + i * item_height, 200, item_height)

                if rect.collidepoint(event.pos) and not self.my_offer:
                    self.my_offer = pokemon.to_dict()
                    self.network.send_to_all(create_message("TRADE_OFFER", {"pokemon_data": self.my_offer}))
                    toast_info(f"Você ofereceu {pokemon.name}")
                    self.selected_index = idx
                    self._check_both_offered()
                    break

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()
            # Scroll com teclas
            elif event.key == pygame.K_UP and self.scroll_offset > 0:
                self.scroll_offset -= 1
            elif event.key == pygame.K_DOWN and self.scroll_offset < len(self.my_pokemon) - self.visible_items:
                self.scroll_offset += 1

    def fixed_update(self, dt):
        while not self.network.incoming_queue.empty():
            item = self.network.incoming_queue.get_nowait()
            if self.is_host:
                msg, conn = item
                self._on_network_message(msg, conn)
            else:
                msg, _ = item
                self._on_network_message(msg, None)

    def render(self, screen):
        screen.fill((30, 30, 45))
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        font = pygame.font.Font(None, 36)
        title = font.render("TROCA DE POKEMON", True, (255, 215, 0))
        screen.blit(title, (vx + vw // 2 - title.get_width() // 2, vy + 30))

        font_small = pygame.font.Font(None, 24)
        my_name = f"Voce: {self.network.my_name}"
        opp_name = f"Oponente: {self.network.opponent_name or 'Aguardando...'}"
        screen.blit(font_small.render(my_name, True, (200, 200, 200)), (vx + 30, vy + 80))
        screen.blit(font_small.render(opp_name, True, (200, 200, 200)), (vx + vw // 2 + 30, vy + 80))

        # ===== LISTA DE POKEMON (COM SCROLL) =====
        list_x = vx + 30
        list_y = vy + 130
        item_height = 40

        # Fundo da lista
        list_bg = pygame.Rect(list_x - 5, list_y - 5, 210, self.visible_items * item_height + 10)
        pygame.draw.rect(screen, (25, 27, 45), list_bg, border_radius=5)

        # Renderiza Pokémon visíveis
        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self.my_pokemon):
                break

            pokemon = self.my_pokemon[idx]
            rect = pygame.Rect(list_x, list_y + i * item_height, 200, item_height)

            color = (60, 60, 80) if idx != self.selected_index else (80, 80, 120)
            if self.my_offer and pokemon.unique_id == self.my_offer.get("unique_id"):
                color = (60, 120, 60)

            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, (200, 200, 200), rect, 1, border_radius=5)

            name_display = pokemon.name
            if len(name_display) > 10:
                name_display = name_display[:10] + "."
            name = f"{name_display} Lv.{pokemon.level}"
            txt = font_small.render(name, True, (255, 255, 255))
            screen.blit(txt, (rect.x + 10, rect.y + 10))

        # ===== BOTÕES DE SCROLL =====
        if len(self.my_pokemon) > self.visible_items:
            # Up
            color = (60, 60, 80) if self.scroll_offset > 0 else (30, 30, 40)
            pygame.draw.rect(screen, color, self.scroll_up_btn, border_radius=5)
            pygame.draw.rect(screen, (200, 200, 200), self.scroll_up_btn, 1, border_radius=5)
            txt = font_small.render("▲", True, (255, 255, 255))
            screen.blit(txt, (self.scroll_up_btn.x + 8, self.scroll_up_btn.y + 5))

            # Down
            color = (60, 60, 80) if self.scroll_offset < len(self.my_pokemon) - self.visible_items else (30, 30, 40)
            self.scroll_down_btn.topleft = (vx + 235, list_y + self.visible_items * item_height + 10)
            pygame.draw.rect(screen, color, self.scroll_down_btn, border_radius=5)
            pygame.draw.rect(screen, (200, 200, 200), self.scroll_down_btn, 1, border_radius=5)
            txt = font_small.render("▼", True, (255, 255, 255))
            screen.blit(txt, (self.scroll_down_btn.x + 8, self.scroll_down_btn.y + 5))

        # ===== OFERTA DO OPONENTE =====
        offer_x = vx + vw // 2 + 30
        offer_y = vy + 120
        offer_rect = pygame.Rect(offer_x, offer_y, 250, 150)
        pygame.draw.rect(screen, (40, 40, 60), offer_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), offer_rect, 1, border_radius=5)

        if self.opponent_offer:
            opp_pokemon = self.opponent_offer
            txt = font_small.render(f"{opp_pokemon['name']} Lv.{opp_pokemon['level']}", True, (255, 255, 100))
            screen.blit(txt, (offer_x + 10, offer_y + 20))

            # Mostra tipos
            types = opp_pokemon.get('types', ['normal'])
            type_str = "/".join([t.capitalize() for t in types])
            txt = font_small.render(f"Tipo: {type_str}", True, (200, 200, 200))
            screen.blit(txt, (offer_x + 10, offer_y + 50))
        else:
            txt = font_small.render("Nenhuma oferta", True, (150, 150, 150))
            screen.blit(txt, (offer_x + 10, offer_y + 20))

        # ===== MINHA OFERTA =====
        my_offer_rect = pygame.Rect(list_x, offer_y + 170, 250, 150)
        pygame.draw.rect(screen, (40, 40, 60), my_offer_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), my_offer_rect, 1, border_radius=5)

        if self.my_offer:
            txt = font_small.render(f"{self.my_offer['name']} Lv.{self.my_offer['level']}", True, (100, 255, 100))
            screen.blit(txt, (my_offer_rect.x + 10, my_offer_rect.y + 20))

            types = self.my_offer.get('types', ['normal'])
            type_str = "/".join([t.capitalize() for t in types])
            txt = font_small.render(f"Tipo: {type_str}", True, (200, 200, 200))
            screen.blit(txt, (my_offer_rect.x + 10, my_offer_rect.y + 50))
        else:
            txt = font_small.render("Clique em um Pokemon para oferecer", True, (150, 150, 150))
            screen.blit(txt, (my_offer_rect.x + 10, my_offer_rect.y + 20))

        # ===== BOTÕES =====
        self._draw_button(screen, self.back_btn, "VOLTAR", (100, 50, 50), (150, 80, 80))

        if self.my_offer and self.opponent_offer:
            if not self.my_accept:
                self._draw_button(screen, self.accept_btn, "ACEITAR", (50, 150, 50), (100, 200, 100))
                self._draw_button(screen, self.decline_btn, "CANCELAR", (150, 50, 50), (200, 80, 80))
            else:
                if self.opponent_accept:
                    self._draw_button(screen, self.confirm_btn, "CONFIRMAR TROCA", (50, 150, 50), (100, 200, 100))
                else:
                    txt = font_small.render("Aguardando confirmacao do oponente...", True, (255, 200, 100))
                    screen.blit(txt, (vx + vw // 2 - txt.get_width() // 2, vy + vh - 60))

        if self.trade_completed:
            msg = "Troca concluida! Pressione VOLTAR."
            txt = font_small.render(msg, True, (255, 255, 0))
            screen.blit(txt, (vx + vw // 2 - txt.get_width() // 2, vy + vh - 100))

    def _draw_button(self, screen, rect, text, color, hover_color):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, hover_color if hover else color, rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), rect, 2, border_radius=10)
        font = pygame.font.Font(None, 28)
        txt = font.render(text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)