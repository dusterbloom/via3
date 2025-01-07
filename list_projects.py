#!/usr/bin/env python3
import os
import re
import time
import urllib.parse
import requests
import csv
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

init()

BASE_URL = "https://va.mite.gov.it"
DELAY_BETWEEN_REQUESTS = 1.0

def build_search_url(keyword: str, search_type="o", page: int = 1):
    """Build the search URL exactly as in main.py"""
    search_endpoint = "/it-IT/Ricerca/ViaLibera"
    params = {
        "Testo": keyword,
        "t": search_type,
        "pagina": page
    }
    return f"{BASE_URL}{search_endpoint}?{urllib.parse.urlencode(params)}"

def find_total_pages(soup) -> int:
    """Extract total pages exactly as in main.py"""
    pag_ul = soup.find("ul", class_="pagination")
    if not pag_ul:
        return 1

    label_li = pag_ul.find("li", class_="etichettaRicerca")
    if not label_li:
        return 1

    match = re.search(r'Pagina\s+(\d+)\s+di\s+(\d+)', label_li.text)
    if match:
        return int(match.group(2))
    return 1

def collect_search_results(keyword: str, search_type="o"):
    """Collect all projects exactly as in main.py but with additional details"""
    all_projects = []
    page = 1

    while True:
        url = build_search_url(keyword, search_type=search_type, page=page)
        print(f"{Fore.YELLOW}[INFO] Fetching page {page}: {url}{Style.RESET_ALL}")
        
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find the projects table
            table = soup.find("table", class_="ElencoViaVasRicerca")
            if not table:
                print(f"{Fore.RED}No results table found on page {page}{Style.RESET_ALL}")
                break

            # Process each row (skip header)
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 5:  # We expect 5 columns
                    continue

                # Extract data from cells
                title = cells[0].text.strip()
                proponent = cells[1].text.strip()
                status = cells[2].text.strip()
                
                # Get project URL from info link
                info_link = cells[3].find("a", href=True)
                if not info_link:
                    continue
                    
                project_url = urllib.parse.urljoin(BASE_URL, info_link["href"])
                project_id = project_url.split("/")[-1]

                # Get documentation URL
                doc_link = cells[4].find("a", href=True)
                doc_url = urllib.parse.urljoin(BASE_URL, doc_link["href"]) if doc_link else ""

                project = {
                    "id": project_id,
                    "url": project_url,
                    "doc_url": doc_url,
                    "title": title,
                    "proponent": proponent,
                    "status": status,
                    "include": "YES"
                }
                all_projects.append(project)
                print(f"{Fore.GREEN}Found: {title[:100]}... (ID: {project_id}){Style.RESET_ALL}")

            total_pages = find_total_pages(soup)
            print(f"Page {page}/{total_pages}, found {len(all_projects)} projects so far")

            if page >= total_pages:
                break

            page += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)

        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to fetch {url}: {e}{Style.RESET_ALL}")
            break

    print(f"{Fore.CYAN}[INFO] Total projects found: {len(all_projects)}{Style.RESET_ALL}")
    return all_projects

def save_projects_csv(projects, output="projects_list.csv"):
    """Save projects to CSV file"""
    fieldnames = ["id", "url", "doc_url", "title", "proponent", "status", "include"]
    with open(output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(projects)
    print(f"{Fore.GREEN}Saved {len(projects)} projects to {output}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Edit the CSV and set 'include' to 'NO' for projects to skip{Style.RESET_ALL}")

def main():
    keyword = input("Enter search keyword (default: Sardegna): ").strip() or "Sardegna"
    projects = collect_search_results(keyword)
    if projects:
        save_projects_csv(projects)
    else:
        print(f"{Fore.RED}No projects found!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()