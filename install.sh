#!/bin/bash
set -e

echo "Installing iMessage → EspoCRM Bridge"

BASE_DIR="$HOME/sms_bridge"
REPO_URL="https://github.com/alexrighetto/sms-push-to-crm.git"

echo "Creating directory..."
mkdir -p "$BASE_DIR"
mkdir -p "$HOME/crm_sync/messages"

command -v crontab >/dev/null 2>&1 || {
    echo "cron is required but not available."
    exit 1
}

echo "Cloning repository..."
if [ ! -d "$BASE_DIR/.git" ]; then
    git clone "$REPO_URL" "$BASE_DIR"
else
    echo "Repository already exists, pulling updates..."
    git -C "$BASE_DIR" pull
fi

echo "Checking Python..."
if ! command -v python3 &> /dev/null
then
    echo "Python3 not found. Install Python first."
    exit 1
fi

echo "Installing dependencies..."
python3 -m pip install --user -r "$BASE_DIR/requirements.txt"

echo "Creating config.py if missing..."
if [ ! -f "$BASE_DIR/config.py" ]; then
    cp "$BASE_DIR/config.example.py" "$BASE_DIR/config.py"
    echo "Edit config.py before running."
fi

echo "Creating state file..."
touch "$BASE_DIR/last_id.txt"

echo "Checking configuration before enabling cron..."

CONFIG_FILE="$BASE_DIR/config.py"

if grep -q "CHANGE_ME" "$CONFIG_FILE"; then
    echo "config.py is not configured yet."
    echo "Edit $CONFIG_FILE before cron can be enabled."
    echo "Installation finished without cron job."
    exit 0
fi

CRON_JOB="*/2 * * * * /usr/bin/python3 $BASE_DIR/send_sms.py"

echo "Installing cron job..."

(crontab -l 2>/dev/null | grep -v send_sms.py; echo "$CRON_JOB") | crontab -

echo "Cron job installed."
echo "Installation complete."

echo ""
echo "Running system health check..."
echo "--------------------------------"

STATUS_OK=true

# Python check
if command -v python3 >/dev/null 2>&1; then
    echo "✓ Python available"
else
    echo "✗ Python missing"
    STATUS_OK=false
fi

# Config check
if grep -q "CHANGE_ME" "$CONFIG_FILE"; then
    echo "✗ config.py not configured"
    STATUS_OK=false
else
    echo "✓ Config configured"
fi

# Messages DB access check
if [ -r "$HOME/Library/Messages/chat.db" ]; then
    echo "✓ Messages database accessible"
else
    echo "✗ Cannot access Messages database"
    echo "  → Enable Full Disk Access for Terminal"
    STATUS_OK=false
fi

# Cron check
if crontab -l 2>/dev/null | grep -q send_sms.py; then
    echo "✓ Cron job installed"
else
    echo "✗ Cron job missing"
    STATUS_OK=false
fi

# Script check
if [ -f "$BASE_DIR/send_sms.py" ]; then
    echo "✓ Bridge script present"
else
    echo "✗ send_sms.py missing"
    STATUS_OK=false
fi

echo "--------------------------------"

if [ "$STATUS_OK" = true ]; then
    echo "Bridge is ACTIVE."
else
    echo "Bridge installed but requires attention."
fi
