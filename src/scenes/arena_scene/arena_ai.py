# src/scenes/arena_scene/arena_ai.py
"""
IA dos treinadores NPC na arena.

Responsabilidades:
  - Decidir QUANDO o NPC usa itens (poção / cura de status).
  - Aplicar o efeito no pokémon inimigo (HP / remoção de status).
  - Emitir TOASTS usando o sistema de notificação do jogo
    (toast_battle), pra avisar o jogador do que aconteceu.

A dificuldade (definida pelo jogador na TrainerSelectScene) controla:
  - Frequência do uso de item (ITEM_COOLDOWN)
  - Threshold de HP pra usar poção (HEAL_THRESHOLD)

A IA NÃO posiciona pokémons — isso é responsabilidade da ArenaBattleScene
(posicionamento incremental 1:1 com o jogador).
"""
from src.battle.effects import StatusType


# Nomes amigáveis em PT-BR pra exibir nos toasts.
_STATUS_LABELS = {
    StatusType.POISON:        "veneno",
    StatusType.TOXIC_POISON:  "veneno grave",
    StatusType.BURN:          "queimadura",
    StatusType.PARALYSIS:     "paralisia",
    StatusType.FREEZE:        "congelamento",
}

# Status que a IA tenta curar.
_CURABLE_STATUSES = set(_STATUS_LABELS.keys())


class ArenaAI:
    """Controla itens e decisões simples do time inimigo."""

    # Cooldown entre usos de item (segundos)
    ITEM_COOLDOWN = {
        "easy":   6.0,
        "normal": 4.0,
        "hard":   2.5,
    }

    # HP threshold para usar poção (fração do HP máximo)
    HEAL_THRESHOLD = {
        "easy":   0.25,
        "normal": 0.35,
        "hard":   0.50,
    }

    # ==================================================================
    # INIT
    # ==================================================================
    def __init__(self, scene, enemy_team, difficulty="normal"):
        self.scene = scene
        self.team = enemy_team
        self.difficulty = (difficulty or "normal").lower()

        # id(pokemon) -> tempo restante de cooldown
        self._cooldowns = {}

        # Orçamento de itens que o NPC pode usar na batalha inteira.
        # 2 usos por pokémon do time — ajuste aqui se quiser mais/menos.
        self._uses_left = max(1, len(enemy_team) * 2)

    # ==================================================================
    # UPDATE (chamado pela cena a cada frame durante a batalha)
    # ==================================================================
    def update(self, dt):
        for poke in self.team:
            if not poke.is_alive() or poke.is_defeated:
                continue

            cd = self._cooldowns.get(id(poke), 0.0)
            if cd > 0:
                self._cooldowns[id(poke)] = cd - dt
                continue

            if self._uses_left <= 0:
                continue

            if self._try_use_item(poke):
                self._cooldowns[id(poke)] = self.ITEM_COOLDOWN.get(
                    self.difficulty, 4.0)
                self._uses_left -= 1

    # ==================================================================
    # DECISÃO
    # ==================================================================
    def _try_use_item(self, poke):
        """Retorna True se o NPC usou algum item neste tick."""
        em = getattr(poke, 'effect_manager', None)
        if em is None:
            return False

        # ----- Prioridade 1: curar status negativos -----
        status = em.get_status(poke)
        if status and status.type in _CURABLE_STATUSES:
            if self._use_full_heal(poke):
                return True
            # Se a cura falhou por algum motivo, tenta poção ainda no
            # mesmo tick (o pokémon pode estar com HP baixo E status).
            # Cai pro bloco de poção abaixo.

        # ----- Prioridade 2: recuperar HP -----
        hp_ratio = poke.current_hp / max(1, poke.max_hp)
        threshold = self.HEAL_THRESHOLD.get(self.difficulty, 0.35)
        if hp_ratio < threshold:
            if self._use_potion(poke):
                return True

        return False

    # ==================================================================
    # AÇÕES
    # ==================================================================
    def _use_potion(self, poke):
        """Cura 50 HP ou 60% do HP máximo (o que for maior). Retorna True se curou."""
        heal = max(50, int(poke.max_hp * 0.6))
        old_hp = poke.current_hp
        poke.current_hp = min(poke.max_hp, poke.current_hp + heal)
        healed = poke.current_hp - old_hp

        if healed <= 0:
            return False

        # Texto flutuante acima do pokémon
        em = getattr(poke, 'effect_manager', None)
        if em is not None:
            em.add_status_text(poke, f"+{healed} HP", duration=1.2)

        # Toast pro jogador
        self._toast(
            f"{poke.name} usou uma Poção! +{healed} HP",
            poke, portrait="happy",
        )

        print(f"[ARENA_AI] {poke.name} usou Poção! +{healed} HP "
              f"({poke.current_hp}/{poke.max_hp})")
        return True

    def _use_full_heal(self, poke):
        """Remove status negativo. Retorna True se removeu algum."""
        em = getattr(poke, 'effect_manager', None)
        if em is None:
            return False

        status = em.get_status(poke)
        if not status or status.type not in _CURABLE_STATUSES:
            return False

        status_label = _STATUS_LABELS.get(status.type, "status")
        em.remove_status(poke)
        em.add_status_text(poke, "Curado!", duration=1.2)

        try:
            poke.update_status_animation()
        except Exception:
            pass

        # Toast pro jogador
        self._toast(
            f"{poke.name} se curou de {status_label}!",
            poke, portrait="happy",
        )

        print(f"[ARENA_AI] {poke.name} se curou de {status_label}!")
        return True

    # ==================================================================
    # TOAST (wrapper defensivo)
    # ==================================================================
    def _toast(self, text, poke, portrait="happy", duration=3.0):
        """
        Envia um toast usando o sistema global do jogo (toast_battle).
        Import tardio + try/except para não quebrar a batalha se o
        sistema de notificações estiver indisponível.
        """
        try:
            from src.ui.toast_renderer import toast_battle
            toast_battle(text, duration=duration, pokemon=poke,
                         portrait=portrait)
        except Exception as e:
            print(f"[ARENA_AI] Falha ao emitir toast: {e}")