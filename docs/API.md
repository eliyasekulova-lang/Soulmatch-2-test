# API (MVP)

## Endpoints
- `GET /health`
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /users`
- `POST /vectors/generate`
- `POST /matches`
- `GET /matches/{user_id}`
- `POST /admin/seed-candidates`
- `GET /policies`
- `GET /policies/{id}`
- `GET /policies/{id}/version/{version}`
- `POST /consent`
- `GET /consent/history`
- `POST /user/export`
- `POST /user/delete`
- `POST /user/correct`
- `POST /user/restrict`
- `POST /user/withdraw-consent`
- `POST /report`
- `POST /block`
- `POST /appeal`
- `GET /admin/reports`
- `POST /admin/ban`
- `POST /admin/suspend`
- `GET /audit/user`
- `GET /audit/admin`
- `GET /legal/privacy`
- `GET /legal/terms`
- `POST /events`

## `POST /users` payload
`birth` accepts:
- `date` (`YYYY-MM-DD`)
- `time` (`HH:MM`, 24h)
- `place` (free text label)
- `latitude` (optional float)
- `longitude` (optional float)
- `timezone` (optional IANA tz, e.g. `America/Toronto`)
- `consent_privacy` (required bool)
- `consent_sensitive_data` (required bool)
- `policy_version` (string, default `v1`)

## Notes
- Protected endpoints require `Authorization: Bearer <token>`.
- `/users`, `/vectors/generate`, `/matches`, `/matches/{user_id}` are bound to authenticated `user_id`.
- Auth responses now include access and refresh token expiry timestamps.
- `POST /auth/refresh` rotates refresh tokens and returns a new token pair.
- Birthplace geocoding uses Nominatim; for high-volume usage, pass latitude/longitude/timezone directly.
- `POST /matches` accepts optional `candidate_ids`; if omitted, API ranks against all other users with vectors.
- Match responses include `candidate_name` and `candidate_city` for mobile rendering.
- `/admin/seed-candidates` requires an authenticated user with `role=admin`.
- Admin roles are assigned when signup email matches `ADMIN_EMAILS`.
- User moderation endpoints write append-only audit logs for both user and admin actions.
- `POST /user/delete` queues deletion propagation tasks for `database`, `file_storage`, `backups`, `search_indexes`, and `analytics`.
