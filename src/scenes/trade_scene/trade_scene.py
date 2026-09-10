# src/scenes/trade_scene/trade_scene.py

import math
import pygame
import uuid
from datetime import datetime

from scenes.team_select_scene.components import PokemonModal
from src.scenes.base_scene import BaseScene
from src.network.protocol import create_message
from src.ui.toast_renderer import toast_info, toast_warning
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.utils.pokemon_origin import (
    build_trade_origin, get_capture_label, TRADE_HISTORY_SEPARATOR,
)
from src.data.pokedex import Pokedex
from src.scenes.team_select_scene.components.gradient_background import GradientBackground

# =========================================================
# Paleta (consistente com TeamSelectScene)
# =========================================================
COL_BG          = (16, 18, 30)
COL_PANEL       = (26, 29, 48)
COL_PANEL_DARK  = (20, 22, 38)
COL_PANEL_SOFT  = (32, 36, 58)
COL_BORDER      = (55, 58, 82)
COL_BORDER_HL   = (110, 115, 150)
COL_DIVIDER     = (45, 48, 70)

COL_ACCENT      = (255, 215, 0)
COL_TEXT        = (235, 235, 245)
COL_TEXT_DIM    = (170, 175, 200)
COL_TEXT_MUTED  = (95, 100, 130)

COL_SUCCESS     = (105, 220, 130)
COL_SUCCESS_DIM = (60, 130, 80)
COL_WARN        = (255, 185, 100)
COL_DANGER      = (230, 90, 90)
COL_INFO        = (110, 170, 255)

COL_ITEM           = (36, 40, 62)
COL_ITEM_HOVER     = (52, 58, 88)
COL_ITEM_SEL       = (58, 120, 78)
COL_ITEM_SEL_HOVER = (70, 145, 95)

COL_BTN_PRIMARY    = (52, 100, 180)
COL_BTN_PRIMARY_H  = (76, 142, 232)
COL_BTN_SUCCESS    = (44, 128, 74)
COL_BTN_SUCCESS_H  = (70, 178, 104)
COL_BTN_DANGER     = (128, 48, 54)
COL_BTN_DANGER_H   = (180, 70, 76)
COL_BTN_INFO       = (70, 85, 150)
COL_BTN_INFO_H     = (95, 115, 200)
COL_BTN_DISABLED   = (40, 43, 58)

COL_SHADOW         = (0, 0, 0, 70)

# =========================================================
# Layout responsivo (valores-base, escalados dinamicamente)
# =========================================================
LAYOUT = {
    "MARGIN": 24,
    "HEADER_H": 70,
    "FOOTER_H": 36,
    "BUTTON_H": 46,
    "GAP": 16,
    "LIST_ITEM_H": 64,
    "LIST_MIN_W": 300,
    "OFFER_MIN_W": 280,
    "OFFER_H": 170,
    "PROGRESS_H": 130,
}


