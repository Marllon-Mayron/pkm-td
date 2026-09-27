# src/scenes/minigames/desafios/snorlax_boss.py
"""
SnorlaxBoss — boss do minigame Desafios.

Padrão de moves:
  Headbutt -> Tackle -> Amnesia -> Headbutt -> REST (ciclo)

Quando usa Rest:
  - HP volta ao máximo.
  - Fica DORMINDO (_snorlax_sleeping = True).
  - NÃO acorda naturalmente: só quando o jogador usa a Poké Flute nele.

PIXEL-PERFECT:
  Usa `pygame.transform.scale` (nearest neighbor), nunca smoothscale.
  O sprite vem de `self.sprite` (atualizado pelo Animation a cada frame).

CACHE DE SPRITE (CORRIGIDO):
  A chave do cache agora inclui `id(sprite)` — sem isso, todas as frames
  que compartilham a mesma dimensão devolviam o Surface antigo (boss
  travado no primeiro frame cacheado).

DORMINDO (CORRIGIDO):
  A animação de sono é forçada ANTES do `super().update(dt)`, e qualquer
  ataque em andamento é cancelado. Antes, o ataque sobrescrevia o sono.
"""
import pygame

from src.scenes.raid_scene.raid_boss import RaidBoss


class SnorlaxBoss(RaidBoss):
    # ===== Tamanho do boss =====
    SIZE_MULTIPLIER = 3.0
    HP_MULTIPLIER = 14
    DEF_MULTIPLIER = 1.6
    ATTACK_RANGE = 900
    FIXED_HP = None

    # Ciclo de 4 ataques antes do Rest
    ATTACK_CYCLE_NAMES = ["headbutt", "tackle", "amnesia", "headbutt"]
    REST_NAME = "rest"
    ATTACKS_BEFORE_REST = 10
    # Cache pixel-perfect
    # Aumentado para caber várias animações × frames (com id(sprite) na chave)
    _PP_CACHE_MAX = 64

    def __init__(self, x, y, pokemon_id=143, level=47, shiny=False,
                 hp_multiplier=None, size_multiplier=None, attack_all=True):
        super().__init__(
            x=x, y=y, pokemon_id=pokemon_id, level=level,
            shiny=shiny,
            hp_multiplier=hp_multiplier or self.HP_MULTIPLIER,
            size_multiplier=size_multiplier or self.SIZE_MULTIPLIER,
            attack_all=attack_all,
        )

        self._is_snorlax_boss = True
        self._snorlax_sleeping = False
        self._snorlax_attack_counter = 0

        # Cache: (id_sprite, w, h) -> Surface já escalada
        self._pp_cache = {}

        # Força moveset
        self._force_snorlax_moveset()

        print(f"[SNORLAX_BOSS] {self.name} Lv.{self.level} | HP: {self.max_hp} | "
              f"moves: {[m.name for m in self.moves]} | "
              f"size={self._raid_size_multiplier}x")

    # ------------------------------------------------------------------
    def _force_snorlax_moveset(self):
        """Garante Rest + Headbutt + Tackle + Amnesia."""
        from src.entities.move import Move
        from src.data.move_data import MoveData
        md = MoveData()

        desired = ["rest", "headbutt", "tackle", "amnesia"]
        new_moves = []
        for name in desired:
            info = md.get_move_info(name)
            if not info:
                info = {
                    "type": "normal", "power": 40, "accuracy": 100,
                    "pp": 20, "category": "physical",
                    "description": f"Usa {name}.",
                }
                print(f"[SNORLAX_BOSS] Move '{name}' não achado — fallback.")
            new_moves.append(Move(name, info))

        self.moves = new_moves
        self.current_move_index = 0
        for m in self.moves:
            m.current_pp = m.max_pp

    # ------------------------------------------------------------------
    def restore_all_pp(self):
        for m in self.moves:
            m.current_pp = m.max_pp

    # ------------------------------------------------------------------
    def get_next_attack_move(self):
        if self._snorlax_attack_counter >= self.ATTACKS_BEFORE_REST:
            self._snorlax_attack_counter = 0
            return self._get_move_by_name(self.REST_NAME)

        # Alterna entre os 4 ataques do ciclo
        idx = self._snorlax_attack_counter % len(self.ATTACK_CYCLE_NAMES)
        name = self.ATTACK_CYCLE_NAMES[idx]
        self._snorlax_attack_counter += 1
        return self._get_move_by_name(name) or self.moves[0]

    def _get_move_by_name(self, name):
        for m in self.moves:
            if m.name.lower() == name.lower():
                return m
        return None

    # ------------------------------------------------------------------
    def enter_sleep_state(self):
        """Chamado quando Rest é usado — boss fica dormindo."""
        self._snorlax_sleeping = True
        self.current_hp = self.max_hp
        self.is_defeated = False

        # ===== CANCELA QUALQUER ATAQUE EM ANDAMENTO =====
        self._cancel_attack_animation()

        # Força sono
        try:
            if self.has_animation("sleep"):
                self.set_animation_direct("sleep")
        except Exception as e:
            print(f"[SNORLAX_BOSS] Erro ao setar animação de sono: {e}")

        print(f"[SNORLAX_BOSS] {self.name} DORMINDO! Use a Poké Flute!")

    def wake_up_from_flute(self):
        if not self._snorlax_sleeping:
            return False
        self._snorlax_sleeping = False
        self._snorlax_attack_counter = 0

        # Cancela animação de sono/ataque antes de voltar pro idle
        self._cancel_attack_animation()

        try:
            if self.has_animation("idle"):
                self.set_animation_direct("idle")
        except Exception as e:
            print(f"[SNORLAX_BOSS] Erro ao setar idle: {e}")

        print(f"[SNORLAX_BOSS] {self.name} ACORDOU!")
        return True

    def _cancel_attack_animation(self):
        """Remove flags de ataque pra evitar que a animação fique travada."""
        for attr in ("_attack_animation_active",
                     "_attack_animation_timer",
                     "_damage_applied",
                     "_damage_frame_percent",
                     "_pending_attack_move",
                     "_pending_attack_target",
                     "_saved_animation_before_attack"):
            if hasattr(self, attr):
                try:
                    delattr(self, attr)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    def update(self, dt, player=None, enemies=None, items=None):
        """
        Ordem CORRIGIDA:
          1) Se dormindo: força animação de sono + cancela ataque
          2) Chama super().update (roda animation.update)
        Assim a animação de sono nunca é sobrescrita pelo ataque.
        """
        # ===== ANTES DO UPDATE: estado dormindo tem prioridade =====
        if self._snorlax_sleeping:
            self.current_hp = self.max_hp
            self._cancel_attack_animation()

            if getattr(self, 'current_animation', None) != "sleep":
                try:
                    if self.has_animation("sleep"):
                        self.set_animation_direct("sleep")
                except Exception:
                    pass

        super().update(dt, player=player, enemies=enemies, items=items)

    # ==================================================================
    # PIXEL-PERFECT + CACHE CORRIGIDO
    # ==================================================================
    def _prepare_sprite(self, zoom_scale):
        """
        Escala o sprite atual (self.sprite) por nearest neighbor.

        CACHE (CORRIGIDO): a chave inclui `id(sprite)` porque diferentes
        frames da mesma animação têm a MESMA dimensão — sem isso, o cache
        devolvia sempre o primeiro frame cacheado (boss travado).
        """
        sprite = getattr(self, 'sprite', None)
        if sprite is None:
            return None

        # ===== Escala final =====
        effect_scale = float(getattr(self, '_current_sprite_scale', 1.0))
        total = (float(zoom_scale)
                 * float(self._raid_size_multiplier)
                 * effect_scale)
        if total < 1.0:
            total = 1.0

        w = max(1, int(sprite.get_width() * total))
        h = max(1, int(sprite.get_height() * total))

        # ===== Chave inclui id(sprite) para invalidar quando o frame muda =====
        key = (id(sprite), w, h)
        cached = self._pp_cache.get(key)
        if cached is not None:
            return cached

        # ===== Nearest neighbor (pixel art nítida) =====
        scaled = pygame.transform.scale(sprite, (w, h))

        # ===== Guarda no cache (limita tamanho) =====
        if len(self._pp_cache) >= self._PP_CACHE_MAX:
            try:
                self._pp_cache.pop(next(iter(self._pp_cache)))
            except Exception:
                self._pp_cache.clear()
        self._pp_cache[key] = scaled

        return scaled

    # ------------------------------------------------------------------
    def _render_placeholder(self, screen, screen_x, screen_y, zoom_scale):
        """Placeholder pixel-perfect (sem interpolação)."""
        total = max(1.0, float(zoom_scale) * float(self._raid_size_multiplier))
        size = int(self.map_sprite_size * total)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(screen_x), int(screen_y))
        pygame.draw.rect(screen, (200, 50, 50), rect, border_radius=12)
        pygame.draw.rect(screen, (255, 200, 0), rect, 4, border_radius=12)
        return rect