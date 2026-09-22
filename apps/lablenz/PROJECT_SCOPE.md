# LabLenz — Project Scope

> **Living document.** Update this file as priorities shift and features are refined. It is the authoritative boundary and roadmap for the project.

---

## 1. Overview

**LabLenz** is a multi-tenant web application that digitizes and connects every step of the laboratory testing lifecycle — from patient registration through to the patient viewing their own results. It serves four distinct user roles operating across clinical, laboratory, catalog, and patient-portal contexts, all within an isolated per-facility (tenant) data environment.

### The one-sentence pitch

> *LabLenz gives providers, lab techs, and patients a shared, real-time view of the lab testing pipeline — orders, specimens, results, and alerts — without the paper, phone calls, and manual reconciliation that burden most clinical environments.*

---

## 2. Problem Space

Modern lab workflows are fragmented:

- Providers write orders on paper or in a generic EHR with no feedback on specimen/result status.
- Lab techs key results into systems detached from the ordering encounter.
- Patients receive paper reports or must call the clinic to learn their results.
- Critical/panic values are communicated via phone with no guaranteed acknowledgment record.
- Building and maintaining a test catalog is manual, error-prone, and time-consuming.

LabLenz addresses all of these gaps in a single, cohesive platform.

---

## 3. Goals & Non-Goals

### Goals

- Connect the full lab lifecycle end-to-end: order → specimen → result → patient view.
- Surface the right information to the right role at the right time.
- Enforce patient safety: flag out-of-range and critical values, require provider acknowledgment of criticals.
- Reduce catalog build time with an AI-assisted workflow that keeps humans in the loop.
- Support multiple independent facilities from one deployment (multi-tenancy).

### Non-Goals (for now)

- Integration with external EHR/LIS/HIS systems via HL7 or FHIR (post-MVP).
- Billing, insurance, and claims processing.
- Pharmacy or medication management.
- Medical imaging or radiology workflows.
- Regulatory/compliance certification (HIPAA formal attestation deferred to a later phase).

---

## 4. Mental Models

Understanding these three mental models is essential before building anything.

### 4.1 The Pipeline

```
Patient → Encounter → LabOrder → LabOrderItem → Result
                          │
                          └──► Specimen → SpecimenStatusHistory
```

| Stage | Owner | Meaning |
|---|---|---|
| Patient & Encounter | Registration | Who the patient is and the context of the visit |
| LabOrder + LabOrderItem | Provider / Lab Tech | *Intent* — what tests are requested |
| Specimen | Lab Tech | *Execution* — the physical sample |
| Result | Lab Tech | *Outcome* — the measured analyte values |

### 4.2 Domains

| Domain | Core entities | Purpose |
|---|---|---|
| Clinical | Patient, Encounter, LabOrder | Drives ordering intent |
| Laboratory | Specimen, LabOrderItem, Result | Tracks execution and outcomes |
| Catalog | LabTest, Analyte, ClinicalDecisionLimits | Knowledge base for tests and reference ranges |
| Identity | User, Staff, UserPatientLink | Access, roles, and relationships |

### 4.3 Tenancy

Every piece of patient data, every order, every result is scoped to a `facility_id`. A single LabLenz deployment can serve multiple independent healthcare facilities. Staff and patients of Facility A can never access data belonging to Facility B.

---

## 5. User Roles & What They Do

### 5.1 Registration Staff

Responsible for onboarding patients and creating encounters.

- Register new patients (collect demographics, generate MRN).
- Create encounters (initial visit or return visit, assign encounter number).
- Trigger portal invitation email to newly registered patients.

### 5.2 Provider (Physician / Ordering Clinician)

Responsible for ordering tests and acting on results.

- Search the test catalog and order one or more tests against an existing patient encounter.
- Specify desired specimen collection time.
- Receive in-app notifications when ordered results are finalized.
- Receive **critical/panic value alerts** and must explicitly **acknowledge** each one.

### 5.3 Lab Technician

Responsible for everything that happens once an order is placed.

- View pending orders; specimens are automatically grouped by the system based on each test's catalog definition.
- Track specimen collection and status changes.
- Manually enter result values per analyte per test.
- Review saved results and **release** them when satisfied.
- Build new lab tests into the catalog (AI-assisted workflow); the specimen type and container type defined during catalog build drive the system's automatic specimen grouping.

