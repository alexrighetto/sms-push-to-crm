# Architecture Notes  
## Future Evolution — iMessage Bridge

---

## Current Status (Stable Phase)

The project currently operates as a:

**iMessage → n8n → EspoCRM incremental bridge**

Architecture:

```
Messages.app (SQLite)
        ↓
Safe snapshot copy
        ↓
Incremental sync (ROWID cursor)
        ↓
Webhook (n8n)
        ↓
EspoCRM Timeline
```

### Current Goals

- Reliable ingestion of Messages.app data
- No duplicates
- Safe database access
- Automatic background execution
- Local-first operation
- Recoverable state via `last_id.txt`

At this stage, stability and observability are the priority.

No architectural changes should be introduced until the system proves stable over time.

---

## Architectural Observation

The current bridge directly pushes data to a webhook endpoint.

This means the script acts simultaneously as:

- database reader
- transport layer
- integration layer

This creates tight coupling between:

```
Message ingestion
AND
CRM destination
```

While functional, this limits extensibility.

---

## Key Insight

The real value of the project is not CRM synchronization.

The real value is:

> Turning personal communication streams into structured local events.

Messages become a **data source**, not a destination workflow.

---

## Proposed Future Evolution (Concept Only — Not Implemented Yet)

### Step Change

Introduce a local event layer between ingestion and delivery.

Instead of:

```
Bridge → Webhook
```

Use:

```
Bridge → Local Event Queue → Consumers
```

---

## Future Architecture (Conceptual)

```
Messages.app
      ↓
Snapshot Reader
      ↓
Bridge (Event Producer)
      ↓
LOCAL EVENT QUEUE
      ↓
Consumers
   ├─ n8n webhook
   ├─ EspoCRM
   ├─ AI memory systems
   ├─ analytics pipelines
   └─ archives
```

---

## Why This Matters

Decoupling ingestion from delivery enables:

- destination independence
- offline safety
- retry mechanisms
- multi-system delivery
- easier debugging
- extensibility without rewriting the bridge

The bridge becomes a **producer**, not an integration.

---

## Concept: Local Event Bus

Each message would be emitted as a structured event:

```
event/
   uuid.json
```

Example payload:

```json
{
  "source": "imessage",
  "event_type": "message",
  "id": 123456,
  "phone": "+19074604674",
  "text": "Hello",
  "from_me": 1,
  "timestamp": "2026-02-27 23:05:51"
}
```

Consumers then decide where events go.

---

## Long-Term Direction

This architecture naturally expands into a:

**Local Personal Event Infrastructure**

Possible future sources:

- iMessage
- SMS
- Calls history
- Mail.app
- Calendar
- Notes
- Messaging desktop databases

Possible destinations:

- CRM systems
- Knowledge bases
- AI memory layers
- analytics dashboards
- personal archives

---

## Guiding Principle

The bridge should evolve toward:

> Local-first, destination-agnostic communication ingestion.

Data ownership remains entirely local.

---

## Current Decision

These ideas are intentionally **parked**.

Immediate focus remains:

- validating stability
- verifying incremental sync correctness
- confirming cron reliability
- ensuring long-running safety

Only after operational confidence will architectural evolution begin.

---

## Next Milestone (Operational)

System considered stable when:

- multiple reboots succeed without intervention
- no duplicate imports occur
- webhook failures recover cleanly
- state file behaves predictably
- long-running cron execution is verified

---

## Note

Architecture evolution should happen incrementally and never break the stable ingestion layer.

The ingestion engine is the core asset.
