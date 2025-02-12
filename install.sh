#!/bin/bash

# Define URL
URL="https://www.sunfunkits.com/Download/SFKDriverVersion-test.xml"

# Function to fetch and parse driver info from XML
fetch_driver_info_xml() {
    echo "Fetching driver details from XML..."
    XML_CONTENT=$(curl -s "$URL")

    if [[ -z "$XML_CONTENT" ]]; then
        echo "Failed to download XML or empty content."
        exit 1
    fi

    DRIVER_NAMES=()
    DRIVER_LINKS=()

    while IFS= read -r line; do
        if [[ "$line" =~ "<DriverName>" ]]; then
            DRIVER_ENTRY=$(echo "$line" | sed -n 's|.*<DriverName>\(.*\)</DriverName>.*|\1|p')

            # Use IFS to split on "|^|"
            IFS='|^|' read -r NAME LINK <<< "$DRIVER_ENTRY"

            NAME=$(echo "$NAME" | xargs)  # Trim spaces
            LINK=$(echo "$LINK" | xargs)  # Trim spaces

            if [[ -n "$NAME" && -n "$LINK" ]]; then
                DRIVER_NAMES+=("$NAME")
                DRIVER_LINKS+=("$LINK")
            fi
        fi
    done <<< "$XML_CONTENT"

    if [[ ${#DRIVER_NAMES[@]} -eq 0 ]]; then
        echo "No drivers found."
        exit 1
    fi

    echo "Available drivers:"
    for i in "${!DRIVER_NAMES[@]}"; do
        echo "$((i+1)). ${DRIVER_NAMES[$i]}"
    done
}

# Function to download selected driver
download_driver() {
    read -p "Enter the index number of the driver you want to download: " SELECTION

    if ! [[ "$SELECTION" =~ ^[0-9]+$ ]] || (( SELECTION < 1 || SELECTION > ${#DRIVER_NAMES[@]} )); then
        echo "Invalid selection. Please enter a number between 1 and ${#DRIVER_NAMES[@]}."
        exit 1
    fi

    INDEX=$((SELECTION - 1))
    DOWNLOAD_URL="${DRIVER_LINKS[$INDEX]}"
    DRIVER_NAME="${DRIVER_NAMES[$INDEX]}"

    echo "Downloading $DRIVER_NAME..."
    curl -o "/tmp/$(basename "$DOWNLOAD_URL")" -L "$DOWNLOAD_URL"

    echo "Download completed: /tmp/$(basename "$DOWNLOAD_URL")"
}

# Run functions
fetch_driver_info_xml
download_driver
