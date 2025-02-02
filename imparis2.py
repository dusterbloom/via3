#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import csv
import urllib.parse
import requests
import logging
import spacy
from spacy.matcher import Matcher
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
        logging.FileHandler("imparis2.log"),
        logging.StreamHandler()
    ]
)

def setup_nlp():
    """
    Setup spaCy NLP pipeline with Italian language model
    """
    try:
        nlp = spacy.load("it_core_news_lg")
    except OSError:
        print(f"{Fore.YELLOW}[INFO] Downloading Italian language model...{Style.RESET_ALL}")
        os.system("python -m spacy download it_core_news_lg")
        nlp = spacy.load("it_core_news_lg")
    
    return nlp

def setup_matchers(nlp):
    """
    Setup spaCy matchers with enhanced patterns for environmental impact documents
    """
    matcher = Matcher(nlp.vocab)
    
    # Geographic coordinates patterns
    matcher.add("COORDINATES", [
        # WGS84 format
        [
            {"LOWER": "wgs84"},
            {"IS_SPACE": True, "OP": "?"},
            {"TEXT": {"REGEX": r"\d+[.,]\d+"}},
            {"TEXT": {"REGEX": r"[NSns]"}},
            {"TEXT": {"REGEX": r"\d+[.,]\d+"}},
            {"TEXT": {"REGEX": r"[EWew]"}}
        ],
        
        # Decimal degrees
        [
            {"TEXT": {"REGEX": r"\d+[.,]\d+°?\s*[NSns]"}},
            {"TEXT": {"REGEX": r"\d+[.,]\d+°?\s*[EWew]"}}
        ],
        
        # Labeled coordinates
        [
            {"LOWER": {"IN": ["latitudine", "lat", "latitude"]}},
            {"TEXT": {"REGEX": r"\d+[.,]\d+"}},
            {"LOWER": {"IN": ["longitudine", "long", "longitude"]}},
            {"TEXT": {"REGEX": r"\d+[.,]\d+"}}
        ],
        
        # DMS format (using standard ASCII characters)
        [
            {"TEXT": {"REGEX": r"\d+°\s*\d+[']\s*\d+([.,]\d+)?[\"]\s*[NSns]"}},
            {"TEXT": {"REGEX": r"\d+°\s*\d+[']\s*\d+([.,]\d+)?[\"]\s*[EWew]"}}
        ],
        
        # Coordinate pairs
        [
            {"TEXT": "("},
            {"TEXT": {"REGEX": r"\d+[.,]\d+"}},
            {"TEXT": ","},
            {"TEXT": {"REGEX": r"\d+[.,]\d+"}},
            {"TEXT": ")"}
        ]
    ])
    
    # Cadastral references
    matcher.add("CADASTRAL", [
        [
            {"LOWER": {"IN": ["foglio", "particella", "mappale"]}},
            {"TEXT": {"REGEX": r"n\.?\s*\d+"}}
        ],
        [
            {"LOWER": "mappali"},
            {"TEXT": {"REGEX": r"n\.?\s*\d+(?:\s*,\s*\d+)*"}}
        ]
    ])
    
    # Wind turbine specifications
    matcher.add("TURBINE_SPECS", [
        # Height specifications
        [
            {"LOWER": {"IN": ["altezza", "hub", "tip"]}},
            {"LIKE_NUM": True},
            {"LOWER": {"IN": ["metri", "m", "mt"]}, "OP": "?"}
        ],
        
        # Rotor specifications
        [
            {"LOWER": {"IN": ["rotore", "diametro", "blade", "lama"]}},
            {"LIKE_NUM": True},
            {"LOWER": {"IN": ["metri", "m", "mt"]}, "OP": "?"}
        ],
        
        # Manufacturer models
        [
            {"LOWER": {"IN": ["nordex", "vestas", "siemens"]}},
            {"TEXT": {"REGEX": r"[A-Z]\d+"}, "OP": "?"}
        ]
    ])
    
    # Environmental impact keywords
    matcher.add("ENVIRONMENTAL", [
        [
            {"LOWER": {"IN": ["impatto", "mitigazione", "compensazione"]}},
            {"IS_PUNCT": True, "OP": "?"},
            {"LOWER": {"IN": ["ambientale", "acustico", "visivo", "paesaggistico"]}}
        ]
    ])
    
    return matcher

