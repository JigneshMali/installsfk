import os
import shutil
import tarfile
import requests
import stat
import subprocess
import CheckUserConfig
import CheckUserConfigJson
import re
import sys
import xml.etree.ElementTree as ET



# Configuration
firmware_url = "https://www.sunfunkits.com/Download/venusos1_67/venus-data.tar.gz"
download_path = "/tmp/venus-data.tar.gz"
install_path = "/data"
config_file = os.path.join(install_path, "dbus-serialbattery", "config.default.ini")
backup_file = f"{config_file}.backup"


# Global variables
driver_versions = []
driver_links = []
driver_texts = []
xml_url = "https://www.sunfunkits.com/Download/SFKDriverVersion.xml"


def extract_os_version(name):
    """Extracts the OS version from the driver name, handles possible beta versions."""
    os_match = re.search(r'Venus OS (\d+\.\d+)(\d*)\s*(Beta|beta)?', name)
    if os_match:
        os_version = os_match.group(1)  # Main OS version (e.g., '3.52')
        patch = os_match.group(2) if os_match.group(2) else ""  # Extra digits (e.g., '1' in '3.521')
        is_os_beta = bool(os_match.group(3))  # Check if it's a beta version

        os_version_string = f"{os_version}{patch}"  # Construct the OS version string
        return os_version_string, is_os_beta  # Return extracted OS version & beta flag
    return None, None  # If no OS version found


def extract_version(name):
    """Extracts the numerical version and detects if it's a beta version."""
    version_match = re.search(r'v(\d+\.\d+)(\d*)\s*(Beta|beta)?', name)

    if version_match:
        major_minor = version_match.group(1)  # Main version (e.g., '1.67')
        patch = version_match.group(2) if version_match.group(2) else ""  # Extra digits (e.g., '8' in '1.678')
        is_beta = bool(version_match.group(3))  # Check if it's a beta version

        version_string = f"{major_minor}{patch}"  # Construct the full number
        return version_string, is_beta  # Return extracted version & beta flag
    return None, None  # If no version found


def fetch_driver_info_xml(url, current_version):
    """Fetch driver details from XML, extract versions, and compare."""
    driver_info = {}
    versions = []
    os_versions = []  # List to store extracted OS versions
    driver_os_versions = []  # List to store both driver and OS versions together

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching XML file: {e}")
        return {}, 0, None, None, []

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return {}, 0, None, None, []

    for driver in root.findall('DriverName'):
        try:
            text = driver.text
            if text and "|^|" in text:
                name, link = map(str.strip, text.split("|^|"))

                # Extract version and beta flag for the firmware
                version, is_beta = extract_version(name)
                os_version, os_is_beta = extract_os_version(name)  # Extract the OS version

                if version:
                    driver_info[name] = {"link": link, "version": version, "is_beta": is_beta, "os_version": os_version, "os_is_beta": os_is_beta}
                    versions.append((version, is_beta))  # Store versions with beta flag
                    os_versions.append(os_version)  # Store extracted OS versions

                    # Add both version and OS version to driver_os_versions
                    driver_os_versions.append({
                        'driver_version': version,
                        'os_version': os_version,
                        'os_is_beta': os_is_beta
                    })

        except Exception as e:
            print(f"Error processing driver entry: {e}")

    if not versions:
        print("No valid driver versions found.")
        return driver_info, 0, None, None, []

    try:
        # Sort versions: prioritize non-beta over beta, then sort numerically
        sorted_versions = sorted(
            versions, key=lambda v: (list(map(int, v[0].split('.'))), not v[1]), reverse=True
        )

        latest_version, latest_is_beta = sorted_versions[0]

        # Compare latest version with the current version
        current_version_number, current_is_beta = extract_version(f"v{current_version}")

        is_newer_available = 0
        if current_version_number:
            if list(map(int, latest_version.split('.'))) > list(map(int, current_version_number.split('.'))):
                is_newer_available = 1

    except Exception as e:
        print(f"Error comparing versions: {e}")
        return driver_info, 0, None, None, []

    # Return the driver information, version comparison result, latest version, latest is beta flag, and driver OS versions
    return driver_info, is_newer_available, latest_version, latest_is_beta, driver_os_versions


def download_firmware(url, dest_file):
    """Download firmware from URL to a specified path."""
    print(f"Downloading firmware from {url}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(dest_file, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Firmware downloaded successfully to {dest_file}.")
    except requests.RequestException as e:
        print(f"Error downloading firmware: {e}")
        raise


