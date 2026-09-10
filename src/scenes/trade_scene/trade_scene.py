# src/scenes/trade_scene/trade_scene.py

import pygame
import uuid
from datetime import datetime
from src.scenes.base_scene import BaseScene
from src.network.protocol import create_message
from src.ui.toast_renderer import toast_info, toast_warning
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.utils.pokemon_origin import (
    build_trade_origin, get_capture_label, TRADE_HISTORY_SEPARATOR,
)

# Paleta
COL_BG          = (16, 18, 30)
COL_PANEL       = (26, 29, 48)
COL_PANEL_DARK  = (20, 22, 38)
COL_BORDER      = (55, 58, 82)
COL_BORDER_HL   = (110, 115, 150)
COL_DIVIDER     = (45, 48, 70)

COL_ACCENT      = (255, 215, 0)
COL_TEXT        = (235, 235, 245)
COL_TEXT_DIM    = (170, 175, 200)
COL_TEXT_MUTED  = (95, 100, 130)

COL_SUCCESS     = (105, 220, 130)
COL_WARN        = (255, 185, 100)
COL_DANGER      = (230, 90, 90)
COL_INFO        = (110, 170, 255)

COL_ITEM           = (36, 40, 62)
COL_ITEM_HOVER     = (52, 58, 88)
COL_ITEM_SEL       = (58, 120, 78)
COL_ITEM_MARKED    = (60, 66, 100)

COL_BTN_PRIMARY    = (52, 100, 180)
COL_BTN_PRIMARY_H  = (76, 142, 232)
COL_BTN_SUCCESS    = (44, 128, 74)
COL_BTN_SUCCESS_H  = (70, 178, 104)
COL_BTN_DANGER     = (128, 48, 54)
COL_BTN_DANGER_H   = (180, 70, 76)
COL_BTN_DISABLED   = (40, 43, 58)


