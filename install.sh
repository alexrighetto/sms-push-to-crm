#!/bin/bash

echo "Installing iMessage → EspoCRM Bridge"

BASE_DIR="$HOME/sms_bridge"
REPO_URL="https://github.com/alexrighetto/sms-push-to-crm.git"

echo "Creating directory..."
mkdir -p "$BASE_DIR"
mkdir -p "$HOME/crm_sync/messages"

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

CRON_JOB="*/2 * * * * /usr/bin/python3 $BASE_DIR/send_sms.py"

echo "Installing cron job..."

(crontab -l 2>/dev/null | grep -v send_sms.py; echo "$CRON_JOB") | crontab -

echo "Installation complete."
echo "Edit config.py and you are ready."
