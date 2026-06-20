import unittest
from datetime import datetime, timedelta, timezone

from bot.messages import account_status_message, build_cities_message, subscription_limit_message
from company_city import CompanyCity
from database import User


class MessageTests(unittest.TestCase):
    def test_subscription_limit_mentions_admin(self):
        text = subscription_limit_message("cities_admin")
        self.assertIn("@cities_admin", text)
        self.assertIn("5", text)

    def test_account_message_for_premium(self):
        user = User(
            telegram_id=1,
            username="demo",
            first_name="Demo",
            plan="premium",
            premium_expires_at=datetime.now(timezone.utc) + timedelta(days=3),
            free_city_requests_used=5,
        )
        text = account_status_message(user, "cities_admin")
        self.assertIn("Premium", text)
        self.assertIn("unlimited", text)

    def test_build_cities_message_lists_all_companies(self):
        text = build_cities_message(
            "REF-1",
            "Object",
            [CompanyCity(name="Alpha", city="Safi"), CompanyCity(name="Beta", city=None)],
        )
        self.assertIn("Consultation: <b>REF-1</b>", text)
        self.assertIn("- Alpha: <b>Safi</b>", text)
        self.assertIn("- Beta: <b>City not found</b>", text)


if __name__ == "__main__":
    unittest.main()
