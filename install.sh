#!/bin/bash

# Configuration
INSTALL_PATH="/data"
BACKUP_DIR="$INSTALL_PATH/etc"
FIRMWARE_DOWNLOAD_PATH="/tmp/venus-data.tar.gz"
XML_URL="https://www.sunfunkits.com/Download/SFKDriverVersion-test.xml"

# Function to fetch and parse driver info from XML
# Function to fetch and parse XML
fetch_driver_info_xml() {
    echo "Fetching driver details from XML..."
    XML_CONTENT=$(curl -s "$XML_URL")

    if [[ -z "$XML_CONTENT" ]]; then
        echo "Failed to download XML or empty content."
        exit 1
    fi

    # Extract driver names and links
    DRIVER_INFO=()
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

# Function to extract version from driver name
extract_version() {
    if [[ "$1" =~ v([0-9]+\.[0-9]+)([0-9]*)[[:space:]]*(Beta|beta)? ]]; then
        echo "${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
    else
        echo ""
    fi
}

# Function to backup configuration files
backup_config() {
    echo "Backing up existing configurations..."
    CONFIG_FILE="$INSTALL_PATH/etc/dbus-serialbattery/config.default.ini"
    SETUP_FILE="$INSTALL_PATH/etc/dbus-serialbattery/SFKVirtualBattery/BatterySetupOptionValue.json"

    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "$BACKUP_DIR/dbus-serialbattery_config.default.ini.backup"
    fi
    if [ -f "$SETUP_FILE" ]; then
        cp "$SETUP_FILE" "$BACKUP_DIR/BatterySetupOptionValue.json.backup"
    fi
}

# Function to extract firmware
extract_firmware() {
    echo "Extracting driver..."
    EXTRACT_PATH="$INSTALL_PATH/etc/dbus-serialbattery"
    BACKUP_CONFIG_PATH="$INSTALL_PATH/etc/dbus-serialbattery_config.ini.backup"
    CONFIG_PATH="$EXTRACT_PATH/config.ini"

    if [ -f "$FIRMWARE_DOWNLOAD_PATH" ]; then
        rm -rf "$EXTRACT_PATH"
        mkdir -p "$EXTRACT_PATH"
        tar -xzf "$FIRMWARE_DOWNLOAD_PATH" -C "$INSTALL_PATH"
    else
        echo "No firmware file found."
        if [ -f "$BACKUP_CONFIG_PATH" ]; then
            echo "Restoring config.ini from backup..."
            mkdir -p "$EXTRACT_PATH"
            mv "$BACKUP_CONFIG_PATH" "$CONFIG_PATH"
        fi
        exit 1
    fi
}

# Function to download firmware
download_firmware() {
    local FIRMWARE_URL="$1"
    echo "Downloading firmware from $FIRMWARE_URL..."
    curl -L "$FIRMWARE_URL" -o "$FIRMWARE_DOWNLOAD_PATH"
}

# Function to install firmware
install_firmware() {
    fetch_driver_info_xml
    if [ ${#DRIVER_VERSIONS[@]} -eq 0 ]; then
        echo "No drivers found in XML."
        return
    fi

    echo "Available driver versions:"
    for i in "${!DRIVER_VERSIONS[@]}"; do
        echo "$((i+1)). ${DRIVER_VERSIONS[i]}"
    done

    read -p "Enter the numbers of versions to install (comma-separated): " USER_INPUT
    IFS=',' read -ra SELECTED_VERSIONS <<< "$USER_INPUT"

    for IDX in "${SELECTED_VERSIONS[@]}"; do
        VERSION_INDEX=$((IDX-1))
        if [[ $VERSION_INDEX -lt ${#DRIVER_VERSIONS[@]} ]]; then
            VERSION=${DRIVER_VERSIONS[$VERSION_INDEX]}
            FIRMWARE_URL=${DRIVER_INFO[$VERSION]}
            echo "Installing firmware version $VERSION..."
            download_firmware "$FIRMWARE_URL"
            backup_config
            extract_firmware
        fi
    done
}

# Start the firmware installation process
install_firmware
