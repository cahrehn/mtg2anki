#!/bin/bash

export PATH="/opt/homebrew/bin:$PATH"

# Set code for the card set to monitor
SET_CODE="tla"

# Directory where the script and data files will be stored
SCRIPT_DIR="$HOME/dev/mtg2anki"
CURRENT_FILE="$SCRIPT_DIR/$SET_CODE.tsv"
PREVIOUS_FILE="$SCRIPT_DIR/$SET_CODE.tsv.previous"
LOG_FILE="$SCRIPT_DIR/card-monitor.log"

# Create the script directory if it doesn't exist
mkdir -p "$SCRIPT_DIR"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Download and process new data
#wget -qO- "https://api.scryfall.com/cards/search?q=set%3A$SET_CODE+-t%3Aland+layout%3Anormal+sort%3Aspoiled+r%3Cr+cn%3C272&pretty=true" | \
#wget -qO- "https://api.scryfall.com/cards/search?q=s%3Aneo+r<r+game%3Apaper+-type%3Abasic+-type%3Asaga+-%28type%3Aland+and+o%3Again%29+-%28shakedown+or+cudgel+or+enormous+or+paint+or+dramatist+or+impossible%29&pretty=true" | \
#wget -qO- "https://api.scryfall.com/cards/search?q=s%3Aneo+r<r+game%3Apaper+-type%3Abasic+-type%3Asaga+-%28type%3Aland+and+o%3Again%29+-%28shakedown+or+cudgel+or+enormous+or+paint+or+dramatist+or+impossible%29&pretty=true" | \
#wget -qO- "https://api.scryfall.com/cards/search?q=s%3Aneo+r%3Cr+type%3Asaga&pretty=true" | \
#wget -qO- "https://api.scryfall.com/cards/search?q=set%3A$SET_CODE+r<r+-type%3Abasic+-is%3Adfc+-type%3Asaga+-%27%5C"%27&pretty=true" | \
#wget -qO- "https://api.scryfall.com/cards/search?q=s%3Aeld+r%3Cr+-type%3Abasic+type%3Aadventure&pretty=true" | \
#wget -qO- "https://api.scryfall.com/cards/search?q=s%3Awoe+r%3Cr+-type%3Abasic+-type%3Aadventure+-type%3Asaga&pretty=true" | \
# wget -qO- "https://api.scryfall.com/cards/search?q=s%3Awoe+r%3Cr+type%3Asaga&pretty=true" | \
wget -qO- "https://api.scryfall.com/cards/search?q=set%3A$SET_CODE+r<r+-type%3Abasic+-is%3Adfc+-type%3Asaga+-type%3Aadventure&pretty=true" | \
    jq -r '.data[] | "\(.name)\t\(.id)"' | \
    grep -v "\"" > "$CURRENT_FILE"
 
# Check if download was successful
if [ $? -ne 0 ]; then
    log_message "Error: Failed to download or process card data"
    exit 1
fi

# If this is the first run, create the previous file
if [ ! -f "$PREVIOUS_FILE" ]; then
    cp "$CURRENT_FILE" "$PREVIOUS_FILE"
    log_message "Initial run - created baseline file"
    exit 0
fi

# Compare the number of lines
current_lines=$(wc -l < "$CURRENT_FILE")
previous_lines=$(wc -l < "$PREVIOUS_FILE")

log_message "Current lines: $current_lines, Previous lines: $previous_lines"

if [ $current_lines -gt $previous_lines ]; then
    log_message "New cards detected! Running AppleScript..."
    
    # Run your AppleScript here
    osascript "$SCRIPT_DIR/tsv2anki.scpt"
    
    # Update the previous file with current data
    cp "$CURRENT_FILE" "$PREVIOUS_FILE"
else
    log_message "No new cards detected"
fi