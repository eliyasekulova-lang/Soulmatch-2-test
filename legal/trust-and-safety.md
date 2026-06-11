# SoulMatch Trust and Safety Policy

Status: Draft for attorney review.

## Purpose
SoulMatch uses trust-and-safety systems to reduce fraud, harassment, coercion, spam, exploitation, and other harmful conduct.

## Safety Inputs
Safety systems may consider:

- user reports and appeals;
- messaging activity and interaction patterns;
- block events;
- abuse reason codes;
- device, session, and request metadata;
- internal risk scoring and recipient-protection flags.

## Safety Actions
SoulMatch may take actions including:

- warning prompts and safety tips;
- hidden-message treatment;
- message limits or friction;
- reduced visibility;
- verification requests;
- temporary restrictions;
- suspension or termination;
- critical escalation for severe risk categories.

## Critical Harm Escalation
The codebase currently treats reasons such as `minor`, `csam`, `sexual_content_minor`, and `violent_threat` as critical escalation categories. Those paths are designed to preserve evidence metadata, create audit entries, and route cases to heightened review.

## Confidentiality of Detection Methods
SoulMatch does not disclose internal abuse-detection logic, moderation thresholds, or risk scoring methods if disclosure would weaken platform safety or security.

## Appeals
The backend includes an appeals model and moderation-action records. Counsel should confirm the external policy language, timelines, and user notice requirements for appeals and reversals.
