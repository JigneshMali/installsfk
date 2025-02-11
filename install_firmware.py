import os
import shutil
import tarfile
import requests
import stat
import subprocess
import xml.etree.ElementTree as ET
import re
import sys
import time

# Configuration
install_path = "/data"
backup_dir = os.path.join(install_path, "etc")
firmware_download_path = "/tmp/venus-data.tar.gz"
xml_url = "https://www.sunfunkits.com/Download/SFKDriverVersion.xml"


def print_progress(message, delay=0.5):
    """Simulates progress with a spinner effect."""
    spinner = ["|", "/", "-", "\\"]
    for _ in range(10):
        sys.stdout.write(f"\r{message} {spinner[_ % 4]}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\r" + " " * len(message) + "\r")  # Clear line


def fetch_driver_info_xml(url):
    """Fetch driver details from XML and return versions & links."""
    driver_info = {}
    driver_versions = []

    print_progress("Fetching driver details from XML...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"\nError fetching XML file: {e}")
        return {}, []

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as e:
        print(f"\nError parsing XML: {e}")
        return {}, []

    for driver in root.findall("DriverName"):
        try:
            text = driver.text
            if text and "|^|" in text:
                name, link = map(str.strip, text.split("|^|"))
                version, is_beta = extract_version(name)

                if version:
                    driver_info[version] = {"link": link, "name": name}
                    driver_versions.append(version)
        except Exception as e:
            print(f"\nError processing driver entry: {e}")

    return driver_info, driver_versions


def extract_version(name):
    """Extracts version number from the driver name."""
    version_match = re.search(r"v(\d+\.\d+)(\d*)\s*(Beta|beta)?", name)
    if version_match:
        major_minor = version_match.group(1)
        patch = version_match.group(2) if version_match.group(2) else ""
        is_beta = bool(version_match.group(3))
        return f"{major_minor}{patch}", is_beta
    return None, None


def backup_config():
    """Backup configuration files."""
    print_progress("Backing up existing configurations...")
    config_file = os.path.join(install_path, "etc", "dbus-serialbattery", "config.default.ini")
    setup_file = os.path.join(install_path, "etc", "dbus-serialbattery", "SFKVirtualBattery", "BatterySetupOptionValue.json")

    if os.path.isfile(config_file):
        shutil.copy(config_file, os.path.join(backup_dir, "dbus-serialbattery_config.default.ini.backup"))

    if os.path.isfile(setup_file):
        shutil.copy(setup_file, os.path.join(backup_dir, "BatterySetupOptionValue.json.backup"))


def extract_firmware():
    """Extract firmware to the correct location."""
    if not os.path.isfile(firmware_download_path):
        print(f"\nFirmware file not found at {firmware_download_path}.")
        return

    print_progress("Extracting firmware...")
    extracted_path = os.path.join(install_path, "etc", "dbus-serialbattery")

    if os.path.exists(extracted_path):
        shutil.rmtree(extracted_path)

    with tarfile.open(firmware_download_path, "r:gz") as tar:
        members = [member for member in tar.getmembers() if member.name.startswith("etc/dbus-serialbattery")]
        tar.extractall(path=install_path, members=members)

    print("\nFirmware extracted successfully.")


def set_permissions():
    """Set permissions for scripts."""
    print_progress("Setting file permissions...")
    for root, _, files in os.walk(os.path.join(install_path, "dbus-serialbattery")):
        for file in files:
            if file.endswith((".sh", ".py")) or file in ["run"]:
                filepath = os.path.join(root, file)
                os.chmod(filepath, os.stat(filepath).st_mode | stat.S_IEXEC)

    print("\nPermissions set successfully.")


def run_optional_scripts():
    """Execute optional install scripts if available."""
    print_progress("Checking for optional install scripts...")
    for script in ["reinstall-local.sh", "reinstalllocal.sh"]:
        script_path = os.path.join(install_path, "dbus-serialbattery", script)
        if os.path.isfile(script_path):
            print(f"\nRunning {script}...")
            subprocess.run(["bash", script_path], check=True)


def download_firmware(firmware_url):
    """Download firmware with progress indication."""
    print("\nDownloading firmware...")
    response = requests.get(firmware_url, stream=True)

    total_size = int(response.headers.get("content-length", 0))
    downloaded_size = 0

    with open(firmware_download_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
            downloaded_size += len(chunk)
            percentage = (downloaded_size / total_size) * 100 if total_size else 0
            sys.stdout.write(f"\rDownloading: [{int(percentage)//2 * '=':<50}] {percentage:.2f}%")
            sys.stdout.flush()

    print("\nDownload complete.")


def install_firmware():
    """Handles the full firmware installation process."""
    driver_info, driver_versions = fetch_driver_info_xml(xml_url)

    if not driver_info:
        print("No drivers found in XML.")
        return

    print("\nAvailable driver versions:")
    for idx, version in enumerate(driver_versions, start=1):
        print(f"  {idx}. {version} - {driver_info[version]['name']}")

    try:
        user_input = input("\nEnter the numbers of versions to install (comma-separated): ")
        selected_versions = [int(x) - 1 for x in user_input.split(",")]
    except ValueError:
        print("Invalid input. Exiting.")
        return

    for selected_version_idx in selected_versions:
        if selected_version_idx < len(driver_versions):
            version = driver_versions[selected_version_idx]
            firmware_url = driver_info[version]["link"]

            print(f"\nInstalling firmware version {version}...")
            download_firmware(firmware_url)
            backup_config()
            # extract_firmware()
            # set_permissions()
            # run_optional_scripts()
            print(f"\nInstallation of version {version} completed.")

    print("\nInstallation process finished.")
    reboot = input("Would you like to reboot now? (y/n): ").strip().lower()
    if reboot == "y":
        print("\nRebooting now...")
        os.system("reboot")


# Start the firmware installation process
install_firmware()
