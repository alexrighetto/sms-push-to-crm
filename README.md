# iMessage → EspoCRM Bridge

> A local-first bridge that turns iMessage into a CRM data source.

Incremental sync bridge that sends iMessage/SMS conversations
from macOS Messages.app into EspoCRM via n8n webhook.

---

## What is this?

A lightweight macOS bridge that reads iMessage/SMS conversations
from the local Messages database and pushes them into a CRM
(EspoCRM via n8n webhook) using safe incremental synchronization.

Designed for self-hosted workflows and full data ownership.

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
- Automatic installer
- Persistent background execution
- Safe restart after system reboot

---

## Requirements

- macOS
- Python 3
- Messages synced via iCloud
- n8n webhook endpoint

---

## Quick Install (Recommended)

Run the installer:

```bash
bash install.sh
