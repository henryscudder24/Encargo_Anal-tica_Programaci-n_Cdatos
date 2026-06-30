# Respaldo tecnico del proyecto Burnout End-to-End Analytics

Fecha de referencia: 2026-06-29

## 1. Proposito del proyecto

Este proyecto implementa una solucion end-to-end de analitica de datos para estudiar patrones operacionales asociados al burnout en perfiles tecnologicos. La solucion integra extraccion, transformacion, validacion, enriquecimiento, persistencia, API REST, dashboard interactivo y containerizacion.

El enfoque analitico es de People Analytics y prevencion operacional. Los resultados no deben interpretarse como diagnostico clinico ni como evaluacion real de una empresa especifica.

## 2. Objetivos tecnicos

- Integrar multiples fuentes de informacion en un flujo reproducible.
- Automatizar un pipeline ETL con validaciones de estructura, calidad y consistencia.
- Exponer una fuente organizacional/territorial mediante API REST.
- Mantener una base SQL para contexto operacional e intervenciones.
- Construir un dashboard BI interactivo para exploracion ejecutiva.
- Containerizar servicios con Docker y Docker Compose.
- Documentar arquitectura, ejecucion, validaciones y alcance metodologico.

## 3. Fuentes de informacion

El proyecto trabaja con tres entradas principales:

### 3.1 Fuente CSV de burnout

Archivo:

```text
../Modelos ML/tech_mental_health_burnout_cleaned_from_dirty.csv
```

Rol en la arquitectura:

- fuente principal de observaciones individuales;
- contiene variables laborales, demograficas, psicosociales y de burnout;
- permite construir indicadores por rol, modalidad, tamano de empresa y nivel de burnout.

Estado de la fuente:

- se considera un insumo de origen publico/abierto dentro del contexto academico del proyecto;
- no se modifica directamente;
- todo enriquecimiento se genera en `data/processed/`.

Caracteristicas verificadas:

- 150.000 filas;
- 25 columnas originales;
- sin nulos en columnas criticas revisadas;
- variable continua principal: `burnout_score`;
- variable categorica principal: `burnout_level`.

### 3.2 Fuente API de empresas y ubicaciones

Servicio:

```text
src/api/company_locations_api.py
```

Archivo base actual:

```text
data/processed/company_alias_locations.csv
```

Rol en la arquitectura:

- expone aliases de organizaciones;
- entrega pais, ciudad, region, coordenadas y zona horaria;
- permite desacoplar el ETL de un archivo local;
- prepara el proyecto para despliegue por servicios.

Nota metodologica:

Los datos territoriales y organizacionales se presentan mediante aliases para no asociar indicadores de burnout a companias reales. Este tratamiento preserva el objetivo academico y reduce riesgos reputacionales. La fuente se documenta como parte del pipeline publico/academico del proyecto, con identificadores anonimizados y no atribuibles a organizaciones reales.

Endpoints disponibles:

```text
GET /health
GET /companies
GET /companies/{company_id}
GET /locations
GET /company-risk-context
```

Validacion observada:

```text
status: ok
companies: 96
countries: 10
company_metrics: 96
```

### 3.3 Fuente SQL operacional

Base:

```text
data/sql/burnout_context.db
```

Tablas:

```text
wellbeing_interventions
company_monthly_operations
```

Rol en la arquitectura:

- aporta contexto de acciones de bienestar;
- agrega presion operacional mensual;
- permite cruzar riesgo, carga, intervenciones, cobertura e inversion.

Metricas incluidas:

- reuniones promedio por semana;
- horas extra operacionales;
- indice de presion por deadlines;
- ausentismo;
- riesgo de rotacion;
- engagement mensual;
- cobertura, costo e impacto esperado de intervenciones.

## 4. Arquitectura general

