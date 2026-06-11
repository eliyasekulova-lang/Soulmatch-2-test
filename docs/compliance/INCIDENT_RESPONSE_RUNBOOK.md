# Incident Response Runbook (Attorney Review Required)

## Severity Levels
- P1: Active safety/legal exposure or confirmed data breach
- P2: High-risk security event with potential exposure
- P3: Contained security defect without known exposure

## Ownership
- Incident Commander: Security lead
- Legal Owner: Privacy/compliance lead
- Communications Owner: Support/ops lead
- Engineering Owner: API lead

## Timeline Targets
- Detection to triage: <= 15 minutes
- Triage to containment: <= 60 minutes
- Initial legal assessment: <= 4 hours
- User/regulator notification timeline: jurisdiction-dependent; default target <= 72 hours where required

## Required Records
- Incident id, severity, status, summary
- Detected timestamp, notified timestamp, resolved timestamp
- Evidence references, impacted systems, impacted data classes
- Notification decision and legal rationale

## API Support
- `POST /v1/admin/incidents`
- `POST /v1/admin/law-enforcement`
- `GET /v1/audit/admin`
