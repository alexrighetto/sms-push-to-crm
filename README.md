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


---

## Roadmap

The project is evolving from a single CRM integration into a
general-purpose local communication bridge.

### Phase 1 — Stable Core (Current)

- Incremental message synchronization
- Safe database snapshot reading
- Webhook delivery via n8n
- Automatic installer
- Cron-based background execution
- Data-loss safe checkpointing

Goal: reliable local → webhook sync.

---

### Phase 2 — Generic Event Bridge

- Standardized event payload format
- Decouple bridge from specific CRM logic
- Support multiple downstream systems
- Configurable webhook targets

Goal: iMessage becomes a generic event source.

---

### Phase 3 — Multi-Destination Output

- Multiple webhook endpoints
- Optional routing rules
- Message filtering
- Contact normalization layer

Goal: send messages to different systems simultaneously.

---

### Phase 4 — Real-Time Operation

- Replace cron polling with filesystem monitoring
- Near real-time message ingestion
- Reduced system overhead

Goal: event-driven local agent.

---

### Phase 5 — Extensible Platform

- Plugin/output adapters
- CRM-agnostic integrations
- Personal knowledge base integrations
- AI memory pipelines

Goal: local-first communication data infrastructure.

---

## Philosophy

This project follows a local-first approach:

- your data stays on your machine
- no external APIs required
- fully self-hosted workflows
- simple components over complex services
