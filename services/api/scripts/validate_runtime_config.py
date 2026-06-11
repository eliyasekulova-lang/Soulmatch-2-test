from app.settings import get_settings


def main() -> None:
    settings = get_settings()
    print(
        {
            "ok": True,
            "app_env": settings.app_env,
            "cors_allowed_origins": settings.cors_allowed_origins,
            "sentry_environment": settings.sentry_environment,
            "min_signup_age_years": settings.min_signup_age_years,
        }
    )


if __name__ == "__main__":
    main()
