# Legal Sign-off Workflow (Required Before Public Launch)

## Policy Draft Lifecycle
1. Draft policy version with locale + jurisdiction + platform metadata.
2. Mark `attorney_review_required=true`.
3. Counsel review and approval.
4. Record approver and approval timestamp.
5. Publish and collect new consent events for impacted users.

## Release Gate
- No public launch if any production policy row still has attorney review required and no approval record.

## Required Approval Artifacts
- Counsel name and approval date
- Jurisdiction notes (CA/US/EU/UK)
- Change-log summary for material updates