### 5.4 Facility IT Personnel

Manages staff accounts within their own facility. Acts as the local administrator for the facility's user directory.

- Create, edit, deactivate, and reactivate `Staff` accounts for their facility.
- Assign and update `org_role` (provider, lab tech, registration, etc.) for staff members.
- Reset staff passwords and manage access credentials.
- Cannot access or modify patient data, orders, or results.
- Cannot manage other facilities or system-level settings.

### 5.5 System Administrator

Global administrator for the LabLenz platform. Operates above the facility level.

- Create, configure, and deactivate `Facility` (tenant) accounts.
- Manage Facility IT Personnel accounts (create, deactivate, reset credentials).
- Monitor platform-level health, audit logs, and cross-facility usage.
- Cannot access patient clinical data within any facility (read access to facility metadata only).

### 5.6 Patient

End consumer of lab results via the patient portal.

- Receive push/email notification when results are released.
- View lab results with clear visual indicators for out-of-range and critical values.
- No ability to modify any data.

---

## 6. Core Feature Set

### 6.1 Patient Registration

- Form captures: first name, last name, date of birth, sex, contact info.
- On submission: system generates a unique **MRN** (Medical Record Number).
- System sends a portal invitation email with a sign-up link.
- Duplicate detection: warn if a patient with matching name + DOB already exists in the facility.

### 6.2 Encounter Management

- Create an encounter for a registered patient.
- Capture: encounter type (initial/follow-up/etc.), floor/unit, provider, date.
- System generates a unique **encounter number** for the duration of the visit.
- A patient can have multiple encounters over time; each is distinct.
- Encounter status tracks: `active`, `discharged`, `cancelled`.

### 6.3 Provider Order Entry

- Search/browse the test catalog by test name or test code.
- Select a patient by name, MRN, or encounter number.
- Add one or more tests to a pending order list (like a cart).
- Set a desired collection time for the order.
- Submit the order — creates a `LabOrder` and individual `LabOrderItems`.
- Lab Techs can also place orders from verbal requests or requisition forms.

### 6.4 Specimen Workflow

- When an order is submitted, the system automatically groups `LabOrderItems` into `Specimens` based on the `required_specimen_type` and `required_container_type` defined on each `LabTest` in the catalog — no manual specimen assignment by the lab tech.
- Each specimen gets a unique **accession number**.
- Lab Tech updates specimen status: `ordered → collected → received → processing → completed`.
- Each status transition is logged in `SpecimenStatusHistory` with a timestamp and staff ID.

### 6.5 Result Entry

- Lab Tech selects a specimen and sees all associated `LabOrderItems` (tests).
- For each test, a result form displays the analytes in `display_order`.
- Tech enters a value for each analyte and saves (status: `saved`/draft).
- On save, the system automatically evaluates each value against `ClinicalDecisionLimits` for the patient's age and sex and assigns a flag: `normal`, `low`, `high`, `critical_low`, `critical_high`.
- Delta checks (crr_low / crr_high): compare against the patient's previous result for the same analyte.

### 6.6 Result Review & Release

- A **Results Monitor** view displays all saved (unreleased) results for the facility.
- Lab Tech reviews result values and flags, then clicks **Release**.
- Released results: `released_at` timestamp and `released_by_staff_id` are recorded.
- Only released results are visible to the Provider and Patient.

### 6.7 Critical Value Alerts & Acknowledgment

- When a result with a `critical_low` or `critical_high` flag is released, the system immediately creates an alert and notifies the ordering provider.
- The provider must open the alert and click **Acknowledge** to dismiss it.
- Unacknowledged critical alerts persist and re-notify on a configurable schedule.
- All acknowledgment events are audit-logged: who acknowledged, when.

### 6.8 Patient Portal

- After results are released, the patient is notified (in-app + email).
- Patient logs in and sees a list of their results grouped by encounter.
- Values are displayed with clear indicators:
  - Normal: no highlight.
  - Out of range (low/high): subtle warning color.
  - Critical: prominent alert color.
- No PHI beyond their own results is accessible.

