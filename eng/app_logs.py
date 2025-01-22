#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://va.mite.gov.it"
DOWNLOAD_FOLDER = "downloads"
DELAY_BETWEEN_REQUESTS = 1.0  # polite delay in seconds

# Ensure the base download folder exists
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def build_search_url(keyword: str, search_type="o", page: int = 1):
    """
    Build the 'Ricerca' URL:
      GET /it-IT/Ricerca/ViaLibera?Testo=<keyword>&t=<search_type>&pagina=<page>

    search_type can be:
      - 'o' => Ricerca Progetti
      - 'd' => Ricerca Documenti
    """
    print(f"[DEBUG] build_search_url() called with keyword='{keyword}', search_type='{search_type}', page={page}")
    search_endpoint = "/it-IT/Ricerca/ViaLibera"
    params = {
        "Testo": keyword,
        "t": search_type,
        "pagina": page
    }
    final_url = f"{BASE_URL}{search_endpoint}?{urllib.parse.urlencode(params)}"
    print(f"[DEBUG] build_search_url() => {final_url}")
    return final_url

def find_total_pages(soup) -> int:
    """
    Extract the total number of pages from the pagination section.
    Example snippet:
      <li class="etichettaRicerca">Pagina 1 di 8</li>
    """
    print("[DEBUG] find_total_pages() called.")
    pag_ul = soup.find("ul", class_="pagination")
    if not pag_ul:
        print("[DEBUG] No pagination <ul> found. Assuming only 1 page.")
        return 1

    label_li = pag_ul.find("li", class_="etichettaRicerca")
    if not label_li:
        print("[DEBUG] No 'etichettaRicerca' label found. Assuming only 1 page.")
        return 1

    match = re.search(r'Pagina\s+(\d+)\s+di\s+(\d+)', label_li.text)
    if match:
        total_pages = int(match.group(2))
        print(f"[DEBUG] Found total_pages={total_pages} from pagination label.")
        return total_pages

    print("[DEBUG] Could not parse total_pages. Defaulting to 1.")
    return 1

def collect_search_results(keyword: str, search_type="o"):
    """
    Step 1: Perform the search for either 'progetti' (o) or 'documenti' (d)
            and collect the links to project or document detail pages.
    Handles multiple pages based on the pagination info.
    """
    print(f"[INFO] collect_search_results() => Searching for '{keyword}' [type='{search_type}']")
    all_links = []
    page = 1

    while True:
        url = build_search_url(keyword, search_type=search_type, page=page)
        print(f"[INFO] Fetching search results page {page}: {url}")
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[ERROR] Failed to fetch {url}: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # For 'o' (Progetti): typically /it-IT/Oggetti/Info/
        # For 'd' (Documenti): typically /it-IT/Oggetti/Documentazione/
        if search_type == 'o':
            link_pattern = "/it-IT/Oggetti/Info/"
        else:
            link_pattern = "/it-IT/Oggetti/Documentazione/"

        print(f"[DEBUG] Looking for link_pattern='{link_pattern}' in the HTML <a> tags...")
        found_this_page = 0
        for a in soup.select(f"a[href*='{link_pattern}']"):
            href = a.get("href", "")
            full_url = urllib.parse.urljoin(BASE_URL, href)
            if full_url not in all_links:
                all_links.append(full_url)
                found_this_page += 1

        print(f"[DEBUG] Found {found_this_page} new links on this page. Total so far: {len(all_links)}")

        total_pages = find_total_pages(soup)
        print(f"[INFO] Page {page}/{total_pages} completed.")

        if page >= total_pages:
            print(f"[INFO] Reached last page: {page}. Breaking out of pagination loop.")
            break

        page += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"[INFO] Finished collecting detail URLs. Total collected: {len(all_links)}")
    return all_links

def get_project_id(detail_url: str) -> str:
    """
    Extract the project ID (or 'UnknownProject' if not found).
    Example for 'o' => /it-IT/Oggetti/Info/10217 => returns '10217'.
    For 'd' => maybe /it-IT/Oggetti/Documentazione/9876 => returns '9876'.
    Adjust based on actual site structure.
    """
    print(f"[DEBUG] get_project_id() => detail_url='{detail_url}'")
    # Attempt to match either Info/<id> or Documentazione/<id>
    match = re.search(r'(?:Info|Documentazione)/(\d+)', detail_url)
    if match:
        project_id = match.group(1)
        print(f"[DEBUG] get_project_id() => Found project_id='{project_id}'")
        return project_id

    print("[DEBUG] Could not find a numeric ID. Using 'UnknownProject'")
    return "UnknownProject"

