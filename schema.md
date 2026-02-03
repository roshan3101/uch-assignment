# Data Schema Documentation

## Overview

This document describes the data models used by the tender scraper, including tender records and run metadata.

---

## Tender Records

### Table/Collection: `tenders`

Complete tender information with all extracted fields.

| Field | Type | Required | Description | Reason for Inclusion |
|-------|------|----------|-------------|----------------------|
| `id` | Integer | Yes | Auto-increment primary key | Database indexing |
| `tender_id` | String(50) | Yes | Unique tender identifier from source | Primary identifier for deduplication |
| `tender_type` | Enum | No | Type of tender (Goods/Works/Services) | Business classification, filtering |
| `tender_status` | Enum | No | Current status (In Progress/Closed/Awarded) | Track tender lifecycle |
| `title` | Text | Yes | Tender title/name of work | Primary description field |
| `organization` | Text | Yes | Issuing organization name | Identify procuring entity |
| `publish_date` | Date | No | Publication date (YYYY-MM-DD) | Track timeline, filter recent tenders |
| `closing_date` | Date | No | Submission deadline (YYYY-MM-DD) | Critical for bidders, urgency indicator |
| `estimated_value` | Float | No | Estimated contract value (₹) | Budget analysis, size classification |
| `description` | Text | No | Detailed tender description | Complete tender requirements |
| `source_url` | Text | Yes | Original tender page URL | Traceability, verification |
| `ifb_number` | String(100) | No | IFB/Tender notice number | Official reference number |
| `document_count` | Integer | No | Number of attachments | Completeness indicator |
| `location` | Text | No | Project location | Geographic filtering |
| `department` | Text | No | Department name | Organizational filtering |
| `category` | Text | No | Tender category | Subject matter classification |
| `attachments` | JSON | No | Array of attachment objects | Document access |
| `raw_html_snippet` | Text | No | Raw HTML for debugging | Troubleshooting extraction issues |
| `ingested_at` | DateTime | Yes | Timestamp when scraped | Data freshness tracking |
| `created_at` | DateTime | Yes | Record creation timestamp | Audit trail |
| `updated_at` | DateTime | Yes | Last update timestamp | Change tracking |

### Tender Type Enum

```
- Goods      : Procurement of physical items
- Works      : Construction/engineering projects  
- Services   : Consultancy/operational services
- Unknown    : Type could not be determined
```

### Attachment Object Schema

```json
{
  "name": "string",      // Document filename
  "url": "string",       // Download URL (optional)
  "size": "string",      // File size (optional)
  "type": "string"       // File extension/type (optional)
}
```

---

## Run Metadata

### Table/Collection: `run_metadata`

Tracks each scraper execution for observability and debugging.

| Field | Type | Required | Description | Reason for Inclusion |
|-------|------|----------|-------------|----------------------|
| `run_id` | String(100) | Yes | Unique run identifier | Correlate logs and outputs |
| `start_time` | DateTime | Yes | Run start timestamp | Performance tracking |
| `end_time` | DateTime | No | Run end timestamp | Calculate duration |
| `duration_seconds` | Float | No | Total execution time | Performance metrics |
| `scraper_version` | String(20) | Yes | Scraper version (git SHA) | Reproducibility |
| `config` | JSON | Yes | Configuration used | Debugging, replay runs |
| `pages_visited` | Integer | Yes | Total pages scraped | Volume indicator |
| `tenders_parsed` | Integer | Yes | Tenders successfully parsed | Success rate |
| `tenders_saved` | Integer | Yes | Tenders saved to storage | Output volume |
| `failures` | Integer | Yes | Number of failures | Error rate |
| `deduped_count` | Integer | Yes | Duplicates removed | Data quality metric |
| `tender_types_processed` | JSON | Yes | Count by tender type | Distribution analysis |
| `error_summary` | JSON | Yes | Categorized error messages | Debugging failed runs |
| `output_file` | String | No | Path to output file | Easy output location |

