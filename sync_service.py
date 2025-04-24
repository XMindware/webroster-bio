import time
import logging
import socket
import os
import subprocess
from fingerprint_manager import FingerprintManager

# Setup logging
logging.basicConfig(
    filename='bioterminal-sync.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Dummy update callback
def log_status(message):
    logging.info(message)

def is_online():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

def run_git_update():
    try:
        logging.info("🔍 Checking for firmware updates...")
        result = subprocess.run(
            ["git", "-C", "/home/mindware/webroster-bio", "pull"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if "Already up to date" in result.stdout:
            logging.info("✅ Already up to date.")
            return False

        logging.info("✅ Update pulled:\n%s", result.stdout)
        return True
    except Exception as e:
        logging.warning(f"❌ Update failed: {e}")
        return False

# Constants
INTERVAL_SECONDS = 20  # 20 seconds

def main():
    logging.info("🔄 Sync service started.")
    manager = FingerprintManager(update_callback=log_status)
    manager.send_handshake()

    last_update_check = 0
    update_interval = 60 * 60  # 1 hour

    while True:
        try:
            if is_online():
                manager.poll_getrequest()
                manager.push_unsynced_logs()

                # 🔁 Check for firmware update
                current_time = time.time()
                if current_time - last_update_check > update_interval:
                    last_update_check = current_time
                    if 0    : #run_git_update():
                        logging.info("♻️ Restarting sync service after update...")
                        os.system("sudo systemctl restart webroster-bio-ui.service")
                        os.system("sudo systemctl restart webroster-sync.service")
                        return  # Exit this instance after triggering restart

            else:
                logging.warning("🌐 No internet connection. Retrying in 20 seconds.")

        except Exception as e:
            logging.exception("💥 Sync loop error")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
