-- Runs once, when the postgres_data volume is first created.
-- One user + one database per app. Dev credentials only.

-- New databases let every user connect by default (via PUBLIC);
-- revoking that means each user can only reach its own database.

-- EHR
CREATE USER ehr_user WITH PASSWORD 'ehr_123';
CREATE DATABASE ehr_db OWNER ehr_user;
REVOKE CONNECT ON DATABASE ehr_db FROM PUBLIC;

-- LabLenz
CREATE USER lablenz_user WITH PASSWORD 'lablenz_123';
CREATE DATABASE lablenz_db OWNER lablenz_user;
REVOKE CONNECT ON DATABASE lablenz_db FROM PUBLIC;

-- Identity (consolidated auth: users, facilities, role grants)
CREATE USER identity_user WITH PASSWORD 'identity_123';
CREATE DATABASE identity_db OWNER identity_user;
REVOKE CONNECT ON DATABASE identity_db FROM PUBLIC;
