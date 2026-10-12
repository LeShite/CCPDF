# CCpdf — Suite local de gestión de PDF

Herramientas de escritorio para trabajar con PDFs sin subirlos a ningún servidor.

## Módulos

- **Extracción Avanzada**: cortar hasta palabra / clasificar por lista.
- **Fusionador**: unir varios PDFs en uno.
- **Divisor por Unidad**: separar un PDF grande por unidad médica.
- **Compresor**: reducir peso con Ghostscript o motor interno.
- **Firmar / Sellar**: *(en desarrollo)*.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Opcional, para mejor compresión en Linux:
sudo apt install ghostscript
