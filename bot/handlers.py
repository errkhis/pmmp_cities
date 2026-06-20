import logging
import os
import re
from typing import Any

from company_city import lookup_company_cities
from database import (
    DatabaseNotConfigured,
    QuotaExceeded,
    can_create_city_request,
    count_users,
    grant_premium,
    record_city_request,
    set_free,
    upsert_telegram_user,
)
from scraper import build_consultation_url, consultation_meta_from_url, scrape_consultation

from .messages import (
    account_status_message,
    build_cities_message,
    database_error_message,
    esc,
    help_message,
    subscription_limit_message,
    welcome_message,
)
from .telegram import configure_public_commands, send, typing


log = logging.getLogger(__name__)

TELEGRAM_ADMIN_ID = os.environ.get("TELEGRAM_ADMIN_ID", "").strip()
TELEGRAM_ADMIN_USERNAME = os.environ.get("TELEGRAM_ADMIN_USERNAME", "").strip().lstrip("@")


def process_update(update: dict[str, Any]) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not text:
        return

    if handle_admin_command(chat_id, text, message):
        return
    if text.startswith("/start"):
        handle_start(chat_id, message)
        return
    if text.startswith("/help"):
        send(chat_id, help_message(TELEGRAM_ADMIN_USERNAME, is_admin(message)))
        return
    if text.startswith("/me") or text.startswith("/subscription"):
        handle_account(chat_id, message)
        return

    url = extract_url(message)
    if not url:
        if not text.startswith("/"):
            send(chat_id, "⚠️ Send a valid <b>marchespublics.gov.ma</b> consultation link.")
        return
    handle_city_request(chat_id, message, url)


def handle_start(chat_id: int, message: dict[str, Any]) -> None:
    user = None
    try:
        user = upsert_telegram_user(message.get("from") or {"id": chat_id})
    except DatabaseNotConfigured:
        log.warning("Database not configured during /start")
    except Exception:
        log.exception("Failed to upsert user during /start")
    try:
        configure_public_commands()
    except Exception:
        log.exception("Failed to configure Telegram commands")
    send(chat_id, welcome_message(user, TELEGRAM_ADMIN_USERNAME))


def handle_account(chat_id: int, message: dict[str, Any]) -> None:
    sender = message.get("from") or {}
    if not sender.get("id"):
        send(chat_id, "❌ Unable to identify your Telegram user id.")
        return
    try:
        user = upsert_telegram_user(sender)
        send(chat_id, account_status_message(user, TELEGRAM_ADMIN_USERNAME))
    except DatabaseNotConfigured:
        send(chat_id, database_error_message())
    except Exception as exc:
        log.exception("Account command error")
        send(chat_id, f"❌ <b>Error:</b> {esc(str(exc)[:400])}")


def handle_admin_command(chat_id: int, text: str, message: dict[str, Any]) -> bool:
    admin_commands = ("/premium", "/free", "/users")
    if not text.startswith(admin_commands):
        return False
    if not is_admin(message):
        send(chat_id, "⛔ This command is reserved for the administrator.")
        return True
    if text.startswith("/users"):
        try:
            send(chat_id, f"👥 Registered users: <b>{count_users()}</b>")
        except DatabaseNotConfigured:
            send(chat_id, database_error_message())
        except Exception as exc:
            log.exception("Users command error")
            send(chat_id, f"❌ <b>Error:</b> {esc(str(exc)[:400])}")
        return True

    parts = text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        send(chat_id, "Format: <code>/premium TELEGRAM_ID [years]</code> or <code>/free TELEGRAM_ID</code>")
        return True
    telegram_id = int(parts[1])
    admin_id = int((message.get("from") or {}).get("id"))
    try:
        if text.startswith("/premium"):
            years = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            user = grant_premium(telegram_id, years, admin_telegram_id=admin_id)
            send(
                chat_id,
                "✅ Premium activated\n"
                f"User ID: <code>{user.telegram_id}</code>\n"
                f"Valid until: <b>{user.premium_expires_at.strftime('%Y-%m-%d')}</b>",
            )
        else:
            user = set_free(telegram_id, admin_telegram_id=admin_id)
            send(chat_id, f"✅ Free plan restored\nUser ID: <code>{user.telegram_id}</code>")
    except DatabaseNotConfigured:
        send(chat_id, database_error_message())
    except Exception as exc:
        log.exception("Admin command error")
        send(chat_id, f"❌ <b>Error:</b> {esc(str(exc)[:400])}")
    return True


