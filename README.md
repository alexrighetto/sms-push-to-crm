# iMessage → EspoCRM Bridge

Incremental sync bridge that sends iMessage/SMS conversations
from macOS Messages.app into EspoCRM via n8n webhook.

---

## What is this?

A lightweight macOS bridge that reads iMessage/SMS conversations
from the local Messages database and pushes them into a CRM
(EspoCRM via n8n webhook) using safe incremental synchronization.

Designed for self-hosted workflows.

---

## Architecture

Messages.app (SQLite database)  
        ↓  
Snapshot copy (safe read)  
        ↓  
Incremental sync (ROWID cursor)  
        ↓  
Webhook (n8n)  
        ↓  
EspoCRM Timeline

---

## Features

- Incremental sync (no duplicates)
- Safe SQLite snapshot reading
- CRM timeline integration
- Local-first architecture
- Self-hosted friendly

---

## Requirements

- macOS
- Python 3
- Messages synced via iCloud
- n8n webhook endpoint

---

## Setup

1. Clone the repository

2. Create your local configuration:

```bash
cp config.example.py config.py
```

3. Edit `config.py` and add your webhook URL and paths.

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run manually:

```bash
python3 send_sms.py
```

---

## Automation (cron example)

Run every 2 minutes:

```bash
*/2 * * * * python3 /path/to/send_sms.py
```

---

## Notes

- `config.py` is intentionally ignored by git.
- `last_id.txt` stores sync state locally and is not versioned.
- The script only imports **new messages**, preventing duplicates.

