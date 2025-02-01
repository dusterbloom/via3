#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import csv
import urllib.parse
import requests
import logging
from bs4 import BeautifulSoup
import pdfplumber
from tqdm import tqdm
from colorama import init, Fore, Style

init()  # Initialize colorama

# --- Global Settings ---
BASE_URL = "https://va.mite.gov.it"
DELAY_BETWEEN_REQUESTS = 1.0  # in seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("unified.log"),
        logging.StreamHandler()
    ]
)

# --- Functions from tzeracu.py (modified) ---

def build_detail_url(project_id: str) -> str:
    """
    Build the detail URL using the project folder ID.
    Example: /it-IT/Oggetti/Info/<project_id>
    """
    return f"{BASE_URL}/it-IT/Oggetti/Info/{project_id}"

def get_procedura_links(detail_url: str, search_type: str = "o") -> list:
    """
    From the detail page (given by its URL), gather links to the "Documentazione" pages.
    """
    logging.info(f"[INFO] Parsing detail page: {detail_url}")
    try:
        resp = requests.get(detail_url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.warning(f"[WARN] Could not retrieve {detail_url}: {e}")
        return []
    
    soup = BeautifulSoup(resp.text, "html.parser")
    procedura_links = []
    # The procedure links for project type 'o' (Progetti) are inside the "Documentazione" section.
    link_pattern = "/it-IT/Oggetti/Documentazione/"
    for a in soup.find_all("a", href=True):
        if link_pattern in a["href"]:
            full_url = urllib.parse.urljoin(BASE_URL, a["href"])
            if full_url not in procedura_links:
                procedura_links.append(full_url)
    
    logging.info(f"[INFO] Found {len(procedura_links)} procedure links in {detail_url}.")
    return procedura_links

def find_total_pages(soup) -> int:
    """
    Determine the pagination: extract total pages from a snippet like 'Pagina 1 di 8'.
    """
    pag_ul = soup.find("ul", class_="pagination")
    if not pag_ul:
        return 1
    label_li = pag_ul.find("li", class_="etichettaRicerca")
    if not label_li:
        return 1
    match = re.search(r'Pagina\s+\d+\s+di\s+(\d+)', label_li.text)
    if match:
        return int(match.group(1))
    return 1

def get_document_links(procedura_url: str) -> list:
    """
    In a given procedure page, find the final "Scarica documento" links and the file name.
    Handles pagination in the documents table.
    """
    logging.info(f"[INFO] Parsing procedure page: {procedura_url}")
    doc_links = []
    page = 1

    while True:
        # Append page parameter if needed
        url = f"{procedura_url}{'&' if '?' in procedura_url else '?'}pagina={page}" if page > 1 else procedura_url
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            logging.warning(f"[WARN] Could not retrieve {url}: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="Documentazione")
        if not table:
            logging.warning(f"[WARN] No 'Documentazione' table found in {url}.")
            break

        # Skip header row and process document rows
        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 9:
                continue
            nome_file = cols[1].get_text(strip=True)
            download_td = cols[8]
            download_a = download_td.find("a", href=True, title="Scarica il documento")
            if download_a:
                href = download_a["href"]
                download_url = urllib.parse.urljoin(BASE_URL, href)
                doc_links.append((download_url, nome_file))

        total_pages = find_total_pages(soup)
        logging.info(f"[INFO] Processing documents page {page}/{total_pages}")
        if page >= total_pages:
            break
        page += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    logging.info(f"[INFO] Found {len(doc_links)} document links in {procedura_url}.")
    return doc_links

def download_file(url: str, nome_file: str, save_path: str):
    """
    Download the file from the given URL and save it under 'save_path' with a sanitized file name.
    """
    try:
        safe_filename = re.sub(r'[\\/*?:"<>|]', "_", nome_file)
        local_path = os.path.join(save_path, safe_filename)
        if os.path.exists(local_path):
            logging.info(f"[INFO] File '{safe_filename}' already exists. Skipping.")
            return

        logging.info(f"[INFO] Downloading: {url}")
        with requests.get(url, stream=True, timeout=20) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        logging.info(f"[OK] Saved => {local_path}")
    except Exception as e:
        logging.error(f"[ERROR] Failed to download {url}: {e}")

# --- Functions from prugadori.py (modified) ---

# List of regex patterns to search within the PDFs.
PATTERNS = [
    re.compile(r"(WGS84|coordinate)", re.IGNORECASE),
    re.compile(r"\b[-+]?[0-9]*\.?[0-9]+°?\s*[NS]?\s*,?\s*[-+]?[0-9]*\.?[0-9]+°?\s*[EW]?\b", re.IGNORECASE),
    re.compile(r"\b\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(\.\d+)?\"?\s*[NSEW]\b", re.IGNORECASE),
    re.compile(r"\b\d{1,3}°?\s*\d{1,2}\.\d+['′]?\s*[NSEW]?\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}[NS]\s*\d{6,7}(\.\d+)?\s*\d{6,7}(\.\d+)?\b", re.IGNORECASE),
    re.compile(r"\b(foglio|particella|mappale)\s*n?\.*\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bmappali\s*n?\.*\s*\d+(?:\s*,\s*\d+)*\b", re.IGNORECASE),
    re.compile(r"(nordex|vestas|siemens)", re.IGNORECASE),
    re.compile(r"\baltezza\b|\baltitudine\b|\bhub\b|\btip\b|\blama\b|\bblade\b|\brotore\b|\bdiametro\b", re.IGNORECASE)
]

def get_all_pdfs(base_folder: str) -> list:
    """
    Recursively find all PDF files in base_folder.
    """
    pdf_files = []
    for root, _, files in os.walk(base_folder):
        for file in files:
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(root, file)
                pdf_files.append(full_path)
                logging.info(f"Found PDF: {full_path}")
    return pdf_files

def search_single_pdf(pdf_path: str, regex_list: list) -> list:
    """
    Search for patterns in a single PDF file and return matches.
    Each match is a tuple: (pdf_file, page_number, line_number, matched_line)
    """
    results = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                lines = text.splitlines()
                for line_idx, line in enumerate(lines, start=1):
                    if any(regex.search(line) for regex in regex_list):
                        results.append((pdf_path, page_idx, line_idx, line))
                        print(f"{Fore.GREEN}Match in {pdf_path}: Page {page_idx}, Line {line_idx}:{Style.RESET_ALL} {line}")
    except Exception as e:
        print(f"{Fore.RED}[WARN] Failed to parse {pdf_path}: {e}{Style.RESET_ALL}")
    return results

def search_pdfs_in_folder(folder_path: str, patterns: list) -> list:
    """
    Search through all PDFs in folder_path for given regex patterns.
    """
    all_matches = []
    pdf_files = get_all_pdfs(folder_path)
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

def write_csv(results: list, output_csv: str):
    """
    Write the PDF scan results into a CSV file.
    """
    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["PDF_File", "Page", "Line", "Matched_Text"])
        for row in results:
            writer.writerow(row)

# --- Main Function ---

def main():
    # 1. Input: Ask for the project folder ID and optional save location
    project_id = input("Inserisci l'ID cartella del progetto: ").strip()
    if not project_id:
        print(f"{Fore.RED}[ERROR] Nessun ID fornito. Uscita.{Style.RESET_ALL}")
        return

    save_location = input("Inserisci il percorso dove salvare i file (invio per usare la cartella corrente): ").strip()
    
    # Use current directory if no save location provided or if provided path doesn't exist
    if not save_location:
        save_location = os.getcwd()
    elif not os.path.exists(save_location):
        print(f"{Fore.YELLOW}[WARN] Il percorso specificato non esiste. Uso la cartella corrente.{Style.RESET_ALL}")
        save_location = os.getcwd()

    # 2. Create a folder in the specified location named with the project ID
    project_folder = os.path.join(save_location, project_id)
    os.makedirs(project_folder, exist_ok=True)
    logging.info(f"[INFO] Cartella progetto creata: {project_folder}")

    # Rest of the function remains the same
    detail_url = build_detail_url(project_id)
    procedure_urls = get_procedura_links(detail_url, search_type="o")
    if not procedure_urls:
        logging.info("[INFO] Nessun link di procedura trovato, terminazione.")
        return

    # 4. Download all documents from the procedure pages into the project folder
    for proc_url in procedure_urls:
        doc_links = get_document_links(proc_url)
        for durl, nome_file in doc_links:
            download_file(durl, nome_file, project_folder)
            time.sleep(DELAY_BETWEEN_REQUESTS)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    logging.info("[INFO] Download completato.")

    # 5. Scan the downloaded PDFs for matches and generate a CSV report
    matches = search_pdfs_in_folder(project_folder, PATTERNS)
    csv_filename = os.path.join(save_location, f"{project_id}_scan_results.csv")
    write_csv(matches, csv_filename)
    print(f"{Fore.GREEN}Trovati {len(matches)} match! Risultati salvati in {csv_filename}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()