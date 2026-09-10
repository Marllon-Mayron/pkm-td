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
    "ERROR": "error",
    "DISCONNECT": "disconnect",
}


def create_message(msg_type, payload=None):
    return {"type": msg_type, "payload": payload or {}}