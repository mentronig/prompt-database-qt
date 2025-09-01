# Automatisierte Testreports

Dieses Paket richtet **JUnit XML** und **HTML**-Reports für jeden Testlauf ein und erzeugt zusätzlich eine kompakte **Summary** (MD & HTML).

## Installation
```
pip install -r requirements-dev.txt
```

## Windows (PowerShell)
```
tools\run_tests.ps1
# oder ohne Zeitstempel:
tools\run_tests.ps1 -NoTimestamp
```

## Linux/macOS
```
bash tools/run_tests.sh
# ohne Zeitstempel:
NO_TIMESTAMP=1 bash tools/run_tests.sh
```

## Details
- `pytest.ini` schreibt Reports nach `reports/last/` (HTML + JUnit).
- `tests/conftest.py` legt die Ordner vorab an.
- Die Wrapper kopieren die Reports nach `reports/<YYYYMMDD-HHMMSS>/` und erzeugen `summary.md` & `summary.html` aus `junit.xml`.