class TradeScene(BaseScene):
    """Tela de troca com fluxo em três etapas (ofertar, aceitar, confirmar)."""

    # -------- Estados --------
    ST_OFFERING  = "offering"
    ST_ACCEPT    = "accept"
    ST_CONFIRM   = "confirm"
    ST_DONE      = "done"
    ST_CANCELLED = "cancelled"

    def __init__(self, game, is_host, network):
        super().__init__(game)
        self.network = network
        self.is_host = is_host
        self.network.current_scene_callback = self._on_network_message

        # ===== POKÉDEX (portraits/sprites) =====
        self.pokedex = Pokedex()

        # ===== BACKGROUND PADRONIZADO =====
        self.background = GradientBackground(game.screen_manager)

        # ===== ESTADO =====
        self.state = self.ST_OFFERING
        self.my_offer = None
        self.opponent_offer = None
        self.my_offer_pokemon = None
        self.opponent_offer_pokemon = None
        self.my_accept = False
        self.opponent_accept = False
        self.my_confirm = False
        self.opponent_confirm = False
        self.trade_in_progress = False
        self.trade_completed = False
        self.trade_error = None

        # ===== OPONENTE =====
        self._opponent_name = getattr(network, "opponent_name", None) or "Oponente"
        self._opponent_uuid = getattr(network, "opponent_uuid", None) or "unknown"

        # ===== LISTA DE POKÉMON =====
        self.my_pokemon = list(game.player.team)
        self.scroll_offset = 0
        self.visible_items = 5

        # ===== MODAL =====
        self.modal = None

        # ===== BOTÕES DE DETALHES (hit-test) =====
        self._detail_buttons = []
        self._offer_detail_buttons = []

        # ===== ANIMAÇÃO DE TROCA =====
        self._anim_active = False
        self._anim_time = 0.0
        self._anim_duration = 1.8
        self._anim_my_data = None
        self._anim_opp_data = None

        # ===== RETÂNGULOS (calculados em _layout) =====
        self.back_btn = pygame.Rect(0, 0, 0, 0)
        self._btn_y = 0
        self._btn_center_x = 0
        self._btn_gap = 12
        self._content_rect = pygame.Rect(0, 0, 0, 0)
        self._list_rect = pygame.Rect(0, 0, 0, 0)
        self._offers_rect = pygame.Rect(0, 0, 0, 0)
        self._opp_panel_rect = pygame.Rect(0, 0, 0, 0)
        self._my_panel_rect = pygame.Rect(0, 0, 0, 0)
        self._progress_rect = pygame.Rect(0, 0, 0, 0)
        self._item_height = LAYOUT["LIST_ITEM_H"]

        # ===== FONTES (criadas no _layout) =====
        self.font_title = pygame.font.Font(None, 44)
        self.font_h1    = pygame.font.Font(None, 28)
        self.font_h2    = pygame.font.Font(None, 24)
        self.font       = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 20)
        self.font_tiny  = pygame.font.Font(None, 18)
        self.font_btn   = pygame.font.Font(None, 22)
        self.font_btn_sm = pygame.font.Font(None, 16)

        self._layout()

    # =========================================================
    # Layout responsivo
    # =========================================================
    def _layout(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # ---- escala global (referência 1280x720) ----
        scale = min(vw / 1280.0, vh / 720.0)
        scale = max(0.65, min(1.25, scale))
        self._ui_scale = scale
        self._rebuild_fonts(scale)

        margin = max(10, int(LAYOUT["MARGIN"] * scale))

        # Botão voltar (canto superior esquerdo)
        back_w = max(90, int(110 * scale))
        back_h = max(30, int(36 * scale))
        self.back_btn = pygame.Rect(vx + margin, vy + 16, back_w, back_h)

        # Botões inferiores (centro)
        btn_h = max(36, int(LAYOUT["BUTTON_H"] * scale))
        footer_h = max(28, int(LAYOUT["FOOTER_H"] * scale))
        self._btn_y = vy + vh - footer_h - btn_h
        self._btn_center_x = vx + vw // 2
        self._btn_gap = max(8, int(12 * scale))

        # ===== Área de conteúdo =====
        header_h = max(56, int(LAYOUT["HEADER_H"] * scale))
        gap = max(10, int(LAYOUT["GAP"] * scale))
        content_top = vy + header_h
        content_bottom = self._btn_y - gap
        content_h = max(80, content_bottom - content_top)
        self._content_rect = pygame.Rect(
            vx + margin,
            content_top,
            max(100, vw - 2 * margin),
            content_h,
        )

        # ===== Divisão horizontal: lista (esquerda) vs ofertas (direita) =====
        total_w = self._content_rect.width
        list_min = max(220, int(LAYOUT["LIST_MIN_W"] * scale))
        offer_min = max(220, int(LAYOUT["OFFER_MIN_W"] * scale))

        list_w = max(list_min, int(total_w * 0.42))
        offers_w = total_w - list_w - gap
        if offers_w < offer_min:
            offers_w = offer_min
            list_w = max(list_min, total_w - offers_w - gap)
        if list_w + offers_w + gap > total_w:
            list_w = int((total_w - gap) * 0.5)
            offers_w = total_w - list_w - gap

        self._list_rect = pygame.Rect(
            self._content_rect.x,
            self._content_rect.y,
            list_w,
            self._content_rect.height,
        )
        self._offers_rect = pygame.Rect(
            self._list_rect.right + gap,
            self._content_rect.y,
            offers_w,
            self._content_rect.height,
        )

        # ===== Lista: quantos itens cabem =====
        list_header_h = max(28, int(32 * scale))
        available_list_h = max(40, self._list_rect.height - list_header_h)
        item_h = max(50, int(LAYOUT["LIST_ITEM_H"] * scale))
        self._item_height = item_h
        self.visible_items = max(2, available_list_h // item_h)
        self._list_header_h = list_header_h

        # ===== Ofertas: dois painéis + progresso =====
        offers_header_h = max(24, int(30 * scale))
        offer_h = max(110, int(LAYOUT["OFFER_H"] * scale))
        progress_h = max(90, int(LAYOUT["PROGRESS_H"] * scale))
        total_offers_h = (
            offers_header_h + offer_h + gap
            + offers_header_h + offer_h + gap
            + progress_h
        )

        if total_offers_h > self._offers_rect.height:
            scale2 = self._offers_rect.height / float(total_offers_h)
            offer_h = int(offer_h * scale2)
            progress_h = int(progress_h * scale2)

        self._offer_h = offer_h
        self._progress_h = progress_h
        self._offers_header_h = offers_header_h

        # Pre-calcula rects dos painéis de oferta
        y = self._offers_rect.y + offers_header_h
        self._opp_panel_rect = pygame.Rect(
            self._offers_rect.x, y, self._offers_rect.width, offer_h
        )
        y += offer_h + gap + offers_header_h
        self._my_panel_rect = pygame.Rect(
            self._offers_rect.x, y, self._offers_rect.width, offer_h
        )
        y += offer_h + gap
        self._progress_rect = pygame.Rect(
            self._offers_rect.x, y, self._offers_rect.width, progress_h
        )

    def _rebuild_fonts(self, scale):
        def sz(base):
            return max(11, int(base * scale))
        self.font_title  = pygame.font.Font(None, sz(44))
        self.font_h1     = pygame.font.Font(None, sz(28))
        self.font_h2     = pygame.font.Font(None, sz(24))
        self.font        = pygame.font.Font(None, sz(22))
        self.font_small  = pygame.font.Font(None, sz(20))
        self.font_tiny   = pygame.font.Font(None, sz(18))
        self.font_btn    = pygame.font.Font(None, sz(22))
        self.font_btn_sm = pygame.font.Font(None, sz(16))

    def _truncate(self, text, font, max_w):
        """Trunca texto com '...' se exceder max_w pixels."""
        if not text:
            return ""
        if max_w <= 0:
            return ""
        if font.size(text)[0] <= max_w:
            return text
        ell = "..."
        ell_w = font.size(ell)[0]
        if ell_w > max_w:
            return ""
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.size(text[:mid])[0] + ell_w <= max_w:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + ell

    # =========================================================
    # Update (rede + animação)
    # =========================================================
    def fixed_update(self, dt):
        # ---- Animação ----
        if self._anim_active:
            self._anim_time += dt
            if self._anim_time >= self._anim_duration:
                self._anim_time = self._anim_duration
                self._anim_active = False

        # ---- Rede ----
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
            self._opponent_name = (
                payload.get("sender_name") or self._opponent_name or "Oponente"
            )
            self._opponent_uuid = (
                payload.get("sender_uuid") or self._opponent_uuid or "unknown"
            )
            if hasattr(self.network, 'opponent_name'):
                self.network.opponent_name = self._opponent_name
            if hasattr(self.network, 'opponent_uuid'):
                self.network.opponent_uuid = self._opponent_uuid

            self.opponent_offer_pokemon = self._build_temp_pokemon(self.opponent_offer)

            print(f"[TRADE] Oferta recebida de {self._opponent_name}")
            self._refresh_state()

        elif msg_type == "TRADE_CANCEL":
            self.opponent_offer = None
            self.opponent_offer_pokemon = None
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
            if not self.is_host and not self.trade_completed:
                # Captura para animação ANTES de limpar
                anim_my = dict(self.my_offer) if self.my_offer else None
                anim_opp = dict(self.opponent_offer) if self.opponent_offer else None

                data = payload.get("pokemon_data")
                self._perform_trade(data)
                self.trade_completed = True
                self.state = self.ST_DONE
                self._start_trade_animation(anim_my, anim_opp)
                toast_info("Troca concluída!")

        elif msg_type == "DISCONNECT":
            if self.state != self.ST_DONE:
                self._cancel_trade("O outro jogador desconectou.")

    def _build_temp_pokemon(self, data):
        if not data:
            return None
        try:
            from src.entities.pokemon import Pokemon
            p = Pokemon.from_dict(data)
            if not p.unique_id:
                p.unique_id = str(uuid.uuid4())
            p.is_in_team = False
            return p
        except Exception as e:
            print(f"[TRADE] Erro ao criar Pokemon temporário: {e}")
            return None

    # =========================================================
    # Máquina de estados
    # =========================================================
    def _refresh_state(self):
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

        if self.is_host and not self.trade_in_progress:
            self._execute_trade()

    def _cancel_trade(self, reason):
        self.state = self.ST_CANCELLED
        self.trade_error = reason
        self.my_offer = None
        self.opponent_offer = None
        self.my_offer_pokemon = None
        self.opponent_offer_pokemon = None
        self.my_accept = False
        self.opponent_accept = False
        self.my_confirm = False
        self.opponent_confirm = False

    # =========================================================
    # Execução
    # =========================================================
    def _execute_trade(self):
        if self.trade_in_progress:
            return
        self.trade_in_progress = True

        self._stamp_trade_origin_on_offer()

        # Captura para animação
        anim_my = dict(self.my_offer) if self.my_offer else None
        anim_opp = dict(self.opponent_offer) if self.opponent_offer else None

        my_offer_snapshot = dict(self.my_offer) if self.my_offer else None

        self._perform_trade(self.opponent_offer)

        self.network.send_to_all(create_message(
            "TRADE_COMPLETE",
            {"pokemon_data": my_offer_snapshot},
        ))

        self.trade_completed = True
        self.state = self.ST_DONE
        self._start_trade_animation(anim_my, anim_opp)
        toast_info("Troca realizada com sucesso!")

    def _perform_trade(self, received_data):
        if not self.my_offer:
            return

        self._stamp_trade_origin_on_offer()

        offered_uid = self.my_offer.get("unique_id")
        self._remove_pokemon_from_player(offered_uid)

        if received_data:
            self._add_pokemon_to_player(received_data)

        self.my_offer = None
        self.opponent_offer = None
        self.my_offer_pokemon = None
        self.opponent_offer_pokemon = None

    def _stamp_trade_origin_on_offer(self):
        if not self.my_offer:
            return

        offered_uid = self.my_offer.get("unique_id")

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

        if other_uuid and other_uuid != "unknown" and len(other_uuid) > 8:
            other_uuid_short = other_uuid[:8]
        else:
            other_uuid_short = other_uuid or "unknown"

        current_method = self.my_offer.get("capture_method", "unknown") or "unknown"

        if TRADE_HISTORY_SEPARATOR in current_method:
            original_base = current_method
            original_extra = current_method
        else:
            original_base = current_method
            original_extra = ""

        new_origin = build_trade_origin(
            original_method=original_base,
            original_origin_extra=original_extra,
            traded_at=datetime.now(),
            other_player_name=other_name,
            other_player_id=other_uuid_short,
        )

        self.my_offer["capture_method"] = new_origin

        for p in self.game.player.team:
            if p.unique_id == offered_uid:
                p.capture_method = new_origin
                break
        else:
            for data in self.game.player.pc_box:
                if data.get("unique_id") == offered_uid:
                    data["capture_method"] = new_origin
                    break

        if offered_uid in self.game.player._pokemon_cache:
            self.game.player._pokemon_cache[offered_uid].capture_method = new_origin

        print(f"[TRADE] Origem estampada: {new_origin}")

    def _add_pokemon_to_player(self, pokemon_data):
        from src.entities.pokemon import Pokemon

        new_pokemon = Pokemon.from_dict(pokemon_data)
        new_pokemon.unique_id = str(uuid.uuid4())
        new_pokemon.is_in_team = True

        if not new_pokemon.capture_method:
            new_pokemon.capture_method = "trade"

        if len(self.game.player.team) < 6:
            self.game.player.team.append(new_pokemon)
        else:
            self.game.player.add_to_box(new_pokemon)

        self.game.player.caught_pokemon.add(new_pokemon.id)
        self.game.player.register_seen(new_pokemon.id)

        self.game.player._pokemon_cache[new_pokemon.unique_id] = new_pokemon
        self.game.player.auto_save()

        print(f"[TRADE] Pokémon recebido: {new_pokemon.name}")

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
        from src.scenes.lobby_scene.lobby_scene import LobbyScene
        self.game.current_scene = LobbyScene(
            self.game, is_host=self.is_host, network=self.network
        )

    # =========================================================
    # Animação de troca
    # =========================================================
    def _start_trade_animation(self, my_data, opp_data):
        # Só anima se ambos os lados tinham oferta válida
        if my_data is None or opp_data is None:
            self._anim_active = False
            return
        self._anim_active = True
        self._anim_time = 0.0
        self._anim_duration = 1.8
        self._anim_my_data = my_data
        self._anim_opp_data = opp_data

    # =========================================================
    # Modal de detalhes
    # =========================================================
    def _open_my_pokemon_modal(self, unique_id):
        try:
            if unique_id not in self.game.player._pokemon_cache:
                for p in self.game.player.team:
                    if p.unique_id == unique_id:
                        self.game.player._pokemon_cache[unique_id] = p
                        break
                else:
                    for data in self.game.player.pc_box:
                        if data.get("unique_id") == unique_id:
                            from src.entities.pokemon import Pokemon
                            p = Pokemon.from_dict(data)
                            self.game.player._pokemon_cache[unique_id] = p
                            break

            if unique_id not in self.game.player._pokemon_cache:
                toast_warning("Não foi possível abrir os detalhes.")
                return

            self.modal = PokemonModal(self.game, unique_id)
            self._neutralize_modal_buttons()
        except Exception as e:
            print(f"[TRADE] Erro ao abrir modal: {e}")
            toast_warning("Erro ao abrir detalhes.")

    def _open_opponent_pokemon_modal(self):
        if not self.opponent_offer:
            toast_warning("Nenhuma oferta recebida ainda.")
            return

        temp_pokemon = self._build_temp_pokemon(self.opponent_offer)
        if not temp_pokemon:
            toast_warning("Não foi possível exibir os detalhes.")
            return

        temp_uid = f"__trade_preview__{temp_pokemon.unique_id}"
        temp_pokemon.unique_id = temp_uid
        self.game.player._pokemon_cache[temp_uid] = temp_pokemon

        try:
            self.modal = PokemonModal(self.game, temp_uid)
            self._neutralize_modal_buttons()
        except Exception as e:
            print(f"[TRADE] Erro ao abrir modal do oponente: {e}")
            toast_warning("Erro ao abrir detalhes.")
        finally:
            if temp_uid in self.game.player._pokemon_cache:
                del self.game.player._pokemon_cache[temp_uid]

    def _neutralize_modal_buttons(self):
        if not self.modal:
            return
        self.modal.action_button = pygame.Rect(0, 0, 0, 0)
        self.modal.release_button = pygame.Rect(0, 0, 0, 0)

    def _close_modal(self):
        self.modal = None

    # =========================================================
    # Botões inferiores (dinâmicos por estado)
    # =========================================================
    def _get_visible_buttons(self):
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
        vw = self.screen_manager.viewport_width
        max_btn_w = int(vw * 0.4)
        widths = []
        for _, label, _ in buttons:
            w = max(140, self.font_btn.size(label)[0] + 40)
            w = min(w, max_btn_w)
            widths.append(w)
        total = sum(widths) + self._btn_gap * (len(buttons) - 1)
        x = self._btn_center_x - total // 2
        rects = []
        btn_h = max(36, int(LAYOUT["BUTTON_H"] * getattr(self, "_ui_scale", 1.0)))
        for (key, label, kind), w in zip(buttons, widths):
            rects.append((pygame.Rect(x, self._btn_y, w, btn_h),
                          key, label, kind))
            x += w + self._btn_gap
        return rects

    # =========================================================
    # Eventos
    # =========================================================
    def handle_event(self, event):
        # ===== BLOQUEIA INPUT DURANTE ANIMAÇÃO =====
        if self._anim_active:
            return

        # ===== MODAL TEM PRIORIDADE =====
        if self.modal and self.modal.visible:
            result = self.modal.handle_event(event)
            if result == "close":
                self._close_modal()
            return

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

            up_rect, down_rect = self._scroll_rects()
            if up_rect.collidepoint(pos):
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
                return
            if down_rect.collidepoint(pos):
                max_off = max(0, len(self.my_pokemon) - self.visible_items)
                if self.scroll_offset < max_off:
                    self.scroll_offset += 1
                return

            if self.back_btn.collidepoint(pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._handle_back_or_cancel()
                return

            for rect, key, _label, _kind in self._build_button_rects():
                if rect.collidepoint(pos):
                    sound_manager.play_effect(SoundEffect.CLICK)
                    self._on_button_clicked(key)
                    return

            for rect, source in self._offer_detail_buttons:
                if rect.collidepoint(pos):
                    sound_manager.play_effect(SoundEffect.CLICK)
                    if source == "opp":
                        self._open_opponent_pokemon_modal()
                    else:
                        if self.my_offer:
                            uid = self.my_offer.get("unique_id")
                            if uid:
                                self._open_my_pokemon_modal(uid)
                    return

            for rect, unique_id in self._detail_buttons:
                if rect.collidepoint(pos):
                    sound_manager.play_effect(SoundEffect.CLICK)
                    self._open_my_pokemon_modal(unique_id)
                    return

            if self.state == self.ST_OFFERING and not self.my_offer:
                idx = self._get_pokemon_at_pos(pos)
                if idx is not None and idx < len(self.my_pokemon):
                    self._select_pokemon(idx)
                    return

    def _select_pokemon(self, idx):
        pokemon = self.my_pokemon[idx]
        self.my_offer = pokemon.to_dict()
        self.my_offer_pokemon = pokemon

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

    def _handle_back_or_cancel(self):
        if self.state in (self.ST_DONE, self.ST_CANCELLED):
            self._return_to_lobby()
            return

        if self.my_offer is not None:
            self.network.send_to_all(create_message("TRADE_CANCEL"))
            self.my_offer = None
            self.my_offer_pokemon = None
            self.my_accept = False
            self.my_confirm = False
            self._refresh_state()
            toast_info("Oferta cancelada.")
            return

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
    def _list_items_origin(self):
        return (
            self._list_rect.x + 10,
            self._list_rect.y + self._list_header_h + 6,
        )

    def _scroll_rects(self):
        x, y = self._list_items_origin()
        btn_w = 28
        btn_h = 28
        up = pygame.Rect(
            self._list_rect.right - btn_w - 8,
            y,
            btn_w, btn_h,
        )
        down = pygame.Rect(
            self._list_rect.right - btn_w - 8,
            y + self.visible_items * self._item_height + 4,
            btn_w, btn_h,
        )
        return up, down

    def _get_pokemon_at_pos(self, pos):
        x0, y0 = self._list_items_origin()
        list_w = self._list_rect.width - 20

        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self.my_pokemon):
                break
            rect = pygame.Rect(
                x0, y0 + i * self._item_height,
                list_w, self._item_height - 4,
            )
            if rect.collidepoint(pos):
                for btn_rect, _ in self._detail_buttons:
                    if btn_rect.collidepoint(pos):
                        return None
                return idx
        return None

    # =========================================================
    # Render
    # =========================================================
    def render(self, screen):
        self.background.render(screen)

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        cx = vx + vw // 2

        self._render_header(screen, vx, vy, vw, cx)
        self._render_list(screen)
        self._render_offers(screen)

        self._draw_button(screen, self.back_btn, "Voltar", kind="danger")
        self._render_bottom_buttons(screen, cx)
        self._render_status_messages(screen, cx)
        self._render_footer(screen, vx, vy, vw, vh, cx)

        # Overlay de estado final (só quando NÃO está animando)
        if not self._anim_active:
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

        # ===== ANIMAÇÃO DE TROCA =====
        if self._anim_active:
            self._render_trade_animation(screen, vx, vy, vw, vh)

        if self.modal and self.modal.visible:
            self.modal.render(screen)

    # ---------- Cabeçalho ----------
    def _render_header(self, screen, vx, vy, vw, cx):
        title = self.font_title.render("TROCA DE POKEMON", True, COL_ACCENT)
        screen.blit(title, title.get_rect(center=(cx, vy + 30)))

        pygame.draw.line(screen, COL_DIVIDER,
                         (vx + vw // 4, vy + 56),
                         (vx + vw * 3 // 4, vy + 56), 1)

        my_name = self.network.my_name or "Você"
        opp_name = self._opponent_name or self.network.opponent_name or "Aguardando..."

        # Área máxima por nome (metade do header - margens)
        max_name_w = max(80, vw // 2 - 140)

        my_name = self._truncate(my_name, self.font_small, max_name_w)
        opp_name = self._truncate(opp_name, self.font_small, max_name_w)

        my_label = self.font_small.render("Você", True, COL_TEXT_MUTED)
        my_value = self.font_small.render(my_name, True, COL_TEXT)
        opp_label = self.font_small.render("Oponente", True, COL_TEXT_MUTED)
        opp_value = self.font_small.render(opp_name, True, COL_TEXT)

        left_x = vx + max(10, int(LAYOUT["MARGIN"] * getattr(self, "_ui_scale", 1.0)))
        right_x = cx + 20

        screen.blit(my_label, (left_x, vy + 22))
        screen.blit(my_value, (left_x + my_label.get_width() + 8, vy + 22))

        screen.blit(opp_label, (right_x, vy + 22))
        screen.blit(opp_value, (right_x + opp_label.get_width() + 8, vy + 22))

    # ---------- Painéis ----------
    def _draw_panel(self, screen, rect, bg=COL_PANEL, border=COL_BORDER,
                    radius=10, border_w=1):
        pygame.draw.rect(screen, bg, rect, border_radius=radius)
        if border_w > 0:
            pygame.draw.rect(screen, border, rect, border_w, border_radius=radius)

    def _draw_section_header(self, screen, x, y, text, color=COL_ACCENT):
        surf = self.font_h2.render(text, True, color)
        screen.blit(surf, (x, y))
        ul_y = y + surf.get_height() + 1
        pygame.draw.line(
            screen, COL_DIVIDER,
            (x, ul_y), (x + surf.get_width(), ul_y), 1
        )
        return surf.get_height() + 4

    # ---------- Lista ----------
    def _render_list(self, screen):
        rect = self._list_rect

        self._draw_panel(screen, rect, bg=COL_PANEL, border=COL_BORDER, radius=10)

        # Header
        hdr_h = self._draw_section_header(
            screen, rect.x + 14, rect.y + 8, "Seus Pokémon"
        )

        # Contador
        count_txt = self.font_tiny.render(
            f"{len(self.my_pokemon)} disponíveis", True, COL_TEXT_MUTED
        )
        screen.blit(count_txt, (
            rect.right - count_txt.get_width() - 14,
            rect.y + 12,
        ))

        self._detail_buttons = []

        x0, y0 = self._list_items_origin()
        list_w = rect.width - 20
        mouse = pygame.mouse.get_pos()

        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self.my_pokemon):
                break

            pokemon = self.my_pokemon[idx]
            item_rect = pygame.Rect(
                x0, y0 + i * self._item_height,
                list_w, self._item_height - 4,
            )
            self._draw_list_item(screen, item_rect, pokemon, mouse)

        # Scroll
        if len(self.my_pokemon) > self.visible_items:
            up, down = self._scroll_rects()
            max_off = max(0, len(self.my_pokemon) - self.visible_items)
            self._draw_scroll_btn(screen, up, "^", self.scroll_offset > 0)
            self._draw_scroll_btn(screen, down, "v", self.scroll_offset < max_off)

        if not self.my_pokemon:
            empty = self.font.render(
                "Nenhum Pokémon no time.", True, COL_TEXT_MUTED
            )
            screen.blit(empty, empty.get_rect(center=rect.center))

    def _draw_list_item(self, screen, rect, pokemon, mouse):
        is_selected = (
            self.my_offer
            and pokemon.unique_id == self.my_offer.get("unique_id")
        )
        can_select = self.state == self.ST_OFFERING and not self.my_offer
        is_hover = rect.collidepoint(mouse) and can_select

        if is_selected:
            bg = COL_ITEM_SEL_HOVER if rect.collidepoint(mouse) else COL_ITEM_SEL
            border = COL_SUCCESS
        elif is_hover:
            bg = COL_ITEM_HOVER
            border = COL_BORDER_HL
        else:
            bg = COL_ITEM
            border = COL_BORDER

        self._draw_panel(screen, rect, bg=bg, border=border, radius=8)

        # Portrait
        scale = getattr(self, "_ui_scale", 1.0)
        portrait_size = max(36, int(48 * scale))
        portrait = self.pokedex.get_portrait(
            pokemon.id, "normal", pokemon.is_shiny
        )
        px = rect.x + 8
        py = rect.y + (rect.height - portrait_size) // 2

        portrait_bg = pygame.Rect(
            px - 2, py - 2, portrait_size + 4, portrait_size + 4
        )
        pygame.draw.rect(screen, COL_PANEL_DARK, portrait_bg, border_radius=6)
        if pokemon.is_shiny:
            pygame.draw.rect(screen, COL_ACCENT, portrait_bg, 2, border_radius=6)
        else:
            pygame.draw.rect(screen, COL_BORDER, portrait_bg, 1, border_radius=6)

        if portrait:
            portrait_scaled = pygame.transform.smoothscale(
                portrait, (portrait_size, portrait_size)
            )
            screen.blit(portrait_scaled, (px, py))

        # ===== Área disponível para texto =====
        detail_btn_w = max(70, int(78 * scale))
        detail_btn_h = max(22, int(26 * scale))
        detail_btn = pygame.Rect(
            rect.right - detail_btn_w - 8,
            rect.y + (rect.height - detail_btn_h) // 2,
            detail_btn_w, detail_btn_h,
        )

        info_x = px + portrait_size + 12
        info_right = detail_btn.left - 8
        info_w = max(20, info_right - info_x)

        # Nome
        name_color = COL_ACCENT if pokemon.is_shiny else COL_TEXT
        name = self._truncate(pokemon.name, self.font_h2, info_w)
        name_surf = self.font_h2.render(name, True, name_color)
        screen.blit(name_surf, (info_x, rect.y + 6))

        # Nível
        lvl_surf = self.font_small.render(
            f"Nível {pokemon.level}", True, COL_TEXT_DIM
        )
        screen.blit(lvl_surf, (info_x, rect.y + 6 + name_surf.get_height() + 2))

        # Tipos
        type_font = pygame.font.Font(
            None, max(11, int(14 * scale))
        )
        type_x = info_x
        type_y = rect.bottom - max(16, int(20 * scale)) - 6
        for t in pokemon.types[:2]:
            t_color = self._get_type_color(t)
            t_surf = type_font.render(f" {t.upper()} ", True, (255, 255, 255))
            t_w = t_surf.get_width() + 6
            if type_x + t_w > info_right:
                break
            t_bg = pygame.Rect(type_x, type_y, t_w, max(16, int(18 * scale)))
            pygame.draw.rect(screen, t_color, t_bg, border_radius=4)
            screen.blit(t_surf, (t_bg.x + 3, t_bg.y + 2))
            type_x = t_bg.right + 6

        # Botão DETALHES
        hover = detail_btn.collidepoint(mouse)
        btn_color = COL_BTN_INFO_H if hover else COL_BTN_INFO
        pygame.draw.rect(screen, btn_color, detail_btn, border_radius=5)
        pygame.draw.rect(screen, COL_BORDER_HL, detail_btn, 1, border_radius=5)
        btn_text = self.font_btn_sm.render("DETALHES", True, COL_TEXT)
        screen.blit(btn_text, btn_text.get_rect(center=detail_btn.center))

        self._detail_buttons.append((detail_btn, pokemon.unique_id))

    def _draw_scroll_btn(self, screen, rect, symbol, enabled):
        bg = COL_PANEL_SOFT if enabled else COL_PANEL_DARK
        fg = COL_TEXT if enabled else COL_TEXT_MUTED
        pygame.draw.rect(screen, bg, rect, border_radius=5)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=5)
        surf = self.font_h2.render(symbol, True, fg)
        screen.blit(surf, surf.get_rect(center=rect.center))

    # ---------- Ofertas + Progresso ----------
    def _render_offers(self, screen):
        rect = self._offers_rect
        self._offer_detail_buttons = []

        gap = max(10, int(LAYOUT["GAP"] * getattr(self, "_ui_scale", 1.0)))

        # Oponente
        self._draw_section_header(
            screen, rect.x, rect.y, "Oferta do Oponente", color=COL_INFO
        )
        self._draw_offer_panel(
            screen, self._opp_panel_rect, self.opponent_offer, side="opp"
        )

        # Minha oferta
        my_header_y = self._opp_panel_rect.bottom + gap
        self._draw_section_header(
            screen, rect.x, my_header_y, "Sua Oferta", color=COL_SUCCESS
        )
        self._draw_offer_panel(
            screen, self._my_panel_rect, self.my_offer, side="me"
        )

        # Progresso
        self._render_progress(screen, self._progress_rect)

    def _draw_offer_panel(self, screen, rect, pokemon, side):
        # Cor da borda leva em conta animação
        has_data = pokemon is not None
        if self._anim_active:
            anim_data = self._anim_my_data if side == "me" else self._anim_opp_data
            has_data = anim_data is not None

        if has_data:
            border = COL_SUCCESS if side == "me" else COL_INFO
            border_w = 2
        else:
            border = COL_BORDER
            border_w = 1

        self._draw_panel(
            screen, rect, bg=COL_PANEL,
            border=border, radius=10, border_w=border_w
        )

        if not pokemon:
            if not self._anim_active:
                empty = self.font.render(
                    "Aguardando oferta...", True, COL_TEXT_MUTED
                )
                screen.blit(empty, empty.get_rect(center=rect.center))
            else:
                # Durante animação: texto sutil
                empty = self.font_small.render(
                    "Trocando...", True, COL_TEXT_MUTED
                )
                screen.blit(empty, empty.get_rect(center=rect.center))
            return

        scale = getattr(self, "_ui_scale", 1.0)

        # Portrait
        portrait_size = max(60, min(int(90 * scale), rect.height - 24))
        portrait = self.pokedex.get_portrait(
            pokemon.get("id", 0), "normal", pokemon.get("is_shiny", False)
        )
        px = rect.x + 14
        py = rect.y + (rect.height - portrait_size) // 2

        portrait_bg = pygame.Rect(
            px - 3, py - 3, portrait_size + 6, portrait_size + 6
        )
        pygame.draw.rect(screen, COL_PANEL_DARK, portrait_bg, border_radius=8)
        if pokemon.get("is_shiny"):
            pygame.draw.rect(screen, COL_ACCENT, portrait_bg, 2, border_radius=8)
        else:
            pygame.draw.rect(screen, COL_BORDER, portrait_bg, 1, border_radius=8)

        if portrait:
            portrait_scaled = pygame.transform.smoothscale(
                portrait, (portrait_size, portrait_size)
            )
            screen.blit(portrait_scaled, (px, py))

        # ===== Dados =====
        detail_btn_w = max(78, int(88 * scale))
        detail_btn_h = max(24, int(28 * scale))
        detail_btn = pygame.Rect(
            rect.right - detail_btn_w - 12,
            rect.bottom - detail_btn_h - 10,
            detail_btn_w, detail_btn_h,
        )

        info_x = px + portrait_size + 14
        info_right = detail_btn.left - 8
        info_w = max(30, info_right - info_x)

        name = pokemon.get("name", "?")
        level = pokemon.get("level", 0)
        is_shiny = pokemon.get("is_shiny", False)

        name_color = COL_ACCENT if is_shiny else COL_TEXT
        name = self._truncate(name, self.font_h1, info_w)
        name_surf = self.font_h1.render(name, True, name_color)
        screen.blit(name_surf, (info_x, rect.y + 12))

        lvl_surf = self.font.render(f"Nível {level}", True, COL_TEXT_DIM)
        screen.blit(lvl_surf, (info_x, rect.y + 12 + name_surf.get_height() + 4))

        # Tipos
        types = pokemon.get("types", [])
        type_font = pygame.font.Font(None, max(12, int(16 * scale)))
        type_x = info_x
        type_y = rect.y + 12 + name_surf.get_height() + lvl_surf.get_height() + 10
        for t in types[:2]:
            t_color = self._get_type_color(t)
            t_surf = type_font.render(f" {t.upper()} ", True, (255, 255, 255))
            t_w = t_surf.get_width() + 6
            if type_x + t_w > info_right:
                break
            t_bg = pygame.Rect(type_x, type_y, t_w, max(16, int(20 * scale)))
            pygame.draw.rect(screen, t_color, t_bg, border_radius=5)
            screen.blit(t_surf, (t_bg.x + 3, t_bg.y + 2))
            type_x = t_bg.right + 8

        # Botão DETALHES
        mouse = pygame.mouse.get_pos()
        hover = detail_btn.collidepoint(mouse)
        btn_color = COL_BTN_INFO_H if hover else COL_BTN_INFO
        pygame.draw.rect(screen, btn_color, detail_btn, border_radius=6)
        pygame.draw.rect(screen, COL_BORDER_HL, detail_btn, 1, border_radius=6)
        btn_text = self.font_btn_sm.render("DETALHES", True, COL_TEXT)
        screen.blit(btn_text, btn_text.get_rect(center=detail_btn.center))

        self._offer_detail_buttons.append((detail_btn, side))

    def _render_progress(self, screen, rect):
        self._draw_panel(screen, rect, bg=COL_PANEL, border=COL_BORDER, radius=10)

        header_map = {
            self.ST_OFFERING: "ETAPA 1 DE 3 - OFERTA",
            self.ST_ACCEPT:   "ETAPA 2 DE 3 - ACEITE",
            self.ST_CONFIRM:  "ETAPA 3 DE 3 - CONFIRMAÇÃO",
            self.ST_DONE:     "CONCLUÍDO",
            self.ST_CANCELLED: "CANCELADO",
        }
        header_txt = header_map.get(self.state, "")

        header_color = COL_ACCENT
        if self.state == self.ST_DONE:
            header_color = COL_SUCCESS
        elif self.state == self.ST_CANCELLED:
            header_color = COL_DANGER

        header = self.font_small.render(header_txt, True, header_color)
        screen.blit(header, (rect.x + 14, rect.y + 8))

        # Colunas
        label_x = rect.x + 16
        me_x = rect.x + int(rect.width * 0.68)
        op_x = rect.x + int(rect.width * 0.86)

        me_hdr = self.font_tiny.render("Você", True, COL_TEXT_MUTED)
        op_hdr = self.font_tiny.render("Oponente", True, COL_TEXT_MUTED)
        screen.blit(me_hdr, (me_x - me_hdr.get_width() // 2, rect.y + 32))
        screen.blit(op_hdr, (op_x - op_hdr.get_width() // 2, rect.y + 32))

        rows = [
            ("Oferta enviada",   self.my_offer   is not None, self.opponent_offer   is not None),
            ("Oferta aceita",    self.my_accept,              self.opponent_accept),
            ("Troca confirmada", self.my_confirm,             self.opponent_confirm),
        ]

        row_h = max(20, self.font_small.get_height() + 4)
        ry = rect.y + 54
        for label, mine, theirs in rows:
            color = COL_SUCCESS if (mine and theirs) else COL_TEXT_DIM
            label_surf = self.font_small.render(label, True, color)
            screen.blit(label_surf, (label_x, ry))
            self._draw_check(screen, me_x, ry + label_surf.get_height() // 2, mine)
            self._draw_check(screen, op_x, ry + label_surf.get_height() // 2, theirs)
            ry += row_h

    def _draw_check(self, screen, x, y, checked):
        r = 8
        if checked:
            pygame.draw.circle(screen, COL_SUCCESS, (x, y), r)
            pygame.draw.lines(screen, COL_BG, False,
                              [(x - 3, y), (x - 1, y + 2), (x + 3, y - 3)], 2)
        else:
            pygame.draw.circle(screen, COL_BORDER, (x, y), r, 2)

    # ---------- Botões inferiores ----------
    def _render_bottom_buttons(self, screen, cx):
        for rect, _key, label, kind in self._build_button_rects():
            self._draw_button(screen, rect, label, kind=kind)

    def _render_status_messages(self, screen, cx):
        if self._anim_active:
            return
        msg_y = self._btn_y + LAYOUT["BUTTON_H"] + 10

        msg = None
        color = COL_WARN
        if self.state == self.ST_CONFIRM and self.my_confirm and not self.opponent_confirm:
            msg, color = "Aguardando confirmação do oponente...", COL_WARN
        elif self.state == self.ST_CONFIRM and self.my_confirm and self.opponent_confirm:
            msg, color = "Executando troca...", COL_INFO
        elif self.state == self.ST_ACCEPT and self.my_accept and not self.opponent_accept:
            msg, color = "Aguardando o oponente aceitar...", COL_WARN
        elif self.state == self.ST_OFFERING and self.my_offer and not self.opponent_offer:
            msg, color = "Aguardando oferta do oponente...", COL_WARN
        elif self.state == self.ST_OFFERING and not self.my_offer and self.opponent_offer:
            msg, color = "Selecione um Pokémon para oferecer.", COL_INFO

        if msg:
            self._draw_center_text(screen, cx, msg_y, msg, color)

    def _draw_center_text(self, screen, cx, cy, text, color):
        surf = self.font.render(text, True, color)
        screen.blit(surf, surf.get_rect(center=(cx, cy)))

    # ---------- Rodapé ----------
    def _render_footer(self, screen, vx, vy, vw, vh, cx):
        instr = self.font_tiny.render(
            "Clique em um Pokémon para oferecer   |   DETALHES abre informações   |   ESC = voltar",
            True, COL_TEXT_MUTED,
        )
        screen.blit(instr, instr.get_rect(center=(cx, vy + vh - 18)))

    # ---------- Overlay de mensagem ----------
    def _render_overlay_message(self, screen, vx, vy, vw, vh,
                                title, color, subtitle):
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (vx, vy))

        cx, cy = vx + vw // 2, vy + vh // 2
        box_w = min(520, int(vw * 0.8))
        box_h = min(180, int(vh * 0.35))
        box = pygame.Rect(0, 0, box_w, box_h)
        box.center = (cx, cy)
        pygame.draw.rect(screen, COL_PANEL, box, border_radius=14)
        pygame.draw.rect(screen, color, box, 2, border_radius=14)

        t = self.font_title.render(title, True, color)
        screen.blit(t, t.get_rect(center=(box.centerx, box.y + box_h // 4)))

        s = self.font.render(subtitle, True, COL_TEXT_DIM)
        screen.blit(s, s.get_rect(center=(box.centerx, box.centery + 5)))

        hint = self.font_small.render(
            "Pressione ESC ou clique em Voltar para sair.",
            True, COL_TEXT_MUTED,
        )
        screen.blit(hint, hint.get_rect(center=(box.centerx, box.bottom - 30)))

    # ---------- Animação de troca ----------
    def _render_trade_animation(self, screen, vx, vy, vw, vh):
        t = min(1.0, self._anim_time / self._anim_duration)

        # Easing suave (smoothstep)
        et = t * t * (3 - 2 * t)

        my_rect = self._my_panel_rect
        opp_rect = self._opp_panel_rect

        my_start = (my_rect.centerx, my_rect.centery)
        my_end = (opp_rect.centerx, opp_rect.centery)
        opp_start = (opp_rect.centerx, opp_rect.centery)
        opp_end = (my_rect.centerx, my_rect.centery)

        # Arco (sobe no meio do caminho)
        arc = max(50, min(120, (my_rect.height + opp_rect.height) // 4))
        arc_off = math.sin(math.pi * t) * arc

        my_x = my_start[0] + (my_end[0] - my_start[0]) * et
        my_y = my_start[1] + (my_end[1] - my_start[1]) * et - arc_off

        opp_x = opp_start[0] + (opp_end[0] - opp_start[0]) * et
        opp_y = opp_start[1] + (opp_end[1] - opp_start[1]) * et - arc_off

        # Pulse de escala
        pulse = 1.0 + 0.18 * math.sin(math.pi * t)

        # Alpha fade no final
        alpha = 255
        if t > 0.85:
            alpha = int(255 * (1.0 - (t - 0.85) / 0.15))
        alpha = max(0, min(255, alpha))

        base_size = max(60, min(int(96 * getattr(self, "_ui_scale", 1.0)),
                                my_rect.height - 10))

        # Fundo escurecido para destacar
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(90 * min(1.0, t * 3))))
        screen.blit(overlay, (vx, vy))

        # Renderiza os dois portraits
        if self._anim_my_data:
            self._render_anim_portrait(
                screen, self._anim_my_data,
                my_x, my_y, base_size, pulse, alpha
            )
        if self._anim_opp_data:
            self._render_anim_portrait(
                screen, self._anim_opp_data,
                opp_x, opp_y, base_size, pulse, alpha
            )

        # Flash no cruzamento
        if 0.35 < t < 0.65:
            intensity = 1.0 - abs(t - 0.5) / 0.15
            flash_surf = pygame.Surface((vw, vh), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 220, int(110 * intensity)))
            screen.blit(flash_surf, (vx, vy))

        # Texto "Trocando..."
        if t < 0.85:
            label = self.font_h1.render("TROCANDO...", True, COL_ACCENT)
            cy = vy + int(vh * 0.12)
            screen.blit(label, label.get_rect(center=(vx + vw // 2, cy)))

    def _render_anim_portrait(self, screen, data, cx, cy, base_size, pulse, alpha):
        """Renderiza um portrait em movimento com glow."""
        if alpha <= 0:
            return

        size = int(base_size * pulse)
        center = (int(cx), int(cy))

        # Glow
        glow_r = size
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        base_color = COL_ACCENT if data.get("is_shiny") else COL_INFO
        for r in range(glow_r, 0, -4):
            a = int(90 * (alpha / 255.0) * (1.0 - r / glow_r))
            if a <= 0:
                continue
            pygame.draw.circle(glow_surf, (*base_color, a),
                               (glow_r, glow_r), r)
        screen.blit(glow_surf, (center[0] - glow_r, center[1] - glow_r))

        # Portrait
        portrait = self.pokedex.get_portrait(
            data.get("id", 0), "normal", data.get("is_shiny", False)
        )
        if portrait:
            portrait_scaled = pygame.transform.smoothscale(portrait, (size, size))
            if alpha < 255:
                portrait_scaled = portrait_scaled.copy()
                portrait_scaled.set_alpha(alpha)
            screen.blit(
                portrait_scaled,
                (center[0] - size // 2, center[1] - size // 2)
            )

    # ---------- Botão genérico ----------
    def _draw_button(self, screen, rect, text, kind="primary"):
        palette = {
            "primary":   (COL_BTN_PRIMARY,  COL_BTN_PRIMARY_H),
            "success":   (COL_BTN_SUCCESS,  COL_BTN_SUCCESS_H),
            "danger":    (COL_BTN_DANGER,   COL_BTN_DANGER_H),
            "info":      (COL_BTN_INFO,     COL_BTN_INFO_H),
            "disabled":  (COL_BTN_DISABLED, COL_BTN_DISABLED),
        }
        base, hover = palette.get(kind, palette["primary"])
        mouse = pygame.mouse.get_pos()
        is_hover = rect.collidepoint(mouse) and kind != "disabled"
        bg = hover if is_hover else base

        # Sombra leve
        shadow = pygame.Surface((rect.width + 4, rect.height + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow, COL_SHADOW,
                         pygame.Rect(2, 2, rect.width, rect.height),
                         border_radius=8)
        screen.blit(shadow, (rect.x - 2, rect.y - 2))

        pygame.draw.rect(screen, bg, rect, border_radius=8)
        border = COL_BORDER_HL if is_hover else COL_BORDER
        pygame.draw.rect(screen, border, rect, 1, border_radius=8)

        color = COL_TEXT if kind != "disabled" else COL_TEXT_MUTED
        surf = self.font_btn.render(text, True, color)
        screen.blit(surf, surf.get_rect(center=rect.center))

    # =========================================================
    # Helpers
    # =========================================================
    def _get_type_color(self, type_name):
        type_colors = {
            "normal":   (168, 168, 120),
            "fire":     (240, 128, 48),
            "water":    (104, 144, 240),
            "electric": (248, 208, 48),
            "grass":    (120, 200, 80),
            "ice":      (152, 216, 216),
            "fighting": (192, 48, 40),
            "poison":   (160, 64, 160),
            "ground":   (224, 192, 104),
            "flying":   (168, 144, 240),
            "psychic":  (248, 88, 136),
            "bug":      (168, 184, 32),
            "rock":     (184, 160, 56),
            "ghost":    (112, 88, 152),
            "dragon":   (112, 56, 248),
            "dark":     (112, 88, 72),
            "steel":    (184, 184, 208),
            "fairy":    (238, 153, 172),
        }
        return type_colors.get(type_name.lower(), (128, 128, 128))