```text
CSV publico/academico de burnout
        |
        v
src/etl/create_initial_datasets.py
        |
        +--> API FastAPI: empresas, aliases y ubicaciones
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

## 5. Pipeline ETL

Script principal:

```text
src/etl/create_initial_datasets.py
```

Responsabilidades:

- leer el CSV fuente sin modificarlo;
- validar columnas obligatorias;
- validar valores esperados en `company_size`, `job_role` y `work_mode`;
- crear `respondent_id`;
- derivar `high_burnout_risk` usando percentil 75 de `burnout_score`;
- crear `experience_group`;
- integrar aliases de empresas y ubicaciones;
- asignar `company_id` respetando compatibilidad por tamano de empresa y rol;
- generar tablas SQL de intervenciones y operaciones;
- crear datasets procesados para dashboard;
- escribir reporte de calidad.

Modo local:

```powershell
python src\etl\create_initial_datasets.py
```

Modo con API:

```powershell
$env:COMPANY_API_URL = "http://127.0.0.1:8000"
python src\etl\create_initial_datasets.py
Remove-Item Env:\COMPANY_API_URL
```

Validacion del modo API:

```text
company_source: http://127.0.0.1:8000/companies
rows: 150000
columns_enriched: 52
company_aliases: 96
interventions: 307
operation_rows: 1152
company_size_mismatches: 0
missing_coordinates: 0
```

## 6. Salidas generadas

Directorio:

```text
data/processed/
```

Archivos principales:

```text
burnout_with_id.csv
company_alias_locations.csv
burnout_enriched_locations.csv
company_dashboard_metrics.csv
wellbeing_interventions.csv
company_monthly_operations.csv
etl_quality_report.json
```

Base SQL:

```text
data/sql/burnout_context.db
```

## 7. API REST

Ejecucion local:

```powershell
python src\api\company_locations_api.py
```

Documentacion interactiva:

```text
http://127.0.0.1:8000/docs
```

Uso esperado:

- consulta de empresas anonimizadas;
- consulta de ubicaciones;
- consulta de contexto agregado de riesgo;
- consumo por ETL mediante `COMPANY_API_URL`.

## 8. Dashboard BI

Script:

```text
src/dashboard/app.py
```

Ejecucion local:

```powershell
python src\dashboard\app.py
```

URL:

```text
http://127.0.0.1:8050
```

Filtros implementados:

- tamano de empresa;
- rol;
- modalidad de trabajo;
- pais;
- nivel de burnout;
- estado de intervencion.

Historias visuales:

- composicion territorial por `burnout_level`;
- aliases sobre o bajo el promedio de riesgo de la vista;
- comparacion por rol, modalidad y experiencia;
- drivers accionables de carga, soporte, balance y sueno;
- relacion entre recuperacion, estres y burnout;
- respuesta organizacional: intervenciones, cobertura, inversion y presion mensual;
- tabla ejecutiva por alias.

## 9. Docker y despliegue local

Imagen dashboard:

```powershell
docker build -f Dockerfile.dashboard -t burnout-dashboard .
docker run --rm -p 8050:8050 burnout-dashboard
```

Imagen API:

```powershell
docker build -f Dockerfile.api -t burnout-api .
docker run --rm -p 8000:8000 burnout-api
```

Docker Compose:

```powershell
docker compose up --build
```

Servicios:

```text
api        -> http://127.0.0.1:8000/docs
dashboard  -> http://127.0.0.1:8050
```

## 10. Validaciones realizadas

Compilacion:

```powershell
python -m py_compile src\etl\create_initial_datasets.py src\api\company_locations_api.py src\dashboard\app.py
```

Callback dashboard:

```text
outputs: 15
figures ok: True
table rows: 50
columns: 18
```

Docker:

```text
Dockerfile.api: build OK
Dockerfile.dashboard: build OK
dashboard container: carga correctamente en http://127.0.0.1:8050
```

## 11. Consideraciones eticas y de alcance

- El proyecto no realiza diagnostico medico.
- La variable `high_burnout_risk` es una derivacion operacional basada en percentil 75, no una etiqueta clinica.
- `burnout_level` proviene del dataset original y no debe confundirse con `high_burnout_risk`.
- Los aliases evitan asociar resultados sensibles a empresas reales.
- La lectura correcta es preventiva: identificar patrones de riesgo, presion operacional y brechas de respuesta.

## 12. Estado de avance

Completado:

- ETL reproducible;
- integracion CSV + API + SQLite;
- API REST documentada por FastAPI;
- dashboard interactivo;
- Dockerfile para API;
- Dockerfile para dashboard;
- Docker Compose con servicios `api` y `dashboard`;
- validaciones tecnicas principales.

Pendiente recomendado:

- validar `docker compose up --build` en ejecucion conjunta;
- crear `.env.example` cuando se decida cerrar configuracion final;
- preparar README final de entrega;
- generar evidencia Git/GitHub con ramas, issues, commits y PRs;
- definir estrategia de despliegue final.
