# SoulMatch — Full Launch Phase Plan
Last updated: 2026-06-11
Status: Active

---

## Strategic Order Logic

The order is driven by three rules:
1. **Stability before users** — broken app in front of beta users kills trust permanently
2. **Legal before money** — you cannot take payments or handle sensitive data (birth + psychology) without legal cover
3. **Momentum compounds** — each phase hands off directly to the next with no wasted waiting

---

## PHASE 0 — Emergency Stabilization
**Duration: 3–5 days (Jun 11–16)**
**Owner: You + Claude**

The house must be clean before anyone walks in.

| Task | Why |
|---|---|
| Push psychology migration files (`20260424_000026` etc.) | Render deploy is broken without them |
| Redeploy Render, confirm Alembic upgrade succeeds | Staging must pass before beta |
| Rotate the exposed Render Postgres credentials | Security — credentials were pasted in chat |
| Disable mobile EAS CI auto-trigger (add `EXPO_TOKEN` secret or set to manual-only) | Currently throwing CI errors on every push |
| Confirm `/health` returns `ok` on staging | Minimum bar for everything else |

**Exit gate:** Staging API is healthy. No broken migrations. No exposed credentials.

---

## PHASE 1 — Beta Infrastructure
**Duration: 1.5 weeks (Jun 16–27)**
**Owner: You + Claude**

Get the tools in place to actually learn from beta users.

| Task | Why |
|---|---|
| Wire landing page email form to real backend (`/events` or Mailchimp/Loops) | Right now signups go to localStorage — you lose every email |
| Set up PostHog or Mixpanel (free tier) | You need to see where users drop off |
| Set up Sentry (`SENTRY_DSN` env var is empty) | You need to know when things break silently |
| Create a simple beta onboarding email (welcome + what to expect) | Sets expectations, reduces churn |
| Test the full app flow end-to-end on a real iPhone and Android | Catch issues before users do |
| Confirm psychology assessment completes and saves correctly | Core product — must work |

**Exit gate:** Sign up on landing page → receive welcome email → complete full onboarding in app → profile appears in database.

---

## PHASE 2 — Legal + Business Setup
**Duration: 3–4 weeks (Jun 16 – Jul 9) — runs parallel to Phase 1**
**Owner: You (with lawyer for legal docs)**

This phase runs at the same time as Phase 1 because most of it is waiting on lawyers/government.

| Task | Why |
|---|---|
| Register the company | Cannot open a business account, take payments, or sign contracts without it. Ontario Business Registry ($300) or Federal ($200) |
| Open a business bank account | Required before Stripe or any revenue |
| Send legal docs to an attorney for review | `legal/ATTORNEY_REVIEW_PACKET.md` is already prepared — send it now |
| Finalize Privacy Policy and Terms of Service | Required before any public access to user data |
| Confirm PIPEDA compliance (Canadian privacy law) | You collect birth data + psychological profiles — this is sensitive data under Canadian law |
| Add in-app account deletion flow | Required by Apple App Store and Google Play before submission |
| Register SoulMatch trademark (optional but recommended) | Prevents someone else from taking the name before launch |

**Exit gate:** Company exists. Business bank account open. Attorney has reviewed and signed off on legal docs. In-app deletion works.

---

## PHASE 3 — Closed Beta (50 Real Users)
**Duration: 4–5 weeks (Jun 27 – Aug 1)**
**Owner: You**

This is the most important phase. The psychology migration cannot proceed to production until you have 50 real users.

| Task | Why |
|---|---|
| Share landing page link with first wave of beta users | Start collecting real users |
| Target Toronto astrology communities (Reddit, Instagram, Facebook groups) | Your pilot city per the PRD |
| Reach out personally to 20–30 people (friends, friends of friends) | First users always come from personal networks |
| Collect weekly feedback (simple Google Form) | You need to know what's confusing |
| Fix bugs as they come in (dedicate 2 hrs/day to support) | Beta trust is fragile |
| Monitor psychology assessment completion rate | If users drop off here, the core loop is broken |
| Get to 50 real users with completed profiles | Hard requirement for production cutover |

**Exit gate:** 50+ real users with completed psychology assessments. `real_users_v2 >= 50`. `v2_partial_ratio < 0.10`.

---

## PHASE 4 — Production Cutover
**Duration: 2 weeks (Aug 1–15)**
**Owner: You + Claude**

Flip from staging to production. This is the technical graduation from "beta app" to "real app."

| Task | Why |
|---|---|
| Run psychology migration report — confirm all blockers cleared | Cutover gate |
| Run full release gate (`scripts/release_gate.py`) | Already scripted — must pass |
| Run staged rollout check | Already scripted |
| Set production environment variables on Render | New Postgres credentials, proper secrets |
| Point production domain (soulmatch.app) to Render | Users need a real URL |
| Run post-deploy verifier (`scripts/verify_deploy_target.py`) | Confirm production API is healthy |
| Capture release evidence package | Compliance requirement |
| Attorney legal sign-off for production release | Required per your `RELEASE_CONTROL.md` |

