# Guida all'Installazione e Utilizzo dello Script per Turbine Eoliche

## 1. Installazione di Python su Windows

### Passo 1: Scaricare Python
1. Vai al sito ufficiale di Python: https://www.python.org/downloads/
2. Clicca sul pulsante giallo "Download Python 3.x.x" (l'ultima versione)
3. Scarica il file .exe

### Passo 2: Installare Python
1. Apri il file scaricato
2. **IMPORTANTE**: Spunta la casella "Add Python to PATH"
3. Clicca "Install Now"
4. Attendi il completamento dell'installazione

### Passo 3: Verifica l'Installazione
1. Apri il "Prompt dei Comandi" (cerca "cmd" nel menu Start)
2. Digita: `python --version`
3. Dovresti vedere la versione di Python installata

## 2. Installazione delle Librerie Necessarie

Nel Prompt dei Comandi, copia e incolla questi comandi uno alla volta:

```bash
pip install pdfplumber
pip install tqdm
pip install colorama
```

Attendi che ogni installazione sia completata prima di procedere con la successiva.

## 3. Preparazione dello Script

1. Crea una nuova cartella sul desktop (es: "TurbineEoliche")
2. Copia il file `coordinate_turbine_eoliche.py` in questa cartella
3. Copia i PDF da analizzare in una sottocartella (es: "PDF")

## 4. Esecuzione dello Script

1. Apri il Prompt dei Comandi
2. Naviga fino alla cartella dello script:
```bash
cd Desktop\TurbineEoliche
```
3. Esegui lo script:
```bash
python coordinate_turbine_eoliche.py
```
4. Quando richiesto, inserisci il percorso della cartella PDF (es: `PDF`)

## 5. Risultati

Lo script creerà due file:
- `turbine_eoliche.csv`: apribile con Excel
- `turbine_eoliche.kml`: apribile con Google Earth

### Per Visualizzare i Risultati in Google Earth:
1. Scarica e installa Google Earth Pro (gratuito)
2. Apri Google Earth Pro
3. File -> Apri
4. Seleziona il file `turbine_eoliche.kml`

## Risoluzione Problemi Comuni

### "Python non è riconosciuto come comando interno..."
- Soluzione: Reinstalla Python assicurandoti di spuntare "Add Python to PATH"

### "ModuleNotFoundError: No module named..."
- Soluzione: Ripeti l'installazione della libreria mancante con pip install

### "PermissionError: Permission denied"
- Soluzione: Esegui il Prompt dei Comandi come amministratore

## Note Importanti
- Lo script analizza ricorsivamente tutti i PDF nella cartella specificata
- Il processo potrebbe richiedere tempo con molti PDF
- I risultati mostrano:
  - Coordinate delle turbine
  - File di origine
  - Pagina del documento
  - Testo circostante

