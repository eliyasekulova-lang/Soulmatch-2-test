from app.database import SessionLocal
from app.domains.legal import seed_legal_documents


def main():
    with SessionLocal() as db:
        seed_legal_documents(db)
    print("legal_documents_seeded")


if __name__ == "__main__":
    main()
