# HRS Data Pipeline

A data pipeline for fetching, parsing, and processing Human Resources Survey (HRS) codebooks and data.

## Project Structure

```
hrs_data_pipeline/
├── config/
│   └── sources.yaml              # Data source configuration
├── src/
│   ├── config_loader.py          # Config loading utilities
│   ├── discovery/                # Codebook discovery module
│   ├── fetch/                    # Data fetching module
│   │   ├── client.py             # HTTP client
│   │   └── fetch_sources.py      # Main fetching script
│   ├── parse/                    # Codebook parsing module
│   │   ├── parse_codebooks.py    # Main parsing script (core)
│   │   ├── parse_by_source.py    # Parse by source (core/exit/post-exit)
│   │   ├── parse_exit_codebook.py # Exit codebook parsing
│   │   ├── parse_post_exit_codebook.py # Post-exit .txt codebook parsing
│   │   ├── parse_txt_codebook.py
│   │   ├── save_codebook.py      # JSON save utilities
│   │   └── ...
│   ├── database/                 # MongoDB integration
│   │   ├── mongodb_client.py              # MongoDB connection
│   │   ├── load_codebooks.py              # Load to local MongoDB
│   │   └── load_codebook_to_mongodb_atlas.py  # Load to MongoDB Atlas (uses .env)
│   ├── api/                      # FastAPI application
│   │   ├── routes/
│   │   │   ├── core/             # codebooks, variables, sections, search
│   │   │   ├── exit/             # Exit codebook routes (routes.py)
│   │   │   ├── post_exit/        # Post-exit codebook routes (routes.py)
│   │   │   └── shared/           # general, categorizer, utilities
│   │   ├── models/               # Pydantic response models (responses.py)
│   │   └── static/               # Web UI
│   │       ├── css/              # base, layout, components, categorization, exit, utilities
│   │       ├── js/               # api, app, dashboard, codebooks, exit, categorization, modal, search, sections, tabs, utils, ...
│   │       ├── index.html
│   │       └── styles.css
│   └── test/                     # Unit tests
├── data/
│   ├── raw/                      # Fetched raw codebook files
│   └── parsed/                   # Structured JSON output
├── report/                       # Documentation and reports
└── scripts/                      # Utility scripts
```

## Development pipeline

One-command setup to run the full stack locally: **vanilla JS/CSS** frontend, **FastAPI** backend, and **MongoDB** (local or Atlas).

### Prerequisites

- **Python 3.10+** and **uv** (recommended) or pip/venv  
- **MongoDB**: local instance, Docker, or MongoDB Atlas (see below)

### 1. Install dependencies

From the project root:

```bash
uv sync
# or: pip install -e .
```

### 2. Environment and database

- Copy `.env.example` to `.env` in the project root.
- Set **local MongoDB** (defaults if omitted):
  - `MONGODB_CONNECTION_STRING=mongodb://localhost:27017/`
  - `MONGODB_DATABASE_NAME=hrs_data`
- **Optional – local MongoDB via Docker:** `docker compose up -d`, then use the same `.env` (or leave defaults).
- **MongoDB Atlas (recommended for production and deploy):** In Atlas, go to **Clusters → Connect → Connect your application** and copy the URI. Set in `.env`: `MONGODB_CONNECTION_STRING=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority` and `MONGODB_DATABASE_NAME=hrs_data`. Ensure your Atlas user has read/write access and that the deployment host’s IP is allowed (or use 0.0.0.0/0 for cloud deploys).

### 3. Run the API (serves UI + API)

From the project root:

```bash
# Recommended: dev server with hot reload
uv run hrs-dev
```

Or use the scripts:

```bash
# Windows
scripts\run_api.bat

# Linux / macOS
./scripts/run_api.sh
```

Or manually with uvicorn:

