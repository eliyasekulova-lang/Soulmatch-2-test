# Security and Secrets Baseline (Attorney Review Required)

## Encryption
- TLS terminated at edge/load balancer.
- Database and object storage encryption at rest enabled.
- App-level field encryption for sensitive birth fields before persistence.

## Key Management
- `PII_ENCRYPTION_KEY` must come from managed secret storage (KMS-backed secret manager in staging/prod).
- Rotation policy:
  - Scheduled rotation every 90 days.
  - Immediate rotation on suspected key compromise.
- Rotation process:
  - Write new encryptions with current key version.
  - Keep previous key version enabled for controlled decryption window.
  - Re-encrypt backlog asynchronously and retire old key.

## Secrets Management
- Environment variables only (no hardcoded secrets in repo).
- Production startup fails if secrets are default/placeholder values.
- Secret access is restricted to runtime principals and audited.

## Backup Deletion Semantics
- User deletion is immediate in active systems.
- Backups are purge-scheduled and evidenced in audit trail.
- Purge windows and proof references are recorded in rights request resolution metadata.