### 6.9 AI-Assisted Test Catalog Builder

Building a `LabTest` record requires many fields (name, code, analytes, units, reference ranges, specimen type, container type, etc.) — enough that doing it manually is slow and error-prone.

**Flow:**

```
Lab Tech seeds input
      │
      ▼
AI agent drafts a full LabTest definition
      │
      ▼
System creates a DRAFT test (not in catalog)
      │
      ▼
Lab Tech reviews / edits each field
      │
      ▼
Tech (or senior tech) approves and publishes
      │
      ▼
Test is LIVE in the facility's catalog
```

**Constraints:**
- Draft tests are invisible to providers until published.
- Every edit to a draft is recorded.
- Approval requires a named reviewer (audit trail).
- AI-generated values for reference ranges and critical limits must be explicitly confirmed by the human reviewer — they cannot be auto-published.

---

## 7. Data Model

### 7.1 Entity Hierarchy

```
Facility
 ├── Patient ── Encounter ── LabOrder ── LabOrderItem ── Result
 │                                  │
 │                                  └── Specimen ── SpecimenStatusHistory
 │
 ├── Staff ── User
 │
 └── LabTest ── LabTestAnalyte ── Analyte ── ClinicalDecisionLimits

User ── UserPatientLink ── Patient
```

### 7.2 Entity Definitions

| Entity | Key fields |
|---|---|
| `User` | id, first_name, last_name, username, email, system_role (`patient`, `staff`, `system_admin`), password_hash, created_at, updated_at |
| `Facility` | id, name, type, created_at, updated_at |
| `Patient` | id, MRN, first_name, last_name, dob, sex, facility_id, created_at, updated_at |
| `UserPatientLink` | id, user_id, patient_id, facility_id, relationship (self/guardian/parent) |
| `Staff` | id, first_name, last_name, user_id, org_role (`provider`, `lab_tech`, `registration`, `facility_it`), title, department, facility_id, created_at, updated_at |
| `Encounter` | id, encounter_number, patient_id, provider_id, facility_id, type, location, status, created_at, updated_at |
| `Analyte` | id, name, description, units, created_at, updated_at |
| `ClinicalDecisionLimits` | id, analyte_id, sex, age_min, age_max, reference_low, reference_high, critical_low, critical_high, crr_low, crr_high |
| `LabTest` | id, name, test_code, required_specimen_type, required_container_type, facility_id, status (draft/active), created_at, updated_at |
| `LabTestAnalyte` | lab_test_id, analyte_id, display_order |
| `LabOrder` | id, patient_id, encounter_id, ordered_by_staff_id, facility_id, status, created_at, updated_at |
| `LabOrderItem` | id, specimen_id, lab_order_id, lab_test_id, status, created_at, updated_at |
| `Specimen` | id, accession_number, lab_order_id, specimen_type, container_type, collected_at, status, created_at, updated_at |
| `SpecimenStatusHistory` | id, specimen_id, status, changed_by_staff_id, changed_at |
| `Result` | id, lab_order_item_id, analyte_id, value, flag, entered_by_staff_id, released_by_staff_id, released_at, created_at, updated_at |

### 7.3 Status Enums

| Entity | Statuses |
|---|---|
| `Encounter` | `active`, `discharged`, `cancelled` |
| `LabOrder` | `pending`, `in_progress`, `completed`, `cancelled` |
| `LabOrderItem` | `pending`, `collected`, `resulted`, `released`, `cancelled` |
| `Specimen` | `ordered`, `collected`, `received`, `processing`, `completed`, `rejected` |
| `LabTest` | `draft`, `pending_review`, `active`, `inactive` |
| `Result.flag` | `normal`, `low`, `high`, `critical_low`, `critical_high`, `delta` |

---

## 8. Notifications & Alerts

| Trigger | Recipient | Channel | Action required |
|---|---|---|---|
| Results released | Ordering provider | In-app | None (informational) |
| Critical/panic result | Ordering provider | In-app + push | Must acknowledge |
| Unacknowledged critical (timeout) | Provider + supervisor | In-app + push | Acknowledge |
| Results released | Patient | In-app + email | None |
| Patient registered | Patient | Email (portal invite) | Sign up for portal |

