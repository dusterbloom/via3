# VA.MITE Document Tools

A collection of Python utilities for working with VA.MITE portal documents.

## Tools Included

### 1. Project Lister (list_projects.py)
Creates a CSV list of projects from VA.MITE portal search results.

- 🔍 Search in "Progetti" section
- 📑 Handles multi-page results
- 📊 Exports to CSV with project details
- ✅ Includes YES/NO flags for selective downloading

### 2. Batch Downloader (download_from_list.py)
Downloads documents from projects listed in projects_list.csv.

- 📋 Reads from projects_list.csv
- ✨ Only downloads projects marked as "YES"
- 📁 User-specified download folders
- 🗂️ Organizes by project ID

### 3. Document Scraper (main.py)
Downloads documents from VA.MITE portal based on search keywords.

- 🔍 Search in "Progetti" or "Documenti" sections
- 📑 Handles multi-page results
- 🗂️ Organizes by keyword and project ID

### 4. PDF Pattern Scanner (scan.py)
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

2. List projects:
```bash
python list_projects.py
# Enter search keyword (e.g., "Sardegna")
# Results saved to projects_list.csv
```

3. Edit projects_list.csv to mark which projects to download (YES/NO)

4. Download selected projects:
```bash
python download_from_list.py
# Enter folder name for downloads
```

5. Or download directly via search:
```bash
python main.py
# Follow prompts for keyword and search type
```

6. Scan PDFs:
```bash
python scan.py
# Results saved to pdf_matches.csv
```

## Configuration

### Common Settings
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

## File Structure
```
.
├── projects_list.csv         # Project list with download flags
├── downloads/               
│   └── [user_folder]/       # User-specified download folder
│       └── [project_id]/    # Individual project folders
│           └── documents... # Downloaded files
└── pdf_matches.csv          # PDF scan results
```

## Requirements

- Python 3.x
- requests
- beautifulsoup4
- pdfplumber
- colorama
- tqdm

## License

MIT License