# src/network/protocol.py

MSG_TYPES = {
    "HANDSHAKE": "handshake",
    "PLAYER_INFO": "player_info",
    "PLAYER_LIST": "player_list",
    "CHAT_MESSAGE": "chat_message",
    "TRADE_REQUEST": "trade_request",
    "TRADE_RESPONSE": "trade_response",
    "TRADE_OFFER": "trade_offer",
    "TRADE_CANCEL": "trade_cancel",
    "TRADE_ACCEPT": "trade_accept",
    "TRADE_DECLINE": "trade_decline",
    "TRADE_CONFIRM": "trade_confirm",
    "TRADE_COMPLETE": "trade_complete",
    # ===== RAID =====
    "RAID_JOIN": "raid_join",
    "RAID_PLAYER_LIST": "raid_player_list",
    "RAID_START_SELECTION": "raid_start_selection",
    "RAID_TEAM_SUBMIT": "raid_team_submit",
    "RAID_TEAM_UPDATE": "raid_team_update",
    "RAID_PLAYER_READY": "raid_player_ready",
    "RAID_COUNTDOWN": "raid_countdown",
    "RAID_START": "raid_start",
    "RAID_LEAVE": "raid_leave",
    "RAID_CANCEL": "raid_cancel",
    # INRAID
    "RAID_PLACEMENT": "raid_placement",
    "RAID_BOSS_SPAWN": "raid_boss_spawn",
    "RAID_BOSS_SYNC": "raid_boss_sync",
    "RAID_BOSS_DEAD": "raid_boss_dead",
    "RAID_POKEMON_STATE": "raid_pokemon_state",
    "RAID_ATTACK_BOSS": "raid_attack_boss",
    "RAID_POKEMON_DAMAGE": "raid_pokemon_damage",
    "RAID_ALL_DEFEATED": "raid_all_defeated",
    "RAID_WEATHER_CHANGE": "raid_weather_change",
    "RAID_BOSS_ATTACK": "raid_boss_attack",
    "RAID_POKEMON_ATTACK": "raid_pokemon_attack",
    "RAID_RETURN_LOBBY": "raid_return_lobby",
    # ========ARENA PVP=========
    "ARENA_JOIN": "arena_join",
    "ARENA_PLAYER_LIST": "arena_player_list",
    "ARENA_START": "arena_start",
    "ARENA_LEAVE": "arena_leave",
    "ARENA_PLACEMENT": "arena_placement",
    "ARENA_POKEMON_STATE": "arena_pokemon_state",
    "ARENA_POKEMON_ATTACK": "arena_pokemon_attack",
    "ARENA_POKEMON_DAMAGE": "arena_pokemon_damage",
    "ARENA_END": "arena_end",

    # ===== PVP =====
    "PVP_JOIN": "pvp_join",
    "PVP_PLAYER_LIST": "pvp_player_list",
    "PVP_SELECT_FORMAT": "pvp_select_format",
    "PVP_TEAM_SUBMIT": "pvp_team_submit",
    "PVP_READY": "pvp_ready",
    "PVP_START_SELECTION": "pvp_start_selection",
    "PVP_COUNTDOWN": "pvp_countdown",
    "PVP_START": "pvp_start",
    "PVP_LEAVE": "pvp_leave",
    "PVP_CANCEL": "pvp_cancel",
    # IN-BATTLE
    "PVP_PLACEMENT": "pvp_placement",
    "PVP_POKEMON_STATE": "pvp_pokemon_state",
    "PVP_POKEMON_ATTACK": "pvp_pokemon_attack",
    "PVP_POKEMON_DAMAGE": "pvp_pokemon_damage",
    "PVP_END": "pvp_end",
    "PVP_TEAM_ASSIGN": "pvp_team_assign",
    "PVP_WEATHER_CHANGE": "pvp_weather_change",
    "PVP_POKEMON_REMOVE": "pvp_pokemon_remove",

    "ERROR": "error",
    "DISCONNECT": "disconnect",
}


def create_message(msg_type, payload=None):
    return {"type": msg_type, "payload": payload or {}}