---

## 9. Security & Multi-tenancy

- All data is scoped to `facility_id`; every query must be facility-filtered.
- Role-based access control (RBAC) enforced at the API layer by `system_role` (`patient`, `staff`, `system_admin`) and, for staff, `org_role` (`provider`, `lab_tech`, `registration`, `facility_it`). System Admins bypass facility scoping for facility-management endpoints only.
- Passwords hashed with a secure algorithm (bcrypt or argon2); never stored in plaintext.
- Sessions managed via short-lived JWT access tokens and longer-lived refresh tokens.
- All sensitive state transitions (result entry, release, acknowledgment) are audit-logged.
- HTTPS enforced; sensitive data encrypted at rest.
- No cross-tenant data leakage — enforced at both the application and database level (row-level security or equivalent).

---

## 10. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | SvelteKit | Existing `frontend/` scaffold |
| Backend | Python + FastAPI | Existing `backend/app/` scaffold |
| Database | PostgreSQL | Alembic migrations in place |
| Containerization | Docker + docker-compose | Existing `docker-compose.yml` |
| AI (Test Builder) | LLM-based agent (TBD) | Encapsulated service, human-in-loop enforced |
| Notifications | TBD (e.g., WebSocket + email service) | In-app real-time + email |

---

## 11. Roadmap

### Phase 1 — MVP (Months 0–3)

Foundation and core loop operational.

- [ ] Auth: registration, login, RBAC, JWT sessions
- [ ] Multi-tenancy: facility isolation enforced end-to-end
- [ ] Patient registration + MRN generation + portal invite email
- [ ] Encounter creation + encounter number generation
- [ ] Test catalog (manually created entries)
- [ ] Provider order entry UI
- [ ] Specimen creation, accession numbering, status tracking
- [ ] Lab Tech result entry (per analyte) + auto-flagging
- [ ] Review and release workflow (Results Monitor)
- [ ] Critical alert notifications + provider acknowledgment
- [ ] Patient portal: view released results with flag highlights
- [ ] Patient push/email notification on result release

### Phase 2 — AI & Advanced Lab Ops (Months 3–6)

- [ ] AI-assisted test builder workflow (draft → review → publish)
- [ ] Advanced catalog management (deactivate tests, version history)
- [ ] Specimen routing and rejection workflow
- [ ] Delta checks (crr_low / crr_high) implemented
- [ ] Reporting: order-to-release time, specimen lag, critical acknowledgment time
- [ ] Provider dashboard with order/result history

### Phase 3 — Integrations & Scale (Months 6+)

- [ ] HL7 / FHIR interfaces for EHR integration
- [ ] Advanced analytics and trend visualizations for patients
- [ ] Multi-facility reporting for healthcare network operators
- [ ] Formal compliance review (HIPAA readiness assessment)
- [ ] Mobile app for patients and providers

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| AI auto-populates incorrect reference ranges | Patient safety | Human-in-loop enforced; AI output never auto-published |
| Critical alert not acknowledged in time | Patient safety | Escalation timer + supervisor notification |
| Cross-tenant data exposure | HIPAA / legal | Facility-scoped queries + RLS at DB layer + API enforcement |
| Notification fatigue causing ignored alerts | Safety | Configurable thresholds; separate UI lanes for criticals |
| Accession number collisions | Data integrity | Auto-generated with uniqueness constraint per facility |
| Result overwrite after release | Data integrity | Released results are immutable; corrections via amendment flow |

---

## 13. Success Criteria (MVP)

The MVP is complete when the following end-to-end scenario works without manual workarounds:

1. A registration clerk registers a new patient → MRN is generated → portal invite email is sent.
2. A registration clerk creates an encounter for the patient and assigns it to the provider.
3. The provider orders two tests from the catalog against that encounter.
4. The system automatically groups the order items into specimens based on the catalog definitions.
5. A lab tech sees the order, confirms specimen collection, and enters result values.
4. The system flags a critical value on one analyte automatically.
5. The lab tech reviews and releases the results.
6. The provider receives an in-app notification and a critical alert — acknowledges it.
7. The patient receives a notification and views their results in the portal, with critical value clearly highlighted.

---

*Last updated: April 2026*

