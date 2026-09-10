# src/scenes/multiplayer_menu_scene/multiplayer_menu_scene.py

import pygame
import socket
import tkinter as tk

from src.scenes.base_scene import BaseScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.network.manager import NetworkManager
from src.network.firewall_utils import request_firewall_permission
from src.ui.toast_renderer import toast_info, toast_warning


# =========================================================
# Paleta
# =========================================================
COL_BG            = (16, 18, 30)
COL_CARD          = (26, 29, 48)
COL_CARD_DARK     = (20, 22, 38)
COL_BORDER        = (55, 58, 82)
COL_BORDER_HOVER  = (110, 115, 150)
COL_DIVIDER       = (45, 48, 70)

COL_ACCENT        = (255, 215, 0)
COL_ACCENT_DIM    = (150, 128, 20)

COL_TEXT          = (235, 235, 245)
COL_TEXT_DIM      = (170, 175, 200)
COL_TEXT_MUTED    = (95, 100, 130)

COL_SUCCESS       = (105, 220, 130)
COL_WARN          = (255, 185, 100)
COL_DANGER        = (230, 90, 90)

COL_BTN_PRIMARY     = (52, 100, 180)
COL_BTN_PRIMARY_H   = (76, 142, 232)
COL_BTN_SECONDARY   = (54, 60, 88)
COL_BTN_SECONDARY_H = (80, 88, 122)
COL_BTN_SUCCESS     = (44, 128, 74)
COL_BTN_SUCCESS_H   = (70, 178, 104)
COL_BTN_DANGER      = (128, 48, 54)
COL_BTN_DANGER_H    = (180, 70, 76)
COL_BTN_DISABLED    = (40, 43, 58)


# =========================================================
# TextInput
# =========================================================
class TextInput:
    """Campo de texto com cursor, placeholder, foco e hover."""

    def __init__(self, font, placeholder="", max_length=32):
        self.font = font
        self.placeholder = placeholder
        self.max_length = max_length
        self.rect = pygame.Rect(0, 0, 100, 44)
        self.text = ""
        self.active = False
        self.enabled = True

        self._hover = False
        self._cursor_t = 0.0
        self._cursor_on = False

    # -------- API --------
    @property
    def value(self):
        return self.text

    def set_value(self, value):
        self.text = (value or "")[: self.max_length]

    def clear(self):
        self.text = ""

    # -------- Eventos --------
    def handle_event(self, event):
        """
        Retorna:
          None      -> nada relevante
          True      -> conteúdo/estado mudou (precisa redesenhar)
          'submit'  -> ENTER pressionado
          'escape'  -> ESC pressionado
          'paste'   -> Ctrl+V pressionado (quem chama decide o que colar)
        """
        if not self.enabled:
            return None

        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if not self.active:
                    self.active = True
                    self._cursor_t = 0.0
                    self._cursor_on = True
                    return True
                return None
            if self.active:
                self.active = False
                return True
            return None

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return "submit"
            if event.key == pygame.K_ESCAPE:
                self.active = False
                return "escape"
            if event.key == pygame.K_BACKSPACE:
                if self.text:
                    self.text = self.text[:-1]
                    return True
                return None
            if event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                return "paste"
            if event.unicode and event.unicode.isprintable() and len(self.text) < self.max_length:
                self.text += event.unicode
                return True
        return None

    def update(self, dt):
        if self.active:
            self._cursor_t += dt
            if self._cursor_t >= 0.5:
                self._cursor_t = 0.0
                self._cursor_on = not self._cursor_on
        else:
            self._cursor_on = False

    def render(self, screen):
        if not self.enabled:
            bg, border = COL_CARD_DARK, COL_BORDER
        elif self.active:
            bg, border = (30, 34, 58), COL_ACCENT
        elif self._hover:
            bg, border = (28, 32, 52), COL_BORDER_HOVER
        else:
            bg, border = COL_CARD_DARK, COL_BORDER

        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=8)

        # Texto
        if self.text:
            surf = self.font.render(self.text, True, COL_TEXT)
        else:
            surf = self.font.render(self.placeholder, True, COL_TEXT_MUTED)

        tx = self.rect.x + 14
        ty = self.rect.centery - surf.get_height() // 2
        screen.blit(surf, (tx, ty))

        # Cursor
        if self.active and self._cursor_on:
            if self.text:
                w = self.font.size(self.text)[0]
                cx = tx + w + 1
            else:
                cx = tx + 1
            pygame.draw.line(
                screen, COL_ACCENT,
                (cx, self.rect.centery - 10),
                (cx, self.rect.centery + 10),
                2,
            )


