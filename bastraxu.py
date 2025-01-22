#!/usr/bin/env python3
import os
import re
import time
import csv
import urllib.parse
import requests
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

init()

# Import constants and functions from main.py
BASE_URL = "https://va.mite.gov.it"
DOWNLOAD_FOLDER = "downloads"
DELAY_BETWEEN_REQUESTS = 1.0

# Reuse these functions from main.py
def get_document_links(procedura_url: str):
    """Reused from main.py"""
    print(f"{Fore.CYAN}[INFO] Parsing procedure page => {procedura_url}{Style.RESET_ALL}")
    doc_links = []
    page = 1
    
    while True:
        url = f"{procedura_url}{'&' if '?' in procedura_url else '?'}pagina={page}" if page > 1 else procedura_url
        
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"{Fore.RED}[WARN] Could not retrieve {url}: {e}{Style.RESET_ALL}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="Documentazione")

        if not table:
            print(f"{Fore.YELLOW}[WARN] No 'Documentazione' table found in {url}.{Style.RESET_ALL}")
            break

        rows = table.find_all("tr")[1:]  # skip header row
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

        # Check if there are more pages
        pag_ul = soup.find("ul", class_="pagination")
        if not pag_ul:
            break
            
        label_li = pag_ul.find("li", class_="etichettaRicerca")
        if not label_li:
            break

        match = re.search(r'Pagina\s+(\d+)\s+di\s+(\d+)', label_li.text)
        if not match:
            break
            
        total_pages = int(match.group(2))
        print(f"{Fore.CYAN}[INFO] Processing documents page {page}/{total_pages}{Style.RESET_ALL}")
        
        if page >= total_pages:
            break
            
        page += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"{Fore.GREEN}[INFO] Found {len(doc_links)} total document links in {procedura_url}.{Style.RESET_ALL}")
    return doc_links

def download_file(url: str, nome_file: str, save_path: str):
    """Reused from main.py"""
    try:
        safe_filename = re.sub(r'[\\/*?:"<>|]', "_", nome_file)
        local_path = os.path.join(save_path, safe_filename)

        if os.path.exists(local_path):
            print(f"{Fore.YELLOW}[INFO] File '{safe_filename}' already exists. Skipping.{Style.RESET_ALL}")
            return

        print(f"{Fore.CYAN}[INFO] Downloading: {url}{Style.RESET_ALL}")
        with requests.get(url, stream=True, timeout=20) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        print(f"{Fore.GREEN}[OK] Saved => {local_path}{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to download {url}: {e}{Style.RESET_ALL}")

def main():
    if not os.path.exists("projects_list.csv"):
        print(f"{Fore.RED}[ERROR] projects_list.csv not found!{Style.RESET_ALL}")
        return

    # Prompt user for folder name
    while True:
        folder_name = input(f"{Fore.CYAN}Enter name for download folder (will be created in {DOWNLOAD_FOLDER}/): {Style.RESET_ALL}").strip()
        if folder_name:
            # Sanitize folder name
            safe_folder = re.sub(r'[\\/*?:"<>|]', "_", folder_name)
            base_folder = os.path.join(DOWNLOAD_FOLDER, safe_folder)
            
            if os.path.exists(base_folder):
                overwrite = input(f"{Fore.YELLOW}Folder already exists. Continue/append to it? (y/n): {Style.RESET_ALL}").lower()
                if overwrite != 'y':
                    continue
            
            os.makedirs(base_folder, exist_ok=True)
            break
        else:
            print(f"{Fore.RED}Please enter a valid folder name{Style.RESET_ALL}")

    # Read projects from CSV
    with open("projects_list.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        projects = [row for row in reader if row['include'].upper() == 'YES']

    print(f"{Fore.CYAN}[INFO] Found {len(projects)} projects marked for download{Style.RESET_ALL}")

    # Process each project
    for project in projects:
        project_id = project['id']
        project_folder = os.path.join(base_folder, project_id)
        os.makedirs(project_folder, exist_ok=True)

        print(f"\n{Fore.CYAN}Processing project {project_id}: {project['title'][:100]}...{Style.RESET_ALL}")
        
        # Get documents from doc_url
        doc_links = get_document_links(project['doc_url'])
        
        # Download each document
        for doc_url, filename in doc_links:
            download_file(doc_url, filename, project_folder)
            time.sleep(DELAY_BETWEEN_REQUESTS)

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n{Fore.GREEN}[INFO] Download completed successfully in {base_folder}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()