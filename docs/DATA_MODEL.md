# Data Model (MVP)

## User
- id (uuid)
- name
- email
- birth_date
- birth_time
- birth_place
- birth_latitude (optional)
- birth_longitude (optional)
- birth_timezone (optional)
- gender
- interested_in
- goals (romance, friendship)
- created_at

## AstroVector
- user_id
- vector (float array)
- schema_version
- created_at

## Match
- user_id
- candidate_id
- mode (romance/friendship)
- score (0-100)
- highlights (json)
- created_at

## Message
- id
- match_id
- sender_id
- body
- created_at
