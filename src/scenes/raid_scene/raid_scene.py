# src/scenes/raid_scene/raid_scene.py

import pygame
import random
import math
import uuid

from src.scenes.base_scene import BaseScene
from src.network.protocol import create_message
from src.ui.toast_renderer import toast_info, toast_warning
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.data.pokedex import Pokedex
from src.scenes.team_select_scene.components.gradient_background import GradientBackground


# =========================================================
# Paleta (consistente com TradeScene)
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


# =========================================================
# Entrada leve (reutiliza a ideia do _TradeEntry do TradeScene)
# =========================================================
class _RaidEntry:
    __slots__ = ("unique_id", "id", "name", "level", "types",
                 "is_shiny", "is_in_team", "source", "_instance", "_raw_data")

    def __init__(self, unique_id, pokemon_id, name, level, types,
                 is_shiny, is_in_team, source, instance=None, raw_data=None):
        self.unique_id = unique_id
        self.id = pokemon_id
        self.name = name
        self.level = level
        self.types = types
        self.is_shiny = is_shiny
        self.is_in_team = is_in_team
        self.source = source
        self._instance = instance
        self._raw_data = raw_data

    def to_dict(self):
        if self._instance is not None:
            return self._instance.to_dict()
        return dict(self._raw_data) if self._raw_data else {}

    def get_instance(self, player):
        """Retorna a instância Pokemon (cria e cacheia se for da box)."""
        if self._instance is not None:
            return self._instance

        cached = player._pokemon_cache.get(self.unique_id)
        if cached is not None:
            return cached

        from src.entities.pokemon import Pokemon
        inst = Pokemon.from_dict(self._raw_data)
        inst.is_in_team = False
        player._pokemon_cache[self.unique_id] = inst
        return inst