def get_procedura_links(detail_url: str, search_type: str):
    """
    Step 2: From the detail page, gather links to the actual "procedure" or "documentazione" pages.
    """
    print(f"[INFO] get_procedura_links() => detail_url='{detail_url}' [type='{search_type}']")
    try:
        resp = requests.get(detail_url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[WARN] Could not retrieve {detail_url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    procedura_links = []

    # Usually, for progetti => look for /it-IT/Oggetti/Documentazione/
    # Possibly the same for 'd' if you want additional doc-level links
    link_pattern = "/it-IT/Oggetti/Documentazione/"
    print(f"[DEBUG] Searching for link_pattern='{link_pattern}' in {detail_url}")
    found_count = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if link_pattern in href:
            full_url = urllib.parse.urljoin(BASE_URL, href)
            if full_url not in procedura_links:
                procedura_links.append(full_url)
                found_count += 1

    print(f"[INFO] Found {found_count} procedure links in {detail_url}.")
    return procedura_links

def get_document_links(procedura_url: str):
    """
    Step 3: Inside a procedure page, find the "Scarica documento" links
    and their 'Nome file' from the 'Documentazione' table.
    Returns a list of (download_url, original_filename).
    """
    print(f"[INFO] get_document_links() => procedura_url='{procedura_url}'")
    try:
        resp = requests.get(procedura_url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[WARN] Could not retrieve {procedura_url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", class_="Documentazione")
    if not table:
        print(f"[WARN] No 'Documentazione' table found in {procedura_url}. Returning empty list.")
        return []

    doc_links = []
    rows = table.find_all("tr")[1:]  # skip header row
    print(f"[DEBUG] Found {len(rows)} data rows in the Documentazione table.")
    for idx, row in enumerate(rows, start=1):
        cols = row.find_all("td")
        if len(cols) < 9:
            print(f"[DEBUG] Row {idx}: Not enough columns ({len(cols)}). Skipping.")
            continue

        # 'Nome file' is the second <td>
        nome_file = cols[1].get_text(strip=True)

        # The ninth <td> contains the "Scarica documento" link
        download_td = cols[8]
        download_a = download_td.find("a", href=True, title="Scarica il documento")
        if not download_a:
            print(f"[DEBUG] Row {idx}: Could not find 'Scarica il documento' link. Skipping.")
            continue

        href = download_a["href"]
        download_url = urllib.parse.urljoin(BASE_URL, href)
        doc_links.append((download_url, nome_file))
        print(f"[DEBUG] Row {idx}: Appended doc => URL='{download_url}', NomeFile='{nome_file}'")

    print(f"[INFO] get_document_links() => returning {len(doc_links)} documents from {procedura_url}")
    return doc_links

def download_file(url: str, nome_file: str, save_path: str):
    """
    Step 4: Download the file from the given URL, saving it under 'nome_file' in 'save_path'.
    """
    try:
        safe_filename = re.sub(r'[\\/*?:"<>|]', "_", nome_file)
        local_path = os.path.join(save_path, safe_filename)

        if os.path.exists(local_path):
            print(f"[INFO] File '{safe_filename}' already exists. Skipping.")
            return

        print(f"[INFO] Downloading: {url}")
        with requests.get(url, stream=True, timeout=20) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        print(f"[OK] Saved => {local_path}")

    except Exception as e:
        print(f"[ERROR] Failed to download {url}: {e}")

def main():
    # Prompt user for keyword
    keyword = input("Insert the keyword to search: ").strip()
    if not keyword:
        print("[ERROR] No keyword entered. Exiting.")
        return

    # Prompt user for search type
    print("\nChoose search type:")
    print("1) Progetti (o)")
    print("2) Documenti (d)")
    choice = input("Enter '1' or '2': ").strip()
    if choice == '1':
        search_type = 'o'
        search_type_full = 'Progetti'
    elif choice == '2':
        search_type = 'd'
        search_type_full = 'Documenti'
    else:
        print("[ERROR] Invalid choice. Exiting.")
        return

    safe_keyword = re.sub(r'[\\/*?:"<>|]', "_", keyword)
    base_save_dir = os.path.join(DOWNLOAD_FOLDER, safe_keyword, search_type_full)
    os.makedirs(base_save_dir, exist_ok=True)

    # Step 1: Gather detail pages for this search
    detail_urls = collect_search_results(keyword, search_type=search_type)
    print(f"[INFO] Found {len(detail_urls)} detail URLs. Now parsing each...")

    # Step 2: For each detail link, parse & extract docs
    for detail_url in detail_urls:
        # For Progetti => we parse them as 'projects' with an ID
        # For Documenti => we might also parse ID, but might differ
        project_id = get_project_id(detail_url)
        project_folder = os.path.join(base_save_dir, project_id)
        os.makedirs(project_folder, exist_ok=True)

        # Extract procedure links from the detail page
        procedure_urls = get_procedura_links(detail_url, search_type=search_type)
        print(f"[INFO] detail_url='{detail_url}' => found {len(procedure_urls)} procedure URLs")

        for proc_url in procedure_urls:
            doc_links = get_document_links(proc_url)
            print(f"[INFO] procedure_url='{proc_url}' => {len(doc_links)} documents found.")
            for durl, nome_file in doc_links:
                download_file(durl, nome_file, project_folder)
                time.sleep(DELAY_BETWEEN_REQUESTS)

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print("[INFO] Scraping completed successfully.")

if __name__ == "__main__":
    main()
