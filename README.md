# HoneyChain

IoT-enabled honey batch pre-screening and hive-to-report traceability prototype.

## Features

- Hive ID, Batch ID, and location registration
- Honey screening report generation
- SHA-256 tamper-evident report hash
- QR code report reference
- JSON report storage
- Simulation mode and Arduino sensor-ready workflow

## Run Locally

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Project Structure

```text
HoneyChain/
├── app.py
├── requirements.txt
└── templates/
    ├── index.html
    └── report.html
```

## Disclaimer

HoneyChain is a prototype pre-screening and traceability system. It does not replace laboratory-certified honey purity, adulteration, or food-safety testing.
