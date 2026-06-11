# SoulMatch Attorney Review Packet

Status: Internal draft for counsel review.

## Purpose
This folder contains draft legal documents aligned to the current SoulMatch codebase so counsel can review what exists now, identify missing clauses, and recommend jurisdiction-specific revisions before launch.

## Included Drafts

- `legal/privacy-policy.md`
- `legal/terms-of-service.md`
- `legal/acceptable-use-policy.md`
- `legal/trust-and-safety.md`
- `legal/data-retention.md`
- `legal/ai-disclosure.md`
- `legal/consent-notice.md`
- `legal/minors-and-age-policy.md`

## Product Facts Reflected in These Drafts

- Mobile-first dating and friendship discovery app.
- User onboarding currently collects name, email, password, date of birth, birth time, birth place, location coordinates/timezone, goals, and matching preference.
- Matching can use psychological, behavioral, and astrology-enhanced inputs.
- Backend supports messaging, moderation reports, appeals, media attachment objects, analytics events, behavior profiles, trust-and-safety risk scoring, consent logging, and user-rights requests.
- Minimum configured sign-up age is 18.
- Current seeded vendor references in the compliance layer are AWS and Sentry.
- Place lookup uses OpenStreetMap Nominatim when live search is available.
- Current retention defaults visible in code are 1095 days for messages, 2555 days for audit logs, 7 days for rights exports, and 2 days for temporary media uploads.

## Main Counsel Review Items

- Confirm the correct contracting entity name, address, and launch jurisdictions.
- Confirm whether Ontario, Canada should remain the governing-law venue.
- Finalize whether arbitration, class-action waiver, limitation caps, and consumer carve-outs are wanted.
- Confirm how to characterize birth data and astrology-enhanced matching under privacy law.
- Confirm whether profiling and automated-decision disclosures need stronger language or user rights.
- Confirm whether the current consent flow is sufficient for sensitive-data processing.
- Confirm cross-border transfer disclosures and whether a public subprocessor list is needed.
- Confirm retention periods and backup-deletion wording.
- Confirm app-store-compliant account deletion language and whether the current product surface is enough.
- Finalize payment/subscription terms before any premium feature launches.
- Confirm child-safety, reporting, and law-enforcement response language before public release.

## Source Files Reviewed For These Drafts

- `apps/mobile/App.js`
- `services/api/app/domains/profile.py`
- `services/api/app/domains/compliance.py`
- `services/api/app/models.py`
- `docs/ARCHITECTURE.md`
- `docs/PRD.md`
- `docs/compliance/APP_STORE_COMPLIANCE.md`

## Drafting Notes

- These documents are not legal advice.
- They are intentionally explicit about unresolved items rather than hiding them.
- Bracketed placeholders should be completed before external use.
