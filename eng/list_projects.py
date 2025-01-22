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
    """Extract total pages from pagination"""
    try:
        # Find the text that shows total results
        results_h3 = soup.find("h3", class_="risultati")
        if results_h3:
            match = re.search(r'\((\d+)\)', results_h3.text)
            if match:
                total_results = int(match.group(1))
                # Each page shows 10 results
                return (total_results + 9) // 10
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to parse total pages: {e}{Style.RESET_ALL}")
    return 1

def collect_search_results(keyword: str, search_type="o"):
    """Collect all projects from search results"""
    all_projects = []
    page = 1
    total_pages = None

    while True:
        url = build_search_url(keyword, search_type=search_type, page=page)
        print(f"{Fore.YELLOW}[INFO] Fetching page {page}{' of '+str(total_pages) if total_pages else ''}: {url}{Style.RESET_ALL}")
        
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            if total_pages is None:
                total_pages = find_total_pages(soup)
                print(f"{Fore.CYAN}[INFO] Found {total_pages} total pages to process{Style.RESET_ALL}")

            # Find the projects table
            table = soup.find("table", class_="ElencoViaVasRicerca")
            if not table:
                print(f"{Fore.RED}[ERROR] No results table found on page {page}{Style.RESET_ALL}")
                break

            # Process each row (skip header)
            rows = table.find_all("tr")[1:]  # Skip header row
            if not rows:
                print(f"{Fore.YELLOW}[WARN] No rows found on page {page}{Style.RESET_ALL}")
                break

            page_projects = 0
            for row in rows:
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
                page_projects += 1
                print(f"{Fore.GREEN}[{len(all_projects)}] Found: {title[:100]}... (ID: {project_id}){Style.RESET_ALL}")

            print(f"{Fore.CYAN}[INFO] Page {page}/{total_pages} complete. Found {page_projects} projects on this page.{Style.RESET_ALL}")

            if page >= total_pages:
                break

            page += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)

        except Exception as e:
            print(f"{Fore.RED}[ERROR] Failed to fetch page {page}: {e}{Style.RESET_ALL}")
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
    print(f"{Fore.GREEN}[INFO] Saved {len(projects)} projects to {output}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[INFO] Edit the CSV and set 'include' to 'NO' for projects to skip{Style.RESET_ALL}")

def main():
    keyword = input(f"{Fore.CYAN}Enter search keyword (default: Sardegna): {Style.RESET_ALL}").strip() or "Sardegna"
    projects = collect_search_results(keyword)
    if projects:
        save_projects_csv(projects)
    else:
        print(f"{Fore.RED}[ERROR] No projects found!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()