# Operational Risk Analytics

An end-to-end operational risk management pipeline — from raw incident data to a governance-ready risk register — built to mirror how a real risk team's tooling connects across SQL, Python, Power BI, and formal reporting.

## Overview

This project simulates the operational risk function of a mid-size financial institution across four connected phases. Each phase feeds the next using the same underlying data — nothing here is a standalone toy exercise.

```
SQL (data foundation) → Python (quantitative model) → Power BI (reporting) → Risk Register (governance)
```

## Phase 1 — SQL Data Layer

Incident frequency is generated as a function of each control's effectiveness score, so weaker controls produce statistically more incidents, this causal link is what the quantitative model later validates.

A relational SQLite database (`op_risk.db`) with four tables: `business_units`, `risk_register`, `controls`, and `incidents`, linked by foreign keys. Synthetic but realistic data was generated with proper statistical structure — loss severity follows a lognormal distribution (many small losses, a few large ones) and incident frequency correlates with control effectiveness (weak controls produce more incidents).

- **8** business units · **40** registered risks · **58** controls · **233** incidents · **$4.5M** total historical loss

`schema.sql` · `01_generate_data.py` · `queries.sql` (7 tested analysis queries covering loss trends, control failures, overdue testing, and outlier detection)

## Phase 2 — Python Quantitative Model

Pulls the real incident data from the SQL database and applies a Loss Distribution Approach (LDA), the standard actuarial method for operational risk capital modeling:

- **Frequency** modeled via Poisson distribution
- **Severity** modeled via lognormal distribution
- **Monte Carlo simulation** — 10,000 simulated years — to estimate the full distribution of possible annual losses
- **Outlier detection** on historical incidents via z-score

### Key results

| Metric | Value |
|---|---|
| Expected Annual Loss | $1,600,373 |
| Value at Risk (95%) | $2,571,369 |
| Value at Risk (99%) | $3,453,258 |
| Conditional VaR (95%) | $3,150,662 |
| Unexpected Loss (95%) | $970,995 |

`risk_model.py`

## Phase 3 — Power BI Dashboard

An interactive report built in Power BI Service, connected directly to the SQL and Python outputs (not static pasted numbers):

- Summary cards — Expected Loss, VaR 95%/99%, CVaR 95%
- Loss trend over time
- Risk heat map (likelihood × impact, sized by cumulative loss)
- Detail table of incidents tied to weak controls

`dashboard_data.xlsx` (consolidated data source for the report)
![Dashboard screenshot](docs/dashboard_screenshot.png)
## Phase 4 — Risk Register (Governance)

A formal Word document tying the quantitative model back to governance: for each of the 40 risks, inherent risk → controls → residual risk, cross-checked against the Monte Carlo output and realized losses.

**Key finding:** 43 controls had not been tested in over 180 days — a governance gap surfaced directly from the data, not assumed.

`Operational_Risk_Register.docx`

## Tech Stack

- **SQL** — SQLite
- **Python** — pandas, numpy, scipy (Poisson, lognormal, Monte Carlo)
- **Power BI** — Service (cloud-based reporting)
- **Documentation** — Node.js (`docx` library) for automated report generation

## Repository Structure

```
schema.sql                          # Database schema
01_generate_data.py                 # Synthetic data generator
queries.sql                         # SQL analysis queries
run_queries.py                      # Runs all queries, prints results
op_risk.db                          # Built SQLite database
risk_model.py                       # Monte Carlo risk model
risk_metrics_summary.csv            # Model output: VaR/CVaR
simulated_annual_losses.csv         # 10,000 Monte Carlo simulation results
incidents_with_outlier_flags.csv    # Historical incidents + outlier detection
monthly_incident_counts.csv         # Frequency data
dashboard_data.xlsx                 # Consolidated Power BI data source
build_register.js                   # Generates the risk register document
register_data.json                  # Data feeding the register
Operational_Risk_Register.docx      # Final governance document
```

## Methodology Notes

Risk categories follow the Basel II operational risk event-type taxonomy. Risk scoring uses a standard 1-5 likelihood/impact scale, tracked both before controls (inherent) and after (residual). The quantitative model exists specifically to validate register ratings against reality — risks with high realized losses but low assigned ratings are flagged for re-assessment, rather than trusting the register's initial scoring alone.


## How to Run

```bash
   pip install -r requirements.txt

   python 01_generate_data.py
   python run_queries.py
   python risk_model.py

   npm install
   node build_register.js
```
