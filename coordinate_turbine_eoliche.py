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

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('turbine_eoliche.log'),
        logging.StreamHandler()
    ]
)

# Pattern specifici per turbine eoliche
PATTERN_EOLICI = [
    # Cerca WTG o identificatori di turbine seguiti da coordinate
    re.compile(r"(?:WTG|Turbina|Pala|Aerogeneratore)\s*(?:n\.)?\s*\d+\s*[-:]+\s*(.*?(?:\d+°\s*\d+'\s*\d+(?:\.\d+)?\"?\s*[NS])\s*(?:\d+°\s*\d+'\s*\d+(?:\.\d+)?\"?\s*[EW]))", re.IGNORECASE),
    
    # Cerca coordinate vicino a menzioni di turbine
    re.compile(r"(?:WTG|Turbina|Pala|Aerogeneratore)\s*(?:n\.)?\s*\d+.*?(\b\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[NS]\s*\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[EW])", re.IGNORECASE),
    
    # Pattern generali di coordinate con contesto
    re.compile(r"coordinate.*?(\b\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[NS]\s*\d{1,3}°\s*\d{1,2}'\s*\d{1,2}(?:\.\d+)?\"?\s*[EW])", re.IGNORECASE),
]

def analizza_coordinate(testo: str) -> Optional[Tuple[float, float]]:
    """
    Analizza le coordinate dal testo e restituisce (latitudine, longitudine)
    """
    testo = testo.strip().upper()
    
    # Pattern 1: Gradi decimali (DD) con simboli opzionali
    pattern_dd = re.compile(
        r"""
        \b
        (?P<lat>[-+]?\d*\.?\d+)°?\s*(?P<lat_dir>[NS])?\s*,?\s*
        (?P<lon>[-+]?\d*\.?\d+)°?\s*(?P<lon_dir>[EW])?\b
        """,
        re.VERBOSE | re.IGNORECASE
    )

    # Pattern 2: Gradi, Minuti, Secondi (GMS)
    pattern_gms = re.compile(
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

    # Prova prima i gradi decimali
    match_dd = pattern_dd.search(testo)
    if match_dd:
        lat = float(match_dd.group('lat'))
        lon = float(match_dd.group('lon'))
        
        if match_dd.group('lat_dir') == 'S':
            lat = -lat
        if match_dd.group('lon_dir') == 'W':
            lon = -lon
            
        return (lat, lon)

    # Prova il formato GMS
    match_gms = pattern_gms.search(testo)
    if match_gms:
        lat = (float(match_gms.group('lat_deg')) +
               float(match_gms.group('lat_min'))/60 +
               float(match_gms.group('lat_sec'))/3600)
        
        lon = (float(match_gms.group('lon_deg')) +
               float(match_gms.group('lon_min'))/60 +
               float(match_gms.group('lon_sec'))/3600)
        
        if match_gms.group('lat_dir') == 'S':
            lat = -lat
        if match_gms.group('lon_dir') == 'W':
            lon = -lon
            
        return (lat, lon)

    return None

def estrai_info_turbine(percorso_pdf: str) -> list:
    """
    Estrae coordinate e metadati delle turbine eoliche da un PDF
    """
    dati_turbine = []
    
    try:
        with pdfplumber.open(percorso_pdf) as pdf:
            for num_pagina, pagina in enumerate(pdf.pages, 1):
                testo = pagina.extract_text() or ""
                
                for riga in testo.splitlines():
                    for pattern in PATTERN_EOLICI:
                        matches = pattern.finditer(riga)
                        for match in matches:
                            coordinate = analizza_coordinate(match.group(1))
                            if coordinate:
                                info_turbina = {
                                    'file_pdf': percorso_pdf,
                                    'pagina': num_pagina,
                                    'testo_turbina': riga.strip(),
                                    'latitudine': coordinate[0],
                                    'longitudine': coordinate[1]
                                }
                                dati_turbine.append(info_turbina)
                                print(f"{Fore.GREEN}Trovata turbina: {info_turbina}{Style.RESET_ALL}")
                                
    except Exception as e:
        logging.error(f"Errore nell'elaborazione di {percorso_pdf}: {e}")
    
    return dati_turbine

def crea_kml_turbine(dati_turbine: list, file_output: str = "turbine_eoliche.kml"):
    """
    Crea file KML per le turbine eoliche con metadati
    """
    intestazione_kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Style id="turbinaEolica">
      <IconStyle>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/shapes/airports.png</href>
        </Icon>
      </IconStyle>
    </Style>"""
    
    chiusura_kml = """
  </Document>
</kml>"""
    
    with open(file_output, 'w', encoding='utf-8') as f:
        f.write(intestazione_kml)
        
        for i, turbina in enumerate(dati_turbine, 1):
            segnaposto = f"""
    <Placemark>
      <name>Turbina Eolica {i}</name>
      <description>
        <![CDATA[
        File: {os.path.basename(turbina['file_pdf'])}
        Pagina: {turbina['pagina']}
        Dettagli: {turbina['testo_turbina']}
        ]]>
      </description>
      <styleUrl>#turbinaEolica</styleUrl>
      <Point>
        <coordinates>{turbina['longitudine']},{turbina['latitudine']},0</coordinates>
      </Point>
    </Placemark>"""
            f.write(segnaposto)
            
        f.write(chiusura_kml)

def main():
    # Elabora i PDF dalla cartella downloads
    cartella_pdf = input("Inserisci il percorso della cartella PDF: ").strip()
    if not os.path.exists(cartella_pdf):
        print(f"{Fore.RED}[ERRORE] Cartella non trovata: {cartella_pdf}{Style.RESET_ALL}")
        return

    tutti_dati_turbine = []
    
    # Trova tutti i PDF ricorsivamente
    file_pdf = [os.path.join(root, f) 
                for root, _, files in os.walk(cartella_pdf)
                for f in files if f.lower().endswith('.pdf')]
    
    print(f"{Fore.CYAN}Elaborazione di {len(file_pdf)} file PDF...{Style.RESET_ALL}")
    
    # Elabora ogni PDF
    for percorso_pdf in tqdm(file_pdf):
        dati_turbine = estrai_info_turbine(percorso_pdf)
        tutti_dati_turbine.extend(dati_turbine)
    
    # Salva in CSV
    if tutti_dati_turbine:
        file_csv = "turbine_eoliche.csv"
        with open(file_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['file_pdf', 'pagina', 'testo_turbina', 'latitudine', 'longitudine'])
            writer.writeheader()
            writer.writerows(tutti_dati_turbine)
        
        # Crea KML
        crea_kml_turbine(tutti_dati_turbine)
        
        print(f"\n{Fore.GREEN}Trovate {len(tutti_dati_turbine)} turbine eoliche!")
        print(f"Risultati salvati in {file_csv} e turbine_eoliche.kml{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Nessuna coordinata di turbina eolica trovata.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()