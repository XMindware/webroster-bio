import time
import logging
import socket
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

# Constants
SN = "BIOPI0001"
ADMS_URL = "http://192.168.5.164"
INTERVAL_SECONDS = 20  # 20 seconds

def main():
    logging.info("🔄 Sync service started.")
    manager = FingerprintManager(update_callback=log_status)
    manager.send_handshake()
    
    while True:
        try:
            if is_online():
                manager.poll_getrequest()
                manager.push_unsynced_logs()
            else:
                logging.warning("🌐 No internet connection. Retrying in 20 seconds.")
        except Exception as e:
            logging.exception("💥 Sync loop error")

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
