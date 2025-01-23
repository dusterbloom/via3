import re
from typing import Optional, Tuple

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

def create_kml(coordinates: list, output_file: str = "coordinates.kml"):
    """
    Create a KML file from a list of (lat, lon) coordinates
    """
    kml_header = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Style id="marker">
      <IconStyle>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/paddle/red-circle.png</href>
        </Icon>
      </IconStyle>
    </Style>"""
    
    kml_footer = """
  </Document>
</kml>"""
    
    with open(output_file, 'w') as f:
        f.write(kml_header)
        
        for i, (lat, lon) in enumerate(coordinates, 1):
            placemark = f"""
    <Placemark>
      <name>Point {i}</name>
      <styleUrl>#marker</styleUrl>
      <Point>
        <coordinates>{lon},{lat},0</coordinates>
      </Point>
    </Placemark>"""
            f.write(placemark)
            
        f.write(kml_footer)

def main():
    # Read the CSV from prugadori.py
    import csv
    coordinates_list = []
    
    with open('pdf_matches.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coords = parse_coordinates(row['Matched_Text'])
            if coords:
                coordinates_list.append(coords)
                print(f"Found coordinates: {coords}")
    
    if coordinates_list:
        create_kml(coordinates_list)
        print(f"Created KML file with {len(coordinates_list)} coordinates")
    else:
        print("No valid coordinates found")

if __name__ == "__main__":
    main()