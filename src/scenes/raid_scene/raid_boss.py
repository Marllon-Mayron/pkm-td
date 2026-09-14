# src/scenes/raid_scene/raid_boss.py
"""
Boss de raid: HP massivo, ataque em área, PP infinito.
Sem aumento de sprite (tamanho natural).
"""
import pygame
from src.entities.pokemon import Pokemon


class RaidBoss(Pokemon):
    SIZE_MULTIPLIER = 1.0   # ⚠️ NÃO aumentar o sprite
    HP_MULTIPLIER = 12
    DEF_MULTIPLIER = 1.5
    ATTACK_RANGE = 900

    def __init__(self, x, y, pokemon_id, level=100, shiny=False,
                 hp_multiplier=None, size_multiplier=None, attack_all=True):
        super().__init__(x, y, pokemon_id, level=level,
                         is_wild=True, shiny=shiny, is_boss=True)

        self._is_raid_boss = True
        self._attack_all = attack_all
        self._raid_size_multiplier = size_multiplier if size_multiplier is not None else self.SIZE_MULTIPLIER

        # ⚠️ NÃO MEXER EM _current_sprite_scale — o rendering base já usa isso.
        # Se mexermos aqui E no _prepare_sprite, o sprite fica 2x escalado (4x total).
        # Deixamos apenas _raid_size_multiplier e aplicamos no _prepare_sprite.
        self._sprite_scaled = None
        # map_sprite_size afeta hit-box/posição — deixa em 1x se multiplier=1
        if self._raid_size_multiplier != 1.0:
            self.map_sprite_size = int(self.map_sprite_size * self._raid_size_multiplier)

        # HP
        multiplier = hp_multiplier or self.HP_MULTIPLIER
        self.max_hp = int(self.max_hp * multiplier)
        self.current_hp = self.max_hp

        # DEF
        self.defense = int(self.defense * self.DEF_MULTIPLIER)
        self.sp_defense = int(self.sp_defense * self.DEF_MULTIPLIER)
        self.defense_value = self._calculate_defense()

        # Parado
        self.path = []
        self.path_index = 0
        self.move_speed = 0.0
        self.is_stationary = True
        self.original_spot_x = x
        self.original_spot_y = y

        # Range global
        self.attack_range = self.ATTACK_RANGE

        from src.battle.attack_pattern import AttackPattern
        self.attack_pattern = AttackPattern.RANDOM

        print(f"[RAID_BOSS] {self.name} Lv.{self.level} | HP: {self.max_hp} | "
              f"Size: {self._raid_size_multiplier}x")

    def restore_all_pp(self):
        for move in self.moves:
            move.current_pp = move.max_pp

    def _prepare_sprite(self, zoom_scale):
        base = super()._prepare_sprite(zoom_scale)
        if base is None:
            return None
        if self._raid_size_multiplier == 1.0:
            return base
        w, h = base.get_size()
        return pygame.transform.smoothscale(
            base,
            (max(1, int(w * self._raid_size_multiplier)),
             max(1, int(h * self._raid_size_multiplier)))
        )

    def _render_placeholder(self, screen, screen_x, screen_y, zoom_scale):
        size = int(self.map_sprite_size * max(1.0, zoom_scale))
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(screen_x), int(screen_y))
        pygame.draw.rect(screen, (200, 50, 50), rect, border_radius=12)
        pygame.draw.rect(screen, (255, 200, 0), rect, 4, border_radius=12)
        return rect

    def _render_hp_bar(self, screen, sprite_rect, zoom_scale):
        if not sprite_rect or not getattr(self, 'screen_manager', None):
            if sprite_rect:
                super()._render_hp_bar(screen, sprite_rect, zoom_scale)
            return

        hp_percent = self.current_hp / self.max_hp if self.max_hp > 0 else 0
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width

        bar_w = int(vw * 0.7)
        bar_h = 24
        bar_x = vx + (vw - bar_w) // 2
        bar_y = vy + 60

        pygame.draw.rect(screen, (20, 10, 10),
                         (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), border_radius=6)
        pygame.draw.rect(screen, (60, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        fill_w = int(bar_w * hp_percent)
        color = (220, 40, 40) if hp_percent > 0.25 else (255, 100, 0)
        if fill_w > 0:
            pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h), border_radius=4)
        pygame.draw.rect(screen, (255, 215, 0), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=4)

        font = pygame.font.Font(None, 26)
        txt = font.render(
            f"{self.name} Lv.{self.level}  -  {self.current_hp}/{self.max_hp}",
            True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=(bar_x + bar_w // 2, bar_y + bar_h // 2)))