# =========================================================
# Cena principal de RAID
# =========================================================
class RaidScene(BaseScene):
    """Sala de Raid: aguarda jogadores → seleção de time → pronto → countdown."""

    # -------- Estados --------
    ST_WAITING   = "waiting"     # aguardando 2+ jogadores
    ST_SELECTING = "selecting"   # cada um escolhe até a quota dele
    ST_READY     = "ready"       # todos confirmam "Pronto"
    ST_COUNTDOWN = "countdown"   # 5..4..3..2..1
    ST_STARTED   = "started"     # raid começou (placeholder)
    ST_CANCELLED = "cancelled"

    MIN_PLAYERS = 2
    MAX_PLAYERS = 6
    MAX_SELECTION = 6            # teto absoluto (nunca pode passar disso)
    RAID_TEAM_SIZE = 6

    def __init__(self, game, is_host, network, raid_id=None):
        super().__init__(game)
        self.network = network
        self.is_host = is_host
        self.network.current_scene_callback = self._on_network_message

        # Só o HOST gera raid_id. Cliente adota o do host quando receber a primeira RAID_PLAYER_LIST.
        if raid_id:
            self.raid_id = raid_id
        elif is_host:
            self.raid_id = str(uuid.uuid4())[:8]
        else:
            self.raid_id = None  # será preenchido pelo host

        # ===== POKÉDEX =====
        self.pokedex = Pokedex()

        # ===== BACKGROUND =====
        self.background = GradientBackground(game.screen_manager)

        # ===== ESTADO =====
        self.state = self.ST_WAITING

        # ===== RAID SORTEADA (chapter + level) =====
        self.raid_chapter = None
        self.raid_level = None

        # Jogadores na raid: uuid -> dict(name, uuid, ready, submitted, team, assigned_count)
        self.raid_players = {}

        # Minha seleção atual (lista de _RaidEntry)
        self._all_entries = []
        self._my_selection = []

        # Times recebidos de todos: uuid -> [pokemon_data, ...]
        self.all_teams = {}

        # Resultado final: lista de {"pokemon": data, "owner_uuid":.., "owner_name":..}
        self.final_team = []

        # ===== QUOTAS DE SELEÇÃO =====
        # uuid -> quantos Pokémon pode escolher.
        # Calculado pelo host ao iniciar a seleção e adotado pelo cliente.
        self._quotas = {}

        # ===== MODAL DE DETALHES =====
        self.modal = None
        self._detail_buttons = []

        # Countdown
        self.countdown_value = 0
        self.countdown_timer = 0.0
        self._countdown_started = False

        # ===== SCROLL da lista =====
        self.scroll_offset = 0
        self.visible_items = 5

        # ===== LAYOUT / RECTS =====
        self.back_btn = pygame.Rect(0, 0, 110, 36)
        self.leave_btn = pygame.Rect(0, 0, 0, 0)
        self.action_btn = pygame.Rect(0, 0, 0, 0)
        self._list_rect = pygame.Rect(0, 0, 0, 0)
        self._players_rect = pygame.Rect(0, 0, 0, 0)
        self._right_rect = pygame.Rect(0, 0, 0, 0)
        self._item_height = 60
        self._list_items_w = 0

        # ===== FONTES =====
        self.font_title = pygame.font.Font(None, 44)
        self.font_h1 = pygame.font.Font(None, 28)
        self.font_h2 = pygame.font.Font(None, 22)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 18)
        self.font_tiny = pygame.font.Font(None, 16)
        self.font_btn = pygame.font.Font(None, 22)

        # ===== SETUP =====
        self._refresh_my_entries()
        self._layout()

        # ===== ANUNCIA ENTRADA =====
        my_uuid = (
                getattr(self.game.player, "uuid", None)
                or getattr(self.network, "my_uuid", None)
                or "unknown"
        )
        self.network.set_uuid(my_uuid)

        # Host já se registra localmente
        if self.is_host:
            self.raid_players[my_uuid] = {
                "name": self.network.my_name,
                "uuid": my_uuid,
                "ready": False,
                "submitted": False,
                "team": [],
                "assigned_count": 0,
            }

        # Todos enviam RAID_JOIN para o host
        self.network.send_to_all(create_message(
            "RAID_JOIN",
            {
                "raid_id": self.raid_id,
                "name": self.network.my_name,
                "uuid": my_uuid,
            },
        ))

        # Host já publica a lista inicial
        if self.is_host:
            self._broadcast_player_list()

        print(f"[RAID] {self.network.my_name} entrou na raid {self.raid_id} (host={self.is_host})")

    # =========================================================
    # Lista de Pokémon (Time + Box) — lazy
    # =========================================================
    def _refresh_my_entries(self):
        entries = []
        seen = set()

        for p in self.game.player.team:
            if p.unique_id in seen:
                continue
            entries.append(_RaidEntry(
                unique_id=p.unique_id, pokemon_id=p.id, name=p.name,
                level=p.level, types=list(p.types) if p.types else [],
                is_shiny=p.is_shiny, is_in_team=True, source="team",
                instance=p,
            ))
            seen.add(p.unique_id)

        for data in self.game.player.pc_box:
            uid = data.get("unique_id")
            if not uid or uid in seen:
                continue
            entries.append(_RaidEntry(
                unique_id=uid, pokemon_id=data.get("id", 0),
                name=data.get("name", "?"), level=data.get("level", 1),
                types=list(data.get("types", [])),
                is_shiny=data.get("is_shiny", False),
                is_in_team=False, source="box", raw_data=data,
            ))
            seen.add(uid)

        self._all_entries = entries

    # =========================================================
    # Layout
    # =========================================================
    def _layout(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        self.back_btn = pygame.Rect(vx + 16, vy + 16, 110, 36)

        margin = 20
        header_h = 70
        footer_h = 70

        content_y = vy + header_h
        content_h = vh - header_h - footer_h

        left_w = 260
        gap = 14

        self._players_rect = pygame.Rect(vx + margin, content_y, left_w, content_h)
        self._right_rect = pygame.Rect(
            self._players_rect.right + gap, content_y,
            vw - left_w - margin * 2 - gap, content_h,
        )

        self._list_rect = pygame.Rect(
            self._right_rect.x + 12,
            self._right_rect.y + 12,
            self._right_rect.width - 24,
            self._right_rect.height - 24,
        )

        header_list = 44
        self._item_height = 58
        avail_h = self._list_rect.height - header_list
        self.visible_items = max(2, avail_h // self._item_height)
        self._list_items_w = self._list_rect.width - 8

        btn_h = 42
        center_x = vx + vw // 2
        self.leave_btn = pygame.Rect(vx + margin, vy + vh - btn_h - 16, 140, btn_h)
        self.action_btn = pygame.Rect(center_x - 130, vy + vh - btn_h - 16, 260, btn_h)

    # =========================================================
    # Rede
    # =========================================================
    def _my_uuid(self):
        return (
            getattr(self.game.player, "uuid", None)
            or getattr(self.network, "my_uuid", None)
            or "unknown"
        )

    def _broadcast_player_list(self):
        if not self.is_host:
            return
        payload = {
            "raid_id": self.raid_id,
            "players": [
                {
                    "name": p["name"],
                    "uuid": p["uuid"],
                    "ready": p.get("ready", False),
                    "submitted": p.get("submitted", False),
                }
                for p in self.raid_players.values()
            ],
            "host_uuid": self._my_uuid(),
        }
        names = [p["name"] for p in self.raid_players.values()]
        print(f"[RAID][HOST] Broadcast PLAYER_LIST → {names}")
        self.network.send_to_all(create_message("RAID_PLAYER_LIST", payload))

    def _on_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        # Ignora mensagens de OUTRAS raids
        incoming_raid_id = payload.get("raid_id")
        if incoming_raid_id and self.raid_id and incoming_raid_id != self.raid_id:
            return

        # Cliente adota o raid_id do host na primeira mensagem
        if incoming_raid_id and not self.raid_id:
            self.raid_id = incoming_raid_id
            print(f"[RAID] Cliente adotou raid_id do host: {self.raid_id}")

        if msg_type == "RAID_JOIN":
            name = payload.get("name", "?")
            uuid_str = payload.get("uuid", "unknown")
            print(f"[RAID][HOST] RAID_JOIN recebido de {name} (uuid={uuid_str[:8]})")

            if self.is_host:
                # Bloqueia entrada depois que a seleção começou
                if self.state != self.ST_WAITING:
                    print(f"[RAID][HOST] Recusando {name} — raid já em andamento.")
                    return
                if uuid_str in self.raid_players:
                    print(f"[RAID][HOST] {name} já está na lista — re-broadcast.")
                    self._broadcast_player_list()
                    return
                if len(self.raid_players) >= self.MAX_PLAYERS:
                    toast_warning(f"Raid cheia! {name} não pôde entrar.")
                    return
                self.raid_players[uuid_str] = {
                    "name": name, "uuid": uuid_str,
                    "ready": False, "submitted": False,
                    "team": [], "assigned_count": 0,
                }
                toast_info(f"{name} entrou na raid.")
                self._broadcast_player_list()

        elif msg_type == "RAID_PLAYER_LIST":
            players = payload.get("players", [])
            print(f"[RAID][CLIENTE?{not self.is_host}] PLAYER_LIST recebida: "
                  f"{[p['name'] for p in players]}")

            new_map = {}
            for p in players:
                u = p["uuid"]
                old = self.raid_players.get(u, {})
                new_map[u] = {
                    "name": p["name"],
                    "uuid": u,
                    "ready": p.get("ready", False),
                    "submitted": p.get("submitted", False),
                    "team": old.get("team", []),
                    "assigned_count": old.get("assigned_count", 0),
                }
            self.raid_players = new_map

            if not self.is_host:
                my_uuid = self._my_uuid()
                if my_uuid not in self.raid_players:
                    print(f"[RAID] Não estou na lista do host — reenviando RAID_JOIN "
                          f"(raid_id={self.raid_id})")
                    self.network.send_to_all(create_message(
                        "RAID_JOIN",
                        {
                            "raid_id": self.raid_id,
                            "name": self.network.my_name,
                            "uuid": my_uuid,
                        },
                    ))

        elif msg_type == "RAID_START_SELECTION":
            if self.state == self.ST_WAITING:
                self.state = self.ST_SELECTING
                self._my_selection = []
                self.scroll_offset = 0

                # Adota quotas do host
                quotas_raw = payload.get("quotas", {})
                if quotas_raw:
                    self._quotas = {str(k): int(v) for k, v in quotas_raw.items()}
                else:
                    self._quotas = self._compute_quotas()

                toast_info(f"Selecione até {self._my_quota()} Pokémon para a raid!")

        elif msg_type == "RAID_TEAM_SUBMIT":
            sender_uuid = payload.get("uuid")
            team_data = payload.get("team", [])
            if self.is_host and sender_uuid in self.raid_players:
                self.raid_players[sender_uuid]["team"] = team_data
                self.raid_players[sender_uuid]["submitted"] = True
                self._broadcast_player_list()
                self._check_all_submitted()

        elif msg_type == "RAID_TEAM_UPDATE":
            self.all_teams = payload.get("all_teams", {})
            self.final_team = payload.get("final_team", [])

            # Adota quotas finais do host
            quotas_raw = payload.get("quotas", {})
            if quotas_raw:
                self._quotas = {str(k): int(v) for k, v in quotas_raw.items()}

            for u, team in self.all_teams.items():
                if u in self.raid_players:
                    self.raid_players[u]["assigned_count"] = len(team)
                    self.raid_players[u]["team"] = team
            if self.state == self.ST_SELECTING:
                self.state = self.ST_READY
                toast_info("Times formados! Todos devem ficar prontos.")

        elif msg_type == "RAID_PLAYER_READY":
            sender_uuid = payload.get("uuid")
            ready = bool(payload.get("ready", False))
            if self.is_host and sender_uuid in self.raid_players:
                self.raid_players[sender_uuid]["ready"] = ready
                self._broadcast_player_list()
                self._check_all_ready()
            else:
                if sender_uuid in self.raid_players:
                    self.raid_players[sender_uuid]["ready"] = ready

        elif msg_type == "RAID_COUNTDOWN":
            self.state = self.ST_COUNTDOWN
            self.countdown_value = int(payload.get("seconds", 5))
            self.countdown_timer = 0.0
            self._countdown_started = True

            rc = payload.get("raid_chapter")
            rl = payload.get("raid_level")
            if rc is not None and rl is not None and not self.is_host:
                self.raid_chapter = int(rc)
                self.raid_level = int(rl)
                print(f"[RAID] Cliente adotou raid: "
                      f"Cap {self.raid_chapter} Level {self.raid_level}")

            toast_info(f"RAID COMEÇANDO EM {self.countdown_value}!")

        elif msg_type == "RAID_START":
            rc = payload.get("raid_chapter")
            rl = payload.get("raid_level")
            if rc is not None and rl is not None:
                self.raid_chapter = int(rc)
                self.raid_level = int(rl)
                print(f"[RAID] Host anunciou raid: Cap {self.raid_chapter} "
                      f"Level {self.raid_level}")
            self.state = self.ST_STARTED
            self._on_raid_started()

        elif msg_type == "RAID_LEAVE":
            sender_uuid = payload.get("uuid")
            name = payload.get("name", "?")
            if sender_uuid in self.raid_players:
                del self.raid_players[sender_uuid]
                toast_warning(f"{name} saiu da raid.")
            if self.is_host:
                self._broadcast_player_list()
                if len(self.raid_players) < self.MIN_PLAYERS and self.state != self.ST_WAITING:
                    self._cancel_raid("Jogadores insuficientes.")

        elif msg_type == "RAID_CANCEL":
            reason = payload.get("reason", "Raid cancelada.")
            self.state = self.ST_CANCELLED
            toast_warning(reason)

        elif msg_type == "DISCONNECT":
            if self.state not in (self.ST_STARTED,):
                self._return_to_lobby()

    # =========================================================
    # Lógica do host
    # =========================================================
    def _check_all_submitted(self):
        if not self.is_host:
            return
        if len(self.raid_players) < self.MIN_PLAYERS:
            return
        if all(p.get("submitted") for p in self.raid_players.values()):
            self._finalize_teams()

    def _check_all_ready(self):
        if not self.is_host:
            return
        if len(self.raid_players) < self.MIN_PLAYERS:
            return
        if all(p.get("ready") for p in self.raid_players.values()):
            # Sorteia a raid
            self._pick_random_raid()

            self.state = self.ST_COUNTDOWN
            self.countdown_value = 5
            self.countdown_timer = 0.0
            self._countdown_started = True

            self.network.send_to_all(create_message(
                "RAID_COUNTDOWN",
                {
                    "raid_id": self.raid_id,
                    "seconds": 5,
                    "raid_chapter": self.raid_chapter,
                    "raid_level": self.raid_level,
                },
            ))
            toast_info("Todos prontos! RAID COMEÇANDO!")

    def _pick_random_raid(self):
        from src.scenes.raid_scene.raid_catalog import pick_random_raid, get_raid_name
        from src.config.raid_season import CURRENT_RAID_CHAPTER, get_season_name

        resultado = pick_random_raid(CURRENT_RAID_CHAPTER)

        if resultado is None:
            print(f"[RAID] Sem raids no capítulo {CURRENT_RAID_CHAPTER} — usando 1-1")
            self.raid_chapter, self.raid_level = 1, 1
            return

        self.raid_chapter, self.raid_level = resultado
        season = get_season_name(self.raid_chapter)
        nome = get_raid_name(self.raid_chapter, self.raid_level)
        print(f"[RAID] Temporada {season} → {nome} (cap {self.raid_chapter} lvl {self.raid_level})")

        try:
            toast_info(f"Raid sorteada: {nome}", duration=3.0)
        except Exception:
            pass

    # -------- Quotas --------
    def _compute_quotas(self):
        """Divide 6 Pokémon entre os jogadores. Sobra vai pra sorteio."""
        n = len(self.raid_players)
        if n <= 0:
            return {}

        base = self.RAID_TEAM_SIZE // n
        remainder = self.RAID_TEAM_SIZE % n

        uuids = list(self.raid_players.keys())
        random.shuffle(uuids)

        quotas = {}
        for i, u in enumerate(uuids):
            quotas[u] = base + (1 if i < remainder else 0)
        return quotas

    def _my_quota(self):
        """Quantos Pokémon EU posso escolher nesta raid."""
        my = self._my_uuid()
        if self._quotas and my in self._quotas:
            return int(self._quotas[my])
        n = max(1, len(self.raid_players))
        return max(1, self.RAID_TEAM_SIZE // n)

    # -------- Finalização dos times --------
    def _finalize_teams(self):
        """Divide o time da raid usando as quotas pré-calculadas."""
        n = len(self.raid_players)
        if n < self.MIN_PLAYERS:
            return

        # Reutiliza quotas se válidas
        if self._quotas and all(u in self._quotas for u in self.raid_players.keys()):
            quotas = dict(self._quotas)
        else:
            quotas = self._compute_quotas()

        all_teams = {}
        final_team = []

        for u, quota in quotas.items():
            if u not in self.raid_players:
                continue
            player = self.raid_players[u]
            candidates = list(player.get("team", []))
            random.shuffle(candidates)
            chosen = candidates[:quota]

            all_teams[u] = chosen
            player["assigned_count"] = len(chosen)

            for poke in chosen:
                final_team.append({
                    "pokemon": poke,
                    "owner_uuid": u,
                    "owner_name": player["name"],
                })

        self.all_teams = all_teams
        self.final_team = final_team

        self.network.send_to_all(create_message(
            "RAID_TEAM_UPDATE",
            {
                "raid_id": self.raid_id,
                "all_teams": all_teams,
                "final_team": final_team,
                "quotas": {str(k): v for k, v in quotas.items()},
            },
        ))

        self.state = self.ST_READY
        toast_info("Times formados! Fiquem prontos.")

    def _cancel_raid(self, reason):
        self.state = self.ST_CANCELLED
        if self.is_host:
            self.network.send_to_all(create_message(
                "RAID_CANCEL",
                {"raid_id": self.raid_id, "reason": reason},
            ))

    def _on_raid_started(self):
        from src.scenes.raid_scene.raid_battle_scene import RaidBattleScene

        if getattr(self, '_raid_battle_launched', False):
            return
        self._raid_battle_launched = True

        if self.is_host and not self.final_team:
            self._finalize_teams()

        if not self.raid_chapter or not self.raid_level:
            self.raid_chapter = 1
            self.raid_level = 1
            print(f"[RAID] AVISO: raid não sorteada — usando fallback 1-1")

        boss_cfg = self._get_raid_boss_config(self.raid_chapter, self.raid_level)
        print(f"[RAID] Iniciando batalha | cap={self.raid_chapter} "
              f"level={self.raid_level} | boss_id={boss_cfg['pokemon_id']} | "
              f"boss_level={boss_cfg['level']} | delay={boss_cfg['initial_delay']}s | "
              f"final_team={len(self.final_team)} pokémon")

        self.game.current_scene = RaidBattleScene(
            self.game,
            is_host=self.is_host,
            network=self.network,
            raid_players=self.raid_players,
            final_team=self.final_team,
            boss_id=boss_cfg["pokemon_id"],
            boss_level=boss_cfg["level"],
            initial_delay=boss_cfg["initial_delay"],
            raid_chapter=self.raid_chapter,
            raid_level=self.raid_level,
        )

    def _get_raid_boss_config(self, raid_chapter, raid_level):
        """Lê o boss da fase de raid ESPECÍFICA (cap + level)."""
        default = {"pokemon_id": 146, "level": 50, "initial_delay": 10.0}
        try:
            import json, os
            from src.scenes.raid_scene.raid_catalog import get_raid_path

            raid_path = get_raid_path(raid_chapter, raid_level)
            if not os.path.exists(raid_path):
                print(f"[RAID] AVISO: JSON da raid não encontrado: {raid_path}")
                return default

            with open(raid_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            waves = data.get("waves", {}).get("waves", [])
            if not waves:
                return default

            wave = waves[0]

            pokemon_id = None
            enemies = wave.get("enemies", [])
            if enemies:
                pokemon_id = enemies[0].get("pokemon_id")

            level = wave.get("min_level", 50)
            initial_delay = wave.get("initial_delay", 10.0)

            print(f"[RAID] Boss config lida ({raid_chapter}-{raid_level}): "
                  f"id={pokemon_id} level={level} delay={initial_delay}")
            return {
                "pokemon_id": pokemon_id or 146,
                "level": int(level),
                "initial_delay": float(initial_delay),
            }

        except Exception as e:
            print(f"[RAID] Erro ao ler config do boss: {e}")
            import traceback
            traceback.print_exc()
            return default

    # =========================================================
    # Ações do jogador
    # =========================================================
    def _toggle_select(self, entry):
        # Se já está selecionado, remove
        for i, e in enumerate(self._my_selection):
            if e.unique_id == entry.unique_id:
                self._my_selection.pop(i)
                return

        quota = self._my_quota()
        if len(self._my_selection) >= quota:
            toast_warning(f"Máximo de {quota} Pokémon para esta raid.")
            return
        self._my_selection.append(entry)

    def _submit_team(self):
        quota = self._my_quota()
        if len(self._my_selection) == 0:
            toast_warning("Selecione pelo menos 1 Pokémon.")
            return
        if len(self._my_selection) > quota:
            toast_warning(f"Máximo {quota}.")
            return

        team_data = []
        for e in self._my_selection:
            data = e.to_dict()
            cached = self.game.player._pokemon_cache.get(e.unique_id)
            if cached is not None:
                data["held_item"] = getattr(cached, "held_item", None)
            team_data.append(data)

        my_uuid = self._my_uuid()
        self.network.send_to_all(create_message(
            "RAID_TEAM_SUBMIT",
            {"raid_id": self.raid_id, "uuid": my_uuid, "team": team_data},
        ))

        if self.is_host:
            self.raid_players[my_uuid]["team"] = team_data
            self.raid_players[my_uuid]["submitted"] = True
            self._broadcast_player_list()
            self._check_all_submitted()

        toast_info(f"Time enviado ({len(team_data)} Pokémon).")
        self.state = self.ST_READY

    def _toggle_ready(self):
        my_uuid = self._my_uuid()
        me = self.raid_players.get(my_uuid)
        if not me:
            return
        new_val = not me.get("ready", False)
        me["ready"] = new_val

        self.network.send_to_all(create_message(
            "RAID_PLAYER_READY",
            {"raid_id": self.raid_id, "uuid": my_uuid, "ready": new_val},
        ))

        if self.is_host:
            self._broadcast_player_list()
            self._check_all_ready()

        toast_info("Você está PRONTO!" if new_val else "Você cancelou o pronto.")

    def _leave_raid(self):
        my_uuid = self._my_uuid()
        self.network.send_to_all(create_message(
            "RAID_LEAVE",
            {"raid_id": self.raid_id, "uuid": my_uuid, "name": self.network.my_name},
        ))
        self._return_to_lobby()

    def _return_to_lobby(self):
        from src.scenes.lobby_scene.lobby_scene import LobbyScene
        self.game.current_scene = LobbyScene(
            self.game, is_host=self.is_host, network=self.network
        )

    # =========================================================
    # MODAL DE DETALHES
    # =========================================================
    def _open_pokemon_modal_by_uid(self, uid):
        for e in self._all_entries:
            if e.unique_id == uid:
                self._open_pokemon_modal(e)
                return

    def _open_pokemon_modal(self, entry):
        try:
            uid = entry.unique_id
            if uid not in self.game.player._pokemon_cache:
                entry.get_instance(self.game.player)

            from scenes.team_select_scene.components import PokemonModal
            self.modal = PokemonModal(self.game, uid)

            # Neutraliza botões de ação do modal
            self.modal.action_button = pygame.Rect(0, 0, 0, 0)
            self.modal.release_button = pygame.Rect(0, 0, 0, 0)
        except Exception as e:
            print(f"[RAID] Erro ao abrir modal: {e}")
            import traceback
            traceback.print_exc()
            toast_warning("Erro ao abrir detalhes.")

    def _close_modal(self):
        self.modal = None

    # =========================================================
    # Update
    # =========================================================
    def fixed_update(self, dt):
        # Fila de rede
        try:
            while not self.network.incoming_queue.empty():
                item = self.network.incoming_queue.get_nowait()
                if isinstance(item, tuple) and len(item) == 2:
                    msg, _ = item
                else:
                    msg = item
                self._on_network_message(msg, None)
        except Exception as e:
            print(f"[RAID] Erro na fila: {e}")

        # Countdown
        if self.state == self.ST_COUNTDOWN and self._countdown_started:
            self.countdown_timer += dt
            if self.countdown_timer >= 1.0:
                self.countdown_timer -= 1.0
                self.countdown_value -= 1
                if self.countdown_value <= 0:
                    self._countdown_started = False
                    if self.is_host:
                        self.network.send_to_all(create_message(
                            "RAID_START",
                            {
                                "raid_id": self.raid_id,
                                "raid_chapter": self.raid_chapter or 1,
                                "raid_level": self.raid_level or 1,
                            },
                        ))
                    self.state = self.ST_STARTED
                    self._on_raid_started()

    # =========================================================
    # Eventos
    # =========================================================
    def handle_event(self, event):
        # ===== MODAL TEM PRIORIDADE =====
        if self.modal and self.modal.visible:
            result = self.modal.handle_event(event)
            if result == "close":
                self._close_modal()
            return

        if event.type == pygame.VIDEORESIZE:
            self._layout()
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._leave_raid()
            return

        if event.type == pygame.MOUSEWHEEL:
            if self.state == self.ST_SELECTING:
                mouse = pygame.mouse.get_pos()
                if self._list_rect.collidepoint(mouse):
                    max_off = max(0, len(self._all_entries) - self.visible_items)
                    self.scroll_offset = max(0, min(max_off,
                                                     self.scroll_offset - event.y))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            if self.back_btn.collidepoint(pos) or self.leave_btn.collidepoint(pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._leave_raid()
                return

            if self.action_btn.collidepoint(pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._on_action_clicked()
                return

            # ===== Botões DETALHES (prioridade sobre toggle) =====
            if self.state == self.ST_SELECTING:
                for btn_rect, uid in self._detail_buttons:
                    if btn_rect.collidepoint(pos):
                        sound_manager.play_effect(SoundEffect.CLICK)
                        self._open_pokemon_modal_by_uid(uid)
                        return

            # Clique na lista (só na fase de seleção)
            if self.state == self.ST_SELECTING:
                idx = self._get_entry_at_pos(pos)
                if idx is not None and idx < len(self._all_entries):
                    self._toggle_select(self._all_entries[idx])
                    return

    def _on_action_clicked(self):
        if self.state == self.ST_WAITING:
            if self.is_host:
                if len(self.raid_players) < self.MIN_PLAYERS:
                    toast_warning(
                        f"Precisa de pelo menos {self.MIN_PLAYERS} jogadores."
                    )
                    return

                # Calcula quotas ANTES de broadcastar
                self._quotas = self._compute_quotas()
                quotas_json = {str(k): int(v) for k, v in self._quotas.items()}

                self.network.send_to_all(create_message(
                    "RAID_START_SELECTION",
                    {"raid_id": self.raid_id, "quotas": quotas_json},
                ))
                self.state = self.ST_SELECTING
                self._my_selection = []
                self.scroll_offset = 0
                toast_info(f"Seleção iniciada! Escolha até {self._my_quota()} Pokémon.")
            else:
                toast_info("Aguardando o host iniciar a seleção...")

        elif self.state == self.ST_SELECTING:
            self._submit_team()

        elif self.state == self.ST_READY:
            self._toggle_ready()

    # =========================================================
    # Hit test da lista
    # =========================================================
    def _list_items_origin(self):
        return (
            self._list_rect.x + 6,
            self._list_rect.y + 50,
        )

    def _get_entry_at_pos(self, pos):
        x0, y0 = self._list_items_origin()
        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self._all_entries):
                break
            rect = pygame.Rect(
                x0, y0 + i * self._item_height,
                self._list_items_w, self._item_height - 4,
            )
            if rect.collidepoint(pos):
                # Se o clique foi no botão DETALHES, não seleciona
                for btn_rect, _uid in self._detail_buttons:
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

        title = self.font_title.render("RAID", True, COL_ACCENT)
        screen.blit(title, title.get_rect(center=(cx, vy + 34)))

        n = len(self.raid_players)
        subtitle = self.font_small.render(
            f"Jogadores: {n}/{self.MAX_PLAYERS}  (mínimo {self.MIN_PLAYERS})",
            True, COL_TEXT_DIM,
        )
        screen.blit(subtitle, subtitle.get_rect(center=(cx, vy + 58)))

        self._draw_button(screen, self.back_btn, "Sair", kind="danger")
        self._render_players_panel(screen)

        if self.state == self.ST_WAITING:
            self._render_waiting(screen)
        elif self.state == self.ST_SELECTING:
            self._render_selection(screen)
        elif self.state == self.ST_READY:
            self._render_ready(screen)
        elif self.state == self.ST_COUNTDOWN:
            self._render_countdown(screen)
        elif self.state == self.ST_STARTED:
            self._render_started(screen)
        elif self.state == self.ST_CANCELLED:
            self._render_cancelled(screen)

        self._render_action_button(screen)

        instr = self.font_tiny.render(
            "ESC = sair  |  Clique nos Pokémon para selecionar/desselecionar",
            True, COL_TEXT_MUTED,
        )
        screen.blit(instr, instr.get_rect(center=(cx, vy + vh - 14)))

        # Modal por cima de tudo
        if self.modal and self.modal.visible:
            self.modal.render(screen)

    # ---------- Painel esquerdo ----------
    def _render_players_panel(self, screen):
        pygame.draw.rect(screen, COL_PANEL, self._players_rect, border_radius=10)
        pygame.draw.rect(screen, COL_BORDER, self._players_rect, 1, border_radius=10)

        title = self.font_h2.render("Jogadores", True, COL_ACCENT)
        screen.blit(title, (self._players_rect.x + 14, self._players_rect.y + 10))

        pygame.draw.line(
            screen, COL_DIVIDER,
            (self._players_rect.x + 10, self._players_rect.y + 36),
            (self._players_rect.right - 10, self._players_rect.y + 36),
            1,
        )

        y = self._players_rect.y + 48
        my_uuid = self._my_uuid()

        for u, p in self.raid_players.items():
            is_me = (u == my_uuid)
            name = p["name"] + (" (você)" if is_me else "")
            color = COL_SUCCESS if is_me else COL_TEXT
            name_s = self.font_small.render(name, True, color)
            screen.blit(name_s, (self._players_rect.x + 14, y))

            status_y = y + 20
            if p.get("ready"):
                status = "PRONTO"
                scolor = COL_SUCCESS
            elif p.get("submitted"):
                status = "Time enviado"
                scolor = COL_INFO
            else:
                status = "Aguardando..."
                scolor = COL_TEXT_MUTED

            status_s = self.font_tiny.render(status, True, scolor)
            screen.blit(status_s, (self._players_rect.x + 24, status_y))

            if p.get("assigned_count", 0) > 0:
                cnt = self.font_tiny.render(
                    f"{p['assigned_count']} pokémon(s)", True, COL_ACCENT
                )
                screen.blit(cnt, (self._players_rect.x + 140, status_y))

            # Quota na fase de seleção
            if self.state == self.ST_SELECTING and u in self._quotas:
                q = self._quotas[u]
                q_s = self.font_tiny.render(f"até {q}", True, COL_TEXT_DIM)
                screen.blit(q_s, (self._players_rect.x + 200, status_y))

            y += 44

        if len(self.raid_players) < self.MIN_PLAYERS:
            warn = self.font_tiny.render(
                "Aguardando mais jogadores...", True, COL_WARN
            )
            screen.blit(warn, (self._players_rect.x + 14,
                               self._players_rect.bottom - 24))

    # ---------- Painel direito por estado ----------
    def _render_waiting(self, screen):
        pygame.draw.rect(screen, COL_PANEL, self._right_rect, border_radius=10)
        pygame.draw.rect(screen, COL_BORDER, self._right_rect, 1, border_radius=10)

        cx = self._right_rect.centerx
        cy = self._right_rect.centery

        t = self.font_h1.render("Sala de Espera", True, COL_ACCENT)
        screen.blit(t, t.get_rect(center=(cx, cy - 60)))

        n = len(self.raid_players)
        info = f"{n} jogador(es) conectado(s)"
        s = self.font.render(info, True, COL_TEXT_DIM)
        screen.blit(s, s.get_rect(center=(cx, cy - 20)))

        if n < self.MIN_PLAYERS:
            hint = self.font_small.render(
                f"Precisa de pelo menos {self.MIN_PLAYERS} para começar.",
                True, COL_WARN,
            )
        else:
            hint = self.font_small.render(
                "Host pode iniciar a seleção." if self.is_host
                else "Aguardando o host iniciar...",
                True, COL_SUCCESS if self.is_host else COL_TEXT_DIM,
            )
        screen.blit(hint, hint.get_rect(center=(cx, cy + 20)))

    def _render_selection(self, screen):
        pygame.draw.rect(screen, COL_PANEL, self._right_rect, border_radius=10)
        pygame.draw.rect(screen, COL_BORDER, self._right_rect, 1, border_radius=10)

        self._detail_buttons = []

        quota = self._my_quota()
        header = self.font_h2.render(
            f"Escolha até {quota}  ({len(self._my_selection)}/{quota})",
            True, COL_ACCENT,
        )
        screen.blit(header, (self._list_rect.x + 4, self._list_rect.y + 10))

        if not self._all_entries:
            empty = self.font.render("Nenhum Pokémon disponível.", True, COL_TEXT_MUTED)
            screen.blit(empty, empty.get_rect(center=self._list_rect.center))
            return

        mouse = pygame.mouse.get_pos()
        x0, y0 = self._list_items_origin()

        selected_ids = {e.unique_id for e in self._my_selection}

        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self._all_entries):
                break
            entry = self._all_entries[idx]
            rect = pygame.Rect(
                x0, y0 + i * self._item_height,
                self._list_items_w, self._item_height - 4,
            )
            self._draw_entry(screen, rect, entry, entry.unique_id in selected_ids, mouse)

        total = len(self._all_entries)
        if total > self.visible_items:
            track_h = self.visible_items * self._item_height
            track_x = self._list_rect.right - 8
            track_y = y0
            track = pygame.Rect(track_x, track_y, 6, track_h)
            pygame.draw.rect(screen, COL_PANEL_DARK, track, border_radius=3)
            ratio = self.visible_items / float(total)
            thumb_h = max(20, int(track_h * ratio))
            max_off = total - self.visible_items
            off_ratio = self.scroll_offset / float(max_off) if max_off else 0
            thumb_y = track_y + int((track_h - thumb_h) * off_ratio)
            thumb = pygame.Rect(track_x, thumb_y, 6, thumb_h)
            pygame.draw.rect(screen, COL_BORDER_HL, thumb, border_radius=3)

    def _draw_entry(self, screen, rect, entry, selected, mouse):
        hover = rect.collidepoint(mouse)
        if selected:
            bg = COL_ITEM_SEL_HOVER if hover else COL_ITEM_SEL
            border = COL_SUCCESS
        elif hover:
            bg = COL_ITEM_HOVER
            border = COL_BORDER_HL
        else:
            bg = COL_ITEM
            border = COL_BORDER

        pygame.draw.rect(screen, bg, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 1, border_radius=8)

        # Portrait
        psize = 44
        px = rect.x + 8
        py = rect.y + (rect.height - psize) // 2
        portrait = self.pokedex.get_portrait(entry.id, "normal", entry.is_shiny)
        bg_rect = pygame.Rect(px - 2, py - 2, psize + 4, psize + 4)
        pygame.draw.rect(screen, COL_PANEL_DARK, bg_rect, border_radius=6)
        pygame.draw.rect(
            screen, COL_ACCENT if entry.is_shiny else COL_BORDER,
            bg_rect, 1 if not entry.is_shiny else 2, border_radius=6,
        )
        if portrait:
            portrait = pygame.transform.smoothscale(portrait, (psize, psize))
            screen.blit(portrait, (px, py))

        # Botão DETALHES (à direita)
        detail_btn_w = 66
        detail_btn_h = 20
        detail_btn = pygame.Rect(
            rect.right - detail_btn_w - 6,
            rect.y + (rect.height - detail_btn_h) // 2,
            detail_btn_w, detail_btn_h,
        )

        # Área de info: da direita do portrait até a esquerda do DETALHES
        info_x = px + psize + 12
        info_right = detail_btn.left - 8
        info_w = max(20, info_right - info_x)

        # Nome
        name_color = COL_ACCENT if entry.is_shiny else COL_TEXT
        name_s = self.font_h2.render(entry.name, True, name_color)
        if name_s.get_width() > info_w:
            # trunca
            trimmed = entry.name
            while trimmed and self.font_h2.size(trimmed + "...")[0] > info_w:
                trimmed = trimmed[:-1]
            name_s = self.font_h2.render(trimmed + "...", True, name_color)
        screen.blit(name_s, (info_x, rect.y + 8))

        # Nível + badge
        lvl_s = self.font_small.render(f"Nível {entry.level}", True, COL_TEXT_DIM)
        screen.blit(lvl_s, (info_x, rect.y + 30))

        badge = "TIME" if entry.is_in_team else "BOX"
        bcolor = COL_SUCCESS if entry.is_in_team else COL_TEXT_MUTED
        b_s = self.font_tiny.render(badge, True, bcolor)
        badge_x = info_x + lvl_s.get_width() + 8
        if badge_x + b_s.get_width() <= info_right:
            screen.blit(b_s, (badge_x, rect.y + 32))

        # Botão DETALHES
        hover_d = detail_btn.collidepoint(mouse)
        d_color = COL_BTN_INFO_H if hover_d else COL_BTN_INFO
        pygame.draw.rect(screen, d_color, detail_btn, border_radius=4)
        pygame.draw.rect(screen, COL_BORDER_HL, detail_btn, 1, border_radius=4)
        d_txt = self.font_tiny.render("DETALHES", True, COL_TEXT)
        screen.blit(d_txt, d_txt.get_rect(center=detail_btn.center))

        # Check de seleção (à esquerda do DETALHES)
        if selected:
            check_x = detail_btn.left - 16
            check_y = rect.centery
            pygame.draw.circle(screen, COL_SUCCESS, (check_x, check_y), 10)
            pygame.draw.lines(
                screen, COL_BG, False,
                [(check_x - 4, check_y), (check_x - 1, check_y + 3),
                 (check_x + 4, check_y - 4)],
                2,
            )

        self._detail_buttons.append((detail_btn, entry.unique_id))

    def _render_ready(self, screen):
        pygame.draw.rect(screen, COL_PANEL, self._right_rect, border_radius=10)
        pygame.draw.rect(screen, COL_BORDER, self._right_rect, 1, border_radius=10)

        header = self.font_h2.render(
            "Time da Raid (6 pokémons no total)", True, COL_ACCENT
        )
        screen.blit(header, (self._list_rect.x + 4, self._list_rect.y + 10))

        if not self.final_team:
            wait = self.font.render(
                "Aguardando todos enviarem o time...", True, COL_TEXT_DIM
            )
            screen.blit(wait, wait.get_rect(center=self._list_rect.center))
            return

        x0, y0 = self._list_items_origin()
        mouse = pygame.mouse.get_pos()

        for i, entry in enumerate(self.final_team[:self.visible_items]):
            poke = entry["pokemon"]
            owner = entry["owner_name"]
            rect = pygame.Rect(
                x0, y0 + i * self._item_height,
                self._list_items_w, self._item_height - 4,
            )
            self._draw_final_entry(screen, rect, poke, owner, mouse)

    def _draw_final_entry(self, screen, rect, poke, owner_name, mouse):
        pygame.draw.rect(screen, COL_ITEM, rect, border_radius=8)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=8)

        psize = 44
        px = rect.x + 8
        py = rect.y + (rect.height - psize) // 2
        portrait = self.pokedex.get_portrait(
            poke.get("id", 0), "normal", poke.get("is_shiny", False)
        )
        bg_rect = pygame.Rect(px - 2, py - 2, psize + 4, psize + 4)
        pygame.draw.rect(screen, COL_PANEL_DARK, bg_rect, border_radius=6)
        pygame.draw.rect(
            screen, COL_ACCENT if poke.get("is_shiny") else COL_BORDER,
            bg_rect, 1, border_radius=6,
        )
        if portrait:
            portrait = pygame.transform.smoothscale(portrait, (psize, psize))
            screen.blit(portrait, (px, py))

        name_color = COL_ACCENT if poke.get("is_shiny") else COL_TEXT
        name_s = self.font_h2.render(poke.get("name", "?"), True, name_color)
        screen.blit(name_s, (rect.x + 62, rect.y + 8))

        lvl_s = self.font_small.render(
            f"Nível {poke.get('level', 0)}", True, COL_TEXT_DIM
        )
        screen.blit(lvl_s, (rect.x + 62, rect.y + 30))

        owner_s = self.font_tiny.render(f"Dono: {owner_name}", True, COL_INFO)
        screen.blit(owner_s, (rect.right - owner_s.get_width() - 12, rect.y + 10))

    def _render_countdown(self, screen):
        pygame.draw.rect(screen, COL_PANEL, self._right_rect, border_radius=10)
        pygame.draw.rect(screen, COL_ACCENT, self._right_rect, 2, border_radius=10)

        cx = self._right_rect.centerx
        cy = self._right_rect.centery

        t = self.font_title.render("PREPARE-SE!", True, COL_ACCENT)
        screen.blit(t, t.get_rect(center=(cx, cy - 100)))

        num = self.countdown_value
        scale = 1.0
        if self._countdown_started:
            frac = self.countdown_timer % 1.0
            scale = 1.0 + 0.35 * math.sin(math.pi * frac)

        num_font = pygame.font.Font(None, int(160 * scale))
        num_s = num_font.render(str(num), True, COL_DANGER)
        screen.blit(num_s, num_s.get_rect(center=(cx, cy)))

        sub = self.font.render("Jogo começando em...", True, COL_TEXT_DIM)
        screen.blit(sub, sub.get_rect(center=(cx, cy + 100)))

    def _render_started(self, screen):
        pygame.draw.rect(screen, COL_PANEL, self._right_rect, border_radius=10)
        pygame.draw.rect(screen, COL_SUCCESS, self._right_rect, 2, border_radius=10)
        cx = self._right_rect.centerx
        cy = self._right_rect.centery

        t = self.font_title.render("RAID INICIADA!", True, COL_SUCCESS)
        screen.blit(t, t.get_rect(center=(cx, cy - 20)))
        s = self.font.render(
            "A batalha será implementada em breve.", True, COL_TEXT_DIM
        )
        screen.blit(s, s.get_rect(center=(cx, cy + 30)))

    def _render_cancelled(self, screen):
        pygame.draw.rect(screen, COL_PANEL, self._right_rect, border_radius=10)
        pygame.draw.rect(screen, COL_DANGER, self._right_rect, 2, border_radius=10)
        cx = self._right_rect.centerx
        cy = self._right_rect.centery
        t = self.font_title.render("RAID CANCELADA", True, COL_DANGER)
        screen.blit(t, t.get_rect(center=(cx, cy)))

    # ---------- Botão de ação ----------
    def _render_action_button(self, screen):
        label = None
        kind = "primary"
        enabled = True

        if self.state == self.ST_WAITING:
            if self.is_host:
                label = "Iniciar Seleção"
                kind = "success"
                enabled = len(self.raid_players) >= self.MIN_PLAYERS
            else:
                label = "Aguardando host..."
                kind = "disabled"
                enabled = False
        elif self.state == self.ST_SELECTING:
            quota = self._my_quota()
            label = f"Enviar Time ({len(self._my_selection)}/{quota})"
            kind = "success" if len(self._my_selection) > 0 else "disabled"
            enabled = len(self._my_selection) > 0
        elif self.state == self.ST_READY:
            my = self.raid_players.get(self._my_uuid(), {})
            if my.get("ready"):
                label = "Cancelar Pronto"
                kind = "danger"
            else:
                label = "PRONTO!"
                kind = "success"
        elif self.state == self.ST_COUNTDOWN:
            label = "Aguarde..."
            kind = "disabled"
            enabled = False
        elif self.state in (self.ST_STARTED, self.ST_CANCELLED):
            label = "Voltar ao Lobby"
            kind = "primary"

        if label is None:
            return

        if not enabled:
            kind = "disabled"

        self._draw_button(screen, self.action_btn, label, kind=kind)

    # ---------- Botão genérico ----------
    def _draw_button(self, screen, rect, text, kind="primary"):
        palette = {
            "primary":  (COL_BTN_PRIMARY, COL_BTN_PRIMARY_H),
            "success":  (COL_BTN_SUCCESS, COL_BTN_SUCCESS_H),
            "danger":   (COL_BTN_DANGER,  COL_BTN_DANGER_H),
            "info":     (COL_BTN_INFO,    COL_BTN_INFO_H),
            "disabled": (COL_BTN_DISABLED, COL_BTN_DISABLED),
        }
        base, hover = palette.get(kind, palette["primary"])
        mouse = pygame.mouse.get_pos()
        is_hover = rect.collidepoint(mouse) and kind != "disabled"
        bg = hover if is_hover else base

        pygame.draw.rect(screen, bg, rect, border_radius=10)
        border = COL_BORDER_HL if is_hover else COL_BORDER
        pygame.draw.rect(screen, border, rect, 1, border_radius=10)

        color = COL_TEXT if kind != "disabled" else COL_TEXT_MUTED
        s = self.font_btn.render(text, True, color)
        screen.blit(s, s.get_rect(center=rect.center))

    # =========================================================
    # Ciclo de vida
    # =========================================================
    def on_enter(self):
        pass

    def on_exit(self):
        pass