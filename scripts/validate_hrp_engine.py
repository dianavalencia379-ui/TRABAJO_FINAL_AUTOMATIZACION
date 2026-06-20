from __future__ import annotations

from pprint import pprint

from data_layer.db import initialize_database
from domain.hrp_engine import build_hrp_portfolio_snapshot


USER_EMAILS = (
    "dianavalencia379@gmail.com",
    "antonio@example.com",
    "jose@example.com",
)


def main() -> int:
    """Ejecuta una validación manual del snapshot HRP para varios usuarios."""
    db_result = initialize_database(reset=False)
    print("Base lista:", db_result["is_functional"])

    for user_email in USER_EMAILS:
        snapshot = build_hrp_portfolio_snapshot(
            user_email=user_email,
            prefer_live_data=False,
            lookback_days=180,
        )
        print(f"\n=== HRP {user_email} ===")
        pprint(snapshot["diagnostics"])
        pprint(snapshot["weights_table"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
