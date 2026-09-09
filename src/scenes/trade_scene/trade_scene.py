# src/scenes/trade_scene/trade_scene.py

import pygame
import uuid
from src.scenes.base_scene import BaseScene
from src.network.protocol import create_message
from src.ui.toast_renderer import toast_info, toast_warning
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class TradeScene(BaseScene):
    """Tela de troca de Pokémon com scroll e design refinado"""

    def __init__(self, game, is_host, network):
        super().__init__(game)
        self.network = network
        self.is_host = is_host
        self.network.current_scene_callback = self._on_network_message

        # ===== ESTADO =====
        self.my_offer = None
        self.opponent_offer = None
        self.my_accept = False
        self.opponent_accept = False
        self.trade_completed = False
        self.trade_in_progress = False

        # ===== LISTA DE POKÉMON DO TIME =====
        self.my_pokemon = game.player.team[:]
        self.scroll_offset = 0
        self.visible_items = 6
        self.selected_index = -1

        # ===== UI =====
        self.back_btn = pygame.Rect(0, 0, 120, 40)
        self.accept_btn = pygame.Rect(0, 0, 150, 40)
        self.decline_btn = pygame.Rect(0, 0, 150, 40)
        self.confirm_btn = pygame.Rect(0, 0, 180, 40)

        self._center_ui()

        # ===== FONTES =====
        self.font_title = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)
        self.font_btn = pygame.font.Font(None, 22)

    def _center_ui(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self.back_btn.topleft = (vx + 20, vy + 20)
        self.accept_btn.center = (vx + vw//2 - 100, vy + vh - 60)
        self.decline_btn.center = (vx + vw//2 + 100, vy + vh - 60)
        self.confirm_btn.center = (vx + vw//2, vy + vh - 60)

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
            self._reset_state()
        elif msg_type == "TRADE_ACCEPT":
            self.opponent_accept = True
            self._check_both_accepted()
        elif msg_type == "TRADE_DECLINE":
            self.opponent_accept = False
            toast_info("O oponente recusou a troca.")
            self._reset_state()
        elif msg_type == "TRADE_CONFIRM":
            # Cliente confirma que aceitou
            self.opponent_accept = True
            if self.is_host and self.my_accept and not self.trade_in_progress:
                self._execute_trade()
        elif msg_type == "TRADE_COMPLETE":
            # Cliente recebe a confirmação do host
            if not self.is_host:
                self._perform_trade(payload.get("pokemon_data"))
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
        """Executa a troca - APENAS O HOST EXECUTA"""
        if self.trade_in_progress:
            return
        self.trade_in_progress = True

        # Host: executa a troca
        self._perform_trade(self.opponent_offer)

        # Envia TRADE_COMPLETE para o cliente
        self.network.send_to_all(create_message("TRADE_COMPLETE", {"pokemon_data": self.my_offer}))

        self.trade_completed = True
        toast_info("Troca realizada com sucesso!")
        self._reset_state()

    def _perform_trade(self, received_data):
        """Realiza a troca localmente"""
        offered_unique_id = self.my_offer.get("unique_id")

        # ===== REMOVE MEU POKEMON =====
        self._remove_pokemon_from_player(offered_unique_id)

        # ===== ADICIONA O POKEMON RECEBIDO =====
        self._add_pokemon_to_player(received_data)

    def _remove_pokemon_from_player(self, unique_id):
        """Remove um Pokémon do jogador (time, box e cache)"""
        # Remove do time
        for i, p in enumerate(self.game.player.team):
            if p.unique_id == unique_id:
                self.game.player.team.pop(i)
                break

        # Remove da box
        for i, data in enumerate(self.game.player.pc_box):
            if data.get("unique_id") == unique_id:
                self.game.player.pc_box.pop(i)
                break

        # Remove do cache
        if unique_id in self.game.player._pokemon_cache:
            del self.game.player._pokemon_cache[unique_id]

    def _add_pokemon_to_player(self, pokemon_data):
        """Adiciona um Pokémon ao jogador"""
        from src.entities.pokemon import Pokemon

        # Cria o Pokémon com novo unique_id
        new_pokemon = Pokemon.from_dict(pokemon_data)
        new_pokemon.unique_id = str(uuid.uuid4())
        new_pokemon.is_in_team = True

        # Adiciona ao time se houver espaço
        if len(self.game.player.team) < 6:
            self.game.player.team.append(new_pokemon)
        else:
            self.game.player.add_to_box(new_pokemon)

        # Atualiza cache
        self.game.player._pokemon_cache[new_pokemon.unique_id] = new_pokemon

        # Salva
        self.game.player.auto_save()

    def _reset_state(self):
        self.my_offer = None
        self.opponent_offer = None
        self.my_accept = False
        self.opponent_accept = False
        self.selected_index = -1
        self.trade_in_progress = False

    def _return_to_menu(self):
        self.network.stop()
        self.game.current_scene = self.game.menu_scene

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._center_ui()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # ===== SCROLL =====
            # Scroll up na lista
            if self._is_scroll_up_click(event.pos):
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
                return

            # Scroll down na lista
            if self._is_scroll_down_click(event.pos):
                if self.scroll_offset < len(self.my_pokemon) - self.visible_items:
                    self.scroll_offset += 1
                return

            # ===== BOTÃO VOLTAR =====
            if self.back_btn.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.network.send_to_all(create_message("DISCONNECT"))
                self._return_to_menu()
                return

            # ===== BOTÕES DE TROCA =====
            if self.my_offer and self.opponent_offer and not self.trade_completed:
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
                        # Envia confirmação para o host
                        self.network.send_to_all(create_message("TRADE_CONFIRM", {}))
                        if self.is_host:
                            self._execute_trade()
                        else:
                            toast_info("Aguardando confirmação do host...")
                        return

            # ===== SELEÇÃO DE POKEMON =====
            if not self.my_offer and not self.trade_completed:
                selected = self._get_pokemon_at_pos(event.pos)
                if selected is not None:
                    pokemon = self.my_pokemon[selected]
                    self.my_offer = pokemon.to_dict()
                    self.network.send_to_all(create_message("TRADE_OFFER", {"pokemon_data": self.my_offer}))
                    toast_info(f"Voce ofereceu {pokemon.name}")
                    self.selected_index = selected
                    self._check_both_offered()
                    return

        # ===== TECLADO =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()
            elif event.key == pygame.K_UP and self.scroll_offset > 0:
                self.scroll_offset -= 1
            elif event.key == pygame.K_DOWN and self.scroll_offset < len(self.my_pokemon) - self.visible_items:
                self.scroll_offset += 1

    def _is_scroll_up_click(self, pos):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        scroll_up = pygame.Rect(vx + 235, vy + 130, 30, 30)
        return scroll_up.collidepoint(pos)

    def _is_scroll_down_click(self, pos):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        scroll_down = pygame.Rect(vx + 235, vy + 130 + self.visible_items * 40 + 5, 30, 30)
        return scroll_down.collidepoint(pos)

    def _get_pokemon_at_pos(self, pos):
        """Retorna o índice do Pokémon clicado na lista"""
        list_x = self.screen_manager.viewport_x + 30
        list_y = self.screen_manager.viewport_y + 130
        item_height = 40

        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self.my_pokemon):
                break
            rect = pygame.Rect(list_x, list_y + i * item_height, 200, item_height)
            if rect.collidepoint(pos):
                return idx
        return None

    def fixed_update(self, dt):
        # Processa mensagens da fila
        try:
            while not self.network.incoming_queue.empty():
                item = self.network.incoming_queue.get_nowait()
                if self.is_host:
                    msg, conn = item
                    self._on_network_message(msg, conn)
                else:
                    msg, _ = item
                    self._on_network_message(msg, None)
        except:
            pass

    def render(self, screen):
        screen.fill((18, 20, 35))

        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        # ===== TÍTULO =====
        title = self.font_title.render("TROCA DE POKEMON", True, (255, 215, 0))
        title_rect = title.get_rect(center=(vx + vw//2, vy + 35))
        screen.blit(title, title_rect)

        # Linha decorativa
        pygame.draw.line(screen, (60, 60, 80),
                         (vx + vw//4, vy + 60),
                         (vx + vw*3//4, vy + 60), 2)

        # ===== NOMES DOS JOGADORES =====
        my_name = f"Voce: {self.network.my_name}"
        opp_name = f"Oponente: {self.network.opponent_name or 'Aguardando...'}"
        screen.blit(self.font.render(my_name, True, (200, 200, 200)), (vx + 30, vy + 80))
        screen.blit(self.font.render(opp_name, True, (200, 200, 200)), (vx + vw//2 + 30, vy + 80))

        # ===== LISTA DE POKEMON =====
        list_x = vx + 30
        list_y = vy + 130
        item_height = 40

        # Fundo da lista
        list_bg = pygame.Rect(list_x - 5, list_y - 5, 215, self.visible_items * item_height + 10)
        pygame.draw.rect(screen, (25, 27, 45), list_bg, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 80), list_bg, 1, border_radius=8)

        # Título da lista
        list_title = self.font_small.render("Seus Pokemon:", True, (200, 200, 200))
        screen.blit(list_title, (list_x, list_y - 25))

        # Pokémon visíveis
        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self.my_pokemon):
                break

            pokemon = self.my_pokemon[idx]
            rect = pygame.Rect(list_x, list_y + i * item_height, 200, item_height)

            # Cor do card
            if self.my_offer and pokemon.unique_id == self.my_offer.get("unique_id"):
                color = (60, 120, 60)
            elif idx == self.selected_index:
                color = (80, 80, 120)
            else:
                color = (50, 50, 70)

            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, (100, 100, 120), rect, 1, border_radius=5)

            # Nome e nível
            name_display = pokemon.name
            if len(name_display) > 12:
                name_display = name_display[:12] + "."
            name_text = f"{name_display} Lv.{pokemon.level}"
            txt = self.font.render(name_text, True, (255, 255, 255))
            screen.blit(txt, (rect.x + 10, rect.y + 10))

            # Shiny indicator
            if pokemon.is_shiny:
                shiny_text = self.font_small.render("⭐", True, (255, 215, 0))
                screen.blit(shiny_text, (rect.x + rect.width - 25, rect.y + 8))

        # ===== BOTÕES DE SCROLL =====
        if len(self.my_pokemon) > self.visible_items:
            # Scroll Up
            scroll_up = pygame.Rect(vx + 235, list_y, 30, 30)
            color = (60, 60, 80) if self.scroll_offset > 0 else (30, 30, 40)
            pygame.draw.rect(screen, color, scroll_up, border_radius=5)
            pygame.draw.rect(screen, (100, 100, 120), scroll_up, 1, border_radius=5)
            txt = self.font.render("▲", True, (255, 255, 255) if self.scroll_offset > 0 else (80, 80, 80))
            screen.blit(txt, (scroll_up.x + 8, scroll_up.y + 4))

            # Scroll Down
            scroll_down = pygame.Rect(vx + 235, list_y + self.visible_items * item_height + 5, 30, 30)
            color = (60, 60, 80) if self.scroll_offset < len(self.my_pokemon) - self.visible_items else (30, 30, 40)
            pygame.draw.rect(screen, color, scroll_down, border_radius=5)
            pygame.draw.rect(screen, (100, 100, 120), scroll_down, 1, border_radius=5)
            txt = self.font.render("▼", True, (255, 255, 255) if self.scroll_offset < len(self.my_pokemon) - self.visible_items else (80, 80, 80))
            screen.blit(txt, (scroll_down.x + 8, scroll_down.y + 4))

        # ===== OFERTA DO OPONENTE =====
        offer_x = vx + vw//2 + 30
        offer_y = vy + 130
        offer_rect = pygame.Rect(offer_x, offer_y, 250, 160)

        # Título
        opp_title = self.font_small.render("Oferta do Oponente:", True, (200, 200, 200))
        screen.blit(opp_title, (offer_x, offer_y - 25))

        pygame.draw.rect(screen, (25, 27, 45), offer_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 80), offer_rect, 1, border_radius=8)

        if self.opponent_offer:
            opp_pokemon = self.opponent_offer
            # Nome
            txt = self.font.render(f"{opp_pokemon['name']} Lv.{opp_pokemon['level']}", True, (255, 255, 100))
            screen.blit(txt, (offer_x + 15, offer_y + 15))

            # Tipos
            types = opp_pokemon.get('types', ['normal'])
            type_str = "/".join([t.capitalize() for t in types])
            txt = self.font_small.render(f"Tipo: {type_str}", True, (200, 200, 200))
            screen.blit(txt, (offer_x + 15, offer_y + 45))

            # Nível (barra)
            level_percent = opp_pokemon['level'] / 100
            bar_x = offer_x + 15
            bar_y = offer_y + 75
            bar_width = 220
            bar_height = 8
            pygame.draw.rect(screen, (40, 40, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
            if level_percent > 0:
                pygame.draw.rect(screen, (255, 215, 0), (bar_x, bar_y, int(bar_width * level_percent), bar_height), border_radius=4)

            # Status
            if opp_pokemon.get('is_shiny', False):
                shiny = self.font_small.render("⭐ SHINY", True, (255, 215, 0))
                screen.blit(shiny, (offer_x + 15, offer_y + 95))
        else:
            txt = self.font.render("Aguardando oferta...", True, (150, 150, 150))
            screen.blit(txt, (offer_x + 15, offer_y + 60))

        # ===== MINHA OFERTA =====
        my_offer_x = vx + 30
        my_offer_y = offer_y + 180
        my_offer_rect = pygame.Rect(my_offer_x, my_offer_y, 250, 160)

        my_title = self.font_small.render("Sua Oferta:", True, (200, 200, 200))
        screen.blit(my_title, (my_offer_x, my_offer_y - 25))

        pygame.draw.rect(screen, (25, 27, 45), my_offer_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 80), my_offer_rect, 1, border_radius=8)

        if self.my_offer:
            my_pokemon = self.my_offer
            txt = self.font.render(f"{my_pokemon['name']} Lv.{my_pokemon['level']}", True, (100, 255, 100))
            screen.blit(txt, (my_offer_x + 15, my_offer_y + 15))

            types = my_pokemon.get('types', ['normal'])
            type_str = "/".join([t.capitalize() for t in types])
            txt = self.font_small.render(f"Tipo: {type_str}", True, (200, 200, 200))
            screen.blit(txt, (my_offer_x + 15, my_offer_y + 45))

            if my_pokemon.get('is_shiny', False):
                shiny = self.font_small.render("⭐ SHINY", True, (255, 215, 0))
                screen.blit(shiny, (my_offer_x + 15, my_offer_y + 75))
        else:
            txt = self.font.render("Clique em um Pokemon para oferecer", True, (150, 150, 150))
            screen.blit(txt, (my_offer_x + 15, my_offer_y + 60))

        # ===== BOTÃO VOLTAR =====
        self._draw_button(screen, self.back_btn, "VOLTAR", (80, 40, 40), (140, 60, 60))

        # ===== BOTÕES DE AÇÃO =====
        if self.my_offer and self.opponent_offer and not self.trade_completed:
            if not self.my_accept:
                self._draw_button(screen, self.accept_btn, "ACEITAR", (50, 150, 50), (80, 200, 80))
                self._draw_button(screen, self.decline_btn, "CANCELAR", (150, 50, 50), (200, 80, 80))
            else:
                if self.opponent_accept:
                    self._draw_button(screen, self.confirm_btn, "CONFIRMAR TROCA", (50, 150, 50), (80, 200, 80))
                else:
                    txt = self.font.render("Aguardando confirmacao do oponente...", True, (255, 200, 100))
                    txt_rect = txt.get_rect(center=(vx + vw//2, vy + vh - 60))
                    screen.blit(txt, txt_rect)

        if self.trade_completed:
            txt = self.font.render("✅ Troca concluida! Pressione VOLTAR.", True, (100, 255, 100))
            txt_rect = txt.get_rect(center=(vx + vw//2, vy + vh - 60))
            screen.blit(txt, txt_rect)

        # ===== INSTRUÇÕES =====
        instr = self.font_small.render("↑/↓ = scroll | ESC = voltar", True, (80, 80, 110))
        screen.blit(instr, (vx + 25, vy + vh - 25))

    def _draw_button(self, screen, rect, text, color, hover_color):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, hover_color if hover else color, rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), rect, 2, border_radius=10)
        txt = self.font_btn.render(text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)