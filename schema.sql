-- ============================================================
-- Operational Risk Database Schema
-- ============================================================

DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS controls;
DROP TABLE IF EXISTS risk_register;
DROP TABLE IF EXISTS business_units;

CREATE TABLE business_units (
    unit_id      INTEGER PRIMARY KEY,
    unit_name    TEXT NOT NULL,
    division     TEXT NOT NULL
);

CREATE TABLE risk_register (
    risk_id              INTEGER PRIMARY KEY,
    unit_id              INTEGER NOT NULL,
    category             TEXT NOT NULL,       -- e.g. Basel op risk event type
    description          TEXT NOT NULL,
    inherent_likelihood   INTEGER NOT NULL,    -- 1-5 scale
    inherent_impact        INTEGER NOT NULL,    -- 1-5 scale
    residual_likelihood    INTEGER NOT NULL,    -- 1-5 scale, after controls
    residual_impact         INTEGER NOT NULL,    -- 1-5 scale, after controls
    risk_owner            TEXT NOT NULL,
    date_identified       TEXT NOT NULL,
    FOREIGN KEY (unit_id) REFERENCES business_units(unit_id)
);

CREATE TABLE controls (
    control_id            INTEGER PRIMARY KEY,
    risk_id                INTEGER NOT NULL,
    control_description    TEXT NOT NULL,
    control_type          TEXT NOT NULL,      -- Preventive / Detective / Corrective
    effectiveness_rating   TEXT NOT NULL,      -- Strong / Adequate / Weak
    last_tested_date       TEXT NOT NULL,
    FOREIGN KEY (risk_id) REFERENCES risk_register(risk_id)
);

CREATE TABLE incidents (
    incident_id    INTEGER PRIMARY KEY,
    unit_id        INTEGER NOT NULL,
    risk_id        INTEGER NOT NULL,
    control_id     INTEGER,                    -- control that was supposed to prevent this (nullable)
    event_date     TEXT NOT NULL,
    loss_amount    REAL NOT NULL,
    event_type     TEXT NOT NULL,               -- Basel event category
    root_cause     TEXT NOT NULL,
    description    TEXT,
    FOREIGN KEY (unit_id) REFERENCES business_units(unit_id),
    FOREIGN KEY (risk_id) REFERENCES risk_register(risk_id),
    FOREIGN KEY (control_id) REFERENCES controls(control_id)
);

CREATE INDEX idx_incidents_date ON incidents(event_date);
CREATE INDEX idx_incidents_unit ON incidents(unit_id);
CREATE INDEX idx_incidents_risk ON incidents(risk_id);
