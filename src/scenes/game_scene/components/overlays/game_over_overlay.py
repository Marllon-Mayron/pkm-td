# src/scenes/game_scene/components/overlays/game_over_overlay.py

import pygame
from .base_overlay import BaseOverlay


class GameOverOverlay(BaseOverlay):
    """Overlay de Game Over - suporta diferentes motivos"""

    def __init__(self, game_scene, reason="items_stolen"):
        super().__init__(game_scene)
        self.target_item_manager = game_scene.target_item_manager
        self.music_played = False
        self.reason = reason

        self.gold_lost = 0
        self._apply_gold_penalty()

        # Botões
        self.retry_button_rect = None       # REJOGAR FASE
        self.button_rect = None             # VOLTAR (team select)
        self.menu_button_rect = None        # SELECIONAR FASE (phase select)
        self.retry_button_hovered = False
        self.button_hovered = False
        self.menu_button_hovered = False

        # ===== NOVO: sub-overlay de confirmação de retry =====
        # Quando não for None, ele intercepta todos os eventos e é renderizado
        # por cima deste overlay, perguntando se o jogador quer manter os
        # pokémons nos spots onde estavam antes de rejogar.
        self.retry_confirm_overlay = None

    def _apply_gold_penalty(self):
        player = self.game_scene.player
        current_gold = player.money

        if current_gold > 0:
            self.gold_lost = max(1, int(current_gold * 0.1))
            player.money -= self.gold_lost
            print(f"[GAME_OVER] Perdeu {self.gold_lost} gold (10% de {current_gold})")
        else:
            self.gold_lost = 0
            print(f"[GAME_OVER] Sem gold para perder")

    def handle_event(self, event):
        # ===== NOVO: se o confirm está aberto, ele intercepta tudo =====
        # Enquanto o jogador não responder SIM/NÃO, nenhum outro botão
        # deste overlay responde.
        if self.retry_confirm_overlay is not None:
            self.retry_confirm_overlay.handle_event(event)
            return True

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._return_to_team_select()
            return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.retry_button_rect and self.retry_button_rect.collidepoint(event.pos):
                self._retry_phase()
                return True
            if self.button_rect and self.button_rect.collidepoint(event.pos):
                self._return_to_team_select()
                return True
            if self.menu_button_rect and self.menu_button_rect.collidepoint(event.pos):
                self._return_to_phase_select()
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.retry_button_rect:
                self.retry_button_hovered = self.retry_button_rect.collidepoint(event.pos)
            if self.button_rect:
                self.button_hovered = self.button_rect.collidepoint(event.pos)
            if self.menu_button_rect:
                self.menu_button_hovered = self.menu_button_rect.collidepoint(event.pos)

        return False

    def update(self, dt):
        if not self.music_played:
            self._play_defeat_music()
            self.music_played = True

        # ===== NOVO: atualiza o sub-overlay de confirmação (se aberto) =====
        if self.retry_confirm_overlay is not None:
            self.retry_confirm_overlay.update(dt)

    def _play_defeat_music(self):
        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.play_defeat_music()

    def _stop_music(self):
        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.stop_music(fade_ms=300)
        print(f"[MUSIC] Música de derrota parada")

    def render(self, screen):
        overlay, viewport = self.create_overlay_surface(200)
        screen.blit(overlay, (viewport.x, viewport.y))

        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 24)
        font_gold = pygame.font.Font(None, 28)

        center_x = viewport.x + viewport.width // 2
        center_y = viewport.y + viewport.height // 2

        y_offset = center_y - 100

        # ===== TÍTULO =====
        game_over_text = font_large.render("GAME OVER", True, (255, 0, 0))
        game_over_x = center_x - game_over_text.get_width() // 2
        screen.blit(game_over_text, (game_over_x, y_offset))
        y_offset += game_over_text.get_height() + 15

        # ===== MOTIVO =====
        if self.reason == "team_defeated":
            reason_text = font_medium.render(
                "Seu time inteiro foi derrotado!",
                True, (255, 100, 100)
            )
        else:
            reason_text = font_medium.render(
                f"{self.target_item_manager.items_stolen} itens foram levados!",
                True, (255, 100, 100)
            )
        reason_x = center_x - reason_text.get_width() // 2
        screen.blit(reason_text, (reason_x, y_offset))
        y_offset += reason_text.get_height() + 15

        # ===== GOLD PERDIDO =====
        if self.gold_lost > 0:
            gold_text = font_gold.render(
                f"Você perdeu {self.gold_lost} gold! (10%)",
                True, (255, 215, 0)
            )
        else:
            gold_text = font_gold.render(
                "Você não tinha gold para perder!",
                True, (200, 200, 200)
            )
        gold_x = center_x - gold_text.get_width() // 2
        screen.blit(gold_text, (gold_x, y_offset))
        y_offset += gold_text.get_height() + 30

        # ===== BOTÕES (3 botões) =====
        button_width = 180
        button_height = 50
        spacing = 20

        total_width = button_width * 3 + spacing * 2
        left_x = center_x - total_width // 2

        # Botão REJOGAR FASE (novo - destaque verde)
        self.retry_button_rect = self._draw_button(
            screen, left_x, y_offset, button_width, button_height,
            "REJOGAR FASE", font_small, self.retry_button_hovered,
            base_color=(40, 100, 50), hover_color=(60, 150, 70),
            border_color=(60, 140, 70), hover_border=(80, 200, 100)
        )

        # Botão TIME (existente)
        self.button_rect = self._draw_button(
            screen, left_x + button_width + spacing, y_offset, button_width, button_height,
            "TIME", font_medium, self.button_hovered,
            base_color=(120, 40, 40), hover_color=(180, 60, 60),
            border_color=(160, 60, 60), hover_border=(220, 80, 80)
        )

        # Botão SELECIONAR FASE (existente)
        self.menu_button_rect = self._draw_button(
            screen, left_x + (button_width + spacing) * 2, y_offset,
            button_width, button_height,
            "SELECIONAR FASE", font_small, self.menu_button_hovered,
            base_color=(40, 60, 120), hover_color=(60, 90, 180),
            border_color=(60, 90, 160), hover_border=(80, 120, 220)
        )

        y_offset = self.retry_button_rect.bottom + 20

        esc_text = font_small.render(
            "Pressione ESC para voltar à seleção de time",
            True, (150, 150, 150)
        )
        esc_x = center_x - esc_text.get_width() // 2
        screen.blit(esc_text, (esc_x, y_offset))

        # ===== NOVO: renderiza o confirm por cima de tudo =====
        if self.retry_confirm_overlay is not None:
            self.retry_confirm_overlay.render(screen)

    def _draw_button(self, screen, x, y, w, h, text, font, hovered,
                     base_color, hover_color, border_color, hover_border):
        """Desenha um botão genérico com hover"""
        rect = pygame.Rect(x, y, w, h)
        color = hover_color if hovered else base_color
        border = hover_border if hovered else border_color

        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 3, border_radius=8)

        text_surf = font.render(text, True, (255, 255, 255))
        screen.blit(
            text_surf,
            (rect.centerx - text_surf.get_width() // 2,
             rect.centery - text_surf.get_height() // 2)
        )
        return rect

    # ================================================================
    # RETRY (REJOGAR FASE)
    # ================================================================
    def _retry_phase(self):
        """
        Chamado quando o jogador clica em REJOGAR FASE.
        Antes de efetivamente reiniciar, abre um sub-overlay perguntando
        se o jogador deseja manter os pokémons nos spots onde estavam.
        """
        from .retry_confirm_overlay import RetryConfirmOverlay

        # Captura o snapshot AGORA (antes do cleanup), pois é o estado
        # que representa "onde os pokémons estavam" durante a fase perdida.
        snapshot = self._capture_placement_snapshot()

        def on_confirm(keep_placement):
            self._do_retry_phase(keep_placement, snapshot)

        self.retry_confirm_overlay = RetryConfirmOverlay(self.game_scene, on_confirm)
        print("[GAME_OVER] Overlay de confirmação de retry aberto.")

    def _capture_placement_snapshot(self):
        """
        Captura a posição atual de todos os Pokémon colocados no mapa.
        Retorna uma lista de dicts com o mínimo necessário para restaurar:
        identificação do pokémon (unique_id + fallback id/level) e o tile.
        """
        snapshot = []
        pm = getattr(self.game_scene, 'placement_manager', None)
        if not pm:
            return snapshot

        tile_size = getattr(pm, 'tile_size', 16)
        for pokemon in pm.placed_pokemon:
            if not getattr(pokemon, 'is_placed', False):
                continue

            tile_x = getattr(pokemon, 'placed_tile_x', None)
            tile_y = getattr(pokemon, 'placed_tile_y', None)
            if tile_x is None:
                tile_x = int(pokemon.x // tile_size)
            if tile_y is None:
                tile_y = int(pokemon.y // tile_size)

            snapshot.append({
                'unique_id': getattr(pokemon, 'unique_id', None),
                'pokemon_id': pokemon.id,
                'level': pokemon.level,
                'tile_x': tile_x,
                'tile_y': tile_y,
            })

        print(f"[GAME_OVER] Snapshot capturado: {len(snapshot)} pokémon(s) no mapa.")
        return snapshot

    def _do_retry_phase(self, keep_placement, snapshot):
        """
        Efetivamente reinicia a fase.
        - keep_placement=True: passa o snapshot para a nova cena restaurar.
        - keep_placement=False: comportamento antigo (fase totalmente limpa).
        """
        from src.scenes.game_scene.game_scene import GameScene

        print(f"[GAME_OVER] Reiniciando fase {self.game_scene.phase_id} "
              f"(keep_placement={keep_placement})...")

        self._stop_music()
        self.game_scene.cleanup()

        # Cria uma nova GameScene com a mesma fase
        new_game_scene = GameScene(
            self.game,
            self.game_scene.chapter_id,
            self.game_scene.phase_number,
            keep_placement=keep_placement,
            placement_snapshot=snapshot if keep_placement else None,
        )
        self.game.current_scene = new_game_scene

        print(f"[GAME_OVER] Fase {self.game_scene.phase_id} reiniciada!")

    def _return_to_team_select(self):
        """Volta para a tela de seleção de time"""
        from src.scenes.team_select_scene.team_select_scene import TeamSelectScene

        self._stop_music()
        self.game_scene.cleanup()

        team_select = TeamSelectScene(
            self.game,
            self.game_scene.phase_info.get("chapter", 1),
            self.game_scene.phase_number
        )
        team_select._needs_refresh = True
        self.game.current_scene = team_select

    def _return_to_phase_select(self):
        """Volta para a tela de seleção de fase (mesmo caminho do start_game do menu)"""
        from src.config.progress import progress_manager
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene

        self._stop_music()
        self.game_scene.cleanup()

        # Mesmo fluxo do MenuScene.start_game() quando o jogador já tem starter:
        progress_manager._load_settings_from_save()

        phase_select = PhaseSelectScene(self.game)
        phase_select._needs_refresh = True   # força refresh dos dados do time/box

        self.game.current_scene = phase_select

        print("[GAME_OVER] Voltando para PhaseSelectScene")