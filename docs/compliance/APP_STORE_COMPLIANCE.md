# App Store / Play Compliance Artifacts (Attorney Review Required)

## Required Artifacts
- In-app account deletion entry point.
- Public web account deletion URL.
- Public policy URLs (privacy, terms, safety).
- Support contact email.

## Runtime Fields
- `APP_SUPPORT_EMAIL`
- `APP_POLICY_BASE_URL`
- `APP_ACCOUNT_DELETE_URL`

## Runtime Endpoint
- `GET /v1/compliance/app-store`

## Platform Notes
- Apple: account deletion must be available in-app and remove records except legally required retention.
- Google Play: deletion request must be available in-app and via web URL.