def handle_city_request(chat_id: int, message: dict[str, Any], url: str) -> None:
    sender = message.get("from") or {"id": chat_id}
    try:
        user = upsert_telegram_user(sender)
        if not can_create_city_request(user):
            send(chat_id, subscription_limit_message(TELEGRAM_ADMIN_USERNAME))
            return
    except DatabaseNotConfigured:
        send(chat_id, database_error_message())
        return
    except Exception as exc:
        log.exception("Database pre-check error")
        send(chat_id, f"❌ <b>Database error:</b> {esc(str(exc)[:400])}")
        return

    typing(chat_id)
    send(chat_id, "⏳ Looking up company cities...")

    reference, org = consultation_meta_from_url(url)
    try:
        consultation = scrape_consultation(url)
        lots = consultation.lots or [consultation]
        names: list[str] = []
        for lot in lots:
            names.extend(b.name for b in lot.bidders if b.name)
        cities = lookup_company_cities(names)
        response_text = build_cities_message(consultation.reference, consultation.object, cities)
        updated_user = record_city_request(
            user.telegram_id,
            consultation_reference=reference,
            org_acronyme=org or "",
            consultation_url=build_consultation_url(reference, org or "") if reference else url,
            consultation_object=consultation.object,
            success=True,
            quota_consumed=True,
            company_count=len(cities),
            error_message=None,
            result_snapshot=_snapshot(consultation.reference, consultation.object, cities),
        )
        if not updated_user.is_premium:
            response_text += (
                "\n\n"
                f"🧾 Free usage: {updated_user.free_city_requests_used}/5"
                f" | remaining {updated_user.remaining_free_requests}"
            )
        send(chat_id, response_text)
    except QuotaExceeded:
        send(chat_id, subscription_limit_message(TELEGRAM_ADMIN_USERNAME))
    except Exception as exc:
        log.exception("City lookup error")
        try:
            record_city_request(
                user.telegram_id,
                consultation_reference=reference,
                org_acronyme=org or "",
                consultation_url=url,
                consultation_object=None,
                success=False,
                quota_consumed=False,
                company_count=0,
                error_message=str(exc),
                result_snapshot={},
            )
        except Exception:
            log.exception("Failed to persist failed request audit")
        send(chat_id, f"❌ <b>Error:</b> {esc(str(exc)[:400])}")


def extract_url(message: dict[str, Any]) -> str | None:
    text = message.get("text") or message.get("caption") or ""
    for entity in message.get("entities") or []:
        if entity.get("type") == "text_link":
            url = entity.get("url", "")
            if "marchespublics.gov.ma" in url:
                return url
    for match in re.findall(r"https?://[^\s]+", text):
        if "marchespublics.gov.ma" in match:
            return match.rstrip(".,)")
    return None


def is_admin(message: dict[str, Any]) -> bool:
    if not TELEGRAM_ADMIN_ID:
        return False
    sender = message.get("from") or {}
    return str(sender.get("id", "")) == TELEGRAM_ADMIN_ID


def _snapshot(reference: str, consultation_object: str, cities) -> dict[str, Any]:
    return {
        "reference": reference,
        "object": consultation_object,
        "cities": [
            {
                "name": item.name,
                "city": item.city,
                "matched_name": item.matched_name,
            }
            for item in cities
        ],
    }
