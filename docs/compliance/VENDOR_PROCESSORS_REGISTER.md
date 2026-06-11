# Vendor Processors Register (Attorney Review Required)

## Mandatory Fields Per Vendor
- Name
- Purpose
- Data categories processed
- Transfer mechanism (DPA/SCC/other)
- DPA URL
- Subprocessor country
- Data transfer region
- SCC reference id
- Active status

## Runtime Source
- API table: `vendor_processors`
- Admin read endpoint: `GET /v1/admin/vendors`

## Governance
- Every new processor requires legal review before activation.
- Keep transfer mechanism and SCC references current.
- Run quarterly processor review and archive audit evidence.
