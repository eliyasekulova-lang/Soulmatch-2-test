# SoulMatch Privacy Policy

Status: Draft for attorney review.
Last updated: [insert date]
Applies to: SoulMatch mobile application, websites, and related services.
Controller/Operator: [insert legal entity name], [insert mailing address], [insert jurisdiction of formation].
Contact: privacy@soulmatch.app

## 1. Scope
This Privacy Policy explains how SoulMatch collects, uses, discloses, stores, and deletes personal information when people use the SoulMatch service. SoulMatch is a matchmaking and social discovery app that offers romance and friendship recommendations using profile data, behavioral signals, and optional astrology-enhanced matching inputs.

## 2. Information We Collect
SoulMatch currently collects or may collect the following categories of information:

- Account and authentication data, such as email address, password hash, user ID, refresh tokens, login timestamps, and related security metadata.
- Profile data, such as display name, legal/profile name fields, locale, jurisdiction, goals, and matching preferences.
- Birth and astrology-related data, such as date of birth, birth time, birth place, birth city, birth country, birth latitude/longitude, and birth timezone.
- Sensitive or high-sensitivity personal data that may be inferred from the product design, including precise birth information used for astrology-enhanced matching and compatibility analysis.
- Matching and preference data, such as selected matching mode, recommendation scores, compatibility highlights, psych profile outputs, and behavioral profile outputs.
- User-generated content, such as messages, reports, appeals, and moderation submissions, plus media metadata; media upload capability exists in the backend even if not all clients currently expose it.
- Analytics and product interaction data, such as onboarding events, match views, likes, passes, messages sent, feedback signals, experiment assignments, and feature usage.
- Safety, fraud, and abuse data, such as moderation reports, block lists, trust-and-safety risk scores, reason codes, safety actions, audit trails, and incident records.
- Device, network, and request metadata, such as IP address, user agent, app version, error telemetry, and request logs.
- Place search data, such as birth-place search queries sent to OpenStreetMap Nominatim when live search is used.

## 3. Sources of Information
We collect information:

- directly from the user during sign-up, onboarding, profile edits, messaging, reports, and support interactions;
- automatically from app and API usage;
- from internal analytics, behavioral models, and safety systems generated from user activity;
- from third-party infrastructure and service providers that help us operate the service.

## 4. How We Use Information
SoulMatch uses personal information to:

- create and secure accounts;
- verify age eligibility and enforce platform access rules;
- generate and refresh romance and friendship recommendations;
- generate astrology-enhanced vectors and compatibility explanations when that matching mode is enabled;
- derive behavioral and psych profile outputs used in ranking, personalization, and trust-and-safety operations;
- deliver messaging, media, blocking, reporting, and moderation features;
- monitor service health, debug incidents, and prevent spam, fraud, harassment, coercion, and abuse;
- maintain legal records, consent logs, audit logs, retention schedules, and user-rights workflows;
- improve product quality, experimentation, and analytics;
- comply with legal obligations, lawful requests, and internal incident response procedures.

## 5. Legal Bases
SoulMatch’s compliance layer currently contemplates use of the following legal bases depending on jurisdiction and processing purpose: consent, contract, legitimate interests, and legal obligation. Additional or different legal bases may apply depending on the user’s location. Counsel should confirm the final legal-basis mapping for Canada, the United States, the European Union, the United Kingdom, and any launch jurisdictions.

## 6. Sensitive Data and Astrology-Enhanced Matching
SoulMatch asks users to provide birth date, birth time, and birth place. That information is used to calculate compatibility inputs and may be treated as sensitive or high-risk personal information in some jurisdictions because it is precise, personal, and used for profiling. Users must separately consent to this processing in the current product flow before a profile is created.

Counsel should confirm:

- whether this data should be described as sensitive personal information, special-category-adjacent data, or another protected category in applicable jurisdictions;
- whether consent language and withdrawal mechanics are sufficient;
- whether any additional disclosures are needed for profiling or automated decision-making rules.

