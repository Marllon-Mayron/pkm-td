# src/scenes/pvp_scene/pvp_swap_overlay.py
"""
Overlay mostrado para o VENCEDOR de uma troca (quem ainda tem pokémon vivo).

Mostra:
  - Barra de tempo (5s)
  - "Deseja trocar?"
  - Cards dos pokémon disponíveis no HUD (para trocar)
  - Card do pokémon atualmente posicionado com legenda "Não trocar"

Se o jogador clicar em um card, o callback recebe o pokémon escolhido.
Se clicar em "Não trocar" ou o tempo esgotar, recebe None.
"""
import math
import pygame


class SwapSelectionOverlay:
    # Tempo total para decidir a troca
    SWAP_TIME = 10.0

    def __init__(self, scene, current_pokemon, available_pokemon,
                 on_choice, subtitle=None):
        self.scene = scene
        self.current_pokemon = current_pokemon
        self.available_pokemon = list(available_pokemon)
        self.on_choice = on_choice  # callback(pokemon_or_None)
        self.subtitle = subtitle or "Escolha um pokémon para trocar"

        self.active = True
        self.elapsed = 0.0
        self.alpha = 0

        self.card_rects = []   # lista de (rect, pokemon_or_None)
        self.no_swap_rect = None

        self.font_title = pygame.font.Font(None, 44)
        self.font_sub = pygame.font.Font(None, 26)
        self.font_card = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 18)
        self.font_timer = pygame.font.Font(None, 28)

        self.panel = pygame.Rect(0, 0, 100, 100)
        self.bar = pygame.Rect(0, 0, 100, 16)

        self._layout()

    # ------------------------------------------------------------------
    def _layout(self):
        sm = self.scene.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        # Último card = "Não trocar" (o pokémon atual)
        all_pokemon = self.available_pokemon + [None]
        n = max(1, len(all_pokemon))

        max_card_w = 140
        min_card_w = 96
        gap = 12
        max_total_w = min(vw - 120, 1100)
        card_w = min(max_card_w, (max_total_w - (n - 1) * gap) // n)
        card_w = max(min_card_w, card_w)
        card_h = 176

        total_w = n * card_w + (n - 1) * gap
        panel_w = max(total_w + 60, 560)
        panel_h = 340

        self.panel = pygame.Rect(0, 0, panel_w, panel_h)
        self.panel.center = (vx + vw // 2, vy + vh // 2)

        self.bar = pygame.Rect(
            self.panel.x + 30, self.panel.y + 22,
            self.panel.width - 60, 16,
        )

        cards_y = self.panel.y + 138
        start_x = self.panel.centerx - total_w // 2

        self.card_rects = []
        for i, pk in enumerate(all_pokemon):
            r = pygame.Rect(
                start_x + i * (card_w + gap),
                cards_y, card_w, card_h,
            )
            self.card_rects.append((r, pk))
            if pk is None:
                self.no_swap_rect = r

    # ------------------------------------------------------------------
    def handle_event(self, event):
        if not self.active:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, pk in self.card_rects:
                if r.collidepoint(event.pos):
                    self._choose(pk)
                    return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._choose(None)
            return True
        return False

    def _choose(self, pokemon):
        if not self.active:
            return
        self.active = False
        try:
            self.on_choice(pokemon)
        except Exception as e:
            print(f"[PVP_Swap] erro callback: {e}")

    # ------------------------------------------------------------------
    def update(self, dt):
        if not self.active:
            return
        self.elapsed += dt
        self.alpha = min(255, int((self.elapsed / 0.2) * 255))
        if self.elapsed >= self.SWAP_TIME:
            self._choose(None)

    # ------------------------------------------------------------------
    def render(self, screen):
        if not self.active:
            return
        sm = self.scene.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(185, self.alpha)))
        screen.blit(overlay, (vx, vy))

        # Painel
        pygame.draw.rect(screen, (24, 27, 44), self.panel, border_radius=18)
        pygame.draw.rect(screen, (200, 60, 60), self.panel, 2, border_radius=18)

        # Barra de tempo (verde → laranja → vermelho)
        remaining = max(0.0, self.SWAP_TIME - self.elapsed)
        frac = remaining / self.SWAP_TIME
        if frac > 0.5:
            bar_color = (105, 220, 130)
        elif frac > 0.25:
            bar_color = (255, 185, 100)
        else:
            bar_color = (230, 90, 90)

        pygame.draw.rect(screen, (40, 45, 60), self.bar, border_radius=8)
        fill_w = int(self.bar.width * frac)
        if fill_w > 0:
            fill = pygame.Rect(self.bar.x, self.bar.y, fill_w, self.bar.height)
            pygame.draw.rect(screen, bar_color, fill, border_radius=8)
        pygame.draw.rect(screen, (80, 85, 105), self.bar, 1, border_radius=8)

        secs = max(0, int(math.ceil(remaining)))
        t = self.font_timer.render(f"{secs}s", True, (255, 255, 255))
        screen.blit(t, t.get_rect(
            midright=(self.bar.right - 6, self.bar.centery)))

        # Título
        title = self.font_title.render("Deseja trocar?", True, (255, 215, 0))
        screen.blit(title, title.get_rect(
            center=(self.panel.centerx, self.panel.y + 74)))

        # Sub-título configurável
        sub = self.font_sub.render(self.subtitle, True, (235, 235, 245))
        screen.blit(sub, sub.get_rect(
            center=(self.panel.centerx, self.panel.y + 110)))

        # Cards
        mouse = pygame.mouse.get_pos()
        for r, pk in self.card_rects:
            hover = r.collidepoint(mouse)
            self._render_card(screen, r, pk, hover)

    # ------------------------------------------------------------------
    def _render_card(self, screen, rect, pokemon, hover):
        if pokemon is None:
            # Card "Não trocar" (usa o retrato do pokémon atual)
            bg = (70, 40, 45) if hover else (50, 30, 35)
            border = (230, 90, 90)
        else:
            bg = (50, 60, 80) if hover else (34, 40, 55)
            border = (110, 170, 255) if hover else (70, 90, 120)

        pygame.draw.rect(screen, bg, rect, border_radius=12)
        pygame.draw.rect(screen, border, rect, 2, border_radius=12)

        # Retrato
        psize = 96
        px = rect.centerx - psize // 2
        py = rect.y + 12

        target = pokemon if pokemon is not None else self.current_pokemon
        try:
            pokedex = getattr(self.scene, 'pokedex', None)
            if pokedex is None:
                from src.data.pokedex import Pokedex
                pokedex = Pokedex()
            portrait = pokedex.get_portrait(
                target.id, "normal",
                getattr(target, 'is_shiny', False))
            if portrait:
                portrait = pygame.transform.smoothscale(portrait, (psize, psize))
                screen.blit(portrait, (px, py))
        except Exception:
            pass

        frame = pygame.Rect(px, py, psize, psize)
        frame_color = ((255, 215, 0) if getattr(target, 'is_shiny', False)
                       else border)
        pygame.draw.rect(screen, frame_color, frame, 2, border_radius=8)

        # Nome / legenda
        if pokemon is None:
            label = "Não trocar"
            label_color = (255, 120, 120)
        else:
            label = pokemon.name
            label_color = ((255, 215, 0) if getattr(pokemon, 'is_shiny', False)
                           else (235, 235, 245))

        name_surf = self.font_card.render(label, True, label_color)
        if name_surf.get_width() > rect.width - 12:
            cut = label
            while len(cut) > 3 and name_surf.get_width() > rect.width - 12:
                cut = cut[:-1]
                name_surf = self.font_card.render(cut + "…", True, label_color)
        screen.blit(name_surf, name_surf.get_rect(
            center=(rect.centerx, rect.bottom - 38)))

        # Linha de baixo
        if pokemon is not None:
            lvl = self.font_small.render(
                f"Nv. {pokemon.level}", True, (170, 175, 200))
            screen.blit(lvl, lvl.get_rect(
                center=(rect.centerx, rect.bottom - 16)))
        else:
            sub = self.font_small.render(
                "Manter atual", True, (200, 120, 120))
            screen.blit(sub, sub.get_rect(
                center=(rect.centerx, rect.bottom - 16)))