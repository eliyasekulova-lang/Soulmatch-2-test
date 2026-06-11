import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
API_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if API_ROOT not in sys.path:
    sys.path.append(API_ROOT)

from app.database import SessionLocal, init_db
from app.seed import seed_demo_candidates


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        inserted = seed_demo_candidates(db)
        print(f"seed_complete inserted={inserted}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