**Exit gate:** `promotion_control` outputs `ok: true`. Production API passes all release gates. Domain resolves correctly.

---

## PHASE 5 — Monetization Setup
**Duration: 3 weeks (Aug 1–22) — starts parallel to Phase 4**
**Owner: You + Claude**

You have a billing skeleton already built. Time to activate it.

| Task | Why |
|---|---|
| Create Stripe account (connected to business bank account) | Revenue gateway |
| Integrate Stripe into billing domain (`domains/billing.py`) | Skeleton exists, needs real Stripe keys |
| Define premium features (advanced synastry report, unlimited matches, timing insights) | What do users pay for? |
| Set pricing (suggested: $14.99/month or $99/year for launch) | Anchor on accessible for Gen Z |
| Build paywall screens in mobile app | Block premium features gracefully |
| Test Stripe checkout end-to-end with a test card | Must work before launch |

**Exit gate:** A user can sign up, hit a paywall, pay via Stripe, and access premium content.

---

## PHASE 6 — App Store Submission
**Duration: 4 weeks (Aug 15 – Sep 12)**
**Owner: You**

Apple's review process alone can take 1–3 weeks. Start early.

| Task | Why |
|---|---|
| Create Apple Developer account ($99/year) | Required for iOS distribution |
| Create Google Play Developer account ($25 one-time) | Required for Android distribution |
| Build production app with EAS (`eas build --platform all`) | The binary Apple/Google will review |
| Write App Store listing (screenshots, description, keywords) | Users find you here |
| Set up app privacy labels (Apple requires detailed data declarations) | You collect birth data + psychology — label it all |
| Confirm in-app account deletion works (Apple hard requirement) | Apps are rejected without this |
| Submit to Apple review (expect 1–3 weeks) | Long tail — submit early |
| Submit to Google Play review (expect 1–3 days) | Faster than Apple |

**Exit gate:** Both apps approved and live in App Store and Google Play.

---

## PHASE 7 — Public Launch
**Duration: 2–3 weeks (Sep 12 – Oct 1)**
**Owner: You**

Toronto launch. Controlled, targeted, loud enough to matter.

| Task | Why |
|---|---|
| Press release to Toronto tech/lifestyle media (BlogTO, Toronto Star tech section, NOW Magazine) | Local press drives local downloads |
| Launch on Product Hunt | Tech-adjacent audience, astrology crossover is strong |
| Instagram + TikTok content push (astrology content works extremely well on both) | Your audience lives here |
| Partner with 3–5 Toronto astrology/wellness influencers | Micro-influencers (10k–100k) convert better than celebrities for niche apps |
| Host a small Toronto launch event (20–30 people) | Community, press, word of mouth |
| Launch referral program ("give a free month, get a free month") | Viral loop |
| Set up customer support email + response SLA | Scale begins here |

**Exit gate:** 500+ downloads in the first 2 weeks. App Store rating ≥ 4.2.

---

## PHASE 8 — Growth + Expansion
**Duration: Ongoing from Oct 2026**

| Focus | Action |
|---|---|
| Retention | Push notifications, weekly compatibility insights, new match suggestions |
| Revenue | Premium conversion optimization, annual plan promotion |
| Geography | Expand to Vancouver, Montreal, then NYC |
| Product | Group compatibility, video profiles, AI-generated compatibility reports |

---

## Timeline Summary

| Phase | What | Start | End | Duration |
|---|---|---|---|---|
| **0** | Emergency fixes | Jun 11 | Jun 16 | 5 days |
| **1** | Beta infrastructure | Jun 16 | Jun 27 | 11 days |
| **2** | Legal + business | Jun 16 | Jul 9 | 3 weeks |
| **3** | Closed beta (50 users) | Jun 27 | Aug 1 | 5 weeks |
| **4** | Production cutover | Aug 1 | Aug 15 | 2 weeks |
| **5** | Monetization | Aug 1 | Aug 22 | 3 weeks |
| **6** | App Store submission | Aug 15 | Sep 12 | 4 weeks |
| **7** | Public launch | Sep 12 | Oct 1 | 3 weeks |
| **8** | Growth | Oct 1 | → | Ongoing |

**Full launch date: ~October 1, 2026** (16 weeks from today)

---

## The Two Things That Will Delay You Most

1. **Attorney turnaround** — Legal review takes 2–4 weeks. Send `legal/ATTORNEY_REVIEW_PACKET.md` **today**. Every day you wait pushes the launch date.

2. **Getting to 50 real users** — This is your hardest gate. 50 real completed psychology assessments takes longer than you think. Start recruiting beta users the moment Phase 1 is done. Use your personal network hard.

---

## What Claude Can Do For You Automatically

- Phase 0 fixes (migrations, CI, credentials)
- Phase 1 backend wiring (email collection, Sentry, PostHog)
- Phase 4 production cutover scripts (already written)
- Phase 5 Stripe integration
- Phase 6 EAS builds and App Store metadata
- All landing page updates and visual changes

---