# =========================================================
# Scene
# =========================================================
class MultiplayerMenuScene(BaseScene):
    """Menu de multiplayer: configurar nome, criar sala ou entrar em uma."""

    MODE_IDLE = "idle"
    MODE_JOIN = "join"

    def __init__(self, game):
        super().__init__(game)
        self.network = NetworkManager()

        # ------ Estado ------
        self.player_name = "Jogador"
        self.host_ip = self._get_local_ip()
        self.port = 12345
        self.mode = self.MODE_IDLE
        self.connecting = False

        self.status_message = ""
        self.status_color = COL_TEXT_DIM
        self.status_timer = 0.0

        # ------ Fontes ------
        self.font_title     = pygame.font.Font(None, 54)
        self.font_subtitle  = pygame.font.Font(None, 22)
        self.font_section   = pygame.font.Font(None, 20)
        self.font_label     = pygame.font.Font(None, 20)
        self.font_input     = pygame.font.Font(None, 26)
        self.font_btn       = pygame.font.Font(None, 26)
        self.font_btn_small = pygame.font.Font(None, 22)
        self.font_mono      = pygame.font.Font(None, 24)
        self.font_hint      = pygame.font.Font(None, 18)

        # ------ Widgets ------
        self.name_input = TextInput(
            self.font_input, placeholder="Digite seu nome...", max_length=20
        )
        self.name_input.set_value(self.player_name)

        self.ip_input = TextInput(
            self.font_input, placeholder="Ex.: 192.168.0.10", max_length=24
        )

        # ------ Retângulos ------
        self.back_btn      = pygame.Rect(0, 0, 110, 38)
        self.create_btn    = pygame.Rect(0, 0, 220, 52)
        self.join_btn      = pygame.Rect(0, 0, 220, 52)
        self.connect_btn   = pygame.Rect(0, 0, 140, 46)
        self.copy_btn      = pygame.Rect(0, 0, 140, 38)
        self.card_rect     = pygame.Rect(0, 0, 100, 100)

        # ------ Clipboard ------
        self._init_clipboard()

        # ------ Aplica nome inicial ------
        self.network.set_name(self.player_name)

        # ------ Layout inicial ------
        self._layout()

        # ------ Foco inicial ------
        self.name_input.active = True

        self._set_status("Defina seu nome para comecar.", COL_WARN)

    # =====================================================
    # Inicialização
    # =====================================================
    def _init_clipboard(self):
        try:
            self._root = tk.Tk()
            self._root.withdraw()
            self._clipboard_available = True
        except Exception:
            self._clipboard_available = False

    def _copy_to_clipboard(self, text):
        if not self._clipboard_available:
            return False
        try:
            self._root.clipboard_clear()
            self._root.clipboard_append(text)
            self._root.update()
            return True
        except Exception:
            return False

    def _paste_from_clipboard(self):
        if not self._clipboard_available:
            return ""
        try:
            return self._root.clipboard_get()
        except Exception:
            return ""

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # =====================================================
    # Status
    # =====================================================
    def _set_status(self, text, color=COL_TEXT_DIM, duration=3.0):
        self.status_message = text
        self.status_color = color
        self.status_timer = duration

    # =====================================================
    # Layout
    # =====================================================
    def _layout(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        cx = vx + vw // 2

        # Botão voltar
        self.back_btn.topleft = (vx + 20, vy + 20)

        # ----- Dimensões do card -----
        card_w = min(560, vw - 60)
        pad = 32
        left_x = cx - card_w // 2 + pad
        inner_w = card_w - pad * 2

        # Começo do card (abaixo do título)
        card_top = vy + 150

        # Cursor vertical dentro do card
        y = card_top + pad

        # ---- Seção: Identificação ----
        y += 22                                        # label da seção
        y += 20                                        # "Seu nome"
        self.name_input.rect = pygame.Rect(left_x, y, inner_w, 46)
        y += 46
        y += 30                                        # espaço

        # ---- Seção: Sala ----
        y += 22                                        # label da seção
        gap = 14
        half = (inner_w - gap) // 2
        self.create_btn = pygame.Rect(left_x, y, half, 52)
        self.join_btn   = pygame.Rect(left_x + half + gap, y, half, 52)
        y += 52
        y += 30

        # ---- Seção condicional ----
        if self.mode == self.MODE_JOIN:
            y += 20                                     # "Endereco do host"
            btn_w = 140
            gap2 = 12
            self.ip_input.rect = pygame.Rect(
                left_x, y, inner_w - btn_w - gap2, 46
            )
            self.connect_btn = pygame.Rect(
                self.ip_input.rect.right + gap2, y, btn_w, 46
            )
            y += 46
            y += 26
        else:
            # Modo idle: pula essa seção
            y += 6

        # ---- Divisor + endereço local ----
        self._divider_y = y
        y += 22                                         # divisor + espaço
        y += 18                                         # "Seu endereco na rede:"
        ip_row_h = 38
        self.copy_btn = pygame.Rect(
            left_x + inner_w - 140, y, 140, ip_row_h
        )
        self._local_ip_y = y + ip_row_h // 2
        y += ip_row_h
        y += 8

        # ---- Altura final do card ----
        card_h = (y - card_top) + pad
        self.card_rect = pygame.Rect(cx - card_w // 2, card_top, card_w, card_h)

    # =====================================================
    # Ações
    # =====================================================
    def _apply_name(self):
        name = self.name_input.value.strip()
        if not name:
            name = "Jogador"
        self.player_name = name[:20]
        self.network.set_name(self.player_name)

        # ===== UUID DO JOGADOR (persistente) =====
        player_uuid = getattr(self.game.player, 'uuid', None) or "unknown"
        self.network.set_uuid(player_uuid)

    def _create_room(self):
        if not self.name_input.value.strip():
            self._set_status("Digite um nome antes de criar a sala.", COL_WARN)
            self.name_input.active = True
            return

        self._apply_name()
        self._set_status("Criando sala...", COL_ACCENT)
        self.connecting = True

        request_firewall_permission(self.port, "Pokemon TD Multiplayer")
        if self.network.start_host(self.port):
            toast_info(f"Sala criada! IP: {self.host_ip}:{self.port}")
            self._set_status(
                f"Sala criada em {self.host_ip}:{self.port}", COL_SUCCESS
            )
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(
                self.game, is_host=True, network=self.network
            )
        else:
            self._set_status("Falha ao criar sala.", COL_DANGER)
            toast_warning("Falha ao criar sala. Verifique a porta.")
            self.connecting = False

    def _try_join(self):
        if not self.name_input.value.strip():
            self._set_status("Digite um nome antes de conectar.", COL_WARN)
            self.name_input.active = True
            return

        if not self.ip_input.value.strip():
            self._set_status("Digite o endereco IP do host.", COL_WARN)
            self.ip_input.active = True
            return

        self._apply_name()

        clean_ip = self.ip_input.value.strip()
        if ":" in clean_ip:
            clean_ip = clean_ip.split(":")[0]
            self.ip_input.set_value(clean_ip)
            toast_info(f"IP ajustado para: {clean_ip}")

        self._set_status(f"Conectando a {clean_ip}...", COL_ACCENT)
        self.connecting = True

        if self.network.connect_to_host(clean_ip, self.port):
            toast_info(f"Conectado ao servidor {clean_ip}:{self.port}")
            self._set_status(f"Conectado a {clean_ip}.", COL_SUCCESS)
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(
                self.game, is_host=False, network=self.network
            )
        else:
            # ★ Mostra o motivo real da recusa (mesmo IP, duplicado, etc.)
            reason = self.network.get_last_rejection_reason()
            if reason:
                self._set_status(reason, COL_DANGER, duration=6.0)
                toast_warning(reason)
            else:
                self._set_status("Nao foi possivel conectar.", COL_DANGER)
                toast_warning("Verifique o IP e se o host esta com a sala aberta.")
            self.connecting = False

    def _copy_ip(self):
        address = f"{self.host_ip}:{self.port}"
        if self._copy_to_clipboard(address):
            self._set_status("Endereco copiado.", COL_SUCCESS)
            toast_info(f"{address} copiado para a area de transferencia.")
        else:
            self._set_status("Nao foi possivel copiar o endereco.", COL_WARN)

    def _return_to_menu(self):
        self.network.stop()
        self.game.current_scene = self.game.menu_scene

    # =====================================================
    # Eventos
    # =====================================================
    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._layout()
            return

        # ---- TextInputs primeiro ----
        for inp in (self.name_input, self.ip_input):
            if not inp.enabled:
                continue
            result = inp.handle_event(event)
            if result is None:
                continue

            # Input tratou o evento
            if inp is self.name_input:
                self._apply_name()
            if result == "paste":
                pasted = self._paste_from_clipboard().strip()
                if pasted:
                    inp.set_value(inp.value + pasted)
                    if inp is self.name_input:
                        self._apply_name()
                    if inp is self.ip_input and ":" in pasted:
                        inp.set_value(pasted.split(":")[0])
                    toast_info("Texto colado.")
            if result == "submit":
                if inp is self.name_input:
                    self._apply_name()
                    self.name_input.active = False
                    self._set_status(
                        f"Ola, {self.player_name}. Escolha uma opcao.", COL_SUCCESS
                    )
                elif inp is self.ip_input:
                    self._try_join()
            if result == "escape":
                self._return_to_menu()
                return
            if result is True:
                # Conteúdo mudou: não deixa o clique "vazar" para botões
                if event.type == pygame.MOUSEBUTTONDOWN:
                    return
            break
        else:
            pass  # nenhum input tratou

        # ---- Atalhos de teclado ----
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()
                return
            if event.key == pygame.K_c and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self._copy_ip()
                return

        # ---- Mouse ----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            if self.back_btn.collidepoint(pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._return_to_menu()
                return

            if self.create_btn.collidepoint(pos) and not self.connecting:
                sound_manager.play_effect(SoundEffect.CLICK)
                self._create_room()
                return

            if self.join_btn.collidepoint(pos) and not self.connecting:
                sound_manager.play_effect(SoundEffect.CLICK)
                if self.mode != self.MODE_JOIN:
                    self.mode = self.MODE_JOIN
                    self._layout()
                    self._set_status("Digite o IP do host e clique em Conectar.", COL_ACCENT)
                    self.ip_input.active = True
                else:
                    self._try_join()
                return

            if self.mode == self.MODE_JOIN and self.connect_btn.collidepoint(pos):
                if not self.connecting:
                    self._try_join()
                return

            if self.copy_btn.collidepoint(pos):
                self._copy_ip()
                return

    # =====================================================
    # Update
    # =====================================================
    def fixed_update(self, dt):
        if self.status_timer > 0:
            self.status_timer -= dt

        self.name_input.update(dt)
        self.ip_input.update(dt)

    # =====================================================
    # Render
    # =====================================================
    def render(self, screen):
        screen.fill(COL_BG)

        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        cx = vx + vw // 2

        self._layout()

        # ---- Cabeçalho ----
        self._draw_button(screen, self.back_btn, "Voltar", kind="danger")

        title = self.font_title.render("MULTIPLAYER", True, COL_ACCENT)
        screen.blit(title, title.get_rect(center=(cx, vy + 60)))

        subtitle = self.font_subtitle.render(
            "Jogue com um amigo pela rede local", True, COL_TEXT_MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(cx, vy + 95)))

        # Linha decorativa
        line_w = min(420, vw - 80)
        line_y = vy + 120
        pygame.draw.line(
            screen, COL_DIVIDER,
            (cx - line_w // 2, line_y),
            (cx + line_w // 2, line_y),
            1,
        )

        # ---- Card ----
        pygame.draw.rect(screen, COL_CARD, self.card_rect, border_radius=14)
        pygame.draw.rect(screen, COL_BORDER, self.card_rect, 1, border_radius=14)

        card = self.card_rect
        pad = 32
        left_x = card.x + pad
        inner_w = card.width - pad * 2

        # ============================
        # Seção: Identificação
        # ============================
        y = card.y + pad
        self._draw_section_label(screen, "IDENTIFICACAO", left_x, y)
        y += 22

        label = self.font_label.render("Seu nome", True, COL_TEXT_DIM)
        screen.blit(label, (left_x, y))
        y += 20
        # (o rect do name_input já está posicionado pelo _layout)

        self.name_input.render(screen)

        # Hint abaixo do nome
        hint = self.font_hint.render(
            "ENTER para confirmar. Voce sera identificado por este nome.",
            True, COL_TEXT_MUTED,
        )
        screen.blit(
            hint,
            (left_x, self.name_input.rect.bottom + 6),
        )

        # ============================
        # Seção: Sala
        # ============================
        y = self.create_btn.y - 26
        self._draw_section_label(screen, "SALA", left_x, y)

        can_click = not self.connecting
        self._draw_button(
            screen, self.create_btn, "Criar Sala",
            kind="success" if can_click else "disabled",
        )
        self._draw_button(
            screen, self.join_btn,
            "Entrar em Sala" if self.mode == self.MODE_IDLE else "Conectar",
            kind="primary" if can_click else "disabled",
        )

        # ============================
        # Seção: Endereço do host (modo join)
        # ============================
        if self.mode == self.MODE_JOIN:
            label_y = self.ip_input.rect.y - 22
            label = self.font_label.render(
                "Endereco do host", True, COL_TEXT_DIM
            )
            screen.blit(label, (left_x, label_y))

            self.ip_input.render(screen)
            self._draw_button(
                screen, self.connect_btn, "Conectar",
                kind="primary" if can_click else "disabled",
            )

        # ============================
        # Divisor + endereço local
        # ============================
        pygame.draw.line(
            screen, COL_DIVIDER,
            (left_x, self._divider_y),
            (left_x + inner_w, self._divider_y),
            1,
        )

        label = self.font_label.render(
            "Seu endereco na rede (compartilhe com o amigo):",
            True, COL_TEXT_DIM,
        )
        screen.blit(label, (left_x, self._divider_y + 12))

        address = f"{self.host_ip}:{self.port}"
        addr_txt = self.font_mono.render(address, True, COL_ACCENT)
        addr_rect = addr_txt.get_rect(midleft=(left_x, self._local_ip_y))
        screen.blit(addr_txt, addr_rect)

        self._draw_button(screen, self.copy_btn, "Copiar", kind="secondary")

        # ============================
        # Status
        # ============================
        if self.status_timer > 0 and self.status_message:
            txt = self.font_subtitle.render(
                self.status_message, True, self.status_color
            )
            screen.blit(txt, txt.get_rect(center=(cx, card.bottom + 32)))

        # ============================
        # Rodapé
        # ============================
        instr = self.font_hint.render(
            "ESC = voltar    |    Ctrl+C = copiar endereco    |    Ctrl+V = colar",
            True, COL_TEXT_MUTED,
        )
        screen.blit(
            instr,
            instr.get_rect(center=(cx, vy + vh - 20)),
        )

    # =====================================================
    # Helpers de desenho
    # =====================================================
    def _draw_section_label(self, screen, text, x, y):
        surf = self.font_section.render(text, True, COL_TEXT_MUTED)
        screen.blit(surf, (x, y))
        # pequeno traço à esquerda
        pygame.draw.line(
            screen, COL_ACCENT_DIM,
            (x - 12, y + surf.get_height() // 2),
            (x - 4, y + surf.get_height() // 2),
            2,
        )

    def _draw_button(self, screen, rect, text, kind="primary"):
        palette = {
            "primary":   (COL_BTN_PRIMARY,   COL_BTN_PRIMARY_H),
            "secondary": (COL_BTN_SECONDARY, COL_BTN_SECONDARY_H),
            "success":   (COL_BTN_SUCCESS,   COL_BTN_SUCCESS_H),
            "danger":    (COL_BTN_DANGER,    COL_BTN_DANGER_H),
            "disabled":  (COL_BTN_DISABLED,  COL_BTN_DISABLED),
        }
        base, hover = palette.get(kind, palette["primary"])

        mouse = pygame.mouse.get_pos()
        is_hover = rect.collidepoint(mouse) and kind != "disabled"
        bg = hover if is_hover else base

        pygame.draw.rect(screen, bg, rect, border_radius=10)

        border = COL_BORDER_HOVER if is_hover else COL_BORDER
        pygame.draw.rect(screen, border, rect, 1, border_radius=10)

        color = COL_TEXT if kind != "disabled" else COL_TEXT_MUTED
        font = self.font_btn if len(text) < 14 else self.font_btn_small
        surf = font.render(text, True, color)
        screen.blit(surf, surf.get_rect(center=rect.center))

    # =====================================================
    # Ciclo de vida
    # =====================================================
    def on_enter(self):
        pass

    def on_exit(self):
        pass