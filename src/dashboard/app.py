from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html, dash_table


APP_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = APP_ROOT / "data" / "processed" / "burnout_enriched_locations.csv"
INTERVENTIONS_PATH = APP_ROOT / "data" / "processed" / "wellbeing_interventions.csv"
OPERATIONS_PATH = APP_ROOT / "data" / "processed" / "company_monthly_operations.csv"


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Processed dataset not found: {DATA_PATH}. Run src/etl/create_initial_datasets.py first."
        )

    df = pd.read_csv(DATA_PATH)
    df["burnout_segment"] = df["high_burnout_risk"].map({1: "High operational risk", 0: "Lower operational risk"})
    if "experience_group" not in df.columns:
        df["experience_group"] = pd.cut(
            df["experience_years"],
            bins=[-0.01, 2, 5, 8, float("inf")],
            labels=["0-2 junior", "3-5 intermedia", "6-8 senior", "9+ muy experimentada"],
        ).astype(str)
    return df


df = load_data()
interventions_df = pd.read_csv(INTERVENTIONS_PATH) if INTERVENTIONS_PATH.exists() else pd.DataFrame()
operations_df = pd.read_csv(OPERATIONS_PATH) if OPERATIONS_PATH.exists() else pd.DataFrame()

COLORS = {
    "page": "#f3f6f8",
    "panel": "#ffffff",
    "ink": "#13202b",
    "muted": "#64748b",
    "line": "#d7dee9",
    "grid": "#e7edf5",
    "brand": "#1f6f78",
    "brand_dark": "#11353d",
    "accent": "#c47a1a",
    "risk": "#b8321d",
    "good": "#087f5b",
    "violet": "#6957c2",
    "blue": "#2f6fbd",
    "soft": "#f8fafc",
}

RISK_DELTA_SCALE = [
    [0.0, "#4f7fa3"],
    [0.5, "#d8dee6"],
    [1.0, "#c47a1a"],
]

BURNOUT_SCALE = [
    [0.0, "#d7e7f2"],
    [0.5, "#8fb7cc"],
    [1.0, "#b7791f"],
]

DELTA_COLOR_RANGE_PP = 5
MIN_DELTA_AXIS_PP = 1.5
RISK_CATEGORY_THRESHOLD_PP = 2

ROLE_COLORS = {
    "Software Engineer": "#245a73",
    "Data Scientist": "#0f766e",
    "ML Engineer": "#6d5bd0",
    "Backend Developer": "#2563eb",
    "Frontend Developer": "#db2777",
    "DevOps": "#d97706",
    "Product Manager": "#475569",
    "QA Engineer": "#16a34a",
}

RISK_CATEGORY_COLORS = {
    "Bajo el promedio": "#4f7fa3",
    "Similar al promedio": "#9ca3af",
    "Sobre el promedio": "#c47a1a",
}

BURNOUT_LEVEL_COLORS = {
    "Low": "#4f7fa3",
    "Moderate": "#c47a1a",
    "High": "#8f5f64",
}

INTERVENTION_TYPE_LABELS = {
    "Manager enablement": "Liderazgo y soporte manager",
    "Meeting load reduction": "Reduccion de reuniones",
    "Focus time program": "Tiempo protegido de foco",
    "Mental health support": "Apoyo en salud mental",
    "Overtime control": "Control de horas extra",
    "Recovery and sleep campaign": "Recuperacion y descanso",
    "Workload triage": "Priorizacion de carga",
    "Flexible schedule reset": "Ajuste de flexibilidad horaria",
}

INTERVENTION_STATUS_LABELS = {
    "Active": "Activa",
    "Planned": "Planificada",
    "Completed": "Completada",
    "Paused": "Pausada",
}

TABLE_COLUMN_LABELS = {
    "company_alias": "Alias",
    "company_size": "Tamano",
    "country": "Pais",
    "city": "Ciudad",
    "respondents": "Registros",
    "high_risk_rate": "Riesgo alto %",
    "risk_delta_pp": "Diferencia pp",
    "active_interventions": "Acciones activas",
    "planned_monthly_cost": "Costo mensual",
    "avg_intervention_coverage": "Cobertura %",
    "deadline_pressure_index": "Presion deadlines",
    "pulse_engagement_score": "Engagement",
    "work_hours_avg": "Horas semanales",
    "overtime_avg": "Horas extra",
    "manager_support_avg": "Soporte manager",
    "work_life_balance_avg": "Balance vida-trabajo",
    "sleep_hours_avg": "Horas sueno",
}

FILTER_STYLE = {"margin": "4px 0 14px 0", "fontSize": "13px"}
CARD_STYLE = {
    "background": COLORS["panel"],
    "border": f"1px solid {COLORS['line']}",
    "borderRadius": "8px",
    "padding": "16px",
    "boxShadow": "0 10px 26px rgba(17, 24, 39, 0.07)",
}
GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}


