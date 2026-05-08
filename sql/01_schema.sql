-- ============================================================
-- PORTFOLIO DATABASE SCHEMA
-- Fictional domain: Social Services Agency (anonymized)
-- Based on a real humanitarian data model
--
-- Design decisions:
--   - dim_user normalized with office FK
--   - One admissibility assessment per individual (operative record)
--   - SCD Type 1 for dim_individual (current state only)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- DIMENSIONS
-- ============================================================

CREATE TABLE dim_office (
    office_id       SERIAL PRIMARY KEY,
    office_name     VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE dim_user (
    user_id         VARCHAR(100) PRIMARY KEY,
    username        VARCHAR(150) NOT NULL,
    office_id       INTEGER NOT NULL REFERENCES dim_office(office_id)
);

CREATE TABLE dim_registration_group (
    rg_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    office_id       INTEGER NOT NULL REFERENCES dim_office(office_id),
    created_at      TIMESTAMP NOT NULL
);

-- Note: FK references to cat_* tables added after catalog section below
CREATE TABLE dim_individual (
    individual_id   VARCHAR(50) PRIMARY KEY,  -- format: IND-000001
    rg_id           UUID NOT NULL REFERENCES dim_registration_group(rg_id),
    process_status  VARCHAR(50) NOT NULL,
    country_origin  VARCHAR(10) NOT NULL,
    legal_status    VARCHAR(50),
    has_biometrics  BOOLEAN NOT NULL DEFAULT FALSE,
    full_name       VARCHAR(200),
    sex             VARCHAR(10),
    date_of_birth   DATE,
    created_at      TIMESTAMP NOT NULL,
    created_date    DATE NOT NULL,
    created_by      VARCHAR(100) REFERENCES dim_user(user_id)
);

-- dim_date intentionally omitted from this schema


-- ============================================================
-- CATALOGS
-- ============================================================

CREATE TABLE cat_process_status (
    status_code     VARCHAR(50) PRIMARY KEY,
    status_name     VARCHAR(100) NOT NULL
);

CREATE TABLE cat_country_origin (
    country_code    VARCHAR(10) PRIMARY KEY,
    country_name    VARCHAR(100) NOT NULL
);

CREATE TABLE cat_legal_status (
    status_code     VARCHAR(50) PRIMARY KEY,
    status_name     VARCHAR(150) NOT NULL
);

CREATE TABLE cat_admissibility_decision (
    decision_code   VARCHAR(100) PRIMARY KEY,
    decision_name   VARCHAR(150) NOT NULL
);

CREATE TABLE cat_admissibility_decision_basis (
    basis_code      VARCHAR(100) PRIMARY KEY,
    basis_name      VARCHAR(150) NOT NULL
);

CREATE TABLE cat_notification_type (
    notification_code   VARCHAR(50) PRIMARY KEY,
    notification_name   VARCHAR(100) NOT NULL
);

CREATE TABLE cat_process_type (
    process_type_code   INTEGER PRIMARY KEY,
    process_type_name   VARCHAR(100) NOT NULL
);

CREATE TABLE cat_eligibility_recommendation (
    recommendation_code     INTEGER PRIMARY KEY,
    recommendation_name     VARCHAR(100) NOT NULL
);

CREATE TABLE cat_recommendation_reason (
    reason_code     INTEGER PRIMARY KEY,
    reason_name     VARCHAR(150) NOT NULL
);

CREATE TABLE cat_review_decision (
    decision_code   INTEGER PRIMARY KEY,
    decision_name   VARCHAR(150) NOT NULL
);

CREATE TABLE cat_appeal_recommendation (
    recommendation_code     VARCHAR(50) PRIMARY KEY,
    recommendation_name     VARCHAR(100) NOT NULL
);

CREATE TABLE cat_appeal_decision (
    decision_code   INTEGER PRIMARY KEY,
    decision_name   VARCHAR(150) NOT NULL
);

CREATE TABLE cat_certificate_type (
    cert_type_code  VARCHAR(50) PRIMARY KEY,
    cert_type_name  VARCHAR(100) NOT NULL,
    cert_subtype    VARCHAR(100)
);

CREATE TABLE cat_reviewer_category (
    category_code   VARCHAR(50) PRIMARY KEY,
    category_name   VARCHAR(100) NOT NULL
);

-- ============================================================
-- FACTS
-- ============================================================

CREATE TABLE fact_admissibility (
    admissibility_id        VARCHAR(50) PRIMARY KEY,  -- format: ADM-000001
    individual_id           VARCHAR(50) NOT NULL REFERENCES dim_individual(individual_id),
    process_status          VARCHAR(50) REFERENCES cat_process_status(status_code),
    business_process_status VARCHAR(100) REFERENCES cat_admissibility_decision(decision_code),
    bps_date                DATE,
    bps_datetime            TIMESTAMP,
    created_at              TIMESTAMP NOT NULL,
    created_date            DATE NOT NULL,
    created_by              VARCHAR(100) REFERENCES dim_user(user_id)
);

CREATE TABLE fact_adm_interview (
    interview_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admissibility_id    VARCHAR(50) NOT NULL REFERENCES fact_admissibility(admissibility_id),
    interview_datetime  TIMESTAMP NOT NULL,
    interview_date      DATE NOT NULL,
    created_by          VARCHAR(100) REFERENCES dim_user(user_id)
);

CREATE TABLE fact_adm_decision (
    decision_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admissibility_id    VARCHAR(50) NOT NULL REFERENCES fact_admissibility(admissibility_id),
    decision_code       VARCHAR(100) REFERENCES cat_admissibility_decision(decision_code),
    decision_date       DATE NOT NULL,
    decision_datetime   TIMESTAMP NOT NULL,
    decision_basis_code VARCHAR(100) REFERENCES cat_admissibility_decision_basis(basis_code),
    created_by          VARCHAR(100) REFERENCES dim_user(user_id)
);

CREATE TABLE fact_eligibility (
    eligibility_id          VARCHAR(50) PRIMARY KEY,  -- format: ELG-000001
    individual_id           VARCHAR(50) NOT NULL REFERENCES dim_individual(individual_id),
    process_type_code       INTEGER REFERENCES cat_process_type(process_type_code),
    notification_type_code  VARCHAR(50) REFERENCES cat_notification_type(notification_code),
    notification_date       TIMESTAMP,
    notification_date_only  DATE,
    created_at              TIMESTAMP NOT NULL,
    created_by              VARCHAR(100) REFERENCES dim_user(user_id)
);

CREATE TABLE fact_elg_recommendation (
    eligibility_id               VARCHAR(50) PRIMARY KEY REFERENCES fact_eligibility(eligibility_id),
    recommendation_code         INTEGER REFERENCES cat_eligibility_recommendation(recommendation_code),
    recommendation_date         TIMESTAMP,
    recommendation_date_only    DATE,
    reason_code                 INTEGER REFERENCES cat_recommendation_reason(reason_code),
    legal_basis                 VARCHAR(150),
    recommended_by              VARCHAR(100) REFERENCES dim_user(user_id)
);

CREATE TABLE fact_elg_review (
    eligibility_id           VARCHAR(50) PRIMARY KEY REFERENCES fact_eligibility(eligibility_id),
    review_decision_code    INTEGER REFERENCES cat_review_decision(decision_code),
    review_date             TIMESTAMP,
    review_date_only        DATE,
    reviewer_category_code  VARCHAR(50) REFERENCES cat_reviewer_category(category_code),
    reviewed_by             VARCHAR(100) REFERENCES dim_user(user_id)
);

CREATE TABLE fact_appeal_recommendation (
    eligibility_id               VARCHAR(50) PRIMARY KEY REFERENCES fact_eligibility(eligibility_id),
    has_appeal                  BOOLEAN NOT NULL DEFAULT TRUE,
    appeal_recommendation_code  VARCHAR(50) REFERENCES cat_appeal_recommendation(recommendation_code),
    appeal_recommendation_date  DATE,
    recommended_by              VARCHAR(100) REFERENCES dim_user(user_id)
);

CREATE TABLE fact_appeal_decision (
    eligibility_id           VARCHAR(50) PRIMARY KEY REFERENCES fact_eligibility(eligibility_id),
    appeal_decision_code    INTEGER REFERENCES cat_appeal_decision(decision_code),
    appeal_decision_date    DATE,
    decided_by              VARCHAR(100) REFERENCES dim_user(user_id)
);

CREATE TABLE fact_certificate (
    certificate_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    individual_id   VARCHAR(50) NOT NULL REFERENCES dim_individual(individual_id),
    cert_name       VARCHAR(200),
    cert_type_code  VARCHAR(50) REFERENCES cat_certificate_type(cert_type_code),
    issued_at       TIMESTAMP NOT NULL,
    issued_date     DATE NOT NULL,
    issued_by       VARCHAR(100) REFERENCES dim_user(user_id)
);

-- ============================================================
-- DEFERRED FK CONSTRAINTS (cat_* tables created after dims)
-- ============================================================

ALTER TABLE dim_individual
    ADD CONSTRAINT fk_ind_status   FOREIGN KEY (process_status) REFERENCES cat_process_status(status_code),
    ADD CONSTRAINT fk_ind_country  FOREIGN KEY (country_origin) REFERENCES cat_country_origin(country_code),
    ADD CONSTRAINT fk_ind_legal    FOREIGN KEY (legal_status)   REFERENCES cat_legal_status(status_code);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_individual_rg          ON dim_individual(rg_id);
CREATE INDEX idx_individual_status      ON dim_individual(process_status);
CREATE INDEX idx_individual_created     ON dim_individual(created_date);
CREATE INDEX idx_rg_office              ON dim_registration_group(office_id);
CREATE INDEX idx_user_office            ON dim_user(office_id);
CREATE INDEX idx_admissibility_individual  ON fact_admissibility(individual_id);
CREATE INDEX idx_admissibility_date        ON fact_admissibility(created_date);
CREATE INDEX idx_adm_interview_adm         ON fact_adm_interview(admissibility_id);
CREATE INDEX idx_adm_interview_date        ON fact_adm_interview(interview_date);
CREATE INDEX idx_adm_decision_adm          ON fact_adm_decision(admissibility_id);
CREATE INDEX idx_adm_decision_date         ON fact_adm_decision(decision_date);
CREATE INDEX idx_eligibility_individual  ON fact_eligibility(individual_id);
CREATE INDEX idx_eligibility_notif_date  ON fact_eligibility(notification_date_only);
CREATE INDEX idx_certificate_individual ON fact_certificate(individual_id);
CREATE INDEX idx_certificate_date       ON fact_certificate(issued_date);