# HRS Data Pipeline

A data pipeline for fetching, parsing, and processing Human Resources Survey (HRS) codebooks and data.

## Project Structure

```
hrs_data_pipeline/
├── config/
│   └── sources.yaml              # Data source configuration
├── src/
│   ├── discovery/               # Codebook discovery module
│   ├── fetch/                   # Data fetching module
│   │   ├── client.py            # HTTP client
│   │   └── fetch_sources.py     # Main fetching script
│   ├── parse/                   # Codebook parsing module
│   │   ├── models.py            # Pydantic data models
│   │   ├── parse_txt_codebook.py
│   │   ├── parse_codebooks.py   # Main parsing script
│   │   └── save_codebook.py     # JSON save utilities
│   ├── database/                # MongoDB integration
│   │   ├── mongodb_client.py    # MongoDB connection
│   │   └── load_codebooks.py    # Data loading script
│   ├── api/                     # FastAPI application
│   │   ├── routes/              # general, codebooks, variables, sections, search, utilities, categorizer
│   │   ├── models/              # Pydantic response models (responses.py)
│   │   └── static/              # Web UI
│   │       ├── css/             # base, layout, components, categorization, utilities
│   │       ├── js/              # state, api, tabs, filters, dashboard, codebooks, categorization, search, sections, modal, utilities, app
│   │       ├── index.html
│   │       └── styles.css
│   └── test/                    # Unit tests
├── data/
│   ├── raw/                     # Fetched raw codebook files
│   └── parsed/                  # Structured JSON output
├── report/                      # Documentation and reports
└── scripts/                     # Utility scripts
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

Parse codebook files into structured JSON:

```bash
# Parse specific year
python -m src.parse.parse_codebooks --data-dir data --output-dir data/parsed --year 2020

# Parse all years
python -m src.parse.parse_codebooks --data-dir data --output-dir data/parsed

# Build cross-year catalog
python -m src.parse.parse_codebooks --build-catalog
```

### Loading into MongoDB

Configure the MongoDB Compass locally to store the parsed data.

Load parsed codebooks into MongoDB:

```bash
# Load all codebooks
python -m src.database.load_codebooks

# Load specific source
python -m src.database.load_codebooks --source hrs_core_codebook

# Load specific year
python -m src.database.load_codebooks --year 2020

# Create indexes for better performance
python -m src.database.load_codebooks --create-indexes
```

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

**Web UI tabs:** Dashboard (years/sources), Codebooks, Categorization (full / by section / level / type / base name / special), Search Variables, Sections, Utilities (extract base name, construct variable name, year↔prefix). Search results and variable-detail modal require a valid year (1992–2030) in filters; year options in dropdowns exclude invalid values (e.g. 0). Static assets are modular: CSS under `static/css/`, JS under `static/js/` (see `report/UI.md`).

**Example Endpoints:**
- `GET /codebooks` - List all codebooks
- `GET /codebooks/{year}` - Get codebook by year
- `GET /variables?year=2020&source=hrs_core_codebook` - List variables (optional section, level, limit)
- `GET /variables/{variable_name}?year=2020&source=hrs_core_codebook` - Get variable details (year required, 1992–2030)
- `GET /variables/base/SUBHH` - Variable by base name (optional `years=2016,2020`)
- `GET /variables/base/SUBHH/temporal` - Temporal mapping for base name
- `GET /search?q=SUBHH&year=2020` - Search variables
- `GET /sections?year=2020` - Get sections for a year
- `GET /years` - Get available years and sources
- `GET /stats` - Get database statistics
- `GET /categorization?year=2020` - Full categorization; also `GET /categorization/sections`, `/levels`, `/types`, `/base-names`, `/special`
- `GET /utils/extract-base-name?variable_name=RSUBHH` - Extract base name
- `GET /utils/construct-variable-name?base_name=SUBHH&year=2020` - Construct variable name
- `GET /utils/year-prefix`, `GET /utils/prefix-year` - Year↔prefix mapping

See `report/APIS.md` and `src/api/README.md` (if present) for full API and model details.

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

### Variable endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/variables` | List variables with optional filters |
| GET | `/variables/{variable_name}` | Get one variable’s full details (year + source required) |
| GET | `/variables/base/{base_name}` | Get a variable by base name across one or all years |
| GET | `/variables/base/{base_name}/temporal` | Get temporal mapping (years, prefixes) for a base name |

**Examples:**

```bash
# List variables for a codebook (optional: section, level, limit; default limit=100)
GET /variables?year=2020&source=hrs_core_codebook
GET /variables?year=2020&section=Household%20Roster&limit=50

# Get full details for a specific variable (year required, 1992–2030)
GET /variables/RSUBHH?year=2020&source=hrs_core_codebook
# Returns: name, description, year, section, level, type, width, decimals, value_codes, assignments, references

# Get SUBHH across all years (optional: source, default hrs_core_codebook)
GET /variables/base/SUBHH

# Get SUBHH for specific years only
GET /variables/base/SUBHH?years=2016,2018,2020
GET /variables/base/SUBHH?years=2016,2018,2020&source=hrs_core_codebook

# Get temporal mapping for a base name (years present, year→prefix, first/last year)
GET /variables/base/SUBHH/temporal
# Returns: base_name, years[], year_prefixes{}, first_year, last_year, consistent_metadata, consistent_values
```

### Other API endpoints

```bash
# Wave information
GET /waves/15
# Returns wave 15 (e.g. year 2020)

# Extract base name from variable name
GET /utils/extract-base-name?variable_name=RSUBHH
# Returns: {"variable_name": "RSUBHH", "base_name": "SUBHH", "prefix": "R"}

# Construct variable name from base name and year
GET /utils/construct-variable-name?base_name=SUBHH&year=2020
# Returns: {"base_name": "SUBHH", "year": 2020, "wave": 15, "prefix": "R", "variable_name": "RSUBHH"}

# Year ↔ prefix (wave) mapping
GET /utils/year-prefix?year=2020
GET /utils/prefix-year?prefix=R
```

### Codebook Discovery
# Categorize all years
python -m src.discovery.discover_codebooks

# Categorize specific year
python -m src.discovery.discover_codebooks --year 2020

# Save to JSON file
python -m src.discovery.discover_codebooks --output report/categorization.json

# Include variable names in output
python -m src.discovery.discover_codebooks --output report/categorization.json --include-names
```