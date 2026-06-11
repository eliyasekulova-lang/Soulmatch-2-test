# SoulMatch Data Retention and Deletion Policy

Status: Draft for attorney review.

## Overview
SoulMatch retains information for service delivery, safety, fraud prevention, legal compliance, dispute handling, and auditability. Retention periods should be treated as operational defaults pending legal review and confirmation against actual production practice.

## Current Operational Retention Defaults Reflected in the Codebase

- Messages: 1095 days.
- Audit logs: 2555 days.
- Rights export bundles: 7 days.
- Temporary media uploads: 2 days.

These periods appear in database migrations and retention-job logic. Counsel should confirm whether they are appropriate and legally defensible for each launch jurisdiction.

## Active Accounts
For active accounts, SoulMatch retains information needed to:

- operate the app and user accounts;
- generate matches and compatibility outputs;
- provide messaging and safety tooling;
- investigate abuse, fraud, and policy violations;
- maintain legal records and audit trails.

## Inactive Accounts
Inactive-account rules are not fully defined in code. Counsel should advise on dormancy windows, notice requirements, and whether any anonymization program should apply to unused accounts.

## Deleted Accounts
When a deletion request is submitted, SoulMatch is designed to queue deletion work across:

- database systems;
- file storage;
- backups;
- search indexes;
- analytics systems.

Deletion from active systems is intended to occur before backup copies age out on scheduled retention cycles. Some records may be retained longer where required for legal compliance, fraud prevention, security, tax, accounting, dispute resolution, or evidence preservation.

## Legal Holds
Some retained classes may be subject to legal hold. Counsel should confirm legal-hold triggers, authorization rules, and notice requirements.

## Rights Requests
SoulMatch’s backend includes request flows for:

- export;
- correction;
- deletion;
- restriction of processing;
- consent withdrawal.

Counsel should confirm response deadlines, verification standards, appeal handling, and any required regional disclosures.

## Public-Facing Disclosure Note
Any public privacy policy or deletion page should explain that backup deletion is not always immediate and may occur on scheduled retention cycles.
