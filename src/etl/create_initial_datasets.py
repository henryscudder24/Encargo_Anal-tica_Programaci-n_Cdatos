from __future__ import annotations

import json
import sqlite3
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
SOURCE_CSV = REPO_ROOT / "Modelos ML" / "tech_mental_health_burnout_cleaned_from_dirty.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
SQL_DIR = PROJECT_ROOT / "data" / "sql"
SQLITE_DB = SQL_DIR / "burnout_context.db"
COMPANY_API_URL = os.getenv("COMPANY_API_URL", "").rstrip("/")

REQUIRED_COLUMNS = {
    "age",
    "gender",
    "job_role",
    "experience_years",
    "company_size",
    "work_mode",
    "work_hours_per_week",
    "overtime_hours",
    "meetings_per_day",
    "deadlines_missed",
    "job_satisfaction",
    "manager_support",
    "work_life_balance",
    "sleep_hours",
    "physical_activity_days",
    "screen_time_hours",
    "caffeine_intake",
    "social_support_score",
    "has_therapy",
    "stress_level",
    "anxiety_score",
    "depression_score",
    "burnout_score",
    "burnout_level",
    "seeks_professional_help",
}

EXPECTED_COMPANY_SIZES = {"Startup", "Mid-size", "Large", "MNC"}
EXPECTED_WORK_MODES = {"Remote", "Hybrid", "Onsite"}
COMPANY_COLUMNS = [
    "company_id",
    "company_alias",
    "company_size",
    "supported_roles",
    "primary_segment",
    "remote_policy",
    "country",
    "city",
    "region",
    "latitude",
    "longitude",
    "timezone",
]


@dataclass(frozen=True)
class Location:
    country: str
    city: str
    region: str
    latitude: float
    longitude: float
    timezone: str


