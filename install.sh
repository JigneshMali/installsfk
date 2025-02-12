#!/bin/bash

# Define URL
URL="https://www.sunfunkits.com/Download/SFKDriverVersion.xml"

# Function to fetch and parse driver info from XML
fetch_driver_info_xml() {
    echo "Fetching driver details from XML..."
    XML_CONTENT=$(curl -s "$URL")

    if [[ -z "$XML_CONTENT" ]]; then
        echo "Failed to download XML or empty content."
        exit 1
    fi

    # Extract driver names and links
    declare -A DRIVER_INFO
    DRIVER_VERSIONS=()

    while IFS= read -r line; do
        if echo "$line" | grep -q "<DriverName>"; then
            DRIVER_ENTRY=$(echo "$line" | sed -E 's|.*<DriverName>(.*)</DriverName>.*|\1|')
            NAME=$(echo "$DRIVER_ENTRY" | cut -d '|^|' -f1 | xargs)
            LINK=$(echo "$DRIVER_ENTRY" | cut -d '|^|' -f2 | xargs)

            if [[ -n "$NAME" && -n "$LINK" ]]; then
                VERSION=$(echo "$NAME" | grep -oP 'v\d+\.\d+\d*' || echo "Unknown")
                DRIVER_INFO["$VERSION"]="$LINK"
                DRIVER_VERSIONS+=("$VERSION")
            fi
        fi
    done <<< "$XML_CONTENT"

    if [[ ${#DRIVER_VERSIONS[@]} -eq 0 ]]; then
        echo "No drivers found."
        exit 1
    fi

    echo "Available driver versions:"
    for i in "${!DRIVER_VERSIONS[@]}"; do
        echo "$((i+1)). ${DRIVER_VERSIONS[$i]}"
    done
}

# Call function
fetch_driver_info_xml()
