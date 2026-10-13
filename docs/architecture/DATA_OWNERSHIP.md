# Data Ownership

Each service is the authoritative source of truth for its own domain. Other services may query or receive copies of this data, but must not write to it directly.

| Service | Owns |
|---|---|
| **EHR** | Orders |
| **LabLenz** | Specimens, Laboratory Results |
| **Analyzer** | Instrument measurements |
| **Integration Engine** | Messages, routing history |
| **Patient Portal** | Patient-facing preferences, presentation state |
| **Tenant IT** | Tenant configuration |
| **Platform Admin** | Platform provisioning, tenant provisioning |

## Principles

- **Write to the owner** — mutations flow to the owning service's API, never directly to its database.
- **Read from copies** — consumers may hold read-optimised projections; the owner's store is the canonical version.
- **Event-driven propagation** — when an owner's data changes, it publishes an event; downstream services update their local copies asynchronously.
