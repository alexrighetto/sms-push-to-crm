#!/bin/bash

echo "Uninstalling iMessage → EspoCRM Bridge"

BASE_DIR="$HOME/sms_bridge"

echo "Removing cron job..."

(crontab -l 2>/dev/null | grep -v send_sms.py) | crontab -

echo "Cron job removed."

echo ""
echo "Application files remain at:"
echo "$BASE_DIR"
echo ""
echo "To remove completely run:"
echo "rm -rf $BASE_DIR"
echo "rm -rf ~/crm_sync"

echo "Uninstall complete."