def backup_config():
    """Backup existing configuration files, if they exist."""
    # Backup directory (target location for backups)
    backup_dir = os.path.join(install_path, "etc")
    os.makedirs(backup_dir, exist_ok=True)  # Ensure the backup directory exists

    # Source file paths (installation files to back up)
    config_default_file = os.path.join(install_path, "etc", "dbus-serialbattery", "config.default.ini")  # Source: config.default.ini
    battery_setup_file = os.path.join(install_path, "etc", "dbus-serialbattery", "SFKVirtualBattery", "BatterySetupOptionValue.json")  # Source: BatterySetupOptionValue.json

    # Backup file paths (target backup files)
    # Backup for config.default.ini -> /data/etc/dbus-serialbattery_config.default.ini.backup
    backup_default_file = os.path.join(backup_dir, "dbus-serialbattery_config.default.ini.backup")
    
    # Backup for BatterySetupOptionValue.json -> /data/etc/BatterySetupOptionValue.json.backup
    backup_battery_setup_file = os.path.join(backup_dir, "BatterySetupOptionValue.json.backup")

    # Back up config.default.ini
    if os.path.isfile(config_default_file):
        print(f"Backing up {config_default_file} to {backup_default_file}...")
        shutil.copy(config_default_file, backup_default_file)
        print(f"Backup created at {backup_default_file}.")

    # Back up BatterySetupOptionValue.json
    if os.path.isfile(battery_setup_file):
        print(f"Backing up {battery_setup_file} to {backup_battery_setup_file}...")
        shutil.copy(battery_setup_file, backup_battery_setup_file)
        print(f"Backup created at {backup_battery_setup_file}.")


def extract_firmware():
    """Extract the 'etc/dbus-serialbattery' directory from the firmware to the installation path."""
    if not os.path.isfile(download_path):
        print(f"Firmware file not found at {download_path}.")
        raise FileNotFoundError("Firmware file not found.")
    
    print("Extracting firmware...")
    target_subpath = "etc/dbus-serialbattery"
    extracted_path = os.path.join(install_path, "etc", "dbus-serialbattery")
    
    # Remove existing directory if it exists
    if os.path.exists(extracted_path):
        shutil.rmtree(extracted_path)
    
    with tarfile.open(download_path, "r:gz") as tar:
        # Extract only the required subpath
        members = [member for member in tar.getmembers() if member.name.startswith(target_subpath)]
        tar.extractall(path=install_path, members=members)
    
    # Ensure the extracted files are moved to the correct location
    temp_path = os.path.join(install_path, "etc", "dbus-serialbattery")
    if not os.path.exists(temp_path):
        print(f"Error: {target_subpath} not found in the archive.")
        raise FileNotFoundError(f"{target_subpath} not found in the archive.")
    
    print(f"Firmware extracted successfully to {extracted_path}.")


def restore_backup():
    """Synchronize the INI file with its backup if both exist."""
    ini_original_file = '/data/etc/dbus-serialbattery/config.default.ini'
    ini_backup_file = '/data/etc/dbus-serialbattery_config.default.ini.backup'
    
    json_original_file = '/data/etc/dbus-serialbattery/SFKVirtualBattery/BatterySetupOptionValue.json'
    json_backup_file = '/data/etc/BatterySetupOptionValue.json.backup'
    # Log the action for JSON setting
    
    # Check existence of both JSON original and backup files
    if os.path.exists(json_original_file) and os.path.exists(json_backup_file):
        CheckUserConfigJson.sync_backup_json_file(json_original_file, json_backup_file)
    
    # Check existence of both INI original and backup files
    if os.path.exists(ini_original_file) and os.path.exists(ini_backup_file):
        print("Synchronizing INI file with check_VirtualBatteryservice()")
       
        print(f"Synchronizing INI file: {ini_original_file}")
        CheckUserConfig.sync_backup_file(ini_original_file, ini_backup_file)
    else:
        print(f"Error: INI original or backup file does not exist: {ini_original_file} or {ini_backup_file}")


def set_permissions():
    """Set executable permissions for specific files."""
    print("Setting permissions...")
    service_path = os.path.join(install_path, "dbus-serialbattery", "service")
    for root, _, files in os.walk(os.path.join(install_path, "dbus-serialbattery")):
        for file in files:
            if file.endswith((".sh", ".py")) or file in ["run"]:
                filepath = os.path.join(root, file)
                os.chmod(filepath, os.stat(filepath).st_mode | stat.S_IEXEC)
    print("Permissions set successfully.")


def run_optional_scripts():
    """Run optional install scripts if they exist."""
    for script in ["reinstall-local.sh", "reinstalllocal.sh"]:
        script_path = os.path.join(install_path, "dbus-serialbattery", script)
        if os.path.isfile(script_path):
            print(f"Running {script}...")
            subprocess.run(["bash", script_path], check=True)


# def install_firmware():
#     """Perform the entire firmware installation process."""
#     download_firmware(firmware_url, download_path)
#     backup_config()
#     extract_firmware()
#     set_permissions()
#     run_optional_scripts()
#     print("Installation complete. Please restart the device to apply changes.")
