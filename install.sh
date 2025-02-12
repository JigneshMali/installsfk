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

    # Extract driver names and links
    declare -A DRIVER_INFO
    DRIVER_VERSIONS=()

    while IFS= read -r line; do
        if echo "$line" | grep -q "<DriverName>"; then
            DRIVER_ENTRY=$(echo "$line" | sed -E 's|.*<DriverName>(.*)</DriverName>.*|\1|')
            
            # Properly split using |^| as delimiter
            NAME=$(echo "$DRIVER_ENTRY" | awk -F '|\\^|' '{print $1}' | xargs)
            LINK=$(echo "$DRIVER_ENTRY" | awk -F '|\\^|' '{print $2}' | xargs)

            if [[ -n "$NAME" && -n "$LINK" ]]; then
                DRIVER_VERSIONS+=("$NAME")
                DRIVER_INFO["$NAME"]="$LINK"
            fi
        fi
    done <<< "$XML_CONTENT"

    if [[ ${#DRIVER_VERSIONS[@]} -eq 0 ]]; then
        echo "No drivers found."
        exit 1
    fi

    echo "Available drivers:"
    for i in "${!DRIVER_VERSIONS[@]}"; do
        echo "$((i+1)). ${DRIVER_VERSIONS[$i]}"
    done

    # Ask user for selection
    echo -n "Enter the index number of the driver you want to download: "
    read -r INDEX

    # Validate input
    if ! [[ "$INDEX" =~ ^[0-9]+$ ]] || (( INDEX < 1 || INDEX > ${#DRIVER_VERSIONS[@]} )); then
        echo "Invalid selection."
        exit 1
    fi

    # Get the selected driver name and link
    SELECTED_DRIVER="${DRIVER_VERSIONS[$((INDEX-1))]}"
    SELECTED_LINK="${DRIVER_INFO[$SELECTED_DRIVER]}"

    echo "Downloading $SELECTED_DRIVER..."
    echo "URL: $SELECTED_LINK"

    # Download driver
    curl -o /tmp/venus-data.tar.gz "$SELECTED_LINK"

    echo "Download completed: /tmp/venus-data.tar.gz"
}

# Call function
fetch_driver_info_xml