## 7. Automated Processing and Profiling
SoulMatch uses automated systems to:

- compute compatibility scores and ranked match suggestions;
- generate psych and behavioral profile outputs;
- log experiment assignments;
- detect suspicious, abusive, or unsafe behavior;
- trigger moderation escalation and recipient-protection flags.

These tools support product and safety decisions, but SoulMatch does not describe them as clinical, psychological, medical, or legal evaluations. Match recommendations are suggestions, not guarantees. Safety and enforcement decisions may involve automated signals plus manual review. Counsel should confirm whether additional automated-decision disclosures, appeal rights, or jurisdiction-specific notices are required.

## 8. How We Share Information
SoulMatch does not state that it sells personal information. We may disclose information:

- to cloud hosting, storage, monitoring, and security providers;
- to vendors that process data on our behalf under contractual controls;
- to other users as part of the core service, such as profile display, matching, and messaging;
- within the company to personnel with a business need to know;
- when required to comply with law, court order, subpoena, or other valid legal process;
- when necessary to investigate, enforce, or protect rights, safety, and platform integrity;
- in connection with a merger, acquisition, financing, or asset transaction, subject to lawful safeguards.

Current seeded processor references in the codebase include AWS and Sentry. Counsel should confirm whether the final public privacy policy should name these processors, publish a subprocessor list, or describe categories only.

## 9. Cross-Border Transfers
SoulMatch’s compliance code anticipates cross-border transfers and references transfer mechanisms such as standard contractual clauses. Data may be stored or processed outside the user’s home jurisdiction, including in Canada and the United States, depending on hosting and vendors. Counsel should finalize transfer language and any regional addenda.

## 10. Retention
SoulMatch retains information according to product, security, legal, and operational needs. Current code and migrations indicate example retention periods for some classes:

- messages: 1095 days;
- audit logs: 2555 days;
- rights export bundles: 7 days;
- temporary media uploads: 2 days.

Deletion requests are designed to propagate across database records, file storage, backups, search indexes, and analytics systems, with backups purged on scheduled retention cycles rather than instantly. Counsel should verify that the public disclosures match actual operational retention and backup deletion practices before launch.

## 11. User Rights
Depending on jurisdiction, users may have rights to:

- access their information;
- correct inaccurate information;
- request deletion;
- restrict certain processing;
- withdraw consent;
- receive an export of certain information;
- appeal or complain to a regulator where applicable.

The backend currently implements workflows for export, correction, deletion, restriction, and consent withdrawal. Counsel should confirm SLA language, identity verification requirements, scope limitations, and region-specific rights notices.

## 12. Security
SoulMatch states that it uses administrative, technical, and organizational safeguards, including encryption for birth data at rest, TLS in transit, access controls, audit logging, and environment-specific configuration controls. No method of storage or transmission is completely secure, and no absolute security guarantee is made.

## 13. Children and Age Restrictions
SoulMatch is intended only for users who meet the minimum age requirement, which is currently configured as 18+. The service is designed to reject sign-up below the minimum age threshold and to escalate critical child-safety reason codes. See the separate age-gating policy for counsel review.

## 14. International and U.S. State Supplements
Additional notices may be needed for:

- California and other U.S. state privacy laws;
- Canada under PIPEDA and provincial rules;
- the GDPR and UK GDPR;
- app store platform requirements;
- jurisdictions with special rules for profiling, sensitive data, or dating services.

These supplements are not finalized in this draft.

## 15. Changes to This Policy
SoulMatch may update this Privacy Policy. Material changes should be versioned, dated, and presented to users with renewed consent or acknowledgment where legally required.

## 16. Contact
Privacy requests and legal notices should be sent to:

- Privacy Officer: privacy@soulmatch.app
- Support: support@soulmatch.app
- Mailing address: [insert legal entity mailing address]