class TradeScene(BaseScene):
    """Tela de troca com fluxo em três etapas (ofertar, aceitar, confirmar)."""

    # -------- Estados --------
    ST_OFFERING  = "offering"   # pelo menos um lado ainda não ofereceu
    ST_ACCEPT    = "accept"     # ambos ofertaram, aguardando aceites
    ST_CONFIRM   = "confirm"    # ambos aceitaram, aguardando confirmação final
    ST_DONE      = "done"       # troca concluída
    ST_CANCELLED = "cancelled"  # troca cancelada / recusada

    def __init__(self, game, is_host, network):
        super().__init__(game)
        self.network = network
        self.is_host = is_host
        self.network.current_scene_callback = self._on_network_message

        # ===== ESTADO =====
        self.state = self.ST_OFFERING
        self.my_offer = None
        self.opponent_offer = None
        self.my_accept = False
        self.opponent_accept = False
        self.my_confirm = False
        self.opponent_confirm = False
        self.trade_in_progress = False
        self.trade_completed = False
        self.trade_error = None

        # ===== OPONENTE (nome + uuid) =====
        # Tenta pegar do network (preenchido pelo Lobby). Se não vier,
        # o TRADE_OFFER traz os dados e atualiza esses campos.
        self._opponent_name = getattr(network, "opponent_name", None) or "Oponente"
        self._opponent_uuid = getattr(network, "opponent_uuid", None) or "unknown"

        # ===== LISTA DE POKÉMON =====
        self.my_pokemon = list(game.player.team)
        self.scroll_offset = 0
        self.visible_items = 6
        self.selected_index = -1
        self._item_height = 44

        # ===== RETÂNGULOS =====
        self.back_btn = pygame.Rect(0, 0, 120, 40)

        # ===== FONTES =====
        self.font_title = pygame.font.Font(None, 40)
        self.font_h1    = pygame.font.Font(None, 26)
        self.font       = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 20)
        self.font_tiny  = pygame.font.Font(None, 18)
        self.font_btn   = pygame.font.Font(None, 22)

        self._layout()

    # =========================================================
    # Layout
    # =========================================================
    def _layout(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        self.back_btn.topleft = (vx + 20, vy + 20)
        self._btn_y = vy + vh - 60
        self._btn_center_x = vx + vw // 2
        self._btn_gap = 12

    # =========================================================
    # Fila de rede
    # =========================================================
    def fixed_update(self, dt):
        try:
            while not self.network.incoming_queue.empty():
                item = self.network.incoming_queue.get_nowait()
                if isinstance(item, tuple) and len(item) == 2:
                    msg, _ = item
                else:
                    msg = item
                self._on_network_message(msg, None)
        except Exception as e:
            print(f"[TRADE] Erro na fila: {e}")

    # =========================================================
    # Rede
    # =========================================================
    def _on_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "TRADE_OFFER":
            self.opponent_offer = payload.get("pokemon_data")
            # ===== GUARDA NOME/UUID DO OPONENTE =====
            self._opponent_name = (
                payload.get("sender_name")
                or self._opponent_name
                or "Oponente"
            )
            self._opponent_uuid = (
                payload.get("sender_uuid")
                or self._opponent_uuid
                or "unknown"
            )
            # Sincroniza no network (para consistência)
            if hasattr(self.network, 'opponent_name'):
                self.network.opponent_name = self._opponent_name
            if hasattr(self.network, 'opponent_uuid'):
                self.network.opponent_uuid = self._opponent_uuid
            print(f"[TRADE] Oferta recebida de {self._opponent_name} (UUID: {self._opponent_uuid})")
            self._refresh_state()

        elif msg_type == "TRADE_CANCEL":
            self.opponent_offer = None
            self.opponent_accept = False
            self.opponent_confirm = False
            toast_info("O oponente cancelou a oferta.")
            self._refresh_state()

        elif msg_type == "TRADE_ACCEPT":
            self.opponent_accept = True
            toast_info("O oponente aceitou a oferta.")
            self._refresh_state()

        elif msg_type == "TRADE_DECLINE":
            toast_info("O oponente recusou a troca.")
            self._cancel_trade("O oponente recusou a troca.")

        elif msg_type == "TRADE_CONFIRM":
            self.opponent_confirm = True
            toast_info("O oponente confirmou a troca.")
            self._refresh_state()

        elif msg_type == "TRADE_COMPLETE":
            # Apenas o cliente recebe; o host já executou localmente
            if not self.is_host and not self.trade_completed:
                data = payload.get("pokemon_data")
                self._perform_trade(data)
                self.trade_completed = True
                self.state = self.ST_DONE
                toast_info("Troca concluída!")

        elif msg_type == "DISCONNECT":
            if self.state != self.ST_DONE:
                self._cancel_trade("O outro jogador desconectou.")

    # =========================================================
    # Máquina de estados
    # =========================================================
    def _refresh_state(self):
        """Recalcula o estado com base nas flags e dispara a execução."""
        if self.trade_completed:
            self.state = self.ST_DONE
            return

        if self.my_offer is None or self.opponent_offer is None:
            self.state = self.ST_OFFERING
            return

        if not (self.my_accept and self.opponent_accept):
            self.state = self.ST_ACCEPT
            return

        if not (self.my_confirm and self.opponent_confirm):
            self.state = self.ST_CONFIRM
            return

        # ★ Ambos confirmaram: SOMENTE o host executa
        if self.is_host and not self.trade_in_progress:
            self._execute_trade()
        # cliente aguarda TRADE_COMPLETE do host (mantém ST_CONFIRM)

    def _cancel_trade(self, reason):
        self.state = self.ST_CANCELLED
        self.trade_error = reason
        self.my_offer = None
        self.opponent_offer = None
        self.my_accept = False
        self.opponent_accept = False
        self.my_confirm = False
        self.opponent_confirm = False
        self.selected_index = -1
        # Não zera _opponent_name/_opponent_uuid — mantém para eventual retry

    # =========================================================
    # Execução
    # =========================================================
    def _execute_trade(self):
        """Apenas o host chama isso, quando AMBOS os lados confirmaram."""
        if self.trade_in_progress:
            return
        self.trade_in_progress = True

        # ★ IMPORTANTE: estampa a origem ANTES de enviar, para que
        # o snapshot que vai no TRADE_COMPLETE já contenha a troca.
        self._stamp_trade_origin_on_offer()

        # Snapshot do meu Pokémon JÁ ESTAMPADO
        my_offer_snapshot = dict(self.my_offer) if self.my_offer else None

        # Executa localmente (recebe o do oponente; meu já foi estampado)
        self._perform_trade(self.opponent_offer)

        # Notifica o cliente do Pokémon que ele deve receber
        self.network.send_to_all(create_message(
            "TRADE_COMPLETE",
            {"pokemon_data": my_offer_snapshot},
        ))

        self.trade_completed = True
        self.state = self.ST_DONE
        toast_info("Troca realizada com sucesso!")

    def _perform_trade(self, received_data):
        if not self.my_offer:
            return

        # ===== 1. ESTAMPA A ORIGEM NO MEU PRÓPRIO POKÉMON OFERECIDO =====
        # (o que vai para o outro jogador). Precisa acontecer ANTES
        # de remover, para que o dict esteja atualizado quando serializado.
        self._stamp_trade_origin_on_offer()

        # ===== 2. REMOVE O MEU POKÉMON DO PLAYER =====
        offered_uid = self.my_offer.get("unique_id")
        self._remove_pokemon_from_player(offered_uid)

        # ===== 3. ADICIONA O RECEBIDO (já vem com a origem do outro lado) =====
        if received_data:
            self._add_pokemon_to_player(received_data)

        self.my_offer = None
        self.opponent_offer = None

    def _stamp_trade_origin_on_offer(self):
        """
        Adiciona uma entrada de troca na origem do Pokémon que ESTOU oferecendo,
        ANTES de removê-lo do player. Isso garante que o dict serializado
        (que vai para o outro jogador) já contenha o histórico de troca.
        """
        if not self.my_offer:
            return

        offered_uid = self.my_offer.get("unique_id")

        # ===== NOME E UUID DO OPONENTE =====
        # Prioridade: atributo local (do TRADE_OFFER) > network > fallback
        other_name = (
            getattr(self, '_opponent_name', None)
            or getattr(self.network, "opponent_name", None)
            or "Oponente"
        )
        other_uuid = (
            getattr(self, '_opponent_uuid', None)
            or getattr(self.network, "opponent_uuid", None)
            or "unknown"
        )

        # Encurta o UUID para exibição (8 chars) — o completo continua no save
        if other_uuid and other_uuid != "unknown" and len(other_uuid) > 8:
            other_uuid_short = other_uuid[:8]
        else:
            other_uuid_short = other_uuid or "unknown"

        # Método atual (pode ser "capture_pokeball" ou já concatenado)
        current_method = self.my_offer.get("capture_method", "unknown") or "unknown"

        # Se já tem histórico, preserva; senão, usa o label legível
        if TRADE_HISTORY_SEPARATOR in current_method:
            original_base = current_method
            original_extra = current_method
        else:
            original_base = get_capture_label(current_method)
            original_extra = ""

        new_origin = build_trade_origin(
            original_method=original_base,
            original_origin_extra=original_extra,
            traded_at=datetime.now(),
            other_player_name=other_name,
            other_player_id=other_uuid_short,
        )

        # Atualiza no dict da oferta
        self.my_offer["capture_method"] = new_origin

        # Atualiza no objeto real (time) ou no dict da box
        for p in self.game.player.team:
            if p.unique_id == offered_uid:
                p.capture_method = new_origin
                break
        else:
            for data in self.game.player.pc_box:
                if data.get("unique_id") == offered_uid:
                    data["capture_method"] = new_origin
                    break

        # Atualiza no cache
        if offered_uid in self.game.player._pokemon_cache:
            self.game.player._pokemon_cache[offered_uid].capture_method = new_origin

        print(f"[TRADE] Origem estampada: {new_origin}")

    def _add_pokemon_to_player(self, pokemon_data):
        """
        Adiciona o Pokémon recebido ao player.
        A origem já vem concatenada do outro lado (que rodou _stamp_trade_origin_on_offer).
        Também registra na Pokédex e como capturado.
        """
        from src.entities.pokemon import Pokemon

        new_pokemon = Pokemon.from_dict(pokemon_data)
        new_pokemon.unique_id = str(uuid.uuid4())
        new_pokemon.is_in_team = True

        # ===== GARANTE QUE A ORIGEM VEM DO OUTRO LADO =====
        if not new_pokemon.capture_method:
            new_pokemon.capture_method = "trade"

        if len(self.game.player.team) < 6:
            self.game.player.team.append(new_pokemon)
        else:
            self.game.player.add_to_box(new_pokemon)

        # ===== REGISTRA NA POKÉDEX =====
        self.game.player.caught_pokemon.add(new_pokemon.id)
        self.game.player.register_seen(new_pokemon.id)

        self.game.player._pokemon_cache[new_pokemon.unique_id] = new_pokemon
        self.game.player.auto_save()

        print(f"[TRADE] Pokémon recebido: {new_pokemon.name} "
              f"(origem: {new_pokemon.capture_method}) - registrado na Pokédex")

    def _remove_pokemon_from_player(self, unique_id):
        if not unique_id:
            return
        for i, p in enumerate(self.game.player.team):
            if p.unique_id == unique_id:
                self.game.player.team.pop(i)
                break
        for i, data in enumerate(self.game.player.pc_box):
            if data.get("unique_id") == unique_id:
                self.game.player.pc_box.pop(i)
                break
        if unique_id in self.game.player._pokemon_cache:
            del self.game.player._pokemon_cache[unique_id]

    def _return_to_menu(self):
        self.network.stop()
        self.game.current_scene = self.game.menu_scene

    def _return_to_lobby(self):
        """Volta para o lobby SEM encerrar a conexão de rede."""
        from src.scenes.lobby_scene.lobby_scene import LobbyScene
        self.game.current_scene = LobbyScene(
            self.game, is_host=self.is_host, network=self.network
        )

    # =========================================================
    # Botões inferiores (dinâmicos por estado)
    # =========================================================
    def _get_visible_buttons(self):
        """Retorna [(key, label, kind), ...] conforme o estado atual."""
        if self.state == self.ST_OFFERING:
            if self.my_offer:
                return [("cancel_offer", "Cancelar Oferta", "danger")]
        elif self.state == self.ST_ACCEPT:
            if not self.my_accept:
                return [
                    ("accept",  "Aceitar", "success"),
                    ("decline", "Recusar", "danger"),
                ]
        elif self.state == self.ST_CONFIRM:
            if not self.my_confirm:
                return [
                    ("confirm",        "Confirmar Troca", "success"),
                    ("cancel_confirm", "Cancelar",        "danger"),
                ]
        return []

    def _build_button_rects(self):
        buttons = self._get_visible_buttons()
        if not buttons:
            return []
        widths = [max(150, self.font_btn.size(label)[0] + 40)
                  for _, label, _ in buttons]
        total = sum(widths) + self._btn_gap * (len(buttons) - 1)
        x = self._btn_center_x - total // 2
        rects = []
        for (key, label, kind), w in zip(buttons, widths):
            rects.append((pygame.Rect(x, self._btn_y, w, 44), key, label, kind))
            x += w + self._btn_gap
        return rects

    # =========================================================
    # Eventos
    # =========================================================
    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._layout()
            return

        # ----- Teclado -----
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._handle_back_or_cancel()
                return
            if event.key == pygame.K_UP and self.scroll_offset > 0:
                self.scroll_offset -= 1
            elif event.key == pygame.K_DOWN:
                max_off = max(0, len(self.my_pokemon) - self.visible_items)
                if self.scroll_offset < max_off:
                    self.scroll_offset += 1

        # ----- Mouse -----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Scroll
            if self._scroll_up_rect().collidepoint(pos):
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
                return
            if self._scroll_down_rect().collidepoint(pos):
                max_off = max(0, len(self.my_pokemon) - self.visible_items)
                if self.scroll_offset < max_off:
                    self.scroll_offset += 1
                return

            # Voltar
            if self.back_btn.collidepoint(pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._handle_back_or_cancel()
                return

            # Botões inferiores (calculados dinamicamente)
            for rect, key, _label, _kind in self._build_button_rects():
                if rect.collidepoint(pos):
                    sound_manager.play_effect(SoundEffect.CLICK)
                    self._on_button_clicked(key)
                    return

            # Selecionar Pokémon (só se ainda não ofereci)
            if self.state == self.ST_OFFERING and not self.my_offer:
                idx = self._get_pokemon_at_pos(pos)
                if idx is not None and idx < len(self.my_pokemon):
                    pokemon = self.my_pokemon[idx]
                    self.my_offer = pokemon.to_dict()
                    self.selected_index = idx

                    # ===== ENVIA UUID DO JOGADOR JUNTO =====
                    my_uuid = (
                        getattr(self.game.player, 'uuid', None)
                        or getattr(self.network, 'my_uuid', None)
                        or "unknown"
                    )
                    self.network.send_to_all(create_message(
                        "TRADE_OFFER",
                        {
                            "pokemon_data": self.my_offer,
                            "sender_name": self.network.my_name,
                            "sender_uuid": my_uuid,
                        },
                    ))
                    toast_info(f"Você ofereceu {pokemon.name}")
                    self._refresh_state()
                    return

    def _handle_back_or_cancel(self):
        """
        ESC / Voltar na TradeScene:
          - Se a troca terminou/cancelou -> volta direto ao lobby.
          - Se eu tenho uma oferta em andamento -> cancela a oferta e permanece.
          - Caso contrário -> volta ao lobby também.
        Nunca envia DISCONNECT (isso é responsabilidade do Lobby).
        """
        # 1) Já terminou ou já cancelou: apenas sai da cena
        if self.state in (self.ST_DONE, self.ST_CANCELLED):
            self._return_to_lobby()
            return

        # 2) Tinha oferta ativa: cancela a oferta e continua na tela
        if self.my_offer is not None:
            self.network.send_to_all(create_message("TRADE_CANCEL"))
            self.my_offer = None
            self.my_accept = False
            self.my_confirm = False
            self.selected_index = -1
            self._refresh_state()
            toast_info("Oferta cancelada.")
            return

        # 3) Sem oferta e sem ter terminado: volta ao lobby
        self._return_to_lobby()

    def _on_button_clicked(self, key):
        if key == "accept":
            self.my_accept = True
            self.network.send_to_all(create_message("TRADE_ACCEPT"))
            self._refresh_state()

        elif key == "decline":
            self.network.send_to_all(create_message("TRADE_DECLINE"))
            self._cancel_trade("Você recusou a troca.")

        elif key == "confirm":
            self.my_confirm = True
            self.network.send_to_all(create_message("TRADE_CONFIRM"))
            self._refresh_state()

        elif key == "cancel_confirm":
            self.network.send_to_all(create_message("TRADE_CANCEL"))
            self._cancel_trade("Você cancelou a confirmação.")

        elif key == "cancel_offer":
            self._handle_back_or_cancel()

    # =========================================================
    # Helpers de hit test
    # =========================================================
    def _list_origin(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        return (vx + 30, vy + 150)

    def _scroll_up_rect(self):
        x, y = self._list_origin()
        return pygame.Rect(x + 205, y, 30, 30)

    def _scroll_down_rect(self):
        x, y = self._list_origin()
        return pygame.Rect(x + 205,
                           y + self.visible_items * self._item_height + 5,
                           30, 30)

    def _get_pokemon_at_pos(self, pos):
        x0, y0 = self._list_origin()
        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self.my_pokemon):
                break
            rect = pygame.Rect(x0, y0 + i * self._item_height, 200, self._item_height)
            if rect.collidepoint(pos):
                return idx
        return None

    # =========================================================
    # Render
    # =========================================================
    def render(self, screen):
        screen.fill(COL_BG)

        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        cx = vx + vw // 2

        # -------- Cabeçalho --------
        title = self.font_title.render("TROCA DE POKEMON", True, COL_ACCENT)
        screen.blit(title, title.get_rect(center=(cx, vy + 36)))

        pygame.draw.line(screen, COL_DIVIDER,
                         (vx + vw // 4, vy + 62),
                         (vx + vw * 3 // 4, vy + 62), 1)

        my_name_txt = f"Você: {self.network.my_name}"
        opp_display = self._opponent_name or self.network.opponent_name or 'Aguardando...'
        opp_name_txt = f"Oponente: {opp_display}"
        screen.blit(self.font_small.render(my_name_txt, True, COL_TEXT_DIM),
                    (vx + 30, vy + 75))
        screen.blit(self.font_small.render(opp_name_txt, True, COL_TEXT_DIM),
                    (vx + vw // 2 + 30, vy + 75))

        # -------- Lista --------
        self._render_list(screen)

        # -------- Painéis de oferta --------
        offer_x = vx + vw // 2 + 20
        offer_y = vy + 150
        offer_w = 260
        offer_h = 130

        screen.blit(self.font_small.render("Oferta do Oponente:", True, COL_TEXT_DIM),
                    (offer_x, offer_y - 25))
        self._draw_offer_panel(screen, offer_x, offer_y, offer_w, offer_h,
                               self.opponent_offer, side="opp")

        my_offer_y = offer_y + offer_h + 40
        screen.blit(self.font_small.render("Sua Oferta:", True, COL_TEXT_DIM),
                    (offer_x, my_offer_y - 25))
        self._draw_offer_panel(screen, offer_x, my_offer_y, offer_w, offer_h,
                               self.my_offer, side="me")

        # -------- Checklist de progresso --------
        self._render_progress(screen, offer_x, my_offer_y + offer_h + 25, offer_w)

        # -------- Botão Voltar --------
        self._draw_button(screen, self.back_btn, "Voltar", kind="danger")

        # -------- Botões inferiores --------
        for rect, _key, label, kind in self._build_button_rects():
            self._draw_button(screen, rect, label, kind=kind)

        # -------- Mensagem "aguardando" quando não há botões --------
        if self.state == self.ST_CONFIRM and self.my_confirm and not self.opponent_confirm:
            self._draw_center_text(screen, cx, self._btn_y + 22,
                                   "Aguardando confirmação do oponente...", COL_WARN)
        elif self.state == self.ST_CONFIRM and self.my_confirm and self.opponent_confirm:
            self._draw_center_text(screen, cx, self._btn_y + 22,
                                   "Executando troca...", COL_INFO)
        elif self.state == self.ST_ACCEPT and self.my_accept and not self.opponent_accept:
            self._draw_center_text(screen, cx, self._btn_y + 22,
                                   "Aguardando o oponente aceitar...", COL_WARN)

        # -------- Estado final --------
        if self.state == self.ST_DONE:
            self._render_overlay_message(
                screen, vx, vy, vw, vh,
                "TROCA CONCLUÍDA", COL_SUCCESS,
                "Os Pokémon foram trocados com sucesso.",
            )
        elif self.state == self.ST_CANCELLED:
            self._render_overlay_message(
                screen, vx, vy, vw, vh,
                "TROCA CANCELADA", COL_DANGER,
                self.trade_error or "A troca não foi concluída.",
            )

        # -------- Rodapé --------
        instr = self.font_tiny.render(
            "Selecione um Pokémon para oferecer   |   ESC = cancelar   |   Setas = scroll",
            True, COL_TEXT_MUTED,
        )
        screen.blit(instr, instr.get_rect(center=(cx, vy + vh - 22)))

    # ---------- sub-renders ----------
    def _render_list(self, screen):
        x0, y0 = self._list_origin()
        list_w = 200

        bg = pygame.Rect(x0 - 5, y0 - 5,
                         list_w + 10,
                         self.visible_items * self._item_height + 10)
        pygame.draw.rect(screen, COL_PANEL, bg, border_radius=8)
        pygame.draw.rect(screen, COL_BORDER, bg, 1, border_radius=8)

        screen.blit(self.font_small.render("Seus Pokémon:", True, COL_TEXT_DIM),
                    (x0, y0 - 25))

        mouse = pygame.mouse.get_pos()
        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self.my_pokemon):
                break
            pokemon = self.my_pokemon[idx]
            rect = pygame.Rect(x0, y0 + i * self._item_height,
                               list_w, self._item_height)

            if self.my_offer and pokemon.unique_id == self.my_offer.get("unique_id"):
                color = COL_ITEM_SEL
            elif idx == self.selected_index:
                color = COL_ITEM_MARKED
            elif (rect.collidepoint(mouse)
                  and self.state == self.ST_OFFERING
                  and not self.my_offer):
                color = COL_ITEM_HOVER
            else:
                color = COL_ITEM

            pygame.draw.rect(screen, color, rect, border_radius=6)
            pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=6)

            name = pokemon.name
            if len(name) > 13:
                name = name[:13] + "..."
            label = f"{name}  Lv.{pokemon.level}"
            screen.blit(self.font.render(label, True, COL_TEXT),
                        (rect.x + 12, rect.y + 12))

            if pokemon.is_shiny:
                s = self.font_small.render("SHINY", True, COL_ACCENT)
                screen.blit(s, (rect.right - s.get_width() - 10, rect.y + 13))

        # Scroll buttons
        if len(self.my_pokemon) > self.visible_items:
            max_off = max(0, len(self.my_pokemon) - self.visible_items)
            self._draw_scroll_btn(screen, self._scroll_up_rect(), "^",
                                  self.scroll_offset > 0)
            self._draw_scroll_btn(screen, self._scroll_down_rect(), "v",
                                  self.scroll_offset < max_off)

    def _draw_scroll_btn(self, screen, rect, symbol, enabled):
        bg = COL_PANEL if enabled else COL_PANEL_DARK
        fg = COL_TEXT if enabled else COL_TEXT_MUTED
        pygame.draw.rect(screen, bg, rect, border_radius=5)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=5)
        surf = self.font.render(symbol, True, fg)
        screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_offer_panel(self, screen, x, y, w, h, pokemon, side):
        rect = pygame.Rect(x, y, w, h)

        if pokemon:
            border = (78, 170, 100) if side == "me" else (78, 130, 200)
        else:
            border = COL_BORDER

        pygame.draw.rect(screen, COL_PANEL, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)

        if not pokemon:
            txt = self.font.render("Aguardando...", True, COL_TEXT_MUTED)
            screen.blit(txt, txt.get_rect(center=rect.center))
            return

        name = pokemon.get("name", "?")
        level = pokemon.get("level", 0)
        types = pokemon.get("types", ["normal"])

        screen.blit(self.font_h1.render(name, True, COL_TEXT), (x + 15, y + 15))
        screen.blit(self.font.render(f"Nível {level}", True, COL_TEXT_DIM),
                    (x + 15, y + 45))

        type_str = " / ".join(t.capitalize() for t in types)
        screen.blit(self.font_small.render(f"Tipo: {type_str}", True, COL_TEXT_DIM),
                    (x + 15, y + 70))

        bar_x, bar_y = x + 15, y + 95
        bar_w, bar_h = w - 30, 6
        pygame.draw.rect(screen, COL_PANEL_DARK,
                         (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        pct = min(1.0, max(0.0, level / 100.0))
        if pct > 0:
            pygame.draw.rect(screen, COL_ACCENT,
                             (bar_x, bar_y, int(bar_w * pct), bar_h),
                             border_radius=3)

        if pokemon.get("is_shiny", False):
            s = self.font_small.render("SHINY", True, COL_ACCENT)
            screen.blit(s, (x + w - s.get_width() - 15, y + 15))

    def _render_progress(self, screen, x, y, w):
        """Checklist visual das três etapas para cada lado."""
        h = 130
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, COL_PANEL, rect, border_radius=8)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=8)

        header = {
            self.ST_OFFERING: "ETAPA 1 DE 3 - OFERTA",
            self.ST_ACCEPT:   "ETAPA 2 DE 3 - ACEITE",
            self.ST_CONFIRM:  "ETAPA 3 DE 3 - CONFIRMAÇÃO",
            self.ST_DONE:     "CONCLUÍDO",
            self.ST_CANCELLED: "CANCELADO",
        }.get(self.state, "")
        header_color = COL_ACCENT
        if self.state == self.ST_DONE:
            header_color = COL_SUCCESS
        elif self.state == self.ST_CANCELLED:
            header_color = COL_DANGER

        screen.blit(self.font_small.render(header, True, header_color),
                    (x + 12, y + 10))

        # Colunas
        label_x = x + 20
        me_x = x + 165
        op_x = x + 220

        screen.blit(self.font_tiny.render("Você", True, COL_TEXT_MUTED),
                    (me_x - 8, y + 34))
        screen.blit(self.font_tiny.render("Oponente", True, COL_TEXT_MUTED),
                    (op_x - 12, y + 34))

        rows = [
            ("Oferta enviada",  self.my_offer   is not None, self.opponent_offer   is not None),
            ("Oferta aceita",   self.my_accept,              self.opponent_accept),
            ("Troca confirmada", self.my_confirm,            self.opponent_confirm),
        ]

        ry = y + 56
        for label, mine, theirs in rows:
            color = COL_SUCCESS if (mine and theirs) else COL_TEXT_DIM
            screen.blit(self.font_small.render(label, True, color),
                        (label_x, ry - 2))
            self._draw_check(screen, me_x, ry + 6, mine)
            self._draw_check(screen, op_x, ry + 6, theirs)
            ry += 24

    def _draw_check(self, screen, x, y, checked):
        if checked:
            pygame.draw.circle(screen, COL_SUCCESS, (x, y), 8)
            # Tick simples
            pygame.draw.lines(screen, COL_BG, False,
                              [(x - 3, y), (x - 1, y + 2), (x + 3, y - 3)], 2)
        else:
            pygame.draw.circle(screen, COL_BORDER, (x, y), 8, 2)

    def _draw_center_text(self, screen, cx, cy, text, color):
        surf = self.font.render(text, True, color)
        screen.blit(surf, surf.get_rect(center=(cx, cy)))

    def _render_overlay_message(self, screen, vx, vy, vw, vh,
                                title, color, subtitle):
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (vx, vy))

        cx, cy = vx + vw // 2, vy + vh // 2
        box = pygame.Rect(0, 0, 480, 170)
        box.center = (cx, cy)
        pygame.draw.rect(screen, COL_PANEL, box, border_radius=14)
        pygame.draw.rect(screen, color, box, 2, border_radius=14)

        t = self.font_title.render(title, True, color)
        screen.blit(t, t.get_rect(center=(box.centerx, box.y + 50)))

        s = self.font.render(subtitle, True, COL_TEXT_DIM)
        screen.blit(s, s.get_rect(center=(box.centerx, box.y + 95)))

        hint = self.font_small.render(
            "Pressione ESC ou clique em Voltar para sair.",
            True, COL_TEXT_MUTED,
        )
        screen.blit(hint, hint.get_rect(center=(box.centerx, box.y + 135)))

    def _draw_button(self, screen, rect, text, kind="primary"):
        palette = {
            "primary":   (COL_BTN_PRIMARY,  COL_BTN_PRIMARY_H),
            "success":   (COL_BTN_SUCCESS,  COL_BTN_SUCCESS_H),
            "danger":    (COL_BTN_DANGER,   COL_BTN_DANGER_H),
            "disabled":  (COL_BTN_DISABLED, COL_BTN_DISABLED),
        }
        base, hover = palette.get(kind, palette["primary"])
        mouse = pygame.mouse.get_pos()
        is_hover = rect.collidepoint(mouse) and kind != "disabled"
        bg = hover if is_hover else base

        pygame.draw.rect(screen, bg, rect, border_radius=8)
        border = COL_BORDER_HL if is_hover else COL_BORDER
        pygame.draw.rect(screen, border, rect, 1, border_radius=8)

        color = COL_TEXT if kind != "disabled" else COL_TEXT_MUTED
        surf = self.font_btn.render(text, True, color)
        screen.blit(surf, surf.get_rect(center=rect.center))