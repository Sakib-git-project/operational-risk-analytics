-- ============================================================
-- Operational Risk Analysis Queries
-- Run against op_risk.db (sqlite3 op_risk.db < queries.sql)
-- ============================================================

-- 1. Monthly loss totals by business unit
-- Shows loss trend over time per unit -- feeds the Power BI trend chart.
SELECT
    bu.unit_name,
    strftime('%Y-%m', i.event_date) AS loss_month,
    COUNT(*) AS incident_count,
    ROUND(SUM(i.loss_amount), 2) AS total_loss,
    ROUND(AVG(i.loss_amount), 2) AS avg_loss
FROM incidents i
JOIN business_units bu ON i.unit_id = bu.unit_id
GROUP BY bu.unit_name, loss_month
ORDER BY bu.unit_name, loss_month;


-- 2. Incidents tied to WEAK controls where loss exceeded a threshold
-- This is the "control failure" query -- flags where a weak control
-- let a material loss through. High-value finding for a risk committee.
SELECT
    i.incident_id,
    bu.unit_name,
    rr.category,
    c.effectiveness_rating,
    i.event_date,
    i.loss_amount,
    i.root_cause
FROM incidents i
JOIN controls c        ON i.control_id = c.control_id
JOIN risk_register rr  ON i.risk_id = rr.risk_id
JOIN business_units bu ON i.unit_id = bu.unit_id
WHERE c.effectiveness_rating = 'Weak'
  AND i.loss_amount > 25000
ORDER BY i.loss_amount DESC;


-- 3. Year-over-year incident frequency trend
-- Simple frequency trend by category -- feeds the "is this getting worse" question.
SELECT
    strftime('%Y', event_date) AS loss_year,
    event_type,
    COUNT(*) AS incident_count,
    ROUND(SUM(loss_amount), 2) AS total_loss
FROM incidents
GROUP BY loss_year, event_type
ORDER BY event_type, loss_year;


-- 4. Risks with no control testing in the last 12 months
-- Governance gap finding -- controls should be tested periodically.
SELECT
    rr.risk_id,
    rr.category,
    bu.unit_name,
    c.control_id,
    c.effectiveness_rating,
    c.last_tested_date,
    CAST(julianday('now') - julianday(c.last_tested_date) AS INTEGER) AS days_since_tested
FROM controls c
JOIN risk_register rr  ON c.risk_id = rr.risk_id
JOIN business_units bu ON rr.unit_id = bu.unit_id
WHERE julianday('now') - julianday(c.last_tested_date) > 365
ORDER BY days_since_tested DESC;


-- 5. Top 10 costliest risks (by cumulative incident loss)
-- Ranks risks by realized loss, not just the register's likelihood/impact
-- score -- useful for sanity-checking whether the register ratings match reality.
SELECT
    rr.risk_id,
    rr.category,
    bu.unit_name,
    rr.inherent_likelihood,
    rr.inherent_impact,
    rr.residual_likelihood,
    rr.residual_impact,
    COUNT(i.incident_id) AS incident_count,
    ROUND(SUM(i.loss_amount), 2) AS cumulative_loss
FROM risk_register rr
JOIN business_units bu ON rr.unit_id = bu.unit_id
LEFT JOIN incidents i  ON rr.risk_id = i.risk_id
GROUP BY rr.risk_id
ORDER BY cumulative_loss DESC
LIMIT 10;


-- 6. Anomalous (outlier) incidents using IQR method
-- Flags incidents whose loss amount is a statistical outlier vs. the
-- overall loss distribution. A SQL-native way to spot the "tail events"
-- that the Python Monte Carlo model will care about most.
WITH quartiles AS (
    SELECT
        loss_amount,
        NTILE(4) OVER (ORDER BY loss_amount) AS quartile
    FROM incidents
),
bounds AS (
    SELECT
        MAX(CASE WHEN quartile = 1 THEN loss_amount END) AS q1_max,
        MIN(CASE WHEN quartile = 4 THEN loss_amount END) AS q4_min
    FROM quartiles
)
SELECT
    i.incident_id,
    bu.unit_name,
    i.event_date,
    i.loss_amount,
    i.event_type
FROM incidents i
JOIN business_units bu ON i.unit_id = bu.unit_id
CROSS JOIN bounds b
WHERE i.loss_amount > (b.q4_min + 1.5 * (b.q4_min - b.q1_max))
ORDER BY i.loss_amount DESC;


-- 7. Business unit summary -- one-row-per-unit rollup for the dashboard header cards
-- NOTE: risk counts and incident stats are computed in separate subqueries
-- and joined back to business_units. Joining risk_register and incidents
-- directly in one query causes a fan-out (row multiplication) since a unit
-- can have many risks AND many incidents -- the join produces risks x incidents
-- combinations instead of the correct counts. Aggregate first, then join.
SELECT
    bu.unit_name,
    bu.division,
    COALESCE(r.open_risks, 0)              AS open_risks,
    COALESCE(inc.total_incidents, 0)       AS total_incidents,
    ROUND(COALESCE(inc.total_loss, 0), 2)  AS total_loss,
    ROUND(COALESCE(inc.avg_loss, 0), 2)    AS avg_loss_per_incident
FROM business_units bu
LEFT JOIN (
    SELECT unit_id, COUNT(*) AS open_risks
    FROM risk_register
    GROUP BY unit_id
) r ON bu.unit_id = r.unit_id
LEFT JOIN (
    SELECT unit_id,
           COUNT(*) AS total_incidents,
           SUM(loss_amount) AS total_loss,
           AVG(loss_amount) AS avg_loss
    FROM incidents
    GROUP BY unit_id
) inc ON bu.unit_id = inc.unit_id
ORDER BY total_loss DESC;
