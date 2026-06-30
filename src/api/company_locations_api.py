from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPANIES_CSV = PROJECT_ROOT / "data" / "processed" / "company_alias_locations.csv"
METRICS_CSV = PROJECT_ROOT / "data" / "processed" / "company_dashboard_metrics.csv"

app = FastAPI(
    title="Burnout Company Context API",
    description="API local para aliases de empresas, ubicaciones y contexto operacional sintetico.",
    version="1.0.0",
)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.where(pd.notna(frame), None)
    return clean.to_dict("records")


@lru_cache(maxsize=1)
def load_companies() -> pd.DataFrame:
    if not COMPANIES_CSV.exists():
        raise FileNotFoundError(f"Companies CSV not found: {COMPANIES_CSV}")
    return pd.read_csv(COMPANIES_CSV)


@lru_cache(maxsize=1)
def load_company_metrics() -> pd.DataFrame:
    if not METRICS_CSV.exists():
        raise FileNotFoundError(f"Company metrics CSV not found: {METRICS_CSV}")
    return pd.read_csv(METRICS_CSV)


@app.get("/health")
def health() -> dict[str, Any]:
    companies = load_companies()
    metrics = load_company_metrics()
    return {
        "status": "ok",
        "companies": int(len(companies)),
        "countries": int(companies["country"].nunique()),
        "company_metrics": int(len(metrics)),
    }


@app.get("/companies")
def companies(
    company_size: str | None = Query(default=None),
    country: str | None = Query(default=None),
    role: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    data = load_companies()

    if company_size:
        data = data[data["company_size"].str.casefold() == company_size.casefold()]
    if country:
        data = data[data["country"].str.casefold() == country.casefold()]
    if role:
        role_key = role.casefold()
        data = data[data["supported_roles"].str.casefold().str.split("|").apply(lambda roles: role_key in roles)]

    return _records(data.sort_values(["company_size", "company_id"]))


@app.get("/companies/{company_id}")
def company_detail(company_id: str) -> dict[str, Any]:
    data = load_companies()
    match = data[data["company_id"].str.casefold() == company_id.casefold()]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Company not found: {company_id}")
    return _records(match)[0]


@app.get("/locations")
def locations(country: str | None = Query(default=None)) -> list[dict[str, Any]]:
    data = load_companies()
    if country:
        data = data[data["country"].str.casefold() == country.casefold()]

    grouped = (
        data.groupby(["country", "city", "region", "latitude", "longitude", "timezone"], as_index=False)
        .agg(
            companies=("company_id", "count"),
            company_sizes=("company_size", lambda values: "|".join(sorted(set(values)))),
        )
        .sort_values(["country", "city"])
    )
    return _records(grouped)


@app.get("/company-risk-context")
def company_risk_context(
    company_size: str | None = Query(default=None),
    country: str | None = Query(default=None),
    min_high_risk_rate: float | None = Query(default=None, ge=0, le=1),
) -> list[dict[str, Any]]:
    data = load_company_metrics()

    if company_size:
        data = data[data["company_size"].str.casefold() == company_size.casefold()]
    if country:
        data = data[data["country"].str.casefold() == country.casefold()]
    if min_high_risk_rate is not None:
        data = data[data["high_burnout_risk_rate"] >= min_high_risk_rate]

    return _records(data.sort_values("high_burnout_risk_rate", ascending=False))


if __name__ == "__main__":
    import uvicorn

    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8000"))
    api_reload = os.getenv("API_RELOAD", "false").lower() == "true"
    uvicorn.run("company_locations_api:app", host=api_host, port=api_port, reload=api_reload)
