# src/network/protocol.py

MSG_TYPES = {
    "HANDSHAKE": "handshake",
    "PLAYER_INFO": "player_info",
    "TRADE_OFFER": "trade_offer",
    "TRADE_CANCEL": "trade_cancel",
    "TRADE_ACCEPT": "trade_accept",
    "TRADE_DECLINE": "trade_decline",
    "TRADE_COMPLETE": "trade_complete",
    "PLAYER_LIST": "player_list",
    "TRADE_REQUEST": "trade_request",
    "TRADE_RESPONSE": "trade_response",
    "CHAT": "chat",
    "ERROR": "error",
    "DISCONNECT": "disconnect",
    "PING": "ping",
    "PONG": "pong",
    "LOBBY_INFO": "lobby_info",
    "GAME_MODE_SELECT": "game_mode_select"
}

def create_message(msg_type, payload=None):
    return {"type": msg_type, "payload": payload or {}}