LOCATIONS = [
    Location("Chile", "Santiago", "South America", -33.4489, -70.6693, "America/Santiago"),
    Location("Chile", "Valparaiso", "South America", -33.0472, -71.6127, "America/Santiago"),
    Location("Chile", "Concepcion", "South America", -36.8201, -73.0444, "America/Santiago"),
    Location("Argentina", "Buenos Aires", "South America", -34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
    Location("Uruguay", "Montevideo", "South America", -34.9011, -56.1645, "America/Montevideo"),
    Location("Peru", "Lima", "South America", -12.0464, -77.0428, "America/Lima"),
    Location("Colombia", "Bogota", "South America", 4.7110, -74.0721, "America/Bogota"),
    Location("Brazil", "Sao Paulo", "South America", -23.5505, -46.6333, "America/Sao_Paulo"),
    Location("Mexico", "Mexico City", "North America", 19.4326, -99.1332, "America/Mexico_City"),
    Location("United States", "Miami", "North America", 25.7617, -80.1918, "America/New_York"),
    Location("Canada", "Toronto", "North America", 43.6532, -79.3832, "America/Toronto"),
    Location("Spain", "Madrid", "Europe", 40.4168, -3.7038, "Europe/Madrid"),
]

ROLE_PORTFOLIOS = [
    ["Software Engineer", "Backend Developer", "Frontend Developer", "QA Engineer", "DevOps"],
    ["Software Engineer", "Data Scientist", "ML Engineer", "Backend Developer", "Product Manager"],
    ["Software Engineer", "Frontend Developer", "Backend Developer", "Product Manager", "QA Engineer"],
    ["Software Engineer", "DevOps", "Data Scientist", "ML Engineer", "QA Engineer"],
]

COMPANY_COUNTS = {
    "Startup": 24,
    "Mid-size": 28,
    "Large": 24,
    "MNC": 20,
}

REMOTE_POLICY_BY_SIZE = {
    "Startup": ["Remote-first", "Hybrid-flex"],
    "Mid-size": ["Hybrid-flex", "Office-optional", "Remote-first"],
    "Large": ["Hybrid-standard", "Office-optional"],
    "MNC": ["Hybrid-standard", "Regional-policy"],
}

SEGMENTS = [
    "SaaS",
    "Fintech",
    "Healthtech",
    "Retail Tech",
    "Cloud Services",
    "Data Platforms",
    "Cybersecurity",
    "Enterprise Software",
]

INTERVENTION_TYPES = [
    "Manager enablement",
    "Meeting load reduction",
    "Focus time program",
    "Mental health support",
    "Overtime control",
    "Recovery and sleep campaign",
    "Workload triage",
    "Flexible schedule reset",
]

INTERVENTION_STATUS = ["Active", "Planned", "Completed", "Paused"]


def validate_source(df: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    critical = ["job_role", "company_size", "work_mode", "burnout_score"]
    null_counts = df[critical].isna().sum()
    with_nulls = null_counts[null_counts > 0]
    if not with_nulls.empty:
        raise ValueError(f"Null values in critical columns: {with_nulls.to_dict()}")

    unknown_sizes = set(df["company_size"].unique()) - EXPECTED_COMPANY_SIZES
    if unknown_sizes:
        raise ValueError(f"Unexpected company_size values: {sorted(unknown_sizes)}")

    unknown_modes = set(df["work_mode"].unique()) - EXPECTED_WORK_MODES
    if unknown_modes:
        raise ValueError(f"Unexpected work_mode values: {sorted(unknown_modes)}")


def make_company_aliases(job_roles: list[str]) -> pd.DataFrame:
    rows = []
    location_weights = {
        "Startup": [0.28, 0.08, 0.06, 0.09, 0.05, 0.07, 0.08, 0.08, 0.08, 0.04, 0.04, 0.05],
        "Mid-size": [0.22, 0.07, 0.07, 0.10, 0.05, 0.08, 0.09, 0.09, 0.08, 0.05, 0.05, 0.05],
        "Large": [0.18, 0.05, 0.05, 0.10, 0.05, 0.08, 0.10, 0.12, 0.10, 0.07, 0.05, 0.05],
        "MNC": [0.12, 0.03, 0.03, 0.08, 0.04, 0.06, 0.08, 0.14, 0.12, 0.10, 0.10, 0.10],
    }

    rng = np.random.default_rng(20260622)

    for size, count in COMPANY_COUNTS.items():
        policies = REMOTE_POLICY_BY_SIZE[size]
        for idx in range(1, count + 1):
            loc = rng.choice(LOCATIONS, p=location_weights[size])
            portfolio = ROLE_PORTFOLIOS[(idx - 1) % len(ROLE_PORTFOLIOS)]

            if size in {"Large", "MNC"}:
                supported_roles = sorted(job_roles)
            else:
                supported_roles = sorted(set(portfolio))

            rows.append(
                {
                    "company_id": f"ORG-{size.upper().replace('-', '')}-{idx:03d}",
                    "company_alias": f"Alias {size.upper().replace('-', '')}-{idx:03d}",
                    "company_size": size,
                    "supported_roles": "|".join(supported_roles),
                    "primary_segment": SEGMENTS[(idx - 1) % len(SEGMENTS)],
                    "remote_policy": policies[(idx - 1) % len(policies)],
                    "country": loc.country,
                    "city": loc.city,
                    "region": loc.region,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "timezone": loc.timezone,
                }
            )

    companies = pd.DataFrame(rows)
    coverage = (
        companies.assign(supported_roles=companies["supported_roles"].str.split("|"))
        .explode("supported_roles")
        .groupby(["company_size", "supported_roles"])
        .size()
    )
    missing_pairs = [
        (size, role)
        for size in EXPECTED_COMPANY_SIZES
        for role in job_roles
        if (size, role) not in coverage.index
    ]
    if missing_pairs:
        raise ValueError(f"Company alias coverage is incomplete: {missing_pairs[:10]}")

    return companies


def validate_companies(companies: pd.DataFrame, job_roles: list[str]) -> None:
    missing_columns = sorted(set(COMPANY_COLUMNS) - set(companies.columns))
    if missing_columns:
        raise ValueError(f"Missing company columns: {missing_columns}")

    duplicated_ids = companies["company_id"].duplicated().sum()
    if duplicated_ids:
        raise ValueError(f"Duplicated company_id values: {duplicated_ids}")

    unknown_sizes = set(companies["company_size"].unique()) - EXPECTED_COMPANY_SIZES
    if unknown_sizes:
        raise ValueError(f"Unexpected API company_size values: {sorted(unknown_sizes)}")

    coverage = (
        companies.assign(supported_roles=companies["supported_roles"].str.split("|"))
        .explode("supported_roles")
        .groupby(["company_size", "supported_roles"])
        .size()
    )
    missing_pairs = [
        (size, role)
        for size in EXPECTED_COMPANY_SIZES
        for role in job_roles
        if (size, role) not in coverage.index
    ]
    if missing_pairs:
        raise ValueError(f"Company alias coverage is incomplete: {missing_pairs[:10]}")


def fetch_company_aliases_from_api(api_url: str, job_roles: list[str]) -> pd.DataFrame:
    endpoint = f"{api_url}/companies"
    try:
        with urlopen(endpoint, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"Could not fetch company aliases from API: {endpoint}") from exc

    companies = pd.DataFrame(payload)
    validate_companies(companies, job_roles)
    return companies[list(COMPANY_COLUMNS)]


def load_company_aliases(job_roles: list[str]) -> tuple[pd.DataFrame, str]:
    if COMPANY_API_URL:
        return fetch_company_aliases_from_api(COMPANY_API_URL, job_roles), f"{COMPANY_API_URL}/companies"

    companies = make_company_aliases(job_roles)
    validate_companies(companies, job_roles)
    return companies, "generated_local"


def assign_companies(df: pd.DataFrame, companies: pd.DataFrame) -> pd.Series:
    rng = np.random.default_rng(20260622)
    assignments = pd.Series(index=df.index, dtype="object")

    expanded = companies.assign(supported_roles=companies["supported_roles"].str.split("|")).explode("supported_roles")

    for (size, role), group_idx in df.groupby(["company_size", "job_role"]).groups.items():
        candidates = expanded[
            (expanded["company_size"] == size) & (expanded["supported_roles"] == role)
        ].copy()
        if candidates.empty:
            raise ValueError(f"No company aliases available for size={size}, role={role}")

        weights = np.ones(len(candidates), dtype=float)
        if size == "Startup":
            weights *= np.linspace(1.4, 0.7, len(candidates))
        elif size == "MNC":
            weights *= np.linspace(1.1, 0.9, len(candidates))

        weights = weights / weights.sum()
        assignments.loc[list(group_idx)] = rng.choice(candidates["company_id"], size=len(group_idx), p=weights)

    return assignments


def make_quality_report(
    source_rows: int,
    source_columns: int,
    enriched: pd.DataFrame,
    companies: pd.DataFrame,
    threshold: float,
    interventions: pd.DataFrame,
    operations: pd.DataFrame,
) -> dict:
    mismatch_count = int(
        (enriched["company_size"] != enriched["company_size_company"]).sum()
    )
    return {
        "source_file": str(SOURCE_CSV),
        "company_source": f"{COMPANY_API_URL}/companies" if COMPANY_API_URL else "generated_local",
        "rows": int(source_rows),
        "columns_source": int(source_columns),
        "columns_enriched": int(enriched.shape[1]),
        "company_aliases": int(len(companies)),
        "sqlite_database": str(SQLITE_DB),
        "interventions": int(len(interventions)),
        "operation_months": int(operations["period_month"].nunique()),
        "operation_rows": int(len(operations)),
        "burnout_risk_threshold_p75": round(float(threshold), 4),
        "high_burnout_risk_rate": round(float(enriched["high_burnout_risk"].mean()), 4),
        "respondent_id_unique": bool(enriched["respondent_id"].is_unique),
        "company_size_mismatches": mismatch_count,
        "missing_coordinates": int(enriched[["latitude", "longitude"]].isna().any(axis=1).sum()),
        "company_size_distribution": enriched["company_size"].value_counts().to_dict(),
        "work_mode_distribution": enriched["work_mode"].value_counts().to_dict(),
        "burnout_level_distribution": enriched["burnout_level"].value_counts().to_dict(),
    }


def make_context_tables(company_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(20260623)
    periods = pd.period_range("2025-07", "2026-06", freq="M").astype(str)
    intervention_rows = []
    operation_rows = []

    size_cost_multiplier = {
        "Startup": 0.75,
        "Mid-size": 1.0,
        "Large": 1.45,
        "MNC": 1.85,
    }

    for idx, row in company_metrics.reset_index(drop=True).iterrows():
        risk = float(row["high_burnout_risk_rate"])
        overtime = float(row["overtime_avg"])
        support_gap = max(0.0, 5.0 - float(row["manager_support_avg"]))
        recovery_gap = max(0.0, 7.0 - float(row["sleep_hours_avg"]))
        pressure = np.clip((risk * 2.2) + (overtime / 18) + (support_gap / 6) + (recovery_gap / 5), 0, 1.6)

        intervention_count = 1 + int(pressure > 0.78) + int(pressure > 1.02)
        if row["company_size"] in {"Large", "MNC"} and pressure > 0.66:
            intervention_count += 1

        for number in range(intervention_count):
            status_weights = np.array([0.38 + min(risk, 0.45), 0.30, 0.22, 0.10])
            status_weights = status_weights / status_weights.sum()
            status = rng.choice(INTERVENTION_STATUS, p=status_weights)
            start_period = periods[max(0, min(len(periods) - 1, int(rng.normal(5 + number, 2))))]
            duration_months = int(rng.integers(3, 9))
            start_index = list(periods).index(start_period)
            end_index = min(len(periods) - 1, start_index + duration_months)
            intervention_type = INTERVENTION_TYPES[(idx + number * 3) % len(INTERVENTION_TYPES)]

            if "Manager" in intervention_type:
                target_role = "All roles"
            elif "Meeting" in intervention_type or "Focus" in intervention_type:
                target_role = "Product Manager"
            elif "Overtime" in intervention_type or "Workload" in intervention_type:
                target_role = rng.choice(["Software Engineer", "Backend Developer", "DevOps", "QA Engineer"])
            else:
                target_role = rng.choice(["All roles", "Data Scientist", "ML Engineer", "Frontend Developer"])

            coverage = np.clip(0.28 + risk + rng.normal(0, 0.11), 0.18, 0.96)
            expected_impact = np.clip(0.04 + risk * 0.22 + rng.normal(0, 0.025), 0.03, 0.22)
            monthly_cost = (
                3200
                * size_cost_multiplier[row["company_size"]]
                * (0.85 + coverage)
                * (1 + number * 0.16)
            )

            intervention_rows.append(
                {
                    "intervention_id": f"INT-{idx + 1:03d}-{number + 1:02d}",
                    "company_id": row["company_id"],
                    "intervention_type": intervention_type,
                    "start_month": start_period,
                    "end_month": periods[end_index],
                    "target_role": target_role,
                    "target_work_mode": rng.choice(["All", "Remote", "Hybrid", "Onsite"], p=[0.46, 0.18, 0.25, 0.11]),
                    "expected_impact": round(float(expected_impact), 3),
                    "monthly_cost": round(float(monthly_cost), 2),
                    "status": status,
                    "coverage_percent": round(float(coverage * 100), 1),
                }
            )

        seasonal_pressure = np.array([0.02, 0.01, 0.03, 0.04, 0.08, 0.10, 0.05, 0.02, 0.04, 0.06, 0.09, 0.11])
        for month_idx, period in enumerate(periods):
            month_pressure = pressure + seasonal_pressure[month_idx] + rng.normal(0, 0.035)
            operation_rows.append(
                {
                    "company_id": row["company_id"],
                    "period_month": period,
                    "avg_meetings_per_week": round(float(np.clip(8 + month_pressure * 7 + rng.normal(0, 1.2), 5, 22)), 2),
                    "avg_overtime_hours": round(float(np.clip(row["overtime_avg"] + month_pressure * 2.5 + rng.normal(0, 1.0), 0, 24)), 2),
                    "deadline_pressure_index": round(float(np.clip(45 + month_pressure * 28 + rng.normal(0, 5), 20, 96)), 1),
                    "absenteeism_rate": round(float(np.clip(0.018 + month_pressure * 0.035 + rng.normal(0, 0.006), 0.005, 0.12)), 4),
                    "turnover_risk_rate": round(float(np.clip(0.035 + risk * 0.18 + month_pressure * 0.04 + rng.normal(0, 0.008), 0.01, 0.28)), 4),
                    "pulse_engagement_score": round(float(np.clip(82 - month_pressure * 18 + rng.normal(0, 4), 35, 94)), 1),
                }
            )

    return pd.DataFrame(intervention_rows), pd.DataFrame(operation_rows)


def write_context_database(interventions: pd.DataFrame, operations: pd.DataFrame) -> None:
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    if SQLITE_DB.exists():
        SQLITE_DB.unlink()

    with sqlite3.connect(SQLITE_DB) as conn:
        interventions.to_sql("wellbeing_interventions", conn, index=False, if_exists="replace")
        operations.to_sql("company_monthly_operations", conn, index=False, if_exists="replace")
        conn.execute("CREATE INDEX idx_interventions_company ON wellbeing_interventions(company_id)")
        conn.execute("CREATE INDEX idx_operations_company_month ON company_monthly_operations(company_id, period_month)")


def summarize_context(interventions: pd.DataFrame, operations: pd.DataFrame) -> pd.DataFrame:
    intervention_summary = (
        interventions.assign(
            active_intervention=lambda frame: frame["status"].isin(["Active", "Planned"]).astype(int),
            active_cost=lambda frame: np.where(frame["status"].isin(["Active", "Planned"]), frame["monthly_cost"], 0),
            active_coverage=lambda frame: np.where(frame["status"].isin(["Active", "Planned"]), frame["coverage_percent"], np.nan),
        )
        .groupby("company_id", as_index=False)
        .agg(
            interventions_total=("intervention_id", "count"),
            active_interventions=("active_intervention", "sum"),
            planned_monthly_cost=("active_cost", "sum"),
            avg_intervention_coverage=("active_coverage", "mean"),
            max_expected_impact=("expected_impact", "max"),
        )
    )

    operations_summary = (
        operations.groupby("company_id", as_index=False)
        .agg(
            avg_meetings_per_week=("avg_meetings_per_week", "mean"),
            avg_operational_overtime=("avg_overtime_hours", "mean"),
            deadline_pressure_index=("deadline_pressure_index", "mean"),
            absenteeism_rate=("absenteeism_rate", "mean"),
            turnover_risk_rate=("turnover_risk_rate", "mean"),
            pulse_engagement_score=("pulse_engagement_score", "mean"),
        )
    )

    context = intervention_summary.merge(operations_summary, on="company_id", how="outer")
    context["interventions_total"] = context["interventions_total"].fillna(0).astype(int)
    context["active_interventions"] = context["active_interventions"].fillna(0).astype(int)
    context["planned_monthly_cost"] = context["planned_monthly_cost"].fillna(0)
    context["avg_intervention_coverage"] = context["avg_intervention_coverage"].fillna(0)
    context["max_expected_impact"] = context["max_expected_impact"].fillna(0)
    return context


def main() -> None:
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(f"Source CSV not found: {SOURCE_CSV}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(SOURCE_CSV)
    source_rows, source_columns = df.shape
    validate_source(df)

    df = df.copy()
    df.insert(0, "respondent_id", [f"RSP-{i:06d}" for i in range(1, len(df) + 1)])
    threshold = df["burnout_score"].quantile(0.75)
    df["high_burnout_risk"] = (df["burnout_score"] >= threshold).astype(int)
    df["experience_group"] = pd.cut(
        df["experience_years"],
        bins=[-0.01, 2, 5, 8, np.inf],
        labels=["0-2 junior", "3-5 intermedia", "6-8 senior", "9+ muy experimentada"],
    ).astype(str)

    job_roles = sorted(df["job_role"].unique())
    companies, company_source = load_company_aliases(job_roles)
    df["company_id"] = assign_companies(df, companies)

    enriched = df.merge(companies, on="company_id", how="left", suffixes=("", "_company"))
    if enriched["company_alias"].isna().any():
        raise ValueError("Company enrichment failed for at least one row.")

    company_metrics = (
        enriched.groupby(
            [
                "company_id",
                "company_alias",
                "company_size",
                "country",
                "city",
                "region",
                "latitude",
                "longitude",
                "remote_policy",
                "primary_segment",
            ],
            as_index=False,
        )
        .agg(
            respondents=("respondent_id", "count"),
            burnout_score_avg=("burnout_score", "mean"),
            high_burnout_risk_rate=("high_burnout_risk", "mean"),
            work_hours_avg=("work_hours_per_week", "mean"),
            overtime_avg=("overtime_hours", "mean"),
            manager_support_avg=("manager_support", "mean"),
            work_life_balance_avg=("work_life_balance", "mean"),
            sleep_hours_avg=("sleep_hours", "mean"),
        )
        .sort_values("high_burnout_risk_rate", ascending=False)
    )

    interventions, operations = make_context_tables(company_metrics)
    write_context_database(interventions, operations)
    context_summary = summarize_context(interventions, operations)

    enriched = enriched.merge(context_summary, on="company_id", how="left")
    company_metrics = company_metrics.merge(context_summary, on="company_id", how="left")
    enriched["intervention_gap"] = (
        (enriched["high_burnout_risk"] == 1) & (enriched["active_interventions"] == 0)
    ).astype(int)

    report = make_quality_report(
        source_rows,
        source_columns,
        enriched,
        companies,
        threshold,
        interventions,
        operations,
    )
    report["company_source"] = company_source
    if not report["respondent_id_unique"]:
        raise ValueError("respondent_id is not unique.")
    if report["company_size_mismatches"] != 0:
        raise ValueError(f"Company size mismatch detected: {report['company_size_mismatches']}")
    if report["missing_coordinates"] != 0:
        raise ValueError(f"Missing coordinates detected: {report['missing_coordinates']}")

    df.to_csv(OUTPUT_DIR / "burnout_with_id.csv", index=False)
    companies.to_csv(OUTPUT_DIR / "company_alias_locations.csv", index=False)
    enriched.to_csv(OUTPUT_DIR / "burnout_enriched_locations.csv", index=False)
    company_metrics.to_csv(OUTPUT_DIR / "company_dashboard_metrics.csv", index=False)
    interventions.to_csv(OUTPUT_DIR / "wellbeing_interventions.csv", index=False)
    operations.to_csv(OUTPUT_DIR / "company_monthly_operations.csv", index=False)

    with (OUTPUT_DIR / "etl_quality_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=True)

    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
