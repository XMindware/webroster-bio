# fingerprint_manager.py (patched version)
import time
import threading
import serial
import adafruit_fingerprint
import requests
import re
import socket
import os
import subprocess
import shutil
import psutil
import uuid
import pygame
from datetime import datetime, timedelta
import json
from db import LocalDB
import logging

with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
    CONFIG = json.load(f)

def get_device_sn(prefix="WBIO"):
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    serial = line.strip().split(":")[1].strip()
                    return f"{prefix}{serial[-6:].upper()}"
    except Exception as e:
        return f"{prefix}000000"    

MAX_FINGERPRINTS_PER_USER = CONFIG.get("MAX_FINGERPRINTS_PER_USER", 1)
SN = get_device_sn(CONFIG.get("SN_PREFIX", "WBIO"))
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
        uart = serial.Serial("/dev/ttyUSB0", baudrate=57600, timeout=1)
        self.finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
        self.update_callback = update_callback
        self.pause_listener = False
        self.allow_listener = True
        self._listener_running = False
        self._listener_thread = None
        self.db = LocalDB()

    def play_sound(self, filename):
        try:            
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            print(f"🔊 Playing sound: {filename}")
        except Exception as e:
            print(f"⚠️ Failed to play sound {filename}: {e}")


    def start_fingerprint_listener(self):
        if self._listener_thread and self._listener_thread.is_alive():
            logging.info("🟢 Fingerprint listener already running.")
            return

        self._listener_running = True

        def listen():
            f = self.finger
            self.update_status("Listo para escanear huellas...")

            while self._listener_running:
                if self.pause_listener or not self.allow_listener:
                    time.sleep(0.5)
                    continue

                logging.debug("Esperando huella en pantalla principal...")
                if f.get_image() == adafruit_fingerprint.OK:
                    if f.image_2_tz(1) != adafruit_fingerprint.OK:
                        self.update_status("❌ Intente de nuevo")
                        continue

                    if f.finger_search() != adafruit_fingerprint.OK:
                        self.update_status("❌ Intente de nuevo")
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
                            self.play_sound("audios/checada_correcta.wav")
                            self.update_callback(f"Bienvenido {name}!\n⏰ {now_display}")
                            if hasattr(self, "refresh_history"):
                                self.refresh_history()
                    else:
                        self.update_status("⚠️ La huella no corresponde a un empleado")

                    time.sleep(3)

                time.sleep(0.2)

        self._listener_thread = threading.Thread(target=listen, daemon=True)
        self._listener_thread.start()
        logging.info("🔄 Fingerprint listener thread started.")

    def stop_fingerprint_listener(self):
        self._listener_running = False
        if hasattr(self, "_listener_thread") and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2)
            logging.info("🛑 Fingerprint listener thread fully joined.")
        else:
            logging.info("🛑 Fingerprint listener was not active.")

    def update_status(self, message):
        if self.update_callback:
            self.update_callback(message)

    def delete_fingerprints_for_user(self, idagente):
        try:
            finger_ids = self.db.get_finger_ids_by_user(idagente)
            for fid in finger_ids:
                result = self.finger.delete_model(fid)
                if result == adafruit_fingerprint.OK:
                    logging.info(f"🗑️ Deleted fingerprint ID {fid} from sensor for user {idagente}")
                elif result == adafruit_fingerprint.NOTFOUND:
                    logging.warning(f"⚠️ Fingerprint ID {fid} not found on sensor")
                else:
                    logging.error(f"❌ Failed to delete fingerprint ID {fid} from sensor, result: {result}")

            self.db.remove_fingerprints_by_user(idagente)
            logging.info(f"🗂️ Deleted fingerprint DB records for user {idagente}")
        except Exception as e:
            logging.exception(f"💥 Error deleting fingerprints for user {idagente}")
    
    def enroll_new_fingerprint_for_user(self, idagente, name, on_update=None, on_status=None):
        logging.info(f"📥 Starting enrollment for {idagente} / {name}")

        def enroll():
            self.pause_listener = True
            try:
                count = self.db.count_fingerprints_by_user(idagente)
                if count >= MAX_FINGERPRINTS_PER_USER:
                    if on_update:
                        on_update("⚠️ El usuario ya tiene el máximo de huellas capturadas.")
                    return

                finger_id = self.db.get_next_available_finger_id()
                if on_update:
                    on_update(f"Capturando huella para usuario...")

                f = self.finger

                # First scan
                while f.get_image() != adafruit_fingerprint.OK:
                    time.sleep(0.1)
                if f.image_2_tz(1) != adafruit_fingerprint.OK:
                    if on_update:
                        on_update("No se pudo leer la huella, reintente")
                    return

                if on_update:
                    on_update("Retire el dedo...")
                while f.get_image() != adafruit_fingerprint.NOFINGER:
                    time.sleep(0.1)

                if on_update:
                    on_update("Coloque el dedo nuevamente...")
                while f.get_image() != adafruit_fingerprint.OK:
                    time.sleep(0.1)
                if f.image_2_tz(2) != adafruit_fingerprint.OK:
                    if on_update:
                        on_update("No se pudo leer la huella, reintente")
                    return

                if f.create_model() != adafruit_fingerprint.OK:
                    if on_update:
                        on_update("No se pudo crear la huella, reintente")
                    return

                if f.store_model(finger_id) == adafruit_fingerprint.OK:
                    self.db.add_fingerprint(idagente, finger_id)
                    if on_update:
                        on_update(f"✅ Se registró la huella para el usuario")
                else:
                    if on_update:
                        on_update("Algo pasó, no se pudo guardar la huella, reintente")
            except Exception as e:
                logging.exception("Error en la captura de huella")
                if on_update:
                    on_update(f"Error: {str(e)}")
            finally:
                self.pause_listener = False
                logging.info("✅ Enrollment flow complete.")

        threading.Thread(target=enroll, daemon=True).start()

    def send_handshake(self):
        adms_url = f"{ADMS_URL}/iclock/cdata"
        try:
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
    
    def upload_latest_log():
        adms_url = f"{ADMS_URL}/iclock/upload-log"  # adjust if needed

        try:
            # Ensure log folder exists
            os.makedirs("logs", exist_ok=True)

            today = datetime.now().strftime("%Y-%m-%d")
            original_log = "logs/webroster.log"
            renamed_log = f"logs/webroster-{today}.log"

            # Rotate the log file: rename current and create a new one
            if os.path.exists(original_log):
                shutil.copy2(original_log, renamed_log)  # make a copy
                open(original_log, 'w').close()  # clear the original log

            with open(renamed_log, "rb") as f:
                headers = {
                    "User-Agent": "Mindware_bioterminal",
                    "Accept": "*/*",
                    "Connection": "close"
                }

                logging.info(f"📤 Uploading log file: {renamed_log} to {adms_url}")
                response = requests.post(
                    adms_url,
                    files={"file": (os.path.basename(renamed_log), f)},
                    data={"sn": get_device_sn()},
                    headers=headers
                )

            if response.status_code == 200:
                logging.info("✅ Log file uploaded successfully.")
                # Optional: delete after upload
                os.remove(renamed_log)
            else:
                logging.warning(f"⚠️ Upload failed: {response.status_code} - {response.text}")

        except Exception as e:
            logging.exception("💥 Exception during log upload")

            
    def poll_getrequest(self):

        def get_cpu_temp():
            try:
                output = os.popen("vcgencmd measure_temp").readline()
                return float(output.replace("temp=", "").replace("'C\n", ""))
            except:
                return -1

        def get_uptime():
            try:
                output = os.popen("uptime -p").readline()
                return output.strip()
            except:
                return "unknown"

        def get_disk_usage():
            total, used, free = shutil.disk_usage("/")
            return f"{int(used / total * 100)}%"

        def get_memory_usage():
            mem = psutil.virtual_memory()
            return f"{int(mem.percent)}%"

        def get_git_version(path="/home/mindware/webroster-bio/webroster-bio-ui"):
            try:
                return subprocess.check_output(["git", "-C", path, "rev-parse", "--short", "HEAD"]).decode().strip()
            except:
                return "unknown"
            
        adms_url = f"{ADMS_URL}/iclock/getrequest"
        try:
            now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)
            current_time = now.strftime("%Y-%m-%d %H:%M:%S")
            params = {
                "SN": SN,
                "options": "all",
                "language": "101",
                "pushver": "3.0.0",
                "PushOptionsFlag": "1",
                "ip": socket.gethostbyname(socket.gethostname()),
                "current_time": current_time,
                "temp": get_cpu_temp(),
                "uptime": get_uptime(),
                "disk": get_disk_usage(),
                "mem": get_memory_usage(),
                "gitver": get_git_version()
            }
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
                        logging.debug(f"📩 Command line: {line}")
                        if "USERINFO" in line:
                            self._parse_userinfo_command(line)
                        elif "CONTROL DEVICE 03000000" in line:
                            logging.warning("🌀 Restart command received from ADMS. Rebooting now.")
                            self._execute_restart()
                else:
                    logging.info("🕊️ No pending commands")
            else:
                logging.warning(f"⚠️ getrequest failed: {response.status_code} - {body}")
        except Exception as e:
            logging.exception("💥 Error during getrequest polling")
    
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
                logging.info(f"🛰️ POSTing to: {adms_url}")
                logging.debug(f"📦 Payload:\n{payload}")

                response = requests.post(adms_url, data=payload, headers=headers)
                response_text = response.text.strip()

                logging.info(f"✅ Response Code: {response.status_code}")
                logging.debug(f"📩 Response Body:\n{response_text}")

                if response.status_code == 200:
                    for log in logs:
                        self.db.mark_event_synced(log[0])
                    self.update_status(f"✅ Synced {len(logs)} events.")
                    
                    # Handle remote commands if returned
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

    def _execute_restart(self):
        try:
            logging.info("🔁 Rebooting device...")
            subprocess.Popen(['sudo', '/sbin/reboot'])
        except Exception as e:
            logging.exception("💥 Failed to reboot the device.")