def apply_chart_style(fig, height: int = 390):
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor=COLORS["panel"],
        plot_bgcolor=COLORS["panel"],
        font=dict(family="Arial, sans-serif", color=COLORS["ink"], size=12),
        title=dict(font=dict(size=15, color=COLORS["ink"]), x=0.01, xanchor="left"),
        margin=dict(l=18, r=18, t=56, b=24),
        coloraxis_colorbar=dict(title="", thickness=12, len=0.72),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["grid"], zeroline=False, title_font=dict(size=12))
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"], zeroline=False, title_font=dict(size=12))
    return fig


def centered_delta_range(series: pd.Series, minimum: float = MIN_DELTA_AXIS_PP) -> list[float]:
    observed = pd.to_numeric(series, errors="coerce").abs().max()
    limit = max(minimum, float(observed) * 1.25 if pd.notna(observed) else minimum)
    return [-limit, limit]


def graph_card(graph_id: str, span: str | None = None) -> html.Div:
    style = {**CARD_STYLE, "padding": "8px 10px 2px 10px", "minHeight": "430px", "minWidth": "0"}
    if span:
        style["gridColumn"] = span
    return html.Div(dcc.Graph(id=graph_id, config=GRAPH_CONFIG, style={"width": "100%", "height": "420px"}), style=style)


def section_header(kicker: str, title: str, text: str) -> html.Div:
    return html.Div(
        [
            html.Div(kicker.upper(), style={"fontSize": "11px", "fontWeight": "800", "color": COLORS["brand"]}),
            html.H2(title, style={"fontSize": "19px", "margin": "3px 0 4px 0", "color": COLORS["ink"]}),
            html.Div(text, style={"fontSize": "13px", "color": COLORS["muted"], "lineHeight": "1.45", "maxWidth": "960px"}),
        ],
        style={"margin": "20px 0 10px 0"},
    )


def options(series: pd.Series) -> list[dict[str, str]]:
    return [{"label": str(value), "value": value} for value in sorted(series.dropna().unique())]


def status_options(series: pd.Series) -> list[dict[str, str]]:
    return [
        {"label": INTERVENTION_STATUS_LABELS.get(str(value), str(value)), "value": value}
        for value in sorted(series.dropna().unique())
    ]


def kpi_card(title: str, value: str, detail: str, accent: str) -> html.Div:
    return html.Div(
        [
            html.Div(style={"height": "3px", "background": accent, "borderRadius": "999px", "marginBottom": "10px"}),
            html.Div(title.upper(), style={"fontSize": "11px", "color": COLORS["muted"], "fontWeight": "700"}),
            html.Div(value, style={"fontSize": "29px", "fontWeight": "800", "marginTop": "4px", "color": COLORS["ink"]}),
            html.Div(detail, style={"fontSize": "12px", "color": COLORS["muted"], "marginTop": "4px"}),
        ],
        style={**CARD_STYLE, "padding": "14px 16px"},
    )


app = Dash(__name__)
app.title = "Burnout Tech Analytics"

app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            "PEOPLE ANALYTICS / EARLY WARNING",
                            style={
                                "fontSize": "11px",
                                "fontWeight": "800",
                                "letterSpacing": "0",
                                "color": "#cfe8ef",
                                "marginBottom": "6px",
                            },
                        ),
                        html.H1("Burnout Tech Analytics", style={"margin": "0", "fontSize": "30px", "fontWeight": "800"}),
                        html.Div(
                            "Informe interactivo para priorizar riesgo operacional por territorio, rol, modalidad y condiciones accionables.",
                            style={"color": "#d9e8ee", "marginTop": "6px", "maxWidth": "860px"},
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div("Dataset del semestre", style={"fontSize": "11px", "color": "#cfe8ef", "fontWeight": "700"}),
                        html.Div(f"{len(df):,}".replace(",", "."), style={"fontSize": "24px", "fontWeight": "800"}),
                        html.Div("registros", style={"fontSize": "12px", "color": "#d9e8ee"}),
                    ],
                    style={
                        "border": "1px solid rgba(255,255,255,0.25)",
                        "borderRadius": "8px",
                        "padding": "10px 14px",
                        "minWidth": "150px",
                        "textAlign": "right",
                    },
                ),
            ],
            style={
                "padding": "22px 28px",
                "background": f"linear-gradient(135deg, {COLORS['brand_dark']} 0%, {COLORS['brand']} 68%, #457b85 100%)",
                "color": "#ffffff",
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "gap": "18px",
            },
        ),
        html.Div(
            [
                html.Aside(
                    [
                        html.H2("Filtros", style={"fontSize": "17px", "margin": "0 0 4px 0", "color": COLORS["ink"]}),
                        html.Div(
                            "Ajustan todo el informe en tiempo real.",
                            style={"fontSize": "12px", "color": COLORS["muted"], "marginBottom": "16px"},
                        ),
                        html.Label("Tamano empresa", style={"fontWeight": "700", "fontSize": "12px"}),
                        dcc.Dropdown(options(df["company_size"]), id="company-size", multi=True, placeholder="Todos", style=FILTER_STYLE),
                        html.Label("Rol", style={"fontWeight": "700", "fontSize": "12px"}),
                        dcc.Dropdown(options(df["job_role"]), id="job-role", multi=True, placeholder="Todos", style=FILTER_STYLE),
                        html.Label("Modalidad", style={"fontWeight": "700", "fontSize": "12px"}),
                        dcc.Dropdown(options(df["work_mode"]), id="work-mode", multi=True, placeholder="Todas", style=FILTER_STYLE),
                        html.Label("Pais", style={"fontWeight": "700", "fontSize": "12px"}),
                        dcc.Dropdown(options(df["country"]), id="country", multi=True, placeholder="Todos", style=FILTER_STYLE),
                        html.Label("Nivel burnout", style={"fontWeight": "700", "fontSize": "12px"}),
                        dcc.Dropdown(options(df["burnout_level"]), id="burnout-level", multi=True, placeholder="Todos", style=FILTER_STYLE),
                        html.Label("Estado intervencion", style={"fontWeight": "700", "fontSize": "12px"}),
                        dcc.Dropdown(
                            options=status_options(interventions_df["status"]) if not interventions_df.empty else [],
                            id="intervention-status",
                            multi=True,
                            placeholder="Todos",
                            style=FILTER_STYLE,
                        ),
                        html.Div(
                            [
                                html.Div("Lectura ejecutiva", style={"fontWeight": "800", "fontSize": "12px", "marginBottom": "6px"}),
                                html.Div(
                                    "El informe prioriza diferencias contra el promedio de la vista para distinguir focos relevantes de variaciones menores.",
                                    style={"fontSize": "12px", "color": COLORS["muted"], "lineHeight": "1.45"},
                                ),
                            ],
                            style={
                                "background": COLORS["soft"],
                                "border": f"1px solid {COLORS['line']}",
                                "borderRadius": "8px",
                                "padding": "12px",
                                "marginTop": "12px",
                            },
                        ),
                    ],
                    style={
                        "width": "292px",
                        "padding": "20px",
                        "borderRight": f"1px solid {COLORS['line']}",
                        "background": COLORS["panel"],
                        "boxShadow": "8px 0 24px rgba(17, 24, 39, 0.05)",
                    },
                ),
                html.Main(
                    [
                        html.Div(id="kpis", style={"display": "grid", "gridTemplateColumns": "repeat(4, minmax(0, 1fr))", "gap": "12px"}),
                        section_header(
                            "1 / Ubicacion",
                            "Distribucion territorial del riesgo",
                            "La vista ubica cada alias en su contexto geografico y muestra la composicion de burnout. El ranking complementa el mapa destacando aliases sobre el promedio de la vista.",
                        ),
                        html.Div(
                            [
                                graph_card("risk-map", "span 2"),
                                graph_card("company-ranking"),
                            ],
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "minmax(0, 1fr) minmax(0, 1fr) minmax(320px, 0.75fr)",
                                "gap": "12px",
                            },
                        ),
                        section_header(
                            "2 / Segmentos",
                            "Diferencias por perfil laboral",
                            "La comparacion por rol, modalidad y experiencia permite identificar si el riesgo se concentra en segmentos especificos o si se mantiene estable entre grupos.",
                        ),
                        html.Div(
                            [
                                graph_card("role-risk"),
                                graph_card("pressure-heatmap"),
                                graph_card("experience-story"),
                            ],
                            style={"display": "grid", "gridTemplateColumns": "repeat(3, minmax(0, 1fr))", "gap": "12px"},
                        ),
                        section_header(
                            "3 / Causas accionables",
                            "Condiciones asociadas al mayor riesgo",
                            "Esta seccion compara el grupo de mayor riesgo con el resto para transformar la alerta en palancas de gestion: carga, overtime, soporte, balance, sueno y estres.",
                        ),
                        html.Div(
                            [
                                graph_card("drivers-chart"),
                                graph_card("recovery-scatter"),
                                graph_card("stress-burnout"),
                            ],
                            style={"display": "grid", "gridTemplateColumns": "repeat(3, minmax(0, 1fr))", "gap": "12px"},
                        ),
                        section_header(
                            "4 / Respuesta",
                            "Respuesta organizacional y brechas",
                            "El cruce entre riesgo, presion operacional, intervenciones, cobertura e inversion permite evaluar si la respuesta es proporcional al nivel de exposicion.",
                        ),
                        html.Div(
                            [
                                graph_card("intervention-gap"),
                                graph_card("operation-trend"),
                                graph_card("investment-impact"),
                                graph_card("action-mix"),
                            ],
                            style={"display": "grid", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "gap": "12px"},
                        ),
                        section_header(
                            "5 / Detalle",
                            "Priorizacion ejecutiva por alias",
                            "La tabla consolida riesgo, diferencia contra promedio, acciones, cobertura, presion operacional y variables de recuperacion para apoyar decisiones de seguimiento.",
                        ),
                        html.Div(
                            [
                                html.H2("Detalle ejecutivo por alias", style={"fontSize": "17px", "margin": "0 0 10px 0", "color": COLORS["ink"]}),
                                dash_table.DataTable(
                                    id="company-table",
                                    page_size=10,
                                    sort_action="native",
                                    style_table={"overflowX": "auto"},
                                    style_cell={
                                        "fontFamily": "Arial",
                                        "fontSize": "12px",
                                        "padding": "9px",
                                        "border": f"1px solid {COLORS['grid']}",
                                    },
                                    style_header={
                                        "fontWeight": "800",
                                        "backgroundColor": "#e8f0f5",
                                        "color": COLORS["ink"],
                                        "border": f"1px solid {COLORS['line']}",
                                    },
                                    style_data_conditional=[
                                        {
                                            "if": {"filter_query": "{risk_delta_pp} >= 2", "column_id": "risk_delta_pp"},
                                            "backgroundColor": "#fff4db",
                                            "color": "#8a4b0f",
                                            "fontWeight": "700",
                                        },
                                        {
                                            "if": {"row_index": "odd"},
                                            "backgroundColor": "#f8fafc",
                                        },
                                    ],
                                ),
                            ],
                            style={**CARD_STYLE, "marginTop": "12px"},
                        ),
                    ],
                    style={"flex": "1", "padding": "18px", "background": COLORS["page"]},
                ),
            ],
            style={"display": "flex", "minHeight": "calc(100vh - 86px)"},
        ),
    ],
    style={"fontFamily": "Arial, sans-serif", "color": COLORS["ink"], "background": COLORS["page"]},
)