def get_project_info(detail_url: str) -> tuple:
    """
    Extract project ID and description from the detail page
    """
    try:
        resp = requests.get(detail_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Extract project description from the page title or relevant element
        description = soup.find("h1").text.strip() if soup.find("h1") else "Unknown"
        
        # Extract project ID from URL
        project_id = detail_url.split("/")[-1]
        
        return project_id, description
    except Exception as e:
        logging.error(f"Failed to get project info: {e}")
        return None, None
    
    
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


def download_file(url: str, nome_file: str, save_path: str) -> str:
    """
    Download the file from the given URL and save it under 'save_path' with a sanitized file name.
    Returns the path of the downloaded file if successful, None otherwise.
    """
    try:
        safe_filename = re.sub(r'[\\/*?:"<>|]', "_", nome_file)
        local_path = os.path.join(save_path, safe_filename)
        if os.path.exists(local_path):
            logging.info(f"[INFO] File '{safe_filename}' already exists. Skipping.")
            return local_path  # Return path even for existing files

        logging.info(f"[INFO] Downloading: {url}")
        with requests.get(url, stream=True, timeout=20) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        logging.info(f"[OK] Saved => {local_path}")
        return local_path  # Return path of downloaded file
    except Exception as e:
        logging.error(f"[ERROR] Failed to download {url}: {e}")
        return None

def download_documents(project_id: str, save_path: str) -> list:
    """
    Download all documents for a given project ID
    """
    detail_url = f"{BASE_URL}/it-IT/Oggetti/Info/{project_id}"
    downloaded_files = []
    
    try:
        # Get procedure links
        procedure_urls = get_procedura_links(detail_url)
        
        # Download documents from each procedure
        for proc_url in procedure_urls:
            doc_links = get_document_links(proc_url)
            for url, filename in doc_links:
                local_path = download_file(url, filename, save_path)
                if local_path:  # If download was successful
                    downloaded_files.append(local_path)
                time.sleep(DELAY_BETWEEN_REQUESTS)
    except Exception as e:
        logging.error(f"Error downloading documents: {e}")
    
    return downloaded_files  # Return list of successfully downloaded files

def analyze_pdf(pdf_path: str, nlp, matcher: Matcher) -> list:
    """
    Analyze a single PDF using spaCy NLP with enhanced error handling
    """
    results = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                    if not text.strip():  # Skip empty pages
                        continue
                        
                    doc = nlp(text)
                    
                    # Pattern matching
                    matches = matcher(doc)
                    for match_id, start, end in matches:
                        match_text = doc[start:end].text
                        pattern_name = nlp.vocab.strings[match_id]
                        results.append({
                            'file': pdf_path,
                            'page': page_idx,
                            'type': pattern_name,
                            'text': match_text,
                            'context': text[max(0, doc[start].idx - 100):min(len(text), doc[end-1].idx + 100)]
                        })
                    
                    # Named Entity Recognition
                    for ent in doc.ents:
                        if ent.label_ in ["LOC", "GPE", "ORG"]:
                            results.append({
                                'file': pdf_path,
                                'page': page_idx,
                                'type': f"NER_{ent.label_}",
                                'text': ent.text,
                                'context': text[max(0, ent.start_char - 100):min(len(text), ent.end_char + 100)]
                            })
                            
                except Exception as page_error:
                    logging.warning(f"Skipping page {page_idx} in {pdf_path}: {str(page_error)}")
                    continue
                    
    except Exception as e:
        logging.error(f"Error analyzing PDF {pdf_path}: {str(e)}")
        results.append({
            'file': pdf_path,
            'page': 0,
            'type': 'ERROR',
            'text': f"Failed to process: {str(e)}",
            'context': ''
        })
    
    return results

def write_results(results: list, output_file: str):
    """
    Write analysis results to CSV with enhanced formatting
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'page', 'type', 'text', 'context'])
        writer.writeheader()
        writer.writerows(results)

def main():
    print(f"{Fore.CYAN}Choose operation mode:")
    print("1. Download and analyze new project")
    print("2. Analyze existing PDF folder")
    print(f"3. Analyze single PDF file{Style.RESET_ALL}")
    
    mode = input("Enter mode (1, 2 or 3): ").strip()
    
    if mode == "1":
        # Existing download and analyze flow
        project_id = input("Inserisci l'ID cartella del progetto: ").strip()
        if not project_id:
            print(f"{Fore.RED}[ERROR] Nessun ID fornito. Uscita.{Style.RESET_ALL}")
            return

        save_location = input("Inserisci il percorso dove salvare i file (invio per usare la cartella corrente): ").strip()
        if not save_location:
            save_location = os.getcwd()
        elif not os.path.exists(save_location):
            print(f"{Fore.YELLOW}[WARN] Il percorso specificato non esiste. Uso la cartella corrente.{Style.RESET_ALL}")
            save_location = os.getcwd()

        # Create project folder
        project_folder = os.path.join(save_location, project_id)
        os.makedirs(project_folder, exist_ok=True)

        # Initialize NLP
        print(f"{Fore.CYAN}Initializing NLP engine...{Style.RESET_ALL}")
        nlp = setup_nlp()
        matcher = setup_matchers(nlp)

        # Download documents
        print(f"{Fore.CYAN}Downloading project documents...{Style.RESET_ALL}")
        downloaded_files = download_documents(project_id, project_folder)
        
        if not downloaded_files:
            print(f"{Fore.RED}No documents found or downloaded. Exiting.{Style.RESET_ALL}")
            return

        folder_to_analyze = project_folder
        output_prefix = project_id

    elif mode == "2":
        # Analyze existing folder
        folder_to_analyze = input("Inserisci il percorso della cartella con i PDF: ").strip()
        if not os.path.exists(folder_to_analyze):
            print(f"{Fore.RED}[ERROR] Cartella non trovata. Uscita.{Style.RESET_ALL}")
            return
        
        # Initialize NLP
        print(f"{Fore.CYAN}Initializing NLP engine...{Style.RESET_ALL}")
        nlp = setup_nlp()
        matcher = setup_matchers(nlp)
        
        # Get list of PDF files
        downloaded_files = [os.path.join(root, f) 
                          for root, _, files in os.walk(folder_to_analyze) 
                          for f in files if f.lower().endswith('.pdf')]
        
        if not downloaded_files:
            print(f"{Fore.RED}No PDF files found in the specified folder. Exiting.{Style.RESET_ALL}")
            return
            
        # Use folder name as prefix for output file
        output_prefix = os.path.basename(os.path.normpath(folder_to_analyze))

    elif mode == "3":
        # Analyze single PDF
        pdf_path = input("Inserisci il percorso completo del file PDF: ").strip()
        if not os.path.exists(pdf_path) or not pdf_path.lower().endswith('.pdf'):
            print(f"{Fore.RED}[ERROR] File PDF non trovato o non valido. Uscita.{Style.RESET_ALL}")
            return

        # Initialize NLP
        print(f"{Fore.CYAN}Initializing NLP engine...{Style.RESET_ALL}")
        nlp = setup_nlp()
        matcher = setup_matchers(nlp)

        downloaded_files = [pdf_path]
        folder_to_analyze = os.path.dirname(pdf_path)
        output_prefix = os.path.splitext(os.path.basename(pdf_path))[0]
        
    else:
        print(f"{Fore.RED}[ERROR] Invalid mode selected. Exiting.{Style.RESET_ALL}")
        return

    # Common analysis code for all modes
    print(f"{Fore.CYAN}Analyzing documents...{Style.RESET_ALL}")
    all_results = []
    with tqdm(total=len(downloaded_files), desc="Analyzing PDFs") as pbar:
        for pdf_file in downloaded_files:
            if pdf_file.lower().endswith('.pdf'):
                results = analyze_pdf(pdf_file, nlp, matcher)
                all_results.extend(results)
            pbar.update(1)

    # Write results in the same directory as the PDFs
    output_file = os.path.join(os.path.dirname(folder_to_analyze), f"{output_prefix}_analysis.csv")
    write_results(all_results, output_file)
    
    print(f"\n{Fore.GREEN}Analysis complete!")
    print(f"Found {len(all_results)} matches")
    print(f"Results saved to: {output_file}{Style.RESET_ALL}")

    # Add error summary
    errors = [r for r in all_results if r['type'] == 'ERROR']
    if errors:
        print(f"\n{Fore.YELLOW}Warning: Some files had processing errors:")
        for error in errors:
            print(f"- {error['file']}: {error['text']}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()