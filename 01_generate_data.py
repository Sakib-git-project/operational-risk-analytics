"""
Step 1: Generate a synthetic vendor dataset.

Why synthetic data here: we don't have the real A&S Construction vendor
records, so we build fake data that mirrors the *structure and patterns*
of real vendor risk data. The key is baking in realistic relationships
(e.g., vendors with more past delays are more likely to delay again)
so the analysis has something real to find -- not just noise.
"""

import numpy as np
import pandas as pd

np.random.seed(42)  # reproducibility -- same data every time we run this

N_VENDORS = 600

# --- Base vendor attributes ---
years_in_business = np.random.gamma(shape=3, scale=3, size=N_VENDORS).clip(0.5, 30)
num_past_projects = np.random.poisson(lam=8, size=N_VENDORS).clip(1, 60)

# Past delay rate: proportion of past projects delivered late.
# Most vendors cluster low, a smaller group is chronically late (realistic skew).
past_delay_rate = np.random.beta(a=2, b=6, size=N_VENDORS)

# Cost variance: % over/under budget on past projects (can be negative = under budget)
avg_cost_variance_pct = np.random.normal(loc=5, scale=12, size=N_VENDORS)

# Contract compliance score (0-100): how well they meet contract terms
# (paperwork, insurance, safety compliance, etc.)
contract_compliance_score = np.random.normal(loc=80, scale=15, size=N_VENDORS).clip(20, 100)

# Current project size ($) -- bigger projects carry more exposure
current_project_budget = np.random.lognormal(mean=11, sigma=0.8, size=N_VENDORS).clip(5000, 2_000_000)

# Communication responsiveness (days to respond to RFIs/change orders)
avg_response_days = np.random.gamma(shape=2, scale=2, size=N_VENDORS).clip(0.2, 20)

df = pd.DataFrame({
    "vendor_id": [f"V{1000+i}" for i in range(N_VENDORS)],
    "years_in_business": years_in_business.round(1),
    "num_past_projects": num_past_projects,
    "past_delay_rate": past_delay_rate.round(3),
    "avg_cost_variance_pct": avg_cost_variance_pct.round(1),
    "contract_compliance_score": contract_compliance_score.round(1),
    "current_project_budget": current_project_budget.round(0),
    "avg_response_days": avg_response_days.round(1),
})

# --- Build the TARGET: is this vendor "high risk" on the current project? ---
# We define high risk using a weighted combination of the real risk drivers,
# then add randomness -- this mimics how real-world outcomes are influenced
# by measurable factors PLUS things we can't observe (unmeasured risk).
risk_score = (
    3.0 * df["past_delay_rate"]
    + 0.03 * df["avg_cost_variance_pct"].clip(lower=0)   # only overruns add risk
    - 0.02 * df["contract_compliance_score"]
    - 0.05 * df["years_in_business"]
    + 0.08 * df["avg_response_days"]
    + np.random.normal(0, 0.4, size=N_VENDORS)            # unobserved noise
)

# Convert to probability with a logistic function, then sample the outcome.
# Shift by the 75th percentile (not the mean) so high_risk is a realistic
# MINORITY class (~20-25%), like real vendor pools -- most vendors are fine,
# a smaller group is genuinely risky. This imbalance matters later when we
# evaluate the model (accuracy alone would be misleading).
threshold = risk_score.quantile(0.75)
prob_high_risk = 1 / (1 + np.exp(-(risk_score - threshold)))
df["high_risk"] = (np.random.rand(N_VENDORS) < prob_high_risk).astype(int)

df.to_csv("vendor_data.csv", index=False)

print(df.head(10))
print(f"\nTotal vendors: {len(df)}")
print(f"High-risk vendors: {df['high_risk'].sum()} ({df['high_risk'].mean():.1%})")
