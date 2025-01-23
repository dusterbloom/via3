#!/usr/bin/env python3
import os
import re
import csv
import pdfplumber
import logging
from tqdm import tqdm
from typing import Optional, Tuple
from colorama import init, Fore, Style

init()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wind_turbines.log'),
        logging.StreamHandler()
    ]
)

# Patterns specifically for wind turbines
WIND_PATTERNS = [
    # Look for WTG or wind turbine identifiers followed by coordinates
    re.compile(r"(?:WTG|Turbina|Pala|Aerogeneratore)\s*(?:n\.)?\s*\d+\s*[-:]+\s*(.*?(?:\d+°\s*\d+'\s*\d+(?:\.\d+)?\"?\s*[NS])\s*(?:\d+°\s*\d+'\s*\d+(?:\.\d+)?\"?\s*[EW]))", re.IGNORECASE),
    
    # Look for coordinates near wind turbine mentions
    re.compile(r"(?:WTG|Turbina|Pala|Aerogeneratore)\s*(?:n\.)?\s*\d+.*?(\b\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[NS]\s*\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[EW])", re.IGNORECASE),
    
    # General coordinate patterns with context
    re.compile(r"coordinate.*?(\b\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[NS]\s*\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[EW])", re.IGNORECASE),
]


def parse_coordinates(text: str) -> Optional[Tuple[float, float]]:
    """
    Parse various coordinate formats and return (latitude, longitude) in decimal degrees.
    Returns None if no valid coordinates found.
    """
    # Clean the text
    text = text.strip().upper()
    
    # Pattern 1: Decimal degrees (DD) with optional symbols
    # Example: 41.40338, 2.17403 or 41.40338°N, 2.17403°E
    dd_pattern = re.compile(
        r"""
        \b
        (?P<lat>[-+]?\d*\.?\d+)°?\s*(?P<lat_dir>[NS])?\s*,?\s*
        (?P<lon>[-+]?\d*\.?\d+)°?\s*(?P<lon_dir>[EW])?\b
        """,
        re.VERBOSE | re.IGNORECASE
    )

    # Pattern 2: Degrees, Minutes, Seconds (DMS)
    # Example: 41°24'12.2"N 2°10'26.5"E
    dms_pattern = re.compile(
        r"""
        \b
        (?P<lat_deg>\d{1,3})°\s*
        (?P<lat_min>\d{1,2})'\s*
        (?P<lat_sec>\d{1,2}(?:\.\d+)?)"?\s*
        (?P<lat_dir>[NS])\s*
        (?P<lon_deg>\d{1,3})°\s*
        (?P<lon_min>\d{1,2})'\s*
        (?P<lon_sec>\d{1,2}(?:\.\d+)?)"?\s*
        (?P<lon_dir>[EW])\b
        """,
        re.VERBOSE | re.IGNORECASE
    )

    # Try decimal degrees first
    dd_match = dd_pattern.search(text)
    if dd_match:
        lat = float(dd_match.group('lat'))
        lon = float(dd_match.group('lon'))
        
        # Apply direction if present
        if dd_match.group('lat_dir') == 'S':
            lat = -lat
        if dd_match.group('lon_dir') == 'W':
            lon = -lon
            
        return (lat, lon)
    # Try DMS format
    dms_match = dms_pattern.search(text)
    if dms_match:
        # Convert DMS to decimal degrees
        lat = (float(dms_match.group('lat_deg')) +
               float(dms_match.group('lat_min'))/60 +
               float(dms_match.group('lat_sec'))/3600)
        
        lon = (float(dms_match.group('lon_deg')) +
               float(dms_match.group('lon_min'))/60 +
               float(dms_match.group('lon_sec'))/3600)
        
        # Apply directions
        if dms_match.group('lat_dir') == 'S':
            lat = -lat
        if dms_match.group('lon_dir') == 'W':
            lon = -lon
            
        return (lat, lon)

    return None


def extract_turbine_info(pdf_path: str) -> list:
    """
    Extract wind turbine coordinates and metadata from a PDF
    """
    turbine_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                
                # Look for turbine information in each line
                for line in text.splitlines():
                    for pattern in WIND_PATTERNS:
                        matches = pattern.finditer(line)
                        for match in matches:
                            coords = parse_coordinates(match.group(1))
                            if coords:
                                turbine_info = {
                                    'pdf_file': pdf_path,
                                    'page': page_num,
                                    'turbine_text': line.strip(),
                                    'latitude': coords[0],
                                    'longitude': coords[1]
                                }
                                turbine_data.append(turbine_info)
                                print(f"{Fore.GREEN}Found turbine: {turbine_info}{Style.RESET_ALL}")
                                
    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {e}")
    
    return turbine_data

def create_turbine_kml(turbine_data: list, output_file: str = "wind_turbines.kml"):
    """
    Create KML file for wind turbines with metadata
    """
    kml_header = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Style id="windTurbine">
      <IconStyle>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/shapes/airports.png</href>
        </Icon>
      </IconStyle>
    </Style>"""
    
    kml_footer = """
  </Document>
</kml>"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(kml_header)
        
        for i, turbine in enumerate(turbine_data, 1):
            placemark = f"""
    <Placemark>
      <name>Wind Turbine {i}</name>
      <description>
        <![CDATA[
        File: {os.path.basename(turbine['pdf_file'])}
        Page: {turbine['page']}
        Details: {turbine['turbine_text']}
        ]]>
      </description>
      <styleUrl>#windTurbine</styleUrl>
      <Point>
        <coordinates>{turbine['longitude']},{turbine['latitude']},0</coordinates>
      </Point>
    </Placemark>"""
            f.write(placemark)
            
        f.write(kml_footer)

def main():
    # Process PDFs from the downloads folder
    pdf_folder = input("Enter the PDF folder path: ").strip()
    if not os.path.exists(pdf_folder):
        print(f"{Fore.RED}[ERROR] Folder not found: {pdf_folder}{Style.RESET_ALL}")
        return

    all_turbine_data = []
    
    # Find all PDFs recursively
    pdf_files = [os.path.join(root, f) 
                 for root, _, files in os.walk(pdf_folder)
                 for f in files if f.lower().endswith('.pdf')]
    
    print(f"{Fore.CYAN}Processing {len(pdf_files)} PDF files...{Style.RESET_ALL}")
    
    # Process each PDF
    for pdf_path in tqdm(pdf_files):
        turbine_data = extract_turbine_info(pdf_path)
        all_turbine_data.extend(turbine_data)
    
    # Save to CSV
    if all_turbine_data:
        csv_file = "wind_turbines.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['pdf_file', 'page', 'turbine_text', 'latitude', 'longitude'])
            writer.writeheader()
            writer.writerows(all_turbine_data)
        
        # Create KML
        create_turbine_kml(all_turbine_data)
        
        print(f"\n{Fore.GREEN}Found {len(all_turbine_data)} wind turbines!")
        print(f"Results saved to {csv_file} and wind_turbines.kml{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}No wind turbine coordinates found.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()