```bash
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open the app

- **Web UI (vanilla JS/CSS):** http://localhost:8000/  
- **API docs (Swagger):** http://localhost:8000/docs  
- **ReDoc:** http://localhost:8000/redoc  

The frontend is served from `src/api/static/` (no build step). The UI uses `window.location.origin` for API calls, so it works against the same host.

### Quick reference

| Task              | Command / step                                      |
|-------------------|------------------------------------------------------|
| Install deps      | `uv sync`                                           |
| Local MongoDB     | `docker compose up -d` (optional)                    |
| Start API + UI    | `uv run hrs-dev` or `scripts\run_api.bat` / `run_api.sh` |
| Load data (local) | `python -m src.database.load_codebooks`              |
| Load data (Atlas) | `python -m src.database.load_codebook_to_mongodb_atlas` |
| Run tests         | `uv run pytest -q` or `python -m pytest src/test/ -v` |

## MongoDB Atlas and deploy from GitHub

The app uses a **single MongoDB connection string** (`MONGODB_CONNECTION_STRING`). For production and hosted deploys, use **MongoDB Atlas** and set that variable to your Atlas URI (see `.env.example`).

### Deploy from GitHub

Two options: **Render** (no Docker, connect repo) or **Fly.io** (Docker, deploy via GitHub Actions).

#### Option A: Render

1. Push this repo to GitHub.
2. In [Render](https://render.com), create a **Web Service**, connect the repo, and use the **Blueprint** (Render will use `render.yaml`).
3. In the service **Environment** tab, set:
   - `MONGODB_CONNECTION_STRING` = your Atlas URI (mark as secret).
   - `MONGODB_DATABASE_NAME` = `hrs_data` (or leave default).
4. Deploy. Render will run `pip install .` and `uvicorn src.api.app:app --host 0.0.0.0 --port $PORT`. Every push to the connected branch will trigger a new deploy.

#### Option B: Fly.io (GitHub Actions)

1. Install [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/) and run **once** from the project root:
   ```bash
   fly auth login
   fly launch
   ```
   Use the default app name or set one; create the app but skip deploying (we’ll use Actions). Set **secrets** for the running app:
   ```bash
   fly secrets set MONGODB_CONNECTION_STRING="mongodb+srv://..."
   fly secrets set MONGODB_DATABASE_NAME=hrs_data
   ```
2. In GitHub: **Settings → Secrets and variables → Actions** → add secret `FLY_API_TOKEN` (from [Fly.io Account → Access Tokens](https://fly.io/user/tokens)).
3. Push to `main`. The **Deploy** workflow (`.github/workflows/deploy.yml`) will build the Docker image and run `flyctl deploy --remote-only`. You can also run **Actions → Deploy → Run workflow** manually.

### CI (tests on push/PR)

The **CI** workflow (`.github/workflows/ci.yml`) runs on every push and pull request to `main`/`master`: installs dependencies with uv and runs `pytest src/test/`.

## Usage

### Fetching Data Sources

The `fetch_sources.py` script fetches data from configured sources defined in `config/sources.yaml`.

#### Fetch All Sources

Fetch all sources defined in the configuration file:

```bash

Create a data dir --> Keep HRS data inside the dir --> unzip h{20}cb folder

Create parsed dir inside the data dir to save the processed core_codebook data

data/
HRS Data/
    2022/
      Core/
        h22cb
parsed/
```


Configured sources include:

- `hrs_core_codebook` - HRS Core Codebook
- `hrs_exit_codebook` - HRS Exit Codebook
- `hrs_exit_imputations_codebook` - HRS Exit Imputations Codebook
- `hrs_core_imputations_codebook` - HRS Core Imputations Codebook
- `hrs_post_exit_codebook` - HRS Post Exit Codebook
- `hrs_core_industry_occupations_codebook` - HRS Core Industry Occupations Codebook
- `ahead_core_codebook` - AHEAD Core Codebook
- `ahead_core_imputations_codebook` - AHEAD Core Imputations Codebook
- `ahead_exit_imputations_codebook` - AHEAD Exit Imputations Codebook


### Parsing Codebooks

Parse codebook files into structured JSON. Core, exit, and post-exit use separate parsers; `parse_codebooks` dispatches by `--source`.

```bash
# Parse specific year (core)
python -m src.parse.parse_codebooks --data-dir data --output-dir data/parsed --year 2020

# Parse all years (core)
python -m src.parse.parse_codebooks --data-dir data --output-dir data/parsed

# Parse post-exit codebooks (.txt under data/HRS Data/{year}/Post Exit/, one main codebook per year)
python -m src.parse.parse_codebooks --source hrs_post_exit_codebook --data-dir data --output-dir data/parsed
python -m src.parse.parse_codebooks --source hrs_post_exit_codebook --data-dir data --output-dir data/parsed --year 2022

# Parse exit codebooks
python -m src.parse.parse_codebooks --source hrs_exit_codebook --data-dir data --output-dir data/parsed

