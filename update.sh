#!/bin/bash

BASE_DIR="$HOME/sms_bridge"

echo "Updating bridge..."
git -C "$BASE_DIR" pull --quiet
