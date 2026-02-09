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
│   │   ├── parse_by_source.py   # Parse by source (core/exit)
│   │   ├── parse_exit_codebook.py # Exit codebook parsing
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

Parse codebook files into structured JSON (core and exit use separate parsers; `parse_codebooks` for core, `parse_exit_codebook` / `parse_by_source` for exit):

```bash
# Parse specific year (core)
python -m src.parse.parse_codebooks --data-dir data --output-dir data/parsed --year 2020

# Parse all years (core)
python -m src.parse.parse_codebooks --data-dir data --output-dir data/parsed

# Build cross-year catalog (core)
python -m src.parse.parse_codebooks --build-catalog
```

### Loading into MongoDB

Configure the MongoDB Compass locally to store the parsed data.

Load parsed codebooks into MongoDB:

```bash
# Load all codebooks locally
python -m src.database.load_codebooks

# load all codebooks into MongoDB Cloud
python -m src.database.load_codebook_to_mongodb_atlas


# Load specific source (core or exit)
python -m src.database.load_codebooks --source hrs_core_codebook
python -m src.database.load_codebooks --source hrs_exit_codebook

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

**Web UI tabs:** Dashboard (years/sources), Codebooks, **Exit Codebooks**, Categorization (full / by section / level / type / base name / special), Search Variables, Sections, Utilities (extract base name, construct variable name, year↔prefix). **Exit Codebooks:** load exit codebooks by year; click a codebook to open the detail panel with Sections and Variables tabs. Sections and variables load in parallel with a single loading state; variables are lazy-loaded in batches with a “Load more” button. Close, Sections, and Variables buttons use the same design pattern as the Search Exit row. Search results and variable-detail modal require a valid year (1992–2030) in filters; year options in dropdowns exclude invalid values (e.g. 0). Static assets are modular: CSS under `static/css/`, JS under `static/js/` (see `report/UI.md`).

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
| GET | `/exit/variables` | List exit variables (`?year=`, optional `?limit=`) |
| GET | `/exit/variables/{variable_name}` | Exit variable details (`?year=`) |
| GET | `/exit/sections` | List exit sections (`?year=`) |
| GET | `/exit/sections/{section_code}` | Exit section details (`?year=`) |
| GET | `/exit/search` | Search exit variables (`?q=`, optional `?year=`, `?limit=`) |

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
GET /exit/variables?year=2020&limit=1000
GET /exit/variables/VARNAME?year=2020
GET /exit/search?q=term&year=2020

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