# Build cross-year catalog (core)
python -m src.parse.parse_codebooks --build-catalog
```

**Post-exit:** Uses `.txt` codebook files (e.g. `PX2022cb.txt`). Parser extracts sections (with level, e.g. Respondent / HH Member Child), variables, and value codes (including missing-value labels). One main codebook file per year is used when multiple `.txt` files exist in the Post Exit folder.

### Loading into MongoDB

Configure the MongoDB Compass locally to store the parsed data.

Load parsed codebooks into MongoDB:

```bash
# Load all codebooks locally
python -m src.database.load_codebooks

# load all codebooks into MongoDB Cloud
python -m src.database.load_codebook_to_mongodb_atlas


# Load specific source (core, exit, or post-exit)
python -m src.database.load_codebooks --source hrs_core_codebook
python -m src.database.load_codebooks --source hrs_exit_codebook
python -m src.database.load_codebooks --source hrs_post_exit_codebook

# Load only post-exit codebooks
python -m src.database.load_codebooks --post-exit-only

# Load specific year
python -m src.database.load_codebooks --year 2020

# Create indexes for better performance
python -m src.database.load_codebooks --create-indexes
```

### Loading into MongoDB Atlas

Load codebooks to MongoDB Atlas using credentials from `.env` (no credentials in the command line):

```bash
# Load all codebooks to Atlas
python -m src.database.load_codebook_to_mongodb_atlas

# Load only exit codebooks
python -m src.database.load_codebook_to_mongodb_atlas --exit-only

# Load only post-exit codebooks
python -m src.database.load_codebook_to_mongodb_atlas --post-exit-only

# Load specific source or year
python -m src.database.load_codebook_to_mongodb_atlas --source hrs_exit_codebook --year 2020

# Create indexes after load
python -m src.database.load_codebook_to_mongodb_atlas --create-indexes
```

**Required in `.env`:** `MONGODB_USER`, `MONGODB_PASSWORD`. Optional: `MONGODB_DB` (default `hrs_data`), `MONGODB_ATLAS_CLUSTER` (e.g. `cluster0.xxxx.mongodb.net`). If `MONGODB_ATLAS_CLUSTER` is not set, the cluster host is taken from `MONGODB_ATLAS_CONNECTION_STRING`.

**MongoDB Setup:**

1. Create `.env` file in project root:
```env
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/
MONGODB_DATABASE_NAME=hrs_data
```

2. Start MongoDB (if running locally)

### Running the API

Start the FastAPI server to query the data:

```bash
# Using uvicorn
uvicorn src.api.app:app --reload

# Or using the script (Windows)
scripts\run_api.bat

# Or using the script (Linux/Mac)
bash scripts/run_api.sh
```

The API and UI will be available at `http://localhost:8000`

**Access Points:**
- **Web UI**: http://localhost:8000 (or http://localhost:8000/static/index.html)
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Web UI tabs:** Dashboard (years/sources), Codebooks, **Exit Codebooks**, **Post Exit Codebooks**, Categorization (full / by section / level / type / base name / special), Search Variables, Sections, Utilities (extract base name, construct variable name, year↔prefix).

- **Exit / Post Exit:** Load codebooks by year; click a codebook to open the detail panel. **Sections** and **Variables** are loaded from the API (`/exit/sections`, `/exit/variables`, `/post-exit/sections`, `/post-exit/variables`). Clicking a section filters variables by that section (and level for post-exit); “All variables” clears the filter. Variables are lazy-loaded in batches with “Load more”. Section cards show level (e.g. Respondent, Other) when present.
- **Variable detail modal:** Clicking a variable (Core, Exit, or Post Exit) opens a modal with full details and value codes; missing-value codes (e.g. Blank, INAP) are labeled. Search results and variable detail require a valid year in filters.
- Static assets are modular: CSS under `static/css/`, JS under `static/js/` (see `report/UI.md`).

See below for **API Endpoints** and `report/APIS.md` (if present) for full API and model details.

### Configuration

Edit `config/sources.yaml` to:
- Add or modify data sources
- Configure URL patterns for each source type
- Set years to fetch for each source
- Define source metadata (type, description, etc.)

### Testing


```bash
# Run all tests
python -m pytest src/test/test_pipeline.py -v
```

```bash
uv sync --extra dev
python.exe -m pytest -q
```

### API Endpoints

**General**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root / UI redirect |
| GET | `/years` | Available years and sources |
| GET | `/stats` | Database statistics |
| GET | `/waves` | List wave info |
| GET | `/waves/{wave}` | Wave details (e.g. wave 15 → year 2020) |

