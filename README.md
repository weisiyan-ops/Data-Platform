# Oncology Data Extraction Platform

Research-oriented oncology data abstraction platform. **Not a clinical decision support tool.**

Extracts structured oncology data from multiple sources (Chinese medical images, Epic FHIR/C-CDA/EHI, English clinical documents) into a canonical schema with full provenance tracking.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Input Sources                  │
│  Chinese Images │ Epic FHIR │ C-CDA │ EHI │ Docs│
└────────┬────────┴─────┬─────┴───┬───┴──┬──┴──┬──┘
         │              │         │      │     │
         ▼              ▼         ▼      ▼     ▼
┌─────────────────────────────────────────────────┐
│              Input Adapters (app/adapters/)       │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│         NLP / Extraction (app/nlp/)              │
│  English │ Chinese │ Translation │ Imaging │ ... │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│          Canonical Models (app/models/)           │
│  Patient │ Condition │ Treatment │ Imaging │ ... │
│          + ProvenanceRecord per field             │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│         Storage (app/db/)                        │
│         DuckDB (default) │ SQLite (fallback)     │
└────────────────────┬────────────────────────────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
    Timeline     Export      Review
    Engine       CSV/Parquet  Queue
```

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Initialize a project
onco-extract init-project my_study --cancer lung

# Start API server
onco-extract serve --port 8000

# Check health
curl http://localhost:8000/health
```

## Project Structure

```
oncology-data-platform/
├── app/                          # Application source code
│   ├── models/                   # 14 Pydantic v2 canonical models
│   │   ├── enums.py              #   15 enumerations (Sex, CancerType, RECIST, etc.)
│   │   ├── provenance.py         #   ProvenanceRecord — field-level evidence
│   │   ├── patient.py            #   Patient demographics
│   │   ├── encounter.py          #   Visit context
│   │   ├── document.py           #   SourceDocument, ClinicalNote, PageInfo
│   │   ├── condition.py          #   Diagnosis / cancer condition
│   │   ├── tumor.py              #   Staging, TNM, biomarkers
│   │   ├── treatment.py          #   MedicationExposure, ProcedureEvent
│   │   ├── lab.py                #   LabResult (CBC, CMP, LDH, etc.)
│   │   ├── imaging.py            #   ImagingReport, RECIST, LesionMeasurement
│   │   ├── progression.py        #   ProgressionEvent, ResponseEvent
│   │   ├── survival.py           #   SurvivalEvent (death, follow-up)
│   │   ├── timeline.py           #   DerivedEndpoints (PFS, OS, LC)
│   │   └── project.py            #   ProjectMeta
│   ├── config/                   # Configuration system
│   │   ├── loader.py             #   YAML loading + deep merge
│   │   ├── settings.py           #   AppSettings (pydantic-settings, env vars)
│   │   └── cancer_config.py      #   CancerConfig model + loader
│   ├── db/                       # Storage layer
│   │   ├── protocol.py           #   StorageBackend Protocol
│   │   ├── duckdb_backend.py     #   DuckDB — columnar analytics
│   │   ├── sqlite_backend.py     #   SQLite — WAL mode fallback
│   │   └── migrations.py         #   Schema definitions (15 tables)
│   ├── api/                      # FastAPI REST API
│   │   ├── app.py                #   App factory
│   │   ├── deps.py               #   Dependency injection
│   │   └── routers/              #   health, projects, patients, pipeline, export
│   ├── cli/main.py               # Typer CLI (9 commands)
│   ├── adapters/                 # Input adapters (5 stubs + base protocol)
│   ├── nlp/                      # NLP modules (6 stubs)
│   ├── timeline/engine.py        # Timeline derivation (stub)
│   ├── export/csv_exporter.py    # CSV export (stub)
│   └── review/queue.py           # Review queue (stub)
├── configs/                      # YAML configuration files
│   ├── app.yaml                  #   Global settings
│   ├── cancers/_base.yaml        #   Shared cancer defaults
│   ├── cancers/lung.yaml         #   Lung-specific config
│   ├── cancers/breast.yaml       #   Breast-specific config
│   ├── endpoints/endpoint_rules.yaml  # PFS/OS/LC rules
│   └── studies/default.yaml      #   Study template
├── tests/                        # 77 tests (all passing)
│   ├── unit/                     #   Model, config, storage tests
│   └── integration/              #   API and CLI tests
├── docker/Dockerfile             # Container definition
├── docker-compose.yml            # Docker Compose
└── docs/PHASE1_REPORT.md         # Full implementation report
```

## Configuration

- `configs/app.yaml` — Global settings (storage, logging, API)
- `configs/cancers/_base.yaml` — Shared defaults across all cancers
- `configs/cancers/{cancer}.yaml` — Cancer-specific overrides (deep-merged with base)
- `configs/endpoints/endpoint_rules.yaml` — PFS/OS/LC derivation rules
- `configs/studies/default.yaml` — Study-level config template

Cancer configs support deep merge: lung.yaml inherits from _base.yaml and overrides only what differs.

## CLI Commands

| Command | Status | Description |
|---------|--------|-------------|
| `onco-extract init-project <name> --cancer <type>` | Live | Create project dirs + config |
| `onco-extract serve --port 8000` | Live | Start FastAPI server |
| `onco-extract ingest <path> --project <name>` | Stub | Ingest source files |
| `onco-extract extract --project <name>` | Stub | Run extraction pipeline |
| `onco-extract derive-endpoints --project <name>` | Stub | Compute PFS/OS/LC |
| `onco-extract export-csv --project <name>` | Stub | Export analysis CSV |
| `onco-extract ocr --project <name>` | Stub | OCR images |
| `onco-extract translate --project <name>` | Stub | Translate Chinese docs |
| `onco-extract review-ui --project <name>` | Stub | Launch review UI |

## API Endpoints

| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | Live |
| `/ready` | GET | Live |
| `/projects/` | GET, POST | Stub |
| `/patients/` | GET | Stub |
| `/pipeline/extract` | POST | Stub |
| `/pipeline/derive-endpoints` | POST | Stub |
| `/export/csv` | POST | Stub |

## Key Design Decisions

1. **ProvenanceRecord** — Every extracted field carries full evidence provenance (source, location, confidence, review status)
2. **Structured-first** — Never use NLP if structured data already answers the question
3. **Protocol-based storage** — DuckDB (columnar analytics) or SQLite (simple fallback), selected via config
4. **Cancer configs** — Base + override YAML with deep merge for extensibility
5. **Null means unknown** — Never default or guess values; unknown must be null
6. **Flat values + linked provenance** — Models store flat queryable values with a provenance list for audit

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests (77 tests, ~2s)
python -m pytest tests/ -v

# Lint + format
ruff check --fix app/ tests/ && ruff format app/ tests/

# Type check
mypy app/

# Docker
docker compose up
```

## Roadmap

| Phase | Scope |
|-------|-------|
| **1 (done)** | Skeleton, models, config, storage, API/CLI stubs, 77 tests |
| 2 | Full DuckDB persistence, provenance queries, serialization |
| 3 | Epic FHIR adapter — Patient/Encounter/Condition/Observation mapping |
| 4 | English NLP — medSpaCy/scispaCy pipelines, section/context extraction |
| 5 | Imaging + staging — RECIST rules, TNM parser, metastasis detection |
| 6 | Timeline engine — event dedup, PFS/OS/LC derivation, censoring |
| 7 | Chinese OCR + translation — PaddleOCR, NLLB, Chinese direct-rule validator |
| 8 | Review UI + export — Streamlit, review queue, analysis_ready.csv |
| 9 | Hardening — integration tests, performance, docs, example studies |
