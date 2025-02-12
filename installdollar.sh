#!/bin/bash

# Configuration
install_path="/data"
backup_dir="$install_path/etc"
firmware_download_path="/tmp/venus-data.tar.gz"

URL="https://raw.githubusercontent.com/JigneshMali/installsfk/main/Sfkdriver.xml"
FIRMWARE_DOWNLOAD_PATH="/tmp/venus-data.tar.gz"

# Backup configuration files
# if [ -f "$install_path/etc/dbus-serialbattery/config.ini" ]; then
#     mv "$install_path/etc/dbus-serialbattery/config.ini" "$install_path/etc/dbus-serialbattery_config.ini.backup"
# fi

if [ -f "$install_path/etc/dbus-serialbattery/config.default.ini" ]; then
    mv "$install_path/etc/dbus-serialbattery/config.default.ini" "$install_path/etc/dbus-serialbattery_config.default.ini.backup"
fi

if [ -f "$install_path/etc/dbus-serialbattery/SFKVirtualBattery/BatterySetupOptionValue.json" ]; then
    mv "$install_path/etc/dbus-serialbattery/SFKVirtualBattery/BatterySetupOptionValue.json" "$install_path/etc/BatterySetupOptionValue.json.backup"
fi

# Function to fetch and parse XML
download_driver() {
    echo "Fetching driver details from XML..."
    XML_CONTENT=$(curl -s "$URL")

    if [[ -z "$XML_CONTENT" ]]; then
        echo "Failed to download XML or empty content."
        exit 1
    fi

    echo "XML Content:"   # Debugging line
    echo "$XML_CONTENT"

    # Extract driver names and URLs
    DRIVER_NAMES=()
    DRIVER_URLS=()

    while IFS= read -r line; do
        if echo "$line" | grep -q "<DriverName>"; then
            ENTRY=$(echo "$line" | sed -E 's|.*<DriverName>(.*)</DriverName>.*|\1|')
            NAME=$(echo "$ENTRY" | awk -F "$" '{print $1}' | xargs)
            LINK=$(echo "$ENTRY" | awk -F "$" '{print $2}' | xargs)

            if [[ -n "$NAME" && -n "$LINK" ]]; then
                DRIVER_NAMES+=("$NAME")
                DRIVER_URLS+=("$LINK")
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

    read -p "Enter the index number of the driver you want to download: " choice
    if [[ $choice -lt 1 || $choice -gt ${#DRIVER_NAMES[@]} ]]; then
        echo "Invalid selection. Exiting."
        exit 1
    fi

    SELECTED_NAME="${DRIVER_NAMES[$((choice-1))]}"
    SELECTED_URL="${DRIVER_URLS[$((choice-1))]}"

    echo "Downloading $SELECTED_NAME..."
    echo "URL: $SELECTED_URL"  # Debugging line

    curl -L "$SELECTED_URL" -o "$FIRMWARE_DOWNLOAD_PATH"
    if [[ $? -ne 0 ]]; then
        echo "Error: Download failed."
        exit 1
    fi
    echo "Download completed: $FIRMWARE_DOWNLOAD_PATH"
}

download_driver

# Extract driver
if [ -f "$FIRMWARE_DOWNLOAD_PATH" ]; then
    # Remove old driver
    rm -rf "$install_path/etc/dbus-serialbattery"
    tar -zxf "$FIRMWARE_DOWNLOAD_PATH" -C "$install_path"
else
    echo "There is no file in \"$FIRMWARE_DOWNLOAD_PATH\""
    exit
fi

if [ -f "$install_path/etc/dbus-serialbattery/reinstall-local.sh" ]; then
    bash "$install_path/etc/dbus-serialbattery/reinstall-local.sh"
fi

# Ask for reboot
read -p "Driver installation completed. Do you want to reboot now? (y/N): " reboot_choice
if [[ "$reboot_choice" =~ ^[Yy]$ ]]; then
    echo "Rebooting now..."
    reboot
else
    echo "Reboot skipped. You may need to restart manually."
fi
