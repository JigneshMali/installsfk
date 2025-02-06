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
install_path = "/data"
backup_dir = os.path.join(install_path, "etc")
firmware_download_path = "/tmp/venus-data.tar.gz"

# XML URL to fetch driver versions
xml_url = "https://www.sunfunkits.com/Download/SFKDriverVersion.xml"

# Function to fetch driver info from XML
def fetch_driver_info_xml(url):
    """Fetch driver details from XML, extract versions, and present options."""
    driver_info = {}
    driver_versions = []

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching XML file: {e}")
        return {}

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return {}

    for driver in root.findall('DriverName'):
        try:
            text = driver.text
            if text and "|^|" in text:
                name, link = map(str.strip, text.split("|^|"))
                version, is_beta = extract_version(name)

                if version:
                    driver_info[version] = {"link": link, "name": name}

                    # Append the version to the list of driver versions
                    driver_versions.append(version)

        except Exception as e:
            print(f"Error processing driver entry: {e}")

    return driver_info, driver_versions


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


def backup_config():
    """Backup existing configuration files, if they exist."""
    config_default_file = os.path.join(install_path, "etc", "dbus-serialbattery", "config.default.ini")
    battery_setup_file = os.path.join(install_path, "etc", "dbus-serialbattery", "SFKVirtualBattery", "BatterySetupOptionValue.json")

    # Backup paths
    backup_default_file = os.path.join(backup_dir, "dbus-serialbattery_config.default.ini.backup")
    backup_battery_setup_file = os.path.join(backup_dir, "BatterySetupOptionValue.json.backup")

    # Back up config.default.ini
    if os.path.isfile(config_default_file):
        shutil.copy(config_default_file, backup_default_file)

    # Back up BatterySetupOptionValue.json
    if os.path.isfile(battery_setup_file):
        shutil.copy(battery_setup_file, backup_battery_setup_file)


def extract_firmware():
    """Extract the 'etc/dbus-serialbattery' directory from the firmware to the installation path."""
    if not os.path.isfile(firmware_download_path):
        print(f"Firmware file not found at {firmware_download_path}.")
        raise FileNotFoundError("Firmware file not found.")
    
    print("Extracting firmware...")
    target_subpath = "etc/dbus-serialbattery"
    extracted_path = os.path.join(install_path, "etc", "dbus-serialbattery")
    
    if os.path.exists(extracted_path):
        shutil.rmtree(extracted_path)

    with tarfile.open(firmware_download_path, "r:gz") as tar:
        members = [member for member in tar.getmembers() if member.name.startswith(target_subpath)]
        tar.extractall(path=install_path, members=members)

    print(f"Firmware extracted successfully to {extracted_path}.")


def set_permissions():
    """Set executable permissions for specific files."""
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
            subprocess.run(["bash", script_path], check=True)


def install_firmware():
    """Complete firmware installation process based on user input."""
    driver_info, driver_versions = fetch_driver_info_xml(xml_url)

    if not driver_info:
        print("No drivers found in XML.")
        return

    # Present available driver versions to the user
    print("Available driver versions:")
    for idx, version in enumerate(driver_versions, start=1):
        print(f"{idx}. {version} - {driver_info[version]['name']}")

    try:
        user_input = input(f"Please select the version to install (comma-separated numbers): ")
        selected_versions = [int(x) - 1 for x in user_input.split(',')]  # Adjust for 0-based index
    except ValueError:
        print("Invalid input.")
        return

    # Download the selected firmware version(s)
    for selected_version_idx in selected_versions:
        if selected_version_idx < len(driver_versions):
            version = driver_versions[selected_version_idx]
            firmware_url = driver_info[version]["link"]
            print(f"Downloading firmware version {version} from {firmware_url}...")
            try:
                response = requests.get(firmware_url, stream=True)
                with open(firmware_download_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                print(f"Firmware version {version} downloaded successfully.")
            except requests.RequestException as e:
                print(f"Error downloading firmware: {e}")
                return

            # Backup configuration before proceeding
            backup_config()
            extract_firmware()
            set_permissions()
            run_optional_scripts()
            print(f"Installation of firmware version {version} complete.")

    print("Installation complete. Please reboot the device to apply changes.")


# To start the installation process
install_firmware()
