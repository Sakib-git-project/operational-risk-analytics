"""
risk_model.py
--------------
Phase 2: Operational risk quantitative analysis.

Pulls real incident data from op_risk.db (built in Phase 1) and:
  1. Fits a frequency distribution (Poisson) to monthly incident counts
  2. Fits a severity distribution (lognormal) to individual loss amounts
  3. Runs a Monte Carlo simulation to estimate the distribution of
     total ANNUAL losses
  4. Calculates VaR (Value at Risk) and CVaR (Conditional VaR / Expected
     Shortfall) at the 95% and 99% confidence levels
  5. Flags individual incidents that are statistical outliers (z-score)
  6. Exports results to CSV files that Power BI can connect to later

This mirrors the real-world "Loss Distribution Approach" (LDA) used in
operational risk capital modeling under Basel frameworks.
"""

import sqlite3
import numpy as np
import pandas as pd
from scipy import stats

DB_PATH = "op_risk.db"
N_SIMULATIONS = 10_000
RANDOM_SEED = 42

np.random.seed(RANDOM_SEED)


# ----------------------------------------------------------------------
# Step 1: Pull real data from the SQL database
# ----------------------------------------------------------------------
def load_incident_data(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT i.incident_id, i.event_date, i.loss_amount, i.event_type,
               i.root_cause, bu.unit_name
        FROM incidents i
        JOIN business_units bu ON i.unit_id = bu.unit_id
        """,
        conn,
    )
    conn.close()
    df["event_date"] = pd.to_datetime(df["event_date"])
    return df


# ----------------------------------------------------------------------
# Step 2: Fit frequency distribution (Poisson) -- how OFTEN incidents happen
# ----------------------------------------------------------------------
def fit_frequency_distribution(df):
    """
    Count incidents per month, then estimate the Poisson rate parameter
    (lambda) as the average monthly incident count. Poisson is the
    standard choice for modeling event counts in a fixed time window.
    """
    df["year_month"] = df["event_date"].dt.to_period("M")
    monthly_counts = df.groupby("year_month").size()

    # Some months may have zero incidents and won't appear in groupby --
    # fill in the full date range so the average reflects true monthly rate.
    full_range = pd.period_range(
        start=df["event_date"].min().to_period("M"),
        end=df["event_date"].max().to_period("M"),
        freq="M",
    )
    monthly_counts = monthly_counts.reindex(full_range, fill_value=0)

    lambda_monthly = monthly_counts.mean()
    lambda_annual = lambda_monthly * 12

    return lambda_monthly, lambda_annual, monthly_counts


# ----------------------------------------------------------------------
# Step 3: Fit severity distribution (lognormal) -- how BIG losses are
# ----------------------------------------------------------------------
def fit_severity_distribution(df):
    """
    Fit a lognormal distribution to loss amounts. Lognormal is standard
    for operational loss severity because losses are strictly positive
    and right-skewed (many small losses, a few very large ones).

    scipy's lognorm.fit returns (shape, loc, scale) where:
      shape = sigma of the underlying normal distribution
      scale = exp(mu) of the underlying normal distribution
    We fix loc=0 since losses start at zero, not some negative offset.
    """
    losses = df["loss_amount"].values
    shape, loc, scale = stats.lognorm.fit(losses, floc=0)
    return shape, scale


# ----------------------------------------------------------------------
# Step 4: Monte Carlo simulation
# ----------------------------------------------------------------------
def run_monte_carlo(lambda_annual, sigma, scale, n_simulations=N_SIMULATIONS):
    """
    For each of n_simulations "simulated years":
      1. Draw a random number of incidents from Poisson(lambda_annual)
      2. Draw that many loss amounts from the fitted lognormal
      3. Sum them to get that simulated year's total loss

    The resulting array of n_simulations total losses approximates the
    full distribution of possible annual losses -- this is what VaR/CVaR
    get calculated from.
    """
    annual_losses = np.zeros(n_simulations)

    for i in range(n_simulations):
        n_incidents = np.random.poisson(lam=lambda_annual)
        if n_incidents > 0:
            simulated_losses = stats.lognorm.rvs(
                s=sigma, loc=0, scale=scale, size=n_incidents
            )
            annual_losses[i] = simulated_losses.sum()
        else:
            annual_losses[i] = 0.0

    return annual_losses


# ----------------------------------------------------------------------
# Step 5: Risk metrics -- VaR and CVaR
# ----------------------------------------------------------------------
def calculate_risk_metrics(annual_losses):
    expected_loss = annual_losses.mean()

    var_95 = np.percentile(annual_losses, 95)
    var_99 = np.percentile(annual_losses, 99)

    # CVaR (a.k.a. Expected Shortfall) = average loss GIVEN that
    # loss exceeds VaR -- answers "how bad is the bad case, on average"
    cvar_95 = annual_losses[annual_losses >= var_95].mean()
    cvar_99 = annual_losses[annual_losses >= var_99].mean()

    unexpected_loss_95 = var_95 - expected_loss  # capital buffer needed above expected loss

    return {
        "expected_annual_loss": expected_loss,
        "var_95": var_95,
        "var_99": var_99,
        "cvar_95": cvar_95,
        "cvar_99": cvar_99,
        "unexpected_loss_95": unexpected_loss_95,
    }


# ----------------------------------------------------------------------
# Step 6: Outlier detection on historical incidents (z-score method)
# ----------------------------------------------------------------------
def flag_outliers(df, z_threshold=2.5):
    """
    Flags incidents whose loss amount is unusually large relative to
    the rest of the data, using a z-score on log-transformed losses
    (log transform because raw losses are heavily right-skewed, which
    would make a raw z-score misleading).
    """
    log_losses = np.log(df["loss_amount"])
    z_scores = (log_losses - log_losses.mean()) / log_losses.std()

    df = df.copy()
    df["z_score"] = z_scores
    df["is_outlier"] = df["z_score"] > z_threshold
    return df


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    print("Loading incident data from op_risk.db ...")
    df = load_incident_data(DB_PATH)
    print(f"  Loaded {len(df)} incidents\n")

    print("Fitting frequency distribution (Poisson) ...")
    lambda_monthly, lambda_annual, monthly_counts = fit_frequency_distribution(df)
    print(f"  Avg incidents/month (lambda): {lambda_monthly:.3f}")
    print(f"  Implied incidents/year:       {lambda_annual:.3f}\n")

    print("Fitting severity distribution (lognormal) ...")
    sigma, scale = fit_severity_distribution(df)
    print(f"  Sigma (shape): {sigma:.3f}")
    print(f"  Scale:         {scale:,.2f}\n")

    print(f"Running Monte Carlo simulation ({N_SIMULATIONS:,} simulated years) ...")
    annual_losses = run_monte_carlo(lambda_annual, sigma, scale)
    print("  Done.\n")

    print("Calculating risk metrics ...")
    metrics = calculate_risk_metrics(annual_losses)
    for k, v in metrics.items():
        print(f"  {k:22s}: ${v:,.2f}")
    print()

    print("Flagging outlier incidents (z-score method) ...")
    df_flagged = flag_outliers(df)
    n_outliers = df_flagged["is_outlier"].sum()
    print(f"  Flagged {n_outliers} outlier incidents out of {len(df_flagged)}\n")

    # ------------------------------------------------------------------
    # Export results for Power BI / further analysis
    # ------------------------------------------------------------------
    print("Exporting results to CSV ...")

    # 1. Simulated annual loss distribution (for a histogram in Power BI)
    pd.DataFrame({"simulated_annual_loss": annual_losses}).to_csv(
        "simulated_annual_losses.csv", index=False
    )

    # 2. Summary risk metrics (single row -- for dashboard summary cards)
    pd.DataFrame([metrics]).to_csv("risk_metrics_summary.csv", index=False)

    # 3. Flagged incidents (full incident list with outlier flag + z-score)
    df_flagged.to_csv("incidents_with_outlier_flags.csv", index=False)

    # 4. Monthly incident counts (for a frequency trend chart)
    monthly_counts.rename("incident_count").reset_index().rename(
        columns={"index": "year_month"}
    ).to_csv("monthly_incident_counts.csv", index=False)

    print("  simulated_annual_losses.csv")
    print("  risk_metrics_summary.csv")
    print("  incidents_with_outlier_flags.csv")
    print("  monthly_incident_counts.csv")
    print("\nPhase 2 complete.")


if __name__ == "__main__":
    main()
