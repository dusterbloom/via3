# VA.MITE Document Tools

A collection of Python utilities for working with VA.MITE portal documents.

## Tools Included

### 1. Document Scraper (main.py)
Downloads documents from VA.MITE portal based on search keywords.

- 🔍 Search in "Progetti" or "Documenti" sections
- 📑 Handles multi-page results
- 🗂️ Organizes by keyword and project ID

### 2. PDF Pattern Scanner (scan.py)
Scans downloaded PDFs for specific patterns and exports matches.

- 📁 Recursive PDF scanning
- 🔍 Built-in patterns for coordinates, technical terms
- 📊 CSV export with page/line references
- 🎨 Colored console output for matches

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Download documents:
```bash
python main.py
# Follow prompts for keyword and search type
```

3. Scan PDFs:
```bash
python scan.py
# Results saved to pdf_matches.csv
```

## Configuration

### Document Scraper (main.py)
```python
BASE_URL = "https://va.mite.gov.it"
DOWNLOAD_FOLDER = "downloads"
DELAY_BETWEEN_REQUESTS = 1.0
```

### PDF Scanner (scan.py)
```python
PDF_FOLDER = "downloads/Serramanna"
OUTPUT_CSV = "pdf_matches.csv"
```

## Requirements

- Python 3.x
- requests
- beautifulsoup4
- pdfplumber
- colorama
- tqdm

## File Structure
```
downloads/
└── [keyword]/
    └── [Progetti|Documenti]/
        └── [project_id]/
            └── documents...
```

## License

MIT License
