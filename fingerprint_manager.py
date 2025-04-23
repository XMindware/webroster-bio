# fingerprint_manager.py
import time
import threading
import serial
import adafruit_fingerprint
import requests
import re
import socket
from datetime import datetime, timedelta
import json
import os
from db import LocalDB

import logging

with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
    CONFIG = json.load(f)

MAX_FINGERPRINTS_PER_USER = CONFIG.get("MAX_FINGERPRINTS_PER_USER", 1)
SN = CONFIG["DEVICE_SN"]
ADMS_URL = CONFIG["ADMS_URL"]
TIMEZONE_OFFSET = CONFIG.get("TIMEZONE_OFFSET", -6)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bioterminal.log"),
        logging.StreamHandler()
    ]
)

class FingerprintManager:
    def __init__(self, update_callback=None):
        uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
        self.finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
        self.update_callback = update_callback
        self.db = LocalDB()  # Initialize local DB
        self.allow_listener = True

        

    def start_fingerprint_listener(self):
        def listen():
            f = self.finger
            self.update_status("Listo para escanear huellas...")

            while True:
                if not self.allow_listener:
                    time.sleep(0.2)
                    continue
                if f.get_image() == adafruit_fingerprint.OK:
                    if f.image_2_tz(1) != adafruit_fingerprint.OK:
                        self.update_status("❌ Fingerprint conversion failed")
                        continue

                    if f.finger_search() != adafruit_fingerprint.OK:
                        self.update_status("❌ No match")
                        time.sleep(2)
                        continue

                    matched_fid = f.finger_id
                    agent_id = self.db.get_agent_by_finger_id(matched_fid)

                    if agent_id:                        
                        user = self.db.conn.execute("SELECT name FROM users WHERE idagente = ?", (agent_id,)).fetchone()
                        name = user[0] if user else f"User {agent_id}"
                        now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)
                        timestamp = now.isoformat()
                        self.db.add_event(agent_id, type="checkin", timestamp=timestamp)  
                        now_display = now.strftime("%d/%m/%Y %H:%M")
                        self.update_status(f"✅ Checada registrada, {name}!\n⏰ {now_display}")

                        if self.update_callback:
                            self.update_callback(f"Bienvenido {name}!\n⏰ {now_display}")
                            if hasattr(self, "refresh_history"):
                                self.refresh_history()
                    else:
                        self.update_status(f"⚠️ Finger ID {matched_fid} not linked to any user")

                    time.sleep(3)  # Pause before restarting loop

                time.sleep(0.2)  # Polling interval

        threading.Thread(target=listen, daemon=True).start()


    def update_status(self, message):
        if self.update_callback:
            self.update_callback(message)

    def enroll_new_fingerprint_for_user(self, idagente):
        def enroll():
            self.allow_listener = False
            try:
                # 💡 Check if the user already has max fingerprints
                count = self.db.count_fingerprints_by_user(idagente)
                print (f"User {idagente} has {count} fingerprints")

                if count >= MAX_FINGERPRINTS_PER_USER:
                    self.update_status(f"⚠️ User {idagente} already has {count} fingerprints (max allowed).")
                    return
                finger_id = self.db.get_next_available_finger_id()
                self.update_status(f"🖐️ Enrolling fingerprint at ID {finger_id} for user {idagente}...")

                f = self.finger
                while f.get_image() != adafruit_fingerprint.OK:
                    time.sleep(0.1)
                if f.image_2_tz(1) != adafruit_fingerprint.OK:
                    self.update_status("❌ First scan failed")
                    return

                self.update_status("👉 Remove finger...")
                while f.get_image() != adafruit_fingerprint.NOFINGER:
                    time.sleep(0.1)

                self.update_status("🖐️ Place same finger again...")
                while f.get_image() != adafruit_fingerprint.OK:
                    time.sleep(0.1)
                if f.image_2_tz(2) != adafruit_fingerprint.OK:
                    self.update_status("❌ Second scan failed")
                    return

                if f.create_model() != adafruit_fingerprint.OK:
                    self.update_status("❌ Model creation failed")
                    return

                if f.store_model(finger_id) == adafruit_fingerprint.OK:
                    self.db.add_fingerprint(idagente, finger_id)
                    self.update_status(f"✅ Finger enrolled at ID {finger_id} for user {idagente}")
                else:
                    self.update_status("❌ Failed to store fingerprint")
            finally:
                self.allow_listener = True

        threading.Thread(target=enroll, daemon=True).start()

    def identify_fingerprint(self):
        def identify():
            f = self.finger
            self.update_status("🧤 Waiting for finger...")

            while f.get_image() != adafruit_fingerprint.OK:
                time.sleep(0.1)
            if f.image_2_tz(1) != adafruit_fingerprint.OK:
                self.update_status("❌ Failed to convert image.")
                return
            if f.finger_search() != adafruit_fingerprint.OK:
                self.update_status("❌ No match.")
                return

            self.update_status(f"✅ Match! ID: {f.finger_id}")

        threading.Thread(target=identify, daemon=True).start()

    def push_unsynced_logs(self):
        def push():
            adms_url = f"{ADMS_URL}/iclock/cdata?SN={SN}&table=ATTLOG"
            logs = self.db.get_unsynced_attlogs()
            if not logs:
                self.update_status("☁️ No new events to push.")
                return

            lines = ["ATTLOG"]
            for log in logs:
                _, user_id, timestamp = log
                lines.append(f"{user_id}\t{timestamp}\t0\t0\t0")

            payload = "\n".join(lines)
            headers = {
                "User-Agent": "Mindware_bioterminal",
                "Content-Type": "text/plain",
                "Accept": "*/*",
                "Connection": "close"
            }

            try:
                print("🛰️ POSTing to:", adms_url)
                print("🧾 Headers:", headers)
                print("📦 Payload:\n", payload)

                response = requests.post(adms_url, data=payload, headers=headers)
                response_text = response.text.strip()
                print("✅ Response Code:", response.status_code)
                print("📩 Response Body:\n", response_text)

                if response.status_code == 200:
                    # Mark events as synced
                    for log in logs:
                        self.db.mark_event_synced(log[0])

                    self.update_status(f"✅ Synced {len(logs)} events.")

                    # Process any commands in response
                    if response_text.startswith("C:"):
                        for line in response_text.splitlines():
                            if "USERINFO" in line:
                                self._parse_userinfo_command(line)
                else:
                    self.update_status(f"❌ Push failed: {response.status_code} - {response.text}")

            except Exception as e:
                self.update_status("📴 Offline: sync failed")
                logging.warning(f"Sync failed due to: {e}")

        threading.Thread(target=push, daemon=True).start()


    def _parse_userinfo_command(self, cmd):
        try:
            if "USERINFO" not in cmd:
                logging.warning("Ignored non-USERINFO command: %s", cmd)
                return

            _, _, payload = cmd.partition("USERINFO ")

            fields = {}
            for part in payload.split("\t"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    fields[key.strip()] = value.strip()

            idagente = int(fields.get("PIN", 0))
            name = fields.get("Name", "Unknown")

            if not idagente or not name:
                logging.warning("Missing PIN or Name in USERINFO: %s", cmd)
                return

            # Customize as needed
            idempresa = 2
            idoficina = 4

            self.db.add_user(idempresa, idoficina, idagente, name)
            self.update_status(f"👤 Synced user {name} (ID {idagente})")

        except Exception as e:
            logging.exception("Error parsing USERINFO command")



    def send_handshake(self):
        adms_url = f"{ADMS_URL}/iclock/cdata"
        try:
            # Optional: add device metadata
            ip = socket.gethostbyname(socket.gethostname())
            params = {
                "SN": SN,
                "options": "all",
                "language": "101",
                "pushver": "3.0.0",
                "PushOptionsFlag": "1"
            }

            headers = {
                "User-Agent": "Mindware_bioterminal",
                "Accept": "*/*",
                "Connection": "close"
            }

            r = requests.get(adms_url, headers=headers, params=params)
            response = r.text.strip()

            if r.status_code == 200:
                logging.info(f"🤝 Handshake successful — Response: {response}")
            else:
                logging.warning(f"⚠️ Handshake failed: {r.status_code} - {response}")

        except Exception as e:
            logging.exception("💥 Handshake error")

    def poll_getrequest(self):
        adms_url = f"{ADMS_URL}/iclock/getrequest"
        try:
            ip = socket.gethostbyname(socket.gethostname())
            now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)
            current_time = now.strftime("%Y-%m-%d %H:%M:%S")

            # Metadata parameters to send with the GET request
            params = {
                "SN": SN,
                "options": "all",
                "language": "101",
                "pushver": "3.0.0",
                "PushOptionsFlag": "1",
                "ip": ip,
                "current_time": current_time
            }

            # Final URL with query string
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{adms_url}?{query_string}"

            headers = {
                "User-Agent": "Mindware_bioterminal",
                "Accept": "*/*",
                "Connection": "close",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            logging.info(f"🔄 Polling getrequest: {url}")

            response = requests.get(url, headers=headers)
            body = response.text.strip()

            if response.status_code == 200:
                if body.startswith("C:"):
                    logging.info("📩 Received commands from getrequest")
                    for line in body.splitlines():
                        if "USERINFO" in line:
                            self._parse_userinfo_command(line)
                        # TODO: handle SETTIME, DELETE, etc.
                else:
                    logging.info("🕊️ No pending commands")
            else:
                logging.warning(f"⚠️ getrequest failed: {response.status_code} - {body}")

        except Exception as e:
            logging.exception("💥 Error during getrequest polling")


    def delete_fingerprints_for_user(self, idagente):
        try:
            finger_ids = self.db.get_finger_ids_by_user(idagente)

            if not finger_ids:
                self.update_status(f"⚠️ No fingerprints found for user {idagente}")
                return

            for fid in finger_ids:
                result = self.finger.delete_model(fid)
                if result == adafruit_fingerprint.OK:
                    logging.info(f"Deleted fingerprint ID {fid} from sensor")
                else:
                    logging.warning(f"Failed to delete fingerprint ID {fid} (result={result})")

            self.db.remove_fingerprints_by_user(idagente)
            self.update_status(f"🗑️ Deleted {len(finger_ids)} fingerprint(s) for user {idagente}")

        except Exception as e:
            logging.exception("Error deleting fingerprints for user")
            self.update_status(f"💥 Error deleting fingerprints")