def filter_data(company_size, job_role, work_mode, country, burnout_level, intervention_status) -> pd.DataFrame:
    filtered = df
    filters = {
        "company_size": company_size,
        "job_role": job_role,
        "work_mode": work_mode,
        "country": country,
        "burnout_level": burnout_level,
    }
    for column, values in filters.items():
        if values:
            filtered = filtered[filtered[column].isin(values)]
    if intervention_status and not interventions_df.empty:
        company_ids = interventions_df[interventions_df["status"].isin(intervention_status)]["company_id"].unique()
        filtered = filtered[filtered["company_id"].isin(company_ids)]
    return filtered


@app.callback(
    Output("kpis", "children"),
    Output("risk-map", "figure"),
    Output("intervention-gap", "figure"),
    Output("operation-trend", "figure"),
    Output("investment-impact", "figure"),
    Output("role-risk", "figure"),
    Output("drivers-chart", "figure"),
    Output("action-mix", "figure"),
    Output("company-ranking", "figure"),
    Output("experience-story", "figure"),
    Output("pressure-heatmap", "figure"),
    Output("recovery-scatter", "figure"),
    Output("stress-burnout", "figure"),
    Output("company-table", "data"),
    Output("company-table", "columns"),
    Input("company-size", "value"),
    Input("job-role", "value"),
    Input("work-mode", "value"),
    Input("country", "value"),
    Input("burnout-level", "value"),
    Input("intervention-status", "value"),
)
def update_dashboard(company_size, job_role, work_mode, country, burnout_level, intervention_status):
    filtered = filter_data(company_size, job_role, work_mode, country, burnout_level, intervention_status)

    if filtered.empty:
        empty_fig = px.scatter(title="Sin datos para los filtros seleccionados")
        empty_fig.update_layout(template="plotly_white")
        return (
            [
                kpi_card("Registros", "0", "Sin datos", COLORS["brand"]),
                kpi_card("Riesgo alto", "0.0%", "Sin datos", COLORS["risk"]),
                kpi_card("Burnout promedio", "0.00", "Sin datos", COLORS["accent"]),
                kpi_card("Aliases", "0", "Sin datos", COLORS["good"]),
            ],
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            [],
            [],
        )

    company = (
        filtered.groupby(
            ["company_id", "company_alias", "company_size", "country", "city", "latitude", "longitude"],
            as_index=False,
        )
        .agg(
            respondents=("respondent_id", "count"),
            high_risk_rate=("high_burnout_risk", "mean"),
            intervention_gap_rate=("intervention_gap", "mean"),
            burnout_avg=("burnout_score", "mean"),
            work_hours_avg=("work_hours_per_week", "mean"),
            overtime_avg=("overtime_hours", "mean"),
            manager_support_avg=("manager_support", "mean"),
            work_life_balance_avg=("work_life_balance", "mean"),
            sleep_hours_avg=("sleep_hours", "mean"),
            active_interventions=("active_interventions", "max"),
            interventions_total=("interventions_total", "max"),
            planned_monthly_cost=("planned_monthly_cost", "max"),
            avg_intervention_coverage=("avg_intervention_coverage", "max"),
            max_expected_impact=("max_expected_impact", "max"),
            deadline_pressure_index=("deadline_pressure_index", "max"),
            absenteeism_rate=("absenteeism_rate", "max"),
            turnover_risk_rate=("turnover_risk_rate", "max"),
            pulse_engagement_score=("pulse_engagement_score", "max"),
        )
    )
    view_high_risk_rate = filtered["high_burnout_risk"].mean()
    company["risk_delta_pp"] = (company["high_risk_rate"] - view_high_risk_rate) * 100
    company["risk_category"] = pd.cut(
        company["risk_delta_pp"],
        bins=[float("-inf"), -RISK_CATEGORY_THRESHOLD_PP, RISK_CATEGORY_THRESHOLD_PP, float("inf")],
        labels=["Bajo el promedio", "Similar al promedio", "Sobre el promedio"],
    ).astype(str)
    burnout_mix = (
        filtered.pivot_table(
            index="company_id",
            columns="burnout_level",
            values="respondent_id",
            aggfunc="count",
            fill_value=0,
        )
        .reindex(columns=["Low", "Moderate", "High"], fill_value=0)
        .reset_index()
    )
    burnout_mix[["low_share", "moderate_share", "high_share"]] = burnout_mix[["Low", "Moderate", "High"]].div(
        burnout_mix[["Low", "Moderate", "High"]].sum(axis=1),
        axis=0,
    )
    burnout_mix["dominant_burnout_level"] = burnout_mix[["Low", "Moderate", "High"]].idxmax(axis=1)
    company = company.merge(
        burnout_mix[["company_id", "low_share", "moderate_share", "high_share", "dominant_burnout_level"]],
        on="company_id",
        how="left",
    )

    map_points = (
        filtered.groupby(
            [
                "company_id",
                "company_alias",
                "company_size",
                "country",
                "city",
                "latitude",
                "longitude",
                "burnout_level",
            ],
            as_index=False,
        )
        .agg(
            respondents_level=("respondent_id", "count"),
            burnout_avg=("burnout_score", "mean"),
            high_risk_rate=("high_burnout_risk", "mean"),
        )
        .merge(company[["company_id", "respondents", "risk_delta_pp"]], on="company_id", how="left")
    )
    map_points["level_share"] = map_points["respondents_level"] / map_points["respondents"]
    map_points["burnout_level"] = pd.Categorical(
        map_points["burnout_level"],
        categories=["Low", "Moderate", "High"],
        ordered=True,
    )
    map_points = map_points.sort_values(["burnout_level", "respondents_level"])

    kpis = [
        kpi_card("Registros", f"{len(filtered):,}".replace(",", "."), "Personas en vista actual", COLORS["brand"]),
        kpi_card("Riesgo alto", f"{view_high_risk_rate * 100:.1f}%", "Percentil 75 operacional", COLORS["brand"]),
        kpi_card("Brecha accion", f"{filtered['intervention_gap'].mean() * 100:.1f}%", "Riesgo alto sin accion activa", COLORS["accent"]),
        kpi_card("Inversion mensual", f"${company['planned_monthly_cost'].sum() / 1000:.0f}k", "Acciones activas o planificadas", COLORS["good"]),
    ]

    map_fig = px.scatter_geo(
        map_points,
        lat="latitude",
        lon="longitude",
        color="burnout_level",
        size="respondents_level",
        hover_name="company_alias",
        hover_data={
            "company_size": True,
            "country": True,
            "city": True,
            "respondents_level": True,
            "level_share": ":.1%",
            "burnout_avg": ":.2f",
            "high_risk_rate": ":.1%",
            "risk_delta_pp": ":.1f",
            "latitude": False,
            "longitude": False,
        },
        color_discrete_map=BURNOUT_LEVEL_COLORS,
        category_orders={"burnout_level": ["Low", "Moderate", "High"]},
        title="Composicion de burnout por territorio y alias",
    )
    map_fig.update_traces(marker=dict(line=dict(width=1.1, color="#334155")), opacity=0.92)
    map_fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor="#f6f8fb",
        showcountries=True,
        countrycolor="#cbd5e1",
        showocean=True,
        oceancolor="#e7f2f8",
        lataxis_showgrid=True,
        lonaxis_showgrid=True,
    )
    apply_chart_style(map_fig, height=430)

    gap = company.copy()
    gap["action_status"] = gap["active_interventions"].where(gap["active_interventions"] > 0, 0)
    gap["action_status"] = gap["action_status"].map(lambda value: "Con acciones" if value > 0 else "Sin acciones")
    gap_fig = px.scatter(
        gap,
        x="high_risk_rate",
        y="deadline_pressure_index",
        size="respondents",
        color="action_status",
        hover_name="company_alias",
        hover_data={
            "company_size": True,
            "country": True,
            "active_interventions": True,
            "intervention_gap_rate": ":.1%",
            "planned_monthly_cost": ":,.0f",
            "pulse_engagement_score": ":.1f",
        },
        color_discrete_map={"Con acciones": COLORS["good"], "Sin acciones": COLORS["risk"]},
        title="Riesgo alto frente a respuesta organizacional",
    )
    gap_fig.add_vline(x=view_high_risk_rate, line_dash="dot", line_color=COLORS["muted"])
    gap_fig.add_hline(y=company["deadline_pressure_index"].mean(), line_dash="dot", line_color=COLORS["muted"])
    gap_fig.update_layout(xaxis_tickformat=".0%")
    gap_fig.update_xaxes(title="Riesgo alto operacional")
    gap_fig.update_yaxes(title="Presion por deadlines")
    apply_chart_style(gap_fig, height=430)

    selected_company_ids = filtered["company_id"].unique()
    operations = operations_df[operations_df["company_id"].isin(selected_company_ids)].copy()
    if operations.empty:
        trend_fig = px.line(title="Evolucion mensual de presion operacional")
    else:
        trend = (
            operations.groupby("period_month", as_index=False)
            .agg(
                deadline_pressure_index=("deadline_pressure_index", "mean"),
                avg_overtime_hours=("avg_overtime_hours", "mean"),
                pulse_engagement_score=("pulse_engagement_score", "mean"),
                absenteeism_rate=("absenteeism_rate", "mean"),
            )
            .sort_values("period_month")
        )
        trend_long = trend.melt(
            id_vars="period_month",
            value_vars=["deadline_pressure_index", "pulse_engagement_score", "avg_overtime_hours"],
            var_name="metric",
            value_name="value",
        )
        trend_long["metric"] = trend_long["metric"].map(
            {
                "deadline_pressure_index": "Presion deadlines",
                "pulse_engagement_score": "Engagement",
                "avg_overtime_hours": "Horas extra",
            }
        )
        trend_fig = px.line(
            trend_long,
            x="period_month",
            y="value",
            color="metric",
            markers=True,
            color_discrete_map={
                "Presion deadlines": COLORS["risk"],
                "Engagement pulse": COLORS["good"],
                "Horas extra": COLORS["accent"],
            },
            title="Pulso mensual de presion, horas extra y engagement",
        )
    trend_fig.update_traces(line=dict(width=3), marker=dict(size=7))
    trend_fig.update_xaxes(title="")
    trend_fig.update_yaxes(title="Indice / promedio")
    apply_chart_style(trend_fig, height=390)

    investment = company.copy()
    investment["coverage_bucket"] = pd.cut(
        investment["avg_intervention_coverage"],
        bins=[-0.1, 1, 45, 70, 100],
        labels=["Sin cobertura", "Baja", "Media", "Alta"],
    ).astype(str)
    investment_fig = px.scatter(
        investment,
        x="planned_monthly_cost",
        y="high_risk_rate",
        size="avg_intervention_coverage",
        color="coverage_bucket",
        hover_name="company_alias",
        hover_data={
            "company_size": True,
            "country": True,
            "active_interventions": True,
            "max_expected_impact": ":.1%",
            "turnover_risk_rate": ":.1%",
        },
        color_discrete_map={
            "Sin cobertura": COLORS["risk"],
            "Baja": COLORS["accent"],
            "Media": COLORS["blue"],
            "Alta": COLORS["good"],
        },
        title="Inversion, cobertura y nivel de riesgo",
    )
    investment_fig.update_layout(yaxis_tickformat=".0%")
    investment_fig.update_xaxes(title="Costo mensual planificado")
    investment_fig.update_yaxes(title="Riesgo alto operacional")
    apply_chart_style(investment_fig, height=390)

    role = (
        filtered.groupby("job_role", as_index=False)
        .agg(high_risk_rate=("high_burnout_risk", "mean"), respondents=("respondent_id", "count"))
        .sort_values("high_risk_rate", ascending=True)
    )
    role["risk_delta_pp"] = (role["high_risk_rate"] - view_high_risk_rate) * 100
    role_fig = px.bar(
        role,
        x="risk_delta_pp",
        y="job_role",
        orientation="h",
        color="risk_delta_pp",
        color_continuous_scale=RISK_DELTA_SCALE,
        range_color=[-DELTA_COLOR_RANGE_PP, DELTA_COLOR_RANGE_PP],
        title="Riesgo relativo por rol",
        text=role["risk_delta_pp"].map(lambda value: f"{value:+.1f} pp"),
    )
    role_fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False)
    role_fig.add_vline(x=0, line_color=COLORS["muted"], line_width=1)
    role_fig.update_layout(showlegend=False)
    role_fig.update_xaxes(
        title="Diferencia vs promedio de la vista (puntos porcentuales)",
        range=centered_delta_range(role["risk_delta_pp"]),
    )
    role_fig.update_yaxes(title="")
    apply_chart_style(role_fig, height=430)

    lower_risk = filtered[filtered["high_burnout_risk"] == 0]
    high_risk = filtered[filtered["high_burnout_risk"] == 1]
    driver_specs = [
        ("Balance vida-trabajo", "work_life_balance", "recuperacion"),
        ("Soporte manager", "manager_support", "soporte"),
        ("Horas de sueno", "sleep_hours", "recuperacion"),
        ("Horas semanales", "work_hours_per_week", "carga"),
        ("Horas extra", "overtime_hours", "carga"),
        ("Estres percibido", "stress_level", "carga"),
    ]
    drivers = pd.DataFrame(
        [
            {
                "driver": label,
                "delta": high_risk[column].mean() - lower_risk[column].mean(),
                "story": story,
            }
            for label, column, story in driver_specs
        ]
    ).sort_values("delta")
    drivers_fig = px.bar(
        drivers,
        x="delta",
        y="driver",
        orientation="h",
        title="Factores que diferencian al grupo de mayor riesgo",
        color="story",
        color_discrete_map={"recuperacion": COLORS["good"], "soporte": COLORS["brand"], "carga": COLORS["accent"]},
        text=drivers["delta"].map(lambda value: f"{value:+.1f}"),
    )
    drivers_fig.add_vline(x=0, line_color=COLORS["muted"], line_width=1)
    drivers_fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False)
    drivers_fig.update_layout(showlegend=True, legend_title_text="")
    drivers_fig.update_xaxes(title="Diferencia de promedio: riesgo alto menos resto")
    drivers_fig.update_yaxes(title="")
    apply_chart_style(drivers_fig, height=390)

    selected_interventions = interventions_df[interventions_df["company_id"].isin(selected_company_ids)].copy()
    if intervention_status and not selected_interventions.empty:
        selected_interventions = selected_interventions[selected_interventions["status"].isin(intervention_status)]
    if selected_interventions.empty:
        action_fig = px.bar(title="Portafolio de acciones de bienestar")
    else:
        selected_interventions["intervention_type_label"] = selected_interventions["intervention_type"].map(INTERVENTION_TYPE_LABELS).fillna(
            selected_interventions["intervention_type"]
        )
        selected_interventions["status_label"] = selected_interventions["status"].map(INTERVENTION_STATUS_LABELS).fillna(
            selected_interventions["status"]
        )
        action_mix = (
            selected_interventions.groupby(["intervention_type_label", "status_label"], as_index=False)
            .agg(
                actions=("intervention_id", "count"),
                avg_coverage=("coverage_percent", "mean"),
                monthly_cost=("monthly_cost", "sum"),
            )
            .sort_values("actions", ascending=False)
        )
        action_fig = px.bar(
            action_mix,
            x="actions",
            y="intervention_type_label",
            color="status_label",
            orientation="h",
            hover_data={"avg_coverage": ":.1f", "monthly_cost": ":,.0f"},
            color_discrete_map={
                "Activa": COLORS["good"],
                "Planificada": COLORS["blue"],
                "Completada": COLORS["violet"],
                "Pausada": COLORS["accent"],
            },
            title="Portafolio de acciones de bienestar por estado",
        )
    action_fig.update_xaxes(title="Intervenciones")
    action_fig.update_yaxes(title="")
    apply_chart_style(action_fig, height=390)

    ranking = company.sort_values(["high_risk_rate", "respondents"], ascending=False).head(12)
    rank_fig = px.bar(
        ranking.sort_values("high_risk_rate"),
        x="risk_delta_pp",
        y="company_alias",
        orientation="h",
        color="risk_delta_pp",
        color_continuous_scale=RISK_DELTA_SCALE,
        range_color=[-DELTA_COLOR_RANGE_PP, DELTA_COLOR_RANGE_PP],
        title="Aliases con mayor diferencia frente al promedio",
        text=ranking.sort_values("high_risk_rate")["risk_delta_pp"].map(lambda value: f"{value:+.1f} pp"),
    )
    rank_fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False)
    rank_fig.add_vline(x=0, line_color=COLORS["muted"], line_width=1)
    rank_fig.update_layout(showlegend=False)
    rank_fig.update_xaxes(
        title="Diferencia vs promedio de la vista (puntos porcentuales)",
        range=centered_delta_range(ranking["risk_delta_pp"]),
    )
    rank_fig.update_yaxes(title="")
    apply_chart_style(rank_fig, height=390)

    experience_order = ["0-2 junior", "3-5 intermedia", "6-8 senior", "9+ muy experimentada"]
    exp_story = (
        filtered.groupby("experience_group", as_index=False)
        .agg(
            high_risk_rate=("high_burnout_risk", "mean"),
            burnout_avg=("burnout_score", "mean"),
            respondents=("respondent_id", "count"),
        )
    )
    exp_story["experience_group"] = pd.Categorical(exp_story["experience_group"], categories=experience_order, ordered=True)
    exp_story = exp_story.sort_values("experience_group")
    exp_fig = px.line(
        exp_story,
        x="experience_group",
        y="high_risk_rate",
        markers=True,
        text=exp_story["high_risk_rate"].map(lambda value: f"{value:.1%}"),
        title="Riesgo alto por tramo de experiencia",
    )
    exp_fig.update_traces(line=dict(width=4, color=COLORS["brand"]), marker=dict(size=11, color=COLORS["accent"]), textposition="top center")
    exp_fig.add_hline(
        y=view_high_risk_rate,
        line_dash="dot",
        line_color=COLORS["muted"],
        annotation_text="promedio vista",
        annotation_position="bottom right",
    )
    exp_fig.update_layout(yaxis_tickformat=".0%")
    exp_fig.update_xaxes(title="")
    exp_fig.update_yaxes(title="Riesgo alto operacional", range=[0, max(0.35, exp_story["high_risk_rate"].max() * 1.25)])
    apply_chart_style(exp_fig, height=390)

    pressure = (
        filtered.groupby(["job_role", "work_mode"], as_index=False)
        .agg(
            high_risk_rate=("high_burnout_risk", "mean"),
            work_hours_avg=("work_hours_per_week", "mean"),
            overtime_avg=("overtime_hours", "mean"),
            respondents=("respondent_id", "count"),
        )
    )
    pressure["risk_delta_pp"] = (pressure["high_risk_rate"] - view_high_risk_rate) * 100
    pressure_matrix = pressure.pivot(index="job_role", columns="work_mode", values="risk_delta_pp")
    pressure_fig = px.imshow(
        pressure_matrix,
        color_continuous_scale=RISK_DELTA_SCALE,
        range_color=[-DELTA_COLOR_RANGE_PP, DELTA_COLOR_RANGE_PP],
        aspect="auto",
        text_auto=".1f",
        title="Diferencia de riesgo por rol y modalidad",
    )
    pressure_fig.update_traces(
        texttemplate="%{z:+.1f}",
        hovertemplate="Rol: %{y}<br>Modalidad: %{x}<br>Diferencia: %{z:+.1f} pp<extra></extra>",
    )
    pressure_fig.update_layout(xaxis_title="", yaxis_title="", coloraxis_colorbar=dict(title="pp vs prom."))
    apply_chart_style(pressure_fig, height=390)

    recovery = (
        filtered.groupby(["company_alias", "company_size", "country", "city"], as_index=False)
        .agg(
            work_life_balance_avg=("work_life_balance", "mean"),
            sleep_hours_avg=("sleep_hours", "mean"),
            manager_support_avg=("manager_support", "mean"),
            high_risk_rate=("high_burnout_risk", "mean"),
            respondents=("respondent_id", "count"),
        )
    )
    recovery["risk_delta_pp"] = (recovery["high_risk_rate"] - view_high_risk_rate) * 100
    recovery_fig = px.scatter(
        recovery,
        x="work_life_balance_avg",
        y="sleep_hours_avg",
        size="respondents",
        color="risk_delta_pp",
        hover_name="company_alias",
        hover_data={
            "company_size": True,
            "country": True,
            "city": True,
            "manager_support_avg": ":.2f",
            "high_risk_rate": ":.1%",
            "risk_delta_pp": ":.1f",
        },
        color_continuous_scale=RISK_DELTA_SCALE,
        range_color=[-DELTA_COLOR_RANGE_PP, DELTA_COLOR_RANGE_PP],
        title="Recuperacion y balance frente al riesgo relativo",
    )
    recovery_fig.update_traces(marker=dict(line=dict(width=1.1, color="#334155")), opacity=0.92)
    recovery_fig.update_xaxes(title="Balance vida-trabajo promedio")
    recovery_fig.update_yaxes(title="Horas de sueno promedio")
    apply_chart_style(recovery_fig, height=400)

    stress_sample = filtered.sample(min(len(filtered), 6000), random_state=20260622)
    stress_fig = px.scatter(
        stress_sample,
        x="stress_level",
        y="burnout_score",
        color="work_life_balance",
        facet_col="work_mode",
        opacity=0.45,
        hover_data=["job_role", "company_size", "company_alias"],
        color_continuous_scale=BURNOUT_SCALE,
        title="Relacion entre estres, burnout y balance por modalidad",
    )
    stress_fig.update_traces(marker=dict(size=5, line=dict(width=0)), selector=dict(mode="markers"))
    stress_fig.update_xaxes(title="Nivel de estres")
    stress_fig.update_yaxes(title="Burnout score")
    apply_chart_style(stress_fig, height=400)

    table = company.sort_values("high_risk_rate", ascending=False).head(50).copy()
    table["high_risk_rate"] = (table["high_risk_rate"] * 100).round(1)
    table["risk_delta_pp"] = table["risk_delta_pp"].round(1)
    for col in [
        "burnout_avg",
        "work_hours_avg",
        "overtime_avg",
        "manager_support_avg",
        "work_life_balance_avg",
        "sleep_hours_avg",
        "planned_monthly_cost",
        "avg_intervention_coverage",
        "deadline_pressure_index",
        "absenteeism_rate",
        "turnover_risk_rate",
        "pulse_engagement_score",
    ]:
        table[col] = table[col].round(2)

    table_cols = [
        "company_alias",
        "company_size",
        "country",
        "city",
        "respondents",
        "high_risk_rate",
        "risk_delta_pp",
        "active_interventions",
        "planned_monthly_cost",
        "avg_intervention_coverage",
        "deadline_pressure_index",
        "pulse_engagement_score",
        "burnout_avg",
        "work_hours_avg",
        "overtime_avg",
        "manager_support_avg",
        "work_life_balance_avg",
        "sleep_hours_avg",
    ]
    columns = [{"name": TABLE_COLUMN_LABELS.get(col, col), "id": col} for col in table_cols]

    return (
        kpis,
        map_fig,
        gap_fig,
        trend_fig,
        investment_fig,
        role_fig,
        drivers_fig,
        action_fig,
        rank_fig,
        exp_fig,
        pressure_fig,
        recovery_fig,
        stress_fig,
        table[table_cols].to_dict("records"),
        columns,
    )


if __name__ == "__main__":
    dash_host = os.getenv("DASH_HOST", "127.0.0.1")
    dash_port = int(os.getenv("DASH_PORT", "8050"))
    dash_debug = os.getenv("DASH_DEBUG", "false").lower() == "true"
    app.run(debug=dash_debug, host=dash_host, port=dash_port, use_reloader=False)
