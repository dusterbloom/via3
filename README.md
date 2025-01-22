## Strumenti Inclusi

### 1. Enumeratore dei progetti (cumponidori.py)
Crea una lista di progetti in formato CSV a partire dai risultati di una ricerca sul portale VA.MITE 

- 🔍 Ricerca nella sezione "Progetti" del VA.MITE
- 📑 Gestisce risultati ripartiti su piu' pagine
- 📊 Esporta i risultati in formato CSV con i dettagli del progetto (lista.csv)
- ✅ Include una colonna SI/NO per selezionare quali progetti scaricare successivamente


### 2. Scaricatore automatico (bastraxu.py)
Scarica i documenti elencati in lista.csv generata da cumponidori.

- 📋 legge il file lista.csv
- ✨ Scarica solo i progetti contrassegnati con SI (EJA?)
- 📁 Permette di specificare la cartella di destinazione
- 🗂️ Organizza i file in cartelle in base all'identificativo di cartella del progetto.


### 3. Scaricatore (tzeracu.py)
Scarica documenti dal portale VA.MITE in base a una chiave di ricerca (ricerca libera, non utilizza lista.csv)

- 🔍 Ricerca nelle sezioni "Progetti" o  "Documenti"
- 📑 Accetta risultati su pagine multiple
- 🗂️ Organizza i documenti per chiave di ricerca e Identificativo progetto

### 4. Cerca parole chiave nei file PDF dei progetti  (prugadori.py)
Ricerca nei PDF scaricati l'occorrenza delle chiavi di ricerca preimpostate e esporta i risultati in un file

- 📁 Ricerca dei PDF in cartelle e sottocartelle
- 🔍 Parametri di ricerca incorporati per coordinate e termini tecnici
- 📊 Esporta i risultati in un file con riferimenti alla pagina e alla linea di origine
- 🎨 Risultati evidenziati su console con colori diversi

## Avvio Rapido

1. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

2. Elenca i progetti:
```bash
python list_projects.py
# Inserisci una parola chiave per la ricerca (ad esempio, "Sardegna")
# I risultati saranno salvati in projects_list.csv
```

3. Modifica il file projects_list.csv per indicare quali progetti scaricare (SÌ/NO).

4. Scarica i progetti selezionati:
```bash
python download_from_list.py
# Inserisci il nome della cartella per i download
```

5. Oppure scarica direttamente tramite ricerca:
```bash
python main.py
# Segui le istruzioni per la parola chiave e il tipo di ricerca
```

6. Scansiona i PDF:
```bash
python scan.py
# I risultati saranno salvati in pdf_matches.csv
```

## Configurazione

### Impostazioni Comuni
```python
BASE_URL = "https://va.mite.gov.it"
DOWNLOAD_FOLDER = "downloads"
DELAY_BETWEEN_REQUESTS = 1.0
```

### Scanner PDF (scan.py)
```python
PDF_FOLDER = "downloads/Serramanna"
OUTPUT_CSV = "pdf_matches.csv"
```

## Struttura dei File
```
.
├── projects_list.csv         # Elenco dei progetti con flag di download
├── downloads/               
│   └── [user_folder]/       # Cartella di download specificata dall'utente
│       └── [project_id]/    # Cartelle dei singoli progetti
│           └── documents... # File scaricati
└── pdf_matches.csv          # Risultati della scansione PDF
```

## Requisiti

- Python 3.x
- requests
- beautifulsoup4
- pdfplumber
- colorama
- tqdm

## Licenza

Licenza MIT