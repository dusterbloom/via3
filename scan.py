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


PDF_FOLDER = "downloads/Serramanna"  # or wherever your PDFs are
OUTPUT_CSV = "pdf_matches.csv"

# Example patterns: coordinates (various forms), turbine models, etc.
# You can make them as broad or specific as needed:
PATTERNS = [
    re.compile(r"(WGS84|coordinate)", re.IGNORECASE),                        
    re.compile(r"\d{1,2}°\d{1,2}'\d{1,2}\.\d+\"?"),           
    re.compile(r"\b(utm|mappali|mappale|foglio|particella)\b", re.IGNORECASE), 
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

def search_pdfs_in_folder(folder_path, patterns):
    """
    Recursively search all PDFs in `folder_path`. For each PDF, open it,
    extract text line-by-line, and see if it matches any pattern in `patterns`.
    Return list of results: [(pdf_file, page_num, line_num, text_line), ...]
    """
    all_matches = []
    pdf_files = [os.path.join(root, f) 
                for root, _, files in os.walk(folder_path)
                for f in files if f.lower().endswith('.pdf')]

    # Add progress bar
    with tqdm(total=len(pdf_files), desc="Scanning PDFs") as pbar:
        for pdf_path in pdf_files:
            logging.info(f"Processing: {pdf_path}")
            matches = search_single_pdf(pdf_path, patterns)
            all_matches.extend(matches)
            pbar.update(1)
            if matches:
                logging.info(f"Found {len(matches)} matches in {pdf_path}")
    
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
    # 1) Recursively find & parse all PDFs
    logging.info(f"{Fore.CYAN}Starting PDF scan...{Style.RESET_ALL}")
    matches = search_pdfs_in_folder(PDF_FOLDER, PATTERNS)

    # 2) Write results to CSV
    write_csv(matches, OUTPUT_CSV)
    print(f"{Fore.GREEN}Found {len(matches)} matches! Results written to {OUTPUT_CSV}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
