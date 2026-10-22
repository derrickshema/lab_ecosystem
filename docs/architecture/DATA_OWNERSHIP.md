# Data Ownership

Each service is the authoritative source of truth for its own domain. Other services may query or receive copies of this data, but must not write to it directly.

| Service | Owns |
|---|---|
| **Identity / Platform** | Users, facilities, staff access grants (facility + role), platform patient identity, patient portal accounts |
| **EHR** | Facility patient records (MRN), encounters, lab orders |
| **LabLenz** | Test catalog, specimens, laboratory results |
| **Analyzer** | Instrument measurements |
| **Integration Engine** | Messages, routing history |
| **Patient Portal** | Patient-facing preferences, presentation state |
| **Tenant IT** | Tenant configuration |
| **Platform Admin** | Platform provisioning, tenant provisioning |

Copies held by non-owners:

| Data | Owner | Copied by | Why |
|---|---|---|---|
| Test catalog | LabLenz | EHR | Providers pick tests when ordering |
| Patient demographics, encounter, lab orders | EHR | LabLenz | Lab work queue, specimen labeling |
| Released results | LabLenz | EHR | Results shown in the patient chart |

## Principles

- **Write to the owner** — mutations flow to the owning service's API, never directly to its database.
- **Read from copies** — consumers may hold read-optimised projections; the owner's store is the canonical version.
- **Event-driven propagation** — when an owner's data changes, it publishes an event; downstream services update their local copies asynchronously.
- **UUIDs across boundaries** — any record another service references (patients, encounters, orders, facilities) has a UUID. Services store each other's IDs as plain columns, never as database foreign keys.

## Clinical Workflow

```
Registration personnel (EHR)   → creates/links Patient, opens Encounter
Provider (EHR)                 → places LabOrder for the encounter, choosing tests from the catalog
                                   │  order sent to LabLenz
Lab technician (LabLenz)       → collects/manages Specimens, runs tests, releases Results
                                   │  results sent back to EHR
Provider (EHR)                 → reviews results in the patient chart
Patient (Patient Portal)       → views released results from every facility they've visited
```

## Patient Identity

Patients have two levels of identity:

```
PlatformPatient                (Identity / Platform — not tied to any facility)
  id: UUID                      ← used for patient portal login and cross-facility access
  │
  └── Patient                  (EHR — one per facility the person has visited)
        id: UUID
        facility_id
        mrn                     ← facility-scoped: UNIQUE(facility_id, mrn)
        platform_patient_id     ← UNIQUE(facility_id, platform_patient_id)
```

- **Registration matching:** search this facility first; otherwise query the platform for a candidate match. The platform returns only the match and its ID — never data from other facilities.
- **Conservative linking:** a wrong link exposes one patient's results to another. When in doubt, create a new platform identity; duplicates can be merged later, a bad link cannot be safely undone.
- **Identity ≠ login:** a `PlatformPatient` exists from first registration; a portal account is created later (verified invite) and linked to it. Patients carry a distinct role and never satisfy staff RBAC checks.

## Authentication

There is one login backend (Identity / Platform) with separate portals for each user type: EHR staff, LabLenz staff, and patients. It issues JWTs carrying `facility_id` and `org_role` for staff. Each service validates the token and enforces its own role checks. Until the Identity service is split out, LabLenz's auth module issues the tokens and EHR validates them with the shared secret.
