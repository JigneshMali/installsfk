#!/bin/sh

# Configuration
INSTALL_PATH="/data"
BACKUP_DIR="$INSTALL_PATH/etc"
FIRMWARE_DOWNLOAD_PATH="/tmp/venus-data.tar.gz"
XML_URL="https://www.sunfunkits.com/Download/SFKDriverVersion.xml"

print_progress() {
    local message="$1"
    local spinner="|/-\\"
    local i=0
    echo -n "$message"
    while [ $i -lt 10 ]; do
        printf "\r%s %s" "$message" "${spinner:$((i % 4)):1}"
        sleep 0.5
        i=$((i + 1))
    done
    printf "\r%-*s\r" ${#message} ""
}

fetch_driver_info_xml() {
    print_progress "Fetching driver details from XML..."
    curl -s "$XML_URL" -o /tmp/driver_info.xml || { echo "\nError fetching XML file."; return 1; }
}

backup_config() {
    print_progress "Backing up existing configurations..."
    [ -f "$INSTALL_PATH/etc/dbus-serialbattery/config.default.ini" ] && \
        cp "$INSTALL_PATH/etc/dbus-serialbattery/config.default.ini" "$BACKUP_DIR/dbus-serialbattery_config.default.ini.backup"
    [ -f "$INSTALL_PATH/etc/dbus-serialbattery/SFKVirtualBattery/BatterySetupOptionValue.json" ] && \
        cp "$INSTALL_PATH/etc/dbus-serialbattery/SFKVirtualBattery/BatterySetupOptionValue.json" "$BACKUP_DIR/BatterySetupOptionValue.json.backup"
}

extract_firmware() {
    print_progress "Extracting firmware..."
    if [ ! -f "$FIRMWARE_DOWNLOAD_PATH" ]; then
        echo "\nFirmware file not found at $FIRMWARE_DOWNLOAD_PATH."
        return 1
    fi
    rm -rf "$INSTALL_PATH/etc/dbus-serialbattery"
    tar -xzf "$FIRMWARE_DOWNLOAD_PATH" -C "$INSTALL_PATH" || { echo "\nError extracting firmware."; return 1; }
    echo "\nFirmware extracted successfully."
}

set_permissions() {
    print_progress "Setting file permissions..."
    find "$INSTALL_PATH/dbus-serialbattery" -type f \( -name "*.sh" -o -name "*.py" -o -name "run" \) -exec chmod +x {} \;
    echo "\nPermissions set successfully."
}

run_optional_scripts() {
    for script in "reinstall-local.sh" "reinstalllocal.sh"; do
        if [ -f "$INSTALL_PATH/dbus-serialbattery/$script" ]; then
            echo "\nRunning $script..."
            sh "$INSTALL_PATH/dbus-serialbattery/$script"
        fi
    done
}

download_firmware() {
    echo "\nDownloading firmware..."
    curl -L "$1" -o "$FIRMWARE_DOWNLOAD_PATH" || { echo "\nError downloading firmware."; return 1; }
    echo "\nDownload complete."
}

install_firmware() {
    fetch_driver_info_xml || return 1
    echo "\nEnter firmware URL to download: "
    read -r firmware_url
    download_firmware "$firmware_url" || return 1
    backup_config
    extract_firmware || return 1
  #  set_permissions
  #  run_optional_scripts
    echo "\nInstallation completed."
}

install_firmware
