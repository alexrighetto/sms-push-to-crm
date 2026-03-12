import re
import sqlite3
import requests
import os
import shutil
import time
from datetime import datetime



# -----------------------------
# LOAD CONFIG
# -----------------------------

try:
    import config
except ImportError:
    raise Exception("Missing config.py. Copy config.example.py to config.py and edit it.")

LIVE_DB = os.path.expanduser(config.LIVE_DB)
SNAPSHOT_DB = os.path.expanduser(config.SNAPSHOT_DB)
WEBHOOK = config.WEBHOOK
STATE_FILE = os.path.expanduser(config.STATE_FILE)

BOOTSTRAP_DAYS = int(getattr(config, "BOOTSTRAP_DAYS", 0))
RATE_LIMIT_SLEEP = float(getattr(config, "RATE_LIMIT_SLEEP", 0))
DEVICE_ID = getattr(config, "DEVICE_ID", "unknown-device")
ENABLED = getattr(config, "ENABLED", True)

if not ENABLED:
    print("Sync disabled via config. Exiting.")
    exit()


# -----------------------------
# SNAPSHOT COPY
# -----------------------------

def refresh_snapshot():

    os.makedirs(os.path.dirname(SNAPSHOT_DB), exist_ok=True)

    shutil.copy2(LIVE_DB, SNAPSHOT_DB)

    for suffix in ("-wal", "-shm"):
        src = LIVE_DB + suffix
        dst = SNAPSHOT_DB + suffix

        if os.path.exists(src):
            shutil.copy2(src, dst)

    print("Snapshot updated:", datetime.now())


# -----------------------------
# STATE MANAGEMENT
# -----------------------------

