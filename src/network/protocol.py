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
    # =================
    "ERROR": "error",
    "DISCONNECT": "disconnect",
}


def create_message(msg_type, payload=None):
    return {"type": msg_type, "payload": payload or {}}