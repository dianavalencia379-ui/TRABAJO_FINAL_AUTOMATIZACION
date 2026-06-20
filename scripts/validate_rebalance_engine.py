from __future__ import annotations

from pprint import pprint

from data_layer.db import initialize_database
from domain.rebalance_engine import build_rebalance_advisor_snapshot


USER_EMAILS = (
    "diana@example.com",
    "antonio@example.com",
    "jose@example.com",
)


def main() -> int:
    """Ejecuta una validación manual del advisor de rebalanceo."""
    db_result = initialize_database(reset=False)
    print("Base lista:", db_result["is_functional"])

    for user_email in USER_EMAILS:
        snapshot = build_rebalance_advisor_snapshot(
            user_email=user_email,
            prefer_live_data=False,
            lookback_days=180,
            rebalance_threshold=3,
        )
        print(f"\n=== Rebalance advisor {user_email} ===")
        pprint(snapshot["summary"])
        pprint(snapshot["advisor_table"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
