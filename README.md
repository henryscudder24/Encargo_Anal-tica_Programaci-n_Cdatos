# Burnout End-to-End Analytics

Solucion end-to-end de analitica de datos para estudiar patrones operacionales asociados al burnout en perfiles tecnologicos. Integra ETL, validacion de datos, API REST, base SQL, dashboard BI y despliegue local con Docker.

El enfoque es People Analytics preventivo. Los resultados no representan diagnostico clinico ni evaluacion de empresas reales; se trabaja con aliases organizacionales para proteger nombres y evitar atribuciones indebidas.

## Objetivos

- Integrar fuentes de informacion en un flujo reproducible.
- Automatizar un pipeline ETL con validaciones de calidad.
- Exponer empresas, aliases y ubicaciones mediante API REST.
- Persistir contexto operacional en SQLite.
- Construir un dashboard interactivo para priorizacion ejecutiva.
- Containerizar API y dashboard con Docker Compose.

## Fuentes y capas de datos

| Fuente | Ubicacion | Rol |
| --- | --- | --- |
| CSV burnout | `../Modelos ML/tech_mental_health_burnout_cleaned_from_dirty.csv` | Fuente principal de observaciones laborales y burnout. |
| API empresas/ubicaciones | `src/api/company_locations_api.py` | Entrega aliases organizacionales, paises, ciudades, coordenadas y contexto agregado. |
| SQLite operacional | `data/sql/burnout_context.db` | Almacena intervenciones de bienestar y metricas operacionales mensuales. |

Caracteristicas verificadas:

- 150.000 registros fuente.
- 25 columnas originales.
- 52 columnas en dataset enriquecido.
- 96 aliases organizacionales.
- 307 intervenciones.
- 1.152 registros operacionales mensuales.

## Arquitectura

```text
CSV burnout publico/academico
        |
        v
src/etl/create_initial_datasets.py
        |
        +--> API FastAPI: aliases, empresas y ubicaciones
        |
        +--> SQLite: intervenciones y operaciones mensuales
        |
        v
data/processed/burnout_enriched_locations.csv
data/processed/company_dashboard_metrics.csv
data/processed/etl_quality_report.json
        |
        v
src/dashboard/app.py
        |
        v
Dashboard Plotly Dash
```

Arquitectura de servicios:

```text
docker-compose.yml
        |
        +--> api        http://127.0.0.1:8000/docs
        |
        +--> dashboard  http://127.0.0.1:8050
```

## Estructura

```text
burnout_end_to_end/
  data/
    processed/
    sql/burnout_context.db
  docs/
    respaldo_tecnico_entrega.md
    plan_arquitectura_flujos.md
  src/
    api/company_locations_api.py
    etl/create_initial_datasets.py
    dashboard/app.py
  Dockerfile.api
  Dockerfile.dashboard
  docker-compose.yml
  requirements.txt
```

## Pipeline ETL

Script principal:

```text
src/etl/create_initial_datasets.py
```

Responsabilidades:

- leer el CSV fuente sin modificarlo;
- validar columnas obligatorias y valores esperados;
- crear `respondent_id`;
- calcular `high_burnout_risk` por percentil 75 de `burnout_score`;
- crear `experience_group`;
- integrar aliases, ubicaciones y contexto SQL;
- generar datasets analiticos para dashboard;
- escribir `etl_quality_report.json`.

Ejecucion local:

```powershell
python src\etl\create_initial_datasets.py
```

Ejecucion consumiendo empresas desde API:

```powershell
$env:COMPANY_API_URL = "http://127.0.0.1:8000"
python src\etl\create_initial_datasets.py
Remove-Item Env:\COMPANY_API_URL
```

Salidas principales:

```text
data/processed/burnout_with_id.csv
data/processed/company_alias_locations.csv
data/processed/burnout_enriched_locations.csv
data/processed/company_dashboard_metrics.csv
data/processed/wellbeing_interventions.csv
data/processed/company_monthly_operations.csv
data/processed/etl_quality_report.json
data/sql/burnout_context.db
```

## Documentacion de API

Ejecucion:

```powershell
python src\api\company_locations_api.py
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Endpoints:

| Metodo | Endpoint | Uso |
| --- | --- | --- |
| GET | `/health` | Estado del servicio y conteos base. |
| GET | `/companies` | Lista aliases organizacionales filtrables. |
| GET | `/companies/{company_id}` | Detalle de un alias. |
| GET | `/locations` | Paises, ciudades, coordenadas y cobertura. |
| GET | `/company-risk-context` | Contexto agregado de riesgo por alias. |

Validacion esperada:

```text
status: ok
companies: 96
countries: 10
company_metrics: 96
```

## Manual de usuario

### 1. Levantar dashboard local

```powershell
python src\dashboard\app.py
```

Abrir:

```text
http://127.0.0.1:8050
```

### 2. Usar filtros

El panel lateral controla todo el informe:

- tamano de empresa;
- rol;
- modalidad de trabajo;
- pais;
- nivel de burnout;
- estado de intervencion.

### 3. Leer el storytelling visual

1. **Ubicacion:** composicion territorial de burnout por alias.
2. **Segmentos:** comparacion por rol, modalidad y experiencia.
3. **Causas accionables:** carga, overtime, soporte, balance, sueno y estres.
4. **Respuesta:** intervenciones, cobertura, inversion y presion mensual.
5. **Detalle:** tabla ejecutiva para priorizar aliases.

### 4. Revisar base SQL

Archivo:

```text
data/sql/burnout_context.db
```

Tablas:

```text
wellbeing_interventions
company_monthly_operations
```

Consulta rapida:

```powershell
python -c "import sqlite3; conn=sqlite3.connect('data/sql/burnout_context.db'); print(conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())"
```

## Guia de despliegue local

Instalar dependencias:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Construir API:

```powershell
docker build -f Dockerfile.api -t burnout-api .
docker run --rm -p 8000:8000 burnout-api
```

Construir dashboard:

```powershell
docker build -f Dockerfile.dashboard -t burnout-dashboard .
docker run --rm -p 8050:8050 burnout-dashboard
```

Levantar ambos servicios:

```powershell
docker compose up --build
```

URLs:

```text
API:       http://127.0.0.1:8000/docs
Dashboard: http://127.0.0.1:8050
```

Detener:

```powershell
docker compose down
```

## Validaciones tecnicas

Compilacion:

```powershell
python -m py_compile src\etl\create_initial_datasets.py src\api\company_locations_api.py src\dashboard\app.py
```

Validacion dashboard:

```text
outputs: 15
figures ok: True
table rows: 50
columns: 18
```

Validacion ETL con API:

```text
company_source: http://127.0.0.1:8000/companies
rows: 150000
company_aliases: 96
interventions: 307
operation_rows: 1152
company_size_mismatches: 0
missing_coordinates: 0
```

## Consideraciones metodologicas

- `burnout_level` proviene del dataset fuente.
- `high_burnout_risk` es una variable derivada por percentil 75.
- Ambas variables no deben interpretarse como equivalentes.
- Los aliases organizacionales evitan usar nombres reales.
- La lectura correcta es preventiva: identificar riesgo, presion operacional y brechas de respuesta.

## Documentacion adicional

- `docs/respaldo_tecnico_entrega.md`: respaldo tecnico completo.