**Core codebooks & variables**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/codebooks` | List codebooks (optional `?year=`, `?source=`) |
| GET | `/codebooks/{year}` | Codebook summary for a year |
| GET | `/variables` | List variables (`year`, `source`; optional `section`, `level`, `limit`) |
| GET | `/variables/{variable_name}` | Variable details (requires `?year=` and `?source=`) |
| GET | `/variables/base/{base_name}` | Variable by base name (optional `?years=`, `?source=`) |
| GET | `/variables/base/{base_name}/temporal` | Temporal mapping (years, prefixes) for base name |
| GET | `/search` | Search variables (`?q=`, optional `?year=`, `?source=`, `?limit=`) |
| GET | `/sections` | List sections for a year (`?year=`) |
| GET | `/sections/{section_code}` | Section details (`?year=`) |

**Exit codebooks & variables**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/exit/codebooks` | List exit codebooks (optional `?year=`, `?source=`) |
| GET | `/exit/codebooks/{year}` | Exit codebook summary for a year |
| GET | `/exit/variables` | List exit variables (`?year=`, optional `?section=`, `?level=`, `?limit=`, max 2000) |
| GET | `/exit/variables/{variable_name}` | Exit variable details (`?year=`) |
| GET | `/exit/sections` | List exit sections (`?year=`) |
| GET | `/exit/sections/{section_code}` | Exit section details (`?year=`) |
| GET | `/exit/search` | Search exit variables (`?q=`, optional `?year=`, `?limit=`) |

**Post-exit codebooks & variables**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/post-exit/codebooks` | List post-exit codebooks (optional `?year=`, `?source=`) |
| GET | `/post-exit/codebooks/{year}` | Post-exit codebook summary for a year |
| GET | `/post-exit/variables` | List post-exit variables (`?year=`, optional `?section=`, `?level=`, `?limit=`, max 2000) |
| GET | `/post-exit/variables/{variable_name}` | Post-exit variable details (`?year=`) |
| GET | `/post-exit/sections` | List post-exit sections (`?year=`) |
| GET | `/post-exit/sections/{section_code}` | Post-exit section by code (optional `?year=`, `?level=` when multiple sections share a code) |
| GET | `/post-exit/search` | Search post-exit variables (`?q=`, optional `?year=`, `?limit=`) |

**Categorization**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categorization` | Full categorization (`?year=`) |
| GET | `/categorization/sections` | By section |
| GET | `/categorization/levels` | By level |
| GET | `/categorization/types` | By type |
| GET | `/categorization/base-names` | By base name |
| GET | `/categorization/special` | Special categories |

**Utilities**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/utils/extract-base-name` | Extract base name from variable (`?variable_name=`) |
| GET | `/utils/construct-variable-name` | Construct variable name (`?base_name=`, `?year=`) |
| GET | `/utils/year-prefix` | Year → prefix (`?year=`) |
| GET | `/utils/prefix-year` | Prefix → year (`?prefix=`) |

**Example requests**

```bash
# Core variables
GET /variables?year=2020&source=hrs_core_codebook&limit=50
GET /variables/RSUBHH?year=2020&source=hrs_core_codebook
GET /variables/base/SUBHH?years=2016,2018,2020
GET /variables/base/SUBHH/temporal
GET /search?q=SUBHH&year=2020

# Exit
GET /exit/codebooks?year=2020
GET /exit/sections?year=2020
GET /exit/variables?year=2020&limit=2000
GET /exit/variables?year=2020&section=PR&level=Respondent&limit=500
GET /exit/variables/VARNAME?year=2020
GET /exit/search?q=term&year=2020

# Post Exit
GET /post-exit/codebooks?year=2020
GET /post-exit/sections?year=2020
GET /post-exit/variables?year=2020&limit=2000
GET /post-exit/variables?year=2020&section=PR&level=Respondent&limit=500
GET /post-exit/sections/PR?year=2020&level=Respondent
GET /post-exit/variables/VARNAME?year=2020
GET /post-exit/search?q=term&year=2020

# Utils
GET /utils/extract-base-name?variable_name=RSUBHH
GET /utils/construct-variable-name?base_name=SUBHH&year=2020
GET /utils/year-prefix?year=2020
GET /utils/prefix-year?prefix=R
```

### Codebook Discovery

```bash
# Categorize all years
python -m src.discovery.discover_codebooks

# Categorize specific year
python -m src.discovery.discover_codebooks --year 2020

# Save to JSON file
python -m src.discovery.discover_codebooks --output report/categorization.json

# Include variable names in output
python -m src.discovery.discover_codebooks --output report/categorization.json --include-names
```