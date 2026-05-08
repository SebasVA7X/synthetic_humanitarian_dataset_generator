-- ============================================================
-- STATIC CATALOGS
-- All reference/lookup data — no Faker needed
-- ============================================================

-- Offices
INSERT INTO dim_office (office_name) VALUES
    ('Quito'),
    ('Guayaquil'),
    ('Manta'),
    ('El Puyo'),
    ('Cuenca'),
    ('Riobamba'),
    ('Macara');

-- Process Status
INSERT INTO cat_process_status (status_code, status_name) VALUES
    ('active',      'Active'),
    ('inactive',    'Inactive'),
    ('hold',        'On Hold'),
    ('closed',      'Closed');

-- Country of Origin
INSERT INTO cat_country_origin (country_code, country_name) VALUES
    ('VEN',     'Venezuela'),
    ('COL',     'Colombia'),
    ('STA',     'Stateless'),
    ('CUB',     'Cuba'),
    ('PER',     'Peru'),
    ('HTI',     'Haiti'),
    ('SYR',     'Syria'),
    ('LEB',     'Lebanon');

-- Legal Status
INSERT INTO cat_legal_status (status_code, status_name) VALUES
    ('asylum_seeker',       'Asylum Seeker'),
    ('idp',                 'Internally Displaced Person'),
    ('not_of_concern',      'Not of Concern'),
    ('other_of_concern',    'Other of Concern'),
    ('refugee',             'Refugee'),
    ('refugee_like',        'Refugee-like Situation'),
    ('returned_idp',        'Returned Displaced Person'),
    ('returnee',            'Returnee'),
    ('stateless',           'Stateless Person');

-- Admissibility Decision Types
INSERT INTO cat_admissibility_decision (decision_code, decision_name) VALUES
    ('ADM',         'Approved'),
    ('ADM_AP',      'Approved on Appeal'),
    ('ADM_NOT',     'Approval Notification Issued'),
    ('INAD',        'Denied'),
    ('INAD_AP',     'Denied on Appeal'),
    ('INAD_NOT',    'Denial Notification Issued'),
    ('INAD_SOL',    'Appeal Submission Received'),
    ('INAD_PROJ',   'Appeal Response Draft'),
    ('INAD_REV',    'Appeal Response Under Review'),
    ('OTHER',       'Other');

-- Admissibility Decision Basis
INSERT INTO cat_admissibility_decision_basis (basis_code, basis_name) VALUES
    ('BASIS_UNFOUNDED_B',   'Unfounded - Category B'),
    ('BASIS_ADMITTED',      'Approved'),
    ('BASIS_FRAUD_C',       'Fraudulent Application - Type C'),
    ('BASIS_EXTEMP',        'Filed Out of Time'),
    ('BASIS_FRAUD_A',       'Fraudulent Application - Type A'),
    ('BASIS_UNFOUNDED_C',   'Unfounded - Category C'),
    ('BASIS_UNFOUNDED_A',   'Unfounded - Category A'),
    ('BASIS_FRAUD_B',       'Fraudulent Application - Type B'),
    ('BASIS_EXTEMP_LATE',   'Filed Out of Time - Late Submission');

-- Notification Types
INSERT INTO cat_notification_type (notification_code, notification_name) VALUES
    ('email',           'Email'),
    ('hand_delivery',   'In-Person Delivery'),
    ('mail',            'Postal Mail'),
    ('phone',           'Phone'),
    ('self_service',    'Online Self-Service');

-- Process Types
INSERT INTO cat_process_type (process_type_code, process_type_name) VALUES
    (5001,      'Status Determination'),
    (5002,      'Derivative Case'),
    (5003,      'Case Reopening'),
    (5004,      'Cancellation'),
    (5005,      'Cessation'),
    (5006,      'Revocation');

-- Eligibility Recommendations
INSERT INTO cat_eligibility_recommendation (recommendation_code, recommendation_name) VALUES
    (101001, 'Status Granted'),
    (101002, 'Status Denied'),
    (101003, 'Status Maintained'),
    (101004, 'Status Cancelled'),
    (101005, 'Status Revoked'),
    (101006, 'Status Ceased');

-- Recommendation Reasons
INSERT INTO cat_recommendation_reason (reason_code, reason_name) VALUES
    (101001, 'Inclusion Criteria Met'),
    (101002, 'General Inclusion Grounds'),
    (101003, 'Specific Inclusion Grounds'),
    (101004, 'Other Grounds'),
    (101005, 'Internal Protection Available'),
    (101006, 'Exclusion Clause Applied'),
    (101007, 'Serious Threat Identified');

-- Review Decisions
INSERT INTO cat_review_decision (decision_code, decision_name) VALUES
    (101001, 'Recommendation Accepted'),
    (101002, 'Returned for Further Review'),
    (101003, 'Returned for Additional Interview'),
    (101004, 'Pending Review');

-- Appeal Recommendations
INSERT INTO cat_appeal_recommendation (recommendation_code, recommendation_name) VALUES
    ('Recognition',     'Grant Status'),
    ('Rejection',       'Deny Status'),
    ('Ceased',          'Cease Status');

-- Appeal Decisions
INSERT INTO cat_appeal_decision (decision_code, decision_name) VALUES
    (101001, 'Recommendation Accepted'),
    (101002, 'Returned for Additional Interview'),
    (101003, 'Pending Review');

-- Certificate Types
INSERT INTO cat_certificate_type (cert_type_code, cert_type_name, cert_subtype) VALUES
    ('CERT_REG',        'Certificate',  'Registration'),
    ('CERT_INTERVIEW',  'Certificate',  'Interview'),
    ('CERT_APPT',       'Certificate',  'Appointment'),
    ('OTHER',           'Other',        NULL);

-- Reviewer Categories
INSERT INTO cat_reviewer_category (category_code, category_name) VALUES
    ('officer',     'Protection Officer'),
    ('senior',      'Senior Protection Officer'),
    ('supervisor',  'Supervisor'),
    ('external',    'External Reviewer');