def get_last_id():
    try:
        with open(STATE_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0


def save_last_id(last_id):

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    with open(STATE_FILE, "w") as f:
        f.write(str(last_id))


# -----------------------------
# APPLE TIME CONVERSION
# -----------------------------

def apple_time_to_unix(date_ns):

    try:
        return int(date_ns / 1_000_000_000 + 978307200)
    except:
        return None


# -----------------------------
# ATTRIBUTED BODY PARSER
# -----------------------------



def parse_attributed_body(blob):

    if not blob:
        return None

    try:
        # decode ignoring binary garbage
        text = blob.decode("utf-8", errors="ignore")

        # remove null bytes
        text = text.replace("\x00", "")

        # remove Apple framework names
        text = re.sub(
            r'(NSAttributedString|NSObject|NSString|NSDictionary|NSNumber|NSValue|streamtyped)',
            '',
            text
        )

        # remove control characters
        text = re.sub(r'[\x00-\x1F\x7F]', ' ', text)

        # collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # extract message after "+" marker used by iMessage serialization
        match = re.search(r'\+\s*([^\n]+)', text)

        if match:
            msg = match.group(1).strip()

            # remove markers like % or #
            msg = re.sub(r'^[#%]', '', msg)

            # remove Apple attributed string tail
            msg = re.split(r'__kIMMessagePartAttributeName', msg)[0].strip()

            # remove leftover serialization tokens
            msg = re.sub(r'\b[iIkK@]+\b', '', msg)
            
            # remove leading @
            msg = msg.lstrip("@")
            
            # normalize spaces
            msg = re.sub(r'\s+', ' ', msg).strip()

            return msg if msg else None

        # fallback if "+" not found
        return text if text else None

    except Exception as e:
        print("Attributed parse error:", e)
        return None
    
# -----------------------------
# EVENT TYPE DETECTION
# -----------------------------

def detect_event_type(text, attachments, reaction_type):

    if reaction_type and int(reaction_type) > 0:
        return "reaction"

    if attachments and text:
        return "message_with_attachment"

    if attachments:
        return "attachment"

    if text:
        return "message"

    return "unknown"


def normalize_protocol(service):

    if not service:
        return "unknown"

    s = str(service).strip().lower()

    if s == "sms":
        return "sms"

    if s == "imessage":
        return "imessage"

    return s


def split_attachments(attachments_csv):

    if not attachments_csv:
        return []

    parts = [p.strip() for p in str(attachments_csv).split(",") if p.strip()]

    seen = set()
    out = []

    for p in parts:

        if p not in seen:
            out.append(p)
            seen.add(p)

    return out


# -----------------------------
# QUERY BUILDER
# -----------------------------

def build_query(last_id):

    base_select = """
    SELECT
        m.ROWID                                AS message_rowid,
        m.text                                 AS text,
        m.attributedBody                       AS attributedBody,
        m.date                                 AS date_ns,
        m.is_from_me                           AS is_from_me,
        h.id                                   AS sender_phone,
        m.service                              AS service,
        m.associated_message_type              AS associated_message_type,

        GROUP_CONCAT(DISTINCT a.filename)      AS attachments_csv,
        GROUP_CONCAT(DISTINCT a.mime_type)     AS attachment_types,

        c.chat_identifier                      AS chat_identifier,
        c.display_name                         AS chat_display_name,

        COUNT(DISTINCT chj.handle_id)          AS participant_count

    FROM message m

    LEFT JOIN handle h
        ON m.handle_id = h.ROWID

    LEFT JOIN chat_message_join cmj
        ON cmj.message_id = m.ROWID

    LEFT JOIN chat c
        ON c.ROWID = cmj.chat_id

    LEFT JOIN chat_handle_join chj
        ON chj.chat_id = c.ROWID

    LEFT JOIN message_attachment_join maj
        ON maj.message_id = m.ROWID

    LEFT JOIN attachment a
        ON a.ROWID = maj.attachment_id
    """

    if last_id == 0 and BOOTSTRAP_DAYS > 0:

        print(f"Bootstrap mode active ({BOOTSTRAP_DAYS} days)")

        query = f"""
        {base_select}
        WHERE datetime(m.date/1000000000 + 978307200, 'unixepoch')
            >= datetime('now', '-{BOOTSTRAP_DAYS} days')
        GROUP BY m.ROWID
        ORDER BY m.ROWID ASC
        """

        params = ()

    else:

        query = f"""
        {base_select}
        WHERE m.ROWID > ?
        GROUP BY m.ROWID
        ORDER BY m.ROWID ASC
        """

        params = (last_id,)

    return query, params


# -----------------------------
# MAIN
# -----------------------------

def main():

    refresh_snapshot()

    conn = sqlite3.connect(SNAPSHOT_DB)

    # read WAL properly (important for iMessage DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA read_uncommitted = true;")
    conn.execute("PRAGMA temp_store = MEMORY;")

    cur = conn.cursor()

    last_id = get_last_id()

    print("Last processed ROWID:", last_id)

    query, params = build_query(last_id)

    cur.execute(query, params)

    rows = cur.fetchall()

    max_id = last_id

    for row in rows:

        rowid = row[0]
        text = row[1]
        attributed = row[2]
        date_ns = row[3]
        is_from_me = bool(row[4])
        sender_phone = row[5]
        service = row[6]
        reaction_type = row[7]
        attachments_csv = row[8]
        attachment_types = row[9]
        chat_identifier = row[10]
        chat_display_name = row[11]
        participant_count = row[12]
        
        # -----------------------------
        # TEXT RESOLUTION
        # -----------------------------

        if not text or "NSAttributedString" in str(text):
        
            if attributed:
        
                parsed = parse_attributed_body(attributed)
        
                if parsed:
                    text = parsed
                    print("Recovered text from attributedBody:", rowid)
        
                else:
                    print("Could not parse attributedBody:", rowid)
        
            else:
                print("Message without text and without attributedBody:", rowid)
        
        if text:
            text = re.sub(r'\s+', ' ', text).strip()
        
        protocol = normalize_protocol(service)
        
        attachments = split_attachments(attachments_csv)
        attachment_types_list = split_attachments(attachment_types)
        
        event_type = detect_event_type(text, attachments, reaction_type)
        
        unix_time = apple_time_to_unix(date_ns)
        if unix_time:
            iso_time = datetime.utcfromtimestamp(unix_time).isoformat() + "Z"
        else:
            iso_time = None

        if participant_count and int(participant_count) > 1:
            conversation_type = "group"
        else:
            conversation_type = "direct"

        payload = {

            "id": rowid,
            "device_id": DEVICE_ID,

            "source": "imessage",
            "event_type": event_type,

            "from_me": is_from_me,
            "phone": sender_phone,

           "text": text or "",

            "date": date_ns,
            "timestamp_unix": unix_time,
            "timestamp_iso": iso_time,

            "protocol": protocol,

            "conversation_type": conversation_type,
            "chat_id": chat_identifier,
            "chat_name": chat_display_name,

            "attachments": attachments,
            "attachment_types": attachment_types_list,

            "reaction_type": reaction_type
        }

        try:

            r = requests.post(WEBHOOK, json=payload, timeout=10)

            r.raise_for_status()

            print(f"Sent {rowid} | {event_type} | {sender_phone}")
            
            if RATE_LIMIT_SLEEP > 0:
                time.sleep(RATE_LIMIT_SLEEP)

        except Exception as e:

            print("Webhook error. Sync stopped:", e)

            conn.close()

            return

        if rowid > max_id:
            max_id = rowid

    save_last_id(max_id)

    print("Checkpoint saved:", max_id)

    conn.close()


if __name__ == "__main__":
    main()
