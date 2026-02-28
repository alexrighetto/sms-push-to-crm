# iMessage → EspoCRM Bridge

Incremental sync bridge that sends iMessage/SMS conversations
from macOS Messages.app into EspoCRM via n8n webhook.

## Features

- Incremental sync (no duplicates)
- Safe SQLite snapshot
- CRM timeline integration
- Self-hosted friendly

## Requirements

- macOS
- Python 3
- Messages synced via iCloud
- n8n webhook endpoint

## Setup

1. Clone repo
2. Copy config.example.py → config.py
3. Install dependencies

```bash
pip3 install -r requirements.txt
