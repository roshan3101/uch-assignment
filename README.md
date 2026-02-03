# Tender Scraper - NProcure Gujarat

A production-ready web scraper for extracting tender data from https://tender.nprocure.com with JSON/File storage.

## Features

- **Browser Automation** - Playwright for reliable extraction
- **Advanced Search** - Filter by keyword, status, type, organization, value range
- **Detail Scraping** - Extract complete tender information including specs & contacts
- **File Storage** - Data persisted in JSON files
- **Configurable** - Rate limiting, concurrency, search filters
- **Metadata Tracking** - Complete run observability

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run scraper
python scrape.py --limit 50
```

## Usage

### Basic Scraping

```bash
# Scrape 50 tenders to data/output directory
python scrape.py --limit 50

# Dry run (no saving)
python scrape.py --limit 10 --dry-run
```

### Advanced Search

```bash
# Search by keyword
python scrape.py --search "construction" --limit 30

# Filter by status
python scrape.py --status in_progress --limit 50

# Filter by type and value range
python scrape.py \
  --tender-type works \
  --min-value 1000000 \
  --limit 30

# Combined filters
python scrape.py \
  --search "road construction" \
  --tender-type works \
  --status in_progress \
  --min-value 1000000 \
  --limit 20
```

### Detail Scraping

Extract complete tender information including eligibility, specifications, and contact details:

```bash
# Scrape with full details
python scrape.py --scrape-details --limit 15

# Search + Details
python scrape.py \
  --search "supply" \
  --scrape-details \
  --limit 20
```

## CLI Options

```bash
--limit N                # Max tenders to scrape
--scrape-details         # Extract full details (slower, more complete)
--search "keyword"       # Search keyword
--status STATUS          # Filter: in_progress|awarded|closed|cancelled
--tender-type TYPE       # Filter: works|goods|services
--organization "name"    # Filter by organization
--min-value N            # Minimum estimated value
--max-value N            # Maximum estimated value
--concurrency N          # Parallel browser instances (default: 3)
--rate-limit N           # Delay between requests (default: 1.0)
--save-file              # Also save to file (in addition to DB)
--format FORMAT          # File format: json (default: json)
--dry-run                # Test without saving
```

## Configuration

Create `.env` file:

```env
# Scraping
API_BASE_URL=https://tender.nprocure.com
RATE_LIMIT=1.0
CONCURRENCY=3
BROWSER_HEADLESS=true

# Optional Directory Config
OUTPUT_DIR=data/output
METADATA_DIR=data/metadata
LOG_DIR=data/logs
```

## Data Output

Data is saved as JSON files in the `data/output` directory.
Run metadata (stats, timings) is saved in `data/metadata`.

### Tender Records

- Basic: tender_id, title, organization, ifb_number
- Dates: publish_date, closing_date
- Financial: estimated_value
- Classification: tender_type, tender_status
- Location: location, department, category
- Details: description, eligibility, specifications, terms_conditions
- Contact: contact_info (JSON)
- Meta: source_url, attachments (JSON), document_count
- Tracking: ingested_at, updated_at

## Project Structure

```
.
├── scraper/              # Main package
│   ├── api/             # API client (backup)
│   ├── browser/         # Browser automation
│   ├── search.py        # Advanced search
│   ├── models.py        # Data models
│   ├── cleaner.py       # Data cleaning
│   ├── storage.py       # Storage (JSON file)
│   └── metadata.py      # Run tracking
├── config/              # Configuration
├── scrape.py            # Main CLI
├── requirements.txt     # Dependencies
├── README.md            # This file
├── schema.md            # Data schema documentation
└── architecture.md      # Architecture documentation
```

## Performance

| Mode | Speed | Data Completeness |
|------|-------|-------------------|
| Basic (homepage) | ~50 tenders/min | 60% |
| With Details | ~10-15 tenders/min | 95% |

**Recommendations:**
- Use basic mode for large datasets (>100 tenders)
- Use detail mode for targeted research (<50 tenders)
- Apply search filters to reduce dataset before scraping

## Support

For issues:
1. Check logs in `data/logs/`
2. Check output files in `data/output/`

---

**Status: Production Ready** | **Storage: Local JSON** | **Version: 2.1**
