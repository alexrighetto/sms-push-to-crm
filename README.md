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
```

The installer will:

- create required directories
- clone/update the repository
- verify Python installation
- install dependencies
- create `config.py`
- create sync state file
- enable background execution (cron)

After installation, edit:

~/sms_bridge/config.py

and configure your webhook.

---

## How Background Execution Works

The bridge runs using a macOS cron job:

*/2 * * * * /usr/bin/python3 ~/sms_bridge/send_sms.py

This means:

- the script runs every 2 minutes
- Terminal does not need to stay open
- execution survives system reboots
- sync resumes automatically after restart

No manual action is required after reboot.

---

## Stop / Uninstall

### Stop background execution

Remove the cron job:

```bash
crontab -e
```

Delete the line containing `send_sms.py`, then save.

### Full uninstall

Run:

```bash
bash uninstall.sh
```

This removes the background job.

To delete all local data:

```bash
rm -rf ~/sms_bridge
rm -rf ~/crm_sync
```

---

## Manual Setup (Advanced)

1. Clone the repository

```bash
git clone https://github.com/alexrighetto/sms-push-to-crm.git
```

2. Create configuration:

```bash
cp config.example.py config.py
```

3. Edit `config.py`.

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run manually:

```bash
python3 send_sms.py
```

---

## Roadmap

The project is evolving from a single CRM integration into a
general-purpose local communication bridge.

### Phase 1 — Stable Core (Current)

- Incremental message synchronization
- Safe database snapshot reading
- Webhook delivery
- Automatic installer
- Cron-based execution
- Data-loss safe checkpointing

Goal: reliable local → webhook sync.

---

### Phase 2 — Generic Event Bridge

- Standardized event payload format
- Decouple bridge from CRM logic
- Configurable webhook targets

Goal: iMessage becomes a generic event source.

---

### Phase 3 — Multi-Destination Output

- Multiple webhook endpoints
- Routing rules
- Message filtering
- Contact normalization

Goal: multi-system delivery.

---

### Phase 4 — Real-Time Operation

- Replace polling with filesystem monitoring
- Near real-time ingestion

Goal: event-driven local agent.

---

### Phase 5 — Extensible Platform

- Plugin/output adapters
- CRM-agnostic integrations
- Knowledge-base integrations
- AI memory pipelines

Goal: local-first communication infrastructure.

---

## Notes

- `config.py` is intentionally ignored by git.
- `last_id.txt` stores sync state locally.
- Only new messages are imported (incremental sync).
- Snapshot reading prevents database lock issues with Messages.app.

---

## License

MIT License
