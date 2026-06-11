# UX Flow (MVP)

## Onboarding
1. Welcome: pilot city message (Toronto) and global support statement
2. Profile basics: name, email, password (JWT signup/login)
3. Birth data: date, time, place search
4. Place picker: select geocoded result or adjust map pin and store latitude/longitude/timezone
5. Goals: romance, friendship, or both
6. Consent: load legal summaries and accept privacy + sensitive data consent
7. Submit onboarding: create user and generate AstroVector via API
8. Event tracking: onboarding and mode-change analytics sent to `/events`

## Home
- Mode toggle: Romance / Friendship
- API-ranked match deck from `/matches`
- Shareable compatibility card CTA

## Match Card
- Compatibility score (0-100)
- Top 3 highlights (elements, aspects, life path)
- Button: View details (premium)
- Button: Chat

## Chat
- Basic text chat
- Icebreaker prompt suggestions

## Premium
- Synastry report
- Timing insights
- Top 1% visibility (boost)
