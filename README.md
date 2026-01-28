# HRS Data Pipeline

A data pipeline for fetching, parsing, and processing Human Resources Survey (HRS) codebooks and data.

## Project Structure

```bash
hrs_pipeline/
  config/
    sources.yaml              # Data source configuration
  src/
    discovery/
      discover_codebooks.py
    fetch/
      http_client.py          # HTTP client for fetching data
      fetch_sources.py        # Main fetching script
    parse/
      parse_html_codebook.py
      parse_pdf_codebook.py   # optional
      models.py               # pydantic schemas for parsed entities
    # normalize/
    #   canonicalize.py
    #   concept_mapping.py
    # db/
    #   schema.sql
    #   write_relational.py
    #   write_embeddings.py     # optional
    api/
      app.py                  # FastAPI: /search, /variable/{id}, /years
  data/
    raw/                      # Raw fetched data (organized by source name)
    parsed/
  scripts/
    run_discovery.sh
    run_ingest.sh
```

## Usage

### Fetching Data Sources

The `fetch_sources.py` script fetches data from configured sources defined in `config/sources.yaml`.

#### Fetch All Sources

Fetch all sources defined in the configuration file:

```bash
# Using Python module
python -m src.fetch.fetch_sources

# Or using uv
uv run python -m src.fetch.fetch_sources
```

#### Fetch Specific Sources

Fetch only specific data sources by name:

```bash
# Fetch a single source
python -m src.fetch.fetch_sources --source hrs_core_codebook

# Fetch multiple sources
python -m src.fetch.fetch_sources --source hrs_core_codebook --source hrs_exit_codebook

# Using short form
python -m src.fetch.fetch_sources -s hrs_core_codebook -s hrs_exit_imputations_codebook
```

#### Custom Configuration and Output

```bash
# Use a custom configuration file
python -m src.fetch.fetch_sources --config path/to/custom_sources.yaml

# Specify a custom output directory
python -m src.fetch.fetch_sources --output-dir data/custom_raw

# Combine options
python -m src.fetch.fetch_sources \
  --config config/custom.yaml \
  --output-dir data/custom \
  --source hrs_core_codebook \
  --source hrs_exit_codebook
```

### Command-Line Options

- `--config`, `-c`: Path to YAML configuration file (default: `config/sources.yaml`)
- `--output-dir`, `-o`: Output directory for fetched files (default: `data/raw`)
- `--source`, `-s`: Name of a source to fetch (can be specified multiple times). If omitted, all sources from config will be fetched.

### Available Data Sources

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

### Output Structure

Fetched files are organized by source name in separate directories:

```
data/raw/
  hrs_core_codebook/
    hrs_core_codebook_1992.html
    hrs_core_codebook_1994.html
    ...
  hrs_exit_codebook/
    hrs_exit_codebook_1996.html
    hrs_exit_codebook_1998.html
    ...
```

### Configuration

Edit `config/sources.yaml` to:
- Add or modify data sources
- Configure URL patterns for each source type
- Set years to fetch for each source
- Define source metadata (type, description, etc.)
