Zusammenarbeit – Kurzleitfaden für neue Chats
1) Kick-off (Kontext-Lock)

Story & Scope bestätigen: Story-ID, Ziel, Akzeptanzkriterien, betroffene Dateien/Tools.

Golden Path festlegen (siehe unten) und Änderungen nur per “Change Request”.

Arbeitsumgebung: Windows + PowerShell, Python 3.13, Qt/PySide6.

2) Golden Path (Import/Hardening)

tools/llm_extract_prompts.py --mode llm-refine

tools/ingest_jsonl_to_db.py --min-content-len 60 --category <cat> --default-tags "<tags>"

tools/dedupe_db.py --mode content --apply

tools/show_last_records.py / tools/print_db_info.py
→ Alle Aufrufe immer über tools\run_with_kpi.cmd.

3) Kontrolle der Arbeitsergebnisse

Nach jedem Schritt: knapper Konsolen-Output zeigen (Erfolg/Counts/Dateipfade).

Self-Check vor Übergabe:

pytest -q (bzw. HTML/JSON-Report).

KPI-Ampel grün (≥90 % pass-rate, keine “extra_errors”).

DB-Pfad und Item-Count plausibel.

Bei Fehlermeldungen: Ursache kurz benennen + Fix durchführen (kein Weitergehen mit “rot”).

4) Entwicklungs-/Lieferregeln

Keine Code-Schnipsel als Endergebnis → ZIP-Paket mit vollständigen Dateien (keine Diffs).

Immer vollständige Module/Dateien liefern, keine manuelle Einfügearbeit erfordern.

Dokus pflegen: BACKLOG.md, CHANGELOG.md, PROJECT_STATUS.md, Handover-MD, COMMIT_MESSAGE.txt.

5) KPI-Pflicht & Messbarkeit

Jeder Python-Aufruf via tools\run_with_kpi.cmd (zählt Erfolge/Fehler).

Bei CLI-Beispielen PowerShell-Syntax verwenden (Backtick ``` für Zeilenumbrüche, keine Bash-Heredocs).

6) Rückfragen & Entscheiden

Unklarheit zu Beginn? Erst fragen (einmal, präzise), dann umsetzen.

Nach Start: eigenständig ausführen, nur bei Blockern erneut nachfragen.

Teil-Ergebnisse sind ok, aber fehlerfrei und messbar (KPI/Tests).

7) Fehlerrobustheit

Pfade defensiv prüfen, klare JSON-Summary aus Tools, Soft-Fallbacks (z. B. Heuristik statt LLM).

Keine Geheimnisse in Logs; API-Keys nur aus Environment.

8) Definition of Done (DoD)

Golden-Path läuft Ende-zu-Ende, KPI grün, pytest grün.

Doku & Handover aktualisiert, ZIP lieferbar, COMMIT_MESSAGE.txt vorhanden.

Merksatz: Ein Schritt – messen – Ergebnis zeigen – erst dann der nächste Schritt