### Configuration Object (config field)

```json
{
  "limit": 100,              // Max tenders to scrape
  "format": "json",          // Output format
  "concurrency": 3,          // Parallel browsers
  "rate_limit": 1.0,         // Seconds between requests
  "headless": true,          // Browser mode
  "scrape_details": false    // Detail page scraping
}
```

### Tender Types Processed (tender_types_processed field)

```json
{
  "Goods": 150,
  "Works": 3500,
  "Services": 650,
  "Unknown": 3
}
```

### Error Summary (error_summary field)

```json
{
  "ParseError": [
    {
      "message": "Failed to extract tender_id",
      "timestamp": "2026-02-01T10:30:00Z"
    }
  ],
  "Navigation": [
    {
      "message": "Timeout loading page",
      "timestamp": "2026-02-01T10:35:00Z"
    }
  ]
}
```

---

## Why These Fields Matter

### For Observability & Debugging

- **run_id**: Correlates all logs, outputs, and errors for a single execution
- **duration_seconds**: Identifies performance regressions
- **pages_visited**: Detects incomplete runs
- **failures**: Immediate error rate visibility
- **error_summary**: Categorized errors for targeted fixes

### For Data Quality

- **tenders_parsed vs tenders_saved**: Data loss detection
- **deduped_count**: Identifies duplicate sources
- **tender_types_processed**: Classification accuracy
- **ingested_at**: Stale data identification

### For Business Intelligence

- **tender_type**: Segment analysis by category
- **estimated_value**: Budget distribution analysis
- **closing_date**: Urgency and timeline tracking
- **organization**: Procurement activity by entity
- **location**: Geographic distribution

---

## Indexes for Performance

### Tenders Table

```sql
CREATE INDEX idx_tenders_tender_id ON tenders(tender_id);
CREATE INDEX idx_tenders_tender_type ON tenders(tender_type);
CREATE INDEX idx_tenders_organization ON tenders(organization);
CREATE INDEX idx_tenders_closing_date ON tenders(closing_date);
CREATE INDEX idx_tenders_ingested_at ON tenders(ingested_at);
```

### Run Metadata Table

```sql
CREATE INDEX idx_run_metadata_run_id ON run_metadata(run_id);
CREATE INDEX idx_run_metadata_start_time ON run_metadata(start_time);
```

---

## Data Normalization Rules

### Dates
- **Format**: YYYY-MM-DD (ISO 8601)
- **Source**: Usually DD-MM-YYYY from website
- **NULL**: Stored when date not available

### Text Fields
- **Trimmed**: Leading/trailing whitespace removed
- **Normalized**: Multiple spaces collapsed to single space
- **HTML**: Tags stripped from descriptions
- **Encoding**: UTF-8

### Numbers
- **Commas**: Removed from currency values
- **Type**: Float for estimated_value
- **NULL**: Stored when value not available

### Enums
- **Case**: PascalCase (e.g., "Works", "Goods")
- **Validation**: Invalid values converted to "Unknown"

---

## Sample Output

### JSON Format
```json
{
  "tender_id": "272210",
  "tender_type": "Works",
  "title": "RENOVATION WORK ON KUMAR AND KUMARI TOILET BLOCK",
  "organization": "RMC Municipal Corporation",
  "closing_date": "2026-02-17",
  "estimated_value": 392667.0,
  "source_url": "https://tender.nprocure.com/view-nit-home?id=272210",
  "document_count": 1,
  "ingested_at": "2026-02-02T18:31:00Z"
}
```

### NDJSON Format
Each line is a separate JSON object (for streaming/batch processing):
```
{"tender_id": "272210", "title": "...", ...}
{"tender_id": "272209", "title": "...", ...}
```

### Parquet Format
Columnar format optimized for analytics with automatic compression.

---

## Version History

- **v1.0.0** (2026-02-02): Initial schema
