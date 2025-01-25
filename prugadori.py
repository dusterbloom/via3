#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import csv
import pdfplumber
import logging
from tqdm import tqdm
from colorama import init, Fore, Style
init()  # Initialize colorama

# PDF_FOLDER = "C:\Users\PC\Dev\via2\downloads\Serramanna" 
#OUTPUT_CSV = "scan_serramanna.csv"

# You can make them as broad or specific as needed:
PATTERNS = [
    # Original patterns
    re.compile(r"(WGS84|coordinate)", re.IGNORECASE),

    # Decimal degrees (DD) format
    # Examples: 41.40338, 2.17403 or 41°24'12.2"N 2°10'26.5"E
    #re.compile(r"\b\d{1,3}[°d]\s*\d{1,2}[′'m]\s*\d{1,2}(\.\d+)?[″"s]\s*[NSEW]\b", re.IGNORECASE),

    re.compile(r"\b[-+]?[0-9]*\.?[0-9]+°?\s*[NS]?\s*,?\s*[-+]?[0-9]*\.?[0-9]+°?\s*[EW]?\b", re.IGNORECASE),

    # Degrees, minutes, seconds (DMS) format
    # Examples: 41°24'12.2"N or 2°10'26.5"E
    re.compile(r"\b\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(\.\d+)?\"?\s*[NSEW]\b", re.IGNORECASE),

    # Degrees and decimal minutes (DMM) format
    # Example: 41 24.2028, 2 10.4418
    re.compile(r"\b\d{1,3}°?\s*\d{1,2}\.\d+['′]?\s*[NSEW]?\b", re.IGNORECASE),

    # UTM coordinates
    # Example: 31N 430959.54 4581999.91
    re.compile(r"\b\d{1,2}[NS]\s*\d{6,7}(\.\d+)?\s*\d{6,7}(\.\d+)?\b", re.IGNORECASE),

    # Italian cadastral references
    re.compile(r"\b(foglio|particella|mappale)\s*n?\.*\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bmappali\s*n?\.*\s*\d+(?:\s*,\s*\d+)*\b", re.IGNORECASE),

    # Your existing patterns for other matches
    re.compile(r"(nordex|vestas|siemens)", re.IGNORECASE),
    re.compile(r"\baltezza\b|\baltitudine\b|\bhub\b|\btip\b|\blama\b|\bblade\b|\brotore\b|\bdiametro\b", re.IGNORECASE)
]



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_scan.log'),
        logging.StreamHandler()
    ]
)

def get_all_pdfs(base_folder: str) -> list:
    """
    Recursively find all PDF files in base_folder and its subfolders.
    Returns a list of full paths to PDF files.
    """
    pdf_files = []
    for root, _, files in os.walk(base_folder):
        for file in files:
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(root, file)
                pdf_files.append(full_path)
                logging.info(f"Found PDF: {full_path}")
    return pdf_files

def search_pdfs_in_folder(folder_path, patterns):
    """
    Recursively search all PDFs in `folder_path` and its subfolders.
    For each PDF, extract text line-by-line, and see if it matches any pattern in `patterns`.
    Return list of results: [(pdf_file, page_num, line_num, text_line), ...]
    """
    all_matches = []
    pdf_files = get_all_pdfs(folder_path)

    # Add progress bar
    with tqdm(total=len(pdf_files), desc="Scanning PDFs") as pbar:
        for pdf_path in pdf_files:
            try:
                logging.info(f"Processing: {pdf_path}")
                matches = search_single_pdf(pdf_path, patterns)
                all_matches.extend(matches)
                if matches:
                    logging.info(f"Found {len(matches)} matches in {pdf_path}")
            except Exception as e:
                logging.error(f"Error processing {pdf_path}: {e}")
            finally:
                pbar.update(1)
    
    return all_matches

def search_single_pdf(pdf_path, regex_list):
    results = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                lines = text.splitlines()
                for line_idx, line in enumerate(lines, start=1):
                    if any(regex.search(line) for regex in regex_list):
                        results.append((pdf_path, page_idx, line_idx, line))
                        # Print match in green
                        print(f"{Fore.GREEN}Match found in {pdf_path}:")
                        print(f"Page {page_idx}, Line {line_idx}: {line}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[WARN] Failed to parse {pdf_path}: {e}{Style.RESET_ALL}")
    return results

def write_csv(results, output_csv):
    """
    Write the matches to a CSV file with columns:
    [filename, page_number, line_number, matched_line]
    """
    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["PDF_File", "Page", "Line", "Matched_Text"])
        for (pdf_file, page_num, line_num, matched_line) in results:
            writer.writerow([pdf_file, page_num, line_num, matched_line])

def main():
    # Prompt user for the base folder
    folder_path = input("Inserisci la cartella da cui partire (lo scan include le sottocartelle): ").strip()
    if not os.path.exists(folder_path):
        print(f"{Fore.RED}[ERROR] Folder not found: {folder_path}{Style.RESET_ALL}")
        return

    # 1) Recursively find & parse all PDFs
    logging.info(f"{Fore.CYAN}Starting PDF scan in {folder_path} and all subfolders...{Style.RESET_ALL}")
    matches = search_pdfs_in_folder(folder_path, PATTERNS)

    # 2) Write results to CSV
    output_csv = "scan_results.csv"
    write_csv(matches, output_csv)
    print(f"{Fore.GREEN}Found {len(matches)} matches! Results written to {output_csv}{Style.RESET_ALL}")

    # Print summary
    pdf_count = len(set(match[0] for match in matches))  # unique PDFs with matches
    print(f"\nSummary:")
    print(f"- Total matches found: {len(matches)}")
    print(f"- PDFs with matches: {pdf_count}")
    print(f"- Results saved to: {output_csv}")

if __name__ == "__main__":
    main()
