# src/scenes/npc_hall_scene/relearn_logic.py
"""
Lógica da tela Reaprender Movimento — apenas dados, sem render.
Segue o padrão de ProfileLogic.
"""
import unicodedata
from typing import List, Dict, Optional

from src.data.pokedex import Pokedex
from src.data.move_data import MoveData
from src.entities.move import Move

# Loaders de sprites (pixel-perfect: usamos get_original, sem escala)
from src.ui.utils.type_bar_loader import type_bar_loader
from src.ui.utils.type_icon_loader import type_icon_loader


# =====================================================================
# Helpers puros
# =====================================================================
_PT_TYPE = {
    'normal': 'Normal', 'fire': 'Fogo', 'water': 'Agua',
    'electric': 'Eletrico', 'grass': 'Planta', 'ice': 'Gelo',
    'fighting': 'Lutador', 'poison': 'Venenoso', 'ground': 'Terra',
    'flying': 'Voador', 'psychic': 'Psiquico', 'bug': 'Inseto',
    'rock': 'Pedra', 'ghost': 'Fantasma', 'dragon': 'Dragao',
    'dark': 'Sombrio', 'steel': 'Aco', 'fairy': 'Fada',
}

_CATEGORY_PT = {
    'physical': ('FISICO',   (255, 175, 90)),
    'special':  ('ESPECIAL', (110, 180, 250)),
    'status':   ('STATUS',   (180, 190, 200)),
}


def _sanitize(text) -> str:
    if text is None:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(text))
    return nfkd.encode('ASCII', 'ignore').decode('ASCII')


def _hex(rgb) -> str:
    if not rgb:
        return "#000000"
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _norm_type(t) -> str:
    """Normaliza nome de tipo (lowercase, hífen, alias)."""
    if not t:
        return "normal"
    return str(t).strip().lower().replace("_", "-").replace(" ", "-")


def _type_bar_surface(t) -> Optional["pygame.Surface"]:
    """Surface do type_bar no tamanho original (pixel-perfect)."""
    try:
        return type_bar_loader.get_original(_norm_type(t))
    except Exception as e:
        print(f"[RELEARN] Falha ao carregar type_bar '{t}': {e}")
        return None


def _type_icon_surface(t) -> Optional["pygame.Surface"]:
    """Surface do type_icon no tamanho original (pixel-perfect)."""
    try:
        return type_icon_loader.get_original(_norm_type(t))
    except Exception as e:
        print(f"[RELEARN] Falha ao carregar type_icon '{t}': {e}")
        return None


# =====================================================================
# RelearnLogic
# =====================================================================
class RelearnLogic:
    """Fonte de verdade da tela de reaprender — nada de pygame.draw aqui."""

    def __init__(self, game, cost: int):
        self.game = game
        self.player = game.player
        self.cost = cost

        self.pokedex = Pokedex()
        self.move_data = MoveData()

        # Estado
        self.entries: List[dict] = []
        self.selected_poke_idx = 0
        self.learnable_moves: List[dict] = []
        self.selected_move_idx = -1
        self.target_slot = -1

        self._desc_cache: Dict[str, str] = {}

        self.refresh_entries()
        self.refresh_learnable_moves()

    # ------------------------------------------------------------------
    # LISTA DE POKÉMON
    # ------------------------------------------------------------------
    def refresh_entries(self):
        self.entries = []
        team_ids = set()

        for p in self.player.team:
            team_ids.add(p.unique_id)
            self.entries.append({
                "source": "team",
                "unique_id": p.unique_id,
                "display": p.get_display_name(),
                "species": p.name,
                "level": p.level,
                "id": p.id,
                "shiny": p.is_shiny,
            })

        for d in self.player.pc_box:
            uid = d.get("unique_id")
            if not uid or uid in team_ids:
                continue
            self.entries.append({
                "source": "box",
                "unique_id": uid,
                "display": d.get("custom_name") or d.get("name", "?"),
                "species": d.get("name", "?"),
                "level": d.get("level", 1),
                "id": d.get("id", 1),
                "shiny": d.get("is_shiny", False),
            })

        if self.selected_poke_idx >= len(self.entries):
            self.selected_poke_idx = 0

    def _get_selected_entry(self) -> Optional[dict]:
        if 0 <= self.selected_poke_idx < len(self.entries):
            return self.entries[self.selected_poke_idx]
        return None

    def get_pokemon_instance(self):
        e = self._get_selected_entry()
        if not e:
            return None
        try:
            inst = self.player.get_pokemon_instance(e["unique_id"])
        except Exception as ex:
            print(f"[RELEARN] get_pokemon_instance falhou para {e.get('unique_id')}: {ex}")
            return None
        if inst is None:
            print(f"[RELEARN] Nenhum Pokémon com unique_id={e.get('unique_id')}")
        return inst

    # ------------------------------------------------------------------
    # LISTA DE GOLPES
    # ------------------------------------------------------------------
    def refresh_learnable_moves(self):
        self.learnable_moves = []
        self.selected_move_idx = -1
        self.target_slot = -1

        pk = self.get_pokemon_instance()
        if not pk:
            print("[RELEARN] Sem Pokémon selecionado — lista de golpes vazia.")
            return

        try:
            all_moves = self._get_family_moves_at_level(pk.id, pk.level)
        except Exception as ex:
            print(f"[RELEARN] _get_family_moves_at_level falhou: {ex}")
            all_moves = []

        current_lower = {m.name.lower() for m in pk.moves}
        print(f"[RELEARN] {pk.name} Lv.{pk.level} — família tem "
              f"{len(all_moves)} golpes, conhecidos: {sorted(current_lower)}")

        for name in all_moves:
            if not name:
                continue
            if name.lower() in current_lower:
                continue
            info = self.move_data.get_move_info(name)
            if not info:
                print(f"[RELEARN] get_move_info('{name}') retornou None — pulando")
                continue
            self.learnable_moves.append({"name": name, "info": info})

        print(f"[RELEARN] Golpes aprendíveis: "
              f"{[mv['name'] for mv in self.learnable_moves]}")

    # ------------------------------------------------------------------
    # FAMÍLIA EVOLUTIVA
    # ------------------------------------------------------------------
    def _get_family_moves_at_level(self, pokemon_id: int, level: int) -> List[str]:
        chain = self._get_species_pre_evolution_chain(pokemon_id)
        seen, result = set(), []
        for species_id in chain:
            try:
                moves = self.move_data.get_moves_at_level(species_id, level)
            except Exception as e:
                print(f"[RELEARN] Erro moves #{species_id}: {e}")
                moves = []

            for mv in moves or []:
                # get_moves_at_level pode retornar str OU dict
                if isinstance(mv, dict):
                    raw = mv.get("move") or mv.get("name") or ""
                else:
                    raw = str(mv)
                if not raw:
                    continue
                key = raw.lower()
                if key in seen:
                    continue
                seen.add(key)
                result.append(raw)
        return result

    def _get_species_pre_evolution_chain(self, pokemon_id: int) -> List[int]:
        """Cadeia até o atual (inclusive), tolerante a ids str/int."""
        try:
            pokemon_id = int(pokemon_id)
        except Exception:
            return [pokemon_id]

        try:
            data = self.pokedex.get_pokemon(pokemon_id)
        except Exception:
            data = None
        if not data:
            return [pokemon_id]

        evo = data.get("evolution") or {}

        # 1) family_members
        fam = evo.get("family_members") or []
        family_ids = []
        for m in fam:
            if isinstance(m, dict):
                mid = m.get("id")
                if mid is not None:
                    try:
                        family_ids.append(int(mid))
                    except Exception:
                        pass
        if family_ids and pokemon_id in family_ids:
            idx = family_ids.index(pokemon_id)
            return family_ids[:idx + 1]

        # 2) sobe por evolves_from
        chain, current_id = [pokemon_id], pokemon_id
        visited = {pokemon_id}
        for _ in range(10):
            try:
                cur_data = self.pokedex.get_pokemon(current_id)
            except Exception:
                break
            if not cur_data:
                break
            prev = (cur_data.get("evolution") or {}).get("evolves_from")
            if not prev:
                break
            if isinstance(prev, dict):
                prev_id = prev.get("id")
            else:
                prev_id = prev
            if prev_id is None:
                break
            try:
                prev_id = int(prev_id)
            except Exception:
                break
            if prev_id in visited:
                break
            visited.add(prev_id)
            chain.insert(0, prev_id)
            current_id = prev_id
        return chain

    # ------------------------------------------------------------------
    # DESCRIÇÃO DO GOLPE
    # ------------------------------------------------------------------
    def get_move_description(self, move_name: str, move_info=None) -> str:
        if move_name in self._desc_cache:
            return self._desc_cache[move_name]

        desc = None
        try:
            from src.battle.effects.effect_factory import EffectFactory
            key = move_name.lower().replace(" ", "-").replace("'", "")
            ef = EffectFactory.create_effect(key)
            if ef and getattr(ef, "description", None):
                desc = ef.description
            if not desc:
                cfg = EffectFactory.MOVE_EFFECTS.get(key)
                if cfg and cfg.get("description"):
                    desc = cfg["description"]
        except Exception:
            pass

        if not desc and move_info:
            d = move_info.get("description")
            if d and not d.startswith(f"Usa {move_name}"):
                desc = d

        if not desc:
            desc = "Um movimento que causa dano ao oponente."

        desc = _sanitize(desc)
        self._desc_cache[move_name] = desc
        return desc

    # ==================================================================
    # ITENS PARA CARD_GRID — POKÉMON
    # ==================================================================
    def pokemon_items(self) -> List[dict]:
        out = []
        for i, e in enumerate(self.entries):
            selected = (i == self.selected_poke_idx)
            if selected:
                bg, border = "#3E3464", "#C8B4FF"
            else:
                bg, border = "#1A1E2A", "#303540"

            portrait = None
            try:
                portrait = self.pokedex.get_portrait(e["id"], "normal", e["shiny"])
            except Exception:
                pass

            out.append({
                "index": i,
                "portrait": portrait,
                "name": e["display"],
                "species": f"Especie: {e['species']}",
                "level_str": f"Lv.{e['level']}",
                "source_tag": "TIME" if e["source"] == "team" else "BOX",
                "source_color": "#5AA0E6" if e["source"] == "team" else "#E6A05A",
                "bg_color": bg,
                "border_color": border,
            })
        return out

    # ==================================================================
    # ITENS PARA CARD_GRID — GOLPES
    # ==================================================================
    def move_items(self) -> List[dict]:
        out = []
        for i, mv in enumerate(self.learnable_moves):
            info = mv["info"]
            selected = (i == self.selected_move_idx)

            if selected:
                bg, border = "#37556E", "#96BEFF"
            else:
                bg, border = "#181C28", "#2E3342"

            mv_type = _norm_type(info.get("type", "normal"))
            type_color = self.pokedex.get_type_color(mv_type) or (150, 150, 150)
            cat = info.get("category", "physical")
            cat_lbl, cat_col = _CATEGORY_PT.get(cat, ("---", (150, 150, 150)))

            pwr = info.get("power", 0)
            acc = info.get("accuracy", 0)
            pp  = info.get("pp", 0)

            out.append({
                "index": i,
                "name": mv["name"].capitalize(),

                # para o grid: sprites pixel-perfect + cor fallback
                "type_name": mv_type,
                "type_icon": _type_icon_surface(mv_type),   # 38x38
                "type_bar":  _type_bar_surface(mv_type),    # 48x16
                "type_tag": _sanitize(_PT_TYPE.get(mv_type, mv_type.upper())).upper(),
                "type_color": _hex(type_color),

                "category_lbl": cat_lbl,
                "category_color": _hex(cat_col),
                "power_str": str(pwr) if pwr else "--",
                "acc_str": f"{acc}%" if acc else "--",
                "pp_str": str(pp),
                "bg_color": bg,
                "border_color": border,
            })
        return out

    # ==================================================================
    # DADOS DE COMPARAÇÃO
    # ==================================================================
    def selected_move_data(self) -> Optional[dict]:
        if 0 <= self.selected_move_idx < len(self.learnable_moves):
            return self.learnable_moves[self.selected_move_idx]
        return None

    def target_slot_move(self):
        if self.target_slot < 0:
            return None
        pk = self.get_pokemon_instance()
        if not pk:
            return None
        if self.target_slot < len(pk.moves):
            return pk.moves[self.target_slot]
        return None

    def _empty_comparison(self, title: str, name: str, description: str) -> dict:
        return {
            "title": title,
            "name": name,
            "type_name": "normal",
            "type_tag": "-",
            "type_color": "#3C3C50",
            "type_bar": None,
            "type_icon": None,
            "cat_lbl": "-",
            "cat_color": "#3C3C50",
            "stats_str": "PWR: --   ACC: --   PP: --",
            "description": description,
        }

    def comparison_data(self, side: str) -> dict:
        if side == "left":
            mv = self.selected_move_data()
            if not mv:
                return self._empty_comparison(
                    "NOVO GOLPE", "-",
                    "Selecione um golpe na lista acima."
                )
            info = mv["info"]
            mv_type = _norm_type(info.get("type", "normal"))
            type_color = self.pokedex.get_type_color(mv_type) or (150, 150, 150)
            cat = info.get("category", "physical")
            cat_lbl, cat_col = _CATEGORY_PT.get(cat, ("---", (150, 150, 150)))
            pwr = info.get("power", 0)
            acc = info.get("accuracy", 0)
            pp  = info.get("pp", 0)
            return {
                "title": "NOVO GOLPE",
                "name": mv["name"].capitalize(),
                "type_name": mv_type,
                "type_tag": _sanitize(_PT_TYPE.get(mv_type, mv_type.upper())).upper(),
                "type_color": _hex(type_color),
                "type_bar":  _type_bar_surface(mv_type),
                "type_icon": _type_icon_surface(mv_type),
                "cat_lbl": cat_lbl,
                "cat_color": _hex(cat_col),
                "stats_str": (f"PWR: {pwr if pwr else '--'}   "
                              f"ACC: {acc}%   PP: {pp}"),
                "description": self.get_move_description(mv["name"], info),
            }

        # side == "right"
        if self.target_slot < 0:
            return self._empty_comparison(
                "GOLPE ATUAL NO SLOT", "-",
                "Clique em um slot abaixo para comparar."
            )

        title = f"GOLPE ATUAL NO SLOT {self.target_slot + 1}"
        cur = self.target_slot_move()
        if cur is None:
            d = self._empty_comparison(
                title, "(VAZIO)",
                "Slot vazio. O novo golpe sera adicionado."
            )
            return d

        mv_type = _norm_type(getattr(cur, "type", "normal"))
        type_color = self.pokedex.get_type_color(mv_type) or (150, 150, 150)
        cat = getattr(cur, "category", "physical")
        cat_lbl, cat_col = _CATEGORY_PT.get(cat, ("---", (150, 150, 150)))

        return {
            "title": title,
            "name": cur.name.capitalize(),
            "type_name": mv_type,
            "type_tag": _sanitize(_PT_TYPE.get(mv_type, mv_type.upper())).upper(),
            "type_color": _hex(type_color),
            "type_bar":  _type_bar_surface(mv_type),
            "type_icon": _type_icon_surface(mv_type),
            "cat_lbl": cat_lbl,
            "cat_color": _hex(cat_col),
            "stats_str": (f"PWR: {getattr(cur, 'power', 0) or '--'}   "
                          f"ACC: {getattr(cur, 'accuracy', 0)}%   "
                          f"PP: {getattr(cur, 'max_pp', 0)}"),
            "description": self.get_move_description(cur.name),
        }

    # ==================================================================
    # TEXTO DOS SLOTS
    # ==================================================================
    def slot_labels(self) -> List[str]:
        """Compat — apenas nomes (para código legado)."""
        return [s["name"] for s in self.slot_data()]

    def slot_selected(self, idx: int) -> bool:
        return idx == self.target_slot

    def slot_data(self) -> List[dict]:
        """
        Dados por slot: nome do golpe + ícone do tipo (para o botão exibir).
        Slots vazios vêm com name="(vazio)" e icon=None.
        """
        pk = self.get_pokemon_instance()
        out = []
        for i in range(4):
            if not pk or i >= len(pk.moves):
                out.append({"name": "(vazio)", "type": None, "icon": None})
                continue
            m = pk.moves[i]
            mv_type = _norm_type(getattr(m, "type", "normal"))
            out.append({
                "name": m.name.capitalize(),
                "type": mv_type,
                "icon": _type_icon_surface(mv_type),  # 38x38 pixel-perfect
            })
        return out

    # ==================================================================
    # SELEÇÃO
    # ==================================================================
    def select_pokemon(self, idx: int) -> bool:
        if 0 <= idx < len(self.entries):
            self.selected_poke_idx = idx
            self.refresh_learnable_moves()
            return True
        return False

    def select_move(self, idx: int) -> bool:
        if 0 <= idx < len(self.learnable_moves):
            self.selected_move_idx = idx
            return True
        return False

    def select_slot(self, idx: int) -> bool:
        if 0 <= idx < 4:
            self.target_slot = idx
            return True
        return False

    # ==================================================================
    # CONFIRMAR — RETORNA (ok, mensagem)
    # ==================================================================
    def try_learn(self) -> tuple:
        pk = self.get_pokemon_instance()
        if not pk:
            return False, "Nenhum Pokemon selecionado."

        if not (0 <= self.selected_move_idx < len(self.learnable_moves)):
            return False, "Selecione um golpe para aprender."

        if self.target_slot < 0:
            return False, "Selecione um slot de destino."

        if self.player.money < self.cost:
            return False, "Gold insuficiente!"

        chosen = self.learnable_moves[self.selected_move_idx]
        new_move = Move(chosen["name"], chosen["info"])

        slot = self.target_slot
        try:
            if slot < len(pk.moves):
                pk.moves[slot] = new_move
            elif slot == len(pk.moves) and slot < 4:
                pk.moves.append(new_move)
            else:
                return False, "Slot invalido."
        except Exception as e:
            print(f"[RELEARN] Erro ao aprender: {e}")
            return False, "Erro ao aprender golpe."

        if not pk.is_in_team:
            for d in self.player.pc_box:
                if d.get("unique_id") == pk.unique_id:
                    d["moves"] = [
                        {
                            "name": m.name,
                            "current_pp": m.current_pp,
                            "max_pp": m.max_pp,
                            "type": m.type,
                            "power": m.power,
                            "accuracy": m.accuracy,
                            "category": m.category,
                        }
                        for m in pk.moves
                    ]
                    break

        self.player.money -= self.cost
        try:
            self.player.auto_save()
        except Exception as e:
            print(f"[RELEARN] Erro ao salvar: {e}")

        return True, f"Seu Pokemon reaprendeu '{chosen['name']}'!"

    # ==================================================================
    # HEADER
    # ==================================================================
    def header_info_text(self) -> str:
        return (f"Custo: {self.cost} G   -   Voce tem: {self.player.money} G   -   "
                f"Apenas golpes que o Pokemon ja poderia aprender ate o nivel atual")

    def confirm_label(self) -> str:
        return f"CONFIRMAR ({self.cost} G)"

    def confirm_ready(self) -> bool:
        return (self.selected_move_idx >= 0
                and self.target_slot >= 0
                and self.player.money >= self.cost)