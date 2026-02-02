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

**Example Endpoints:**
- `GET /codebooks` - List all codebooks
- `GET /codebooks/{year}` - Get codebook by year
- `GET /variables/{variable_name}?year=2020` - Get variable details
- `GET /search?q=SUBHH` - Search variables
- `GET /sections?year=2020` - Get sections for a year
- `GET /years` - Get available years and sources
- `GET /stats` - Get database statistics

See `src/api/README.md` for complete API documentation.

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
