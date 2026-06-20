import os

import requests as http


BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TG = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""


def tg(method: str, payload: dict) -> None:
    if not TG:
        return
    try:
        http.post(f"{TG}/{method}", json=payload, timeout=15)
    except Exception:
        return


def send(chat_id: int, text: str) -> None:
    tg(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )


def typing(chat_id: int) -> None:
    tg("sendChatAction", {"chat_id": chat_id, "action": "typing"})


def configure_public_commands() -> None:
    commands = [
        {"command": "start", "description": "Show welcome message"},
        {"command": "help", "description": "Show help"},
        {"command": "me", "description": "Show your account"},
    ]
    tg("setMyCommands", {"commands": commands})
