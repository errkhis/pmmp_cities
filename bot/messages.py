from company_city import CompanyCity
from database import FREE_CITY_LIMIT, User


def esc(value) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_date(value):
    return value.strftime("%Y-%m-%d") if value else "—"


def admin_contact(admin_username: str) -> str:
    return f"@{admin_username.lstrip('@')}" if admin_username else "the administrator"


def welcome_message(user: User | None, admin_username: str) -> str:
    lines = [
        "🏙️ <b>PMMP Cities Bot</b>",
        "",
        "Send one <b>marchespublics.gov.ma</b> consultation link.",
        "The bot returns the city for each company found in that consultation.",
        "",
        f"Free plan: <b>{FREE_CITY_LIMIT}</b> lifetime city lookups.",
        f"Premium plan: <b>unlimited</b> lookups after admin activation via <b>{esc(admin_contact(admin_username))}</b>.",
    ]
    if user:
        lines.extend(["", account_status_message(user, admin_username)])
    return "\n".join(lines)


def help_message(admin_username: str, is_admin: bool) -> str:
    lines = [
        "📖 <b>Commands</b>",
        "/start - Show welcome message",
        "/help - Show commands",
        "/me - Show your plan and usage",
        "/subscription - Alias of /me",
        "",
        "Send a consultation link directly to get company cities.",
        "",
        f"Premium activation contact: <b>{esc(admin_contact(admin_username))}</b>",
    ]
    if is_admin:
        lines.extend(["", "<b>Admin</b>", "/premium TELEGRAM_ID [years]", "/free TELEGRAM_ID", "/users"])
    return "\n".join(lines)


def account_status_message(user: User, admin_username: str) -> str:
    if user.is_premium:
        return (
            "👤 <b>Your account</b>\n"
            "Plan: <b>Premium</b>\n"
            f"Valid until: <b>{fmt_date(user.premium_expires_at)}</b>\n"
            "City lookups: <b>unlimited</b>"
        )
    return (
        "👤 <b>Your account</b>\n"
        "Plan: <b>Free</b>\n"
        f"Used: <b>{user.free_city_requests_used}/{FREE_CITY_LIMIT}</b>\n"
        f"Remaining: <b>{user.remaining_free_requests}</b>\n"
        f"To activate Premium, contact <b>{esc(admin_contact(admin_username))}</b>."
    )


def subscription_limit_message(admin_username: str) -> str:
    return (
        "🔒 <b>Free plan limit reached</b>\n\n"
        f"The free plan includes <b>{FREE_CITY_LIMIT}</b> lifetime city lookups.\n"
        f"To continue, contact <b>{esc(admin_contact(admin_username))}</b> to activate Premium."
    )


def database_error_message() -> str:
    return (
        "❌ <b>Database is not configured.</b>\n"
        "Add `DATABASE_URL` or `POSTGRES_URL` to your deployment environment."
    )


def build_cities_message(reference: str, consultation_object: str | None, cities: list[CompanyCity]) -> str:
    if not cities:
        return "❌ No companies were found in this consultation."

    lines = [f"Consultation: <b>{esc(reference)}</b>"]
    if consultation_object:
        lines.append(f"Object: <b>{esc(consultation_object)}</b>")
    lines.extend(["", "<b>Company cities:</b>"])
    for item in cities:
        city = esc(item.city or "City not found")
        lines.append(f"- {esc(item.name)}: <b>{city}</b>")
    return "\n".join(lines)
