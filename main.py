import os
import sys
import time
import json
import uuid
import psutil
import shutil
import signal
import socket
import logging
import threading
import subprocess
import pygame
import glob
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from tkinter import messagebox
import tkinter as tk
from PIL import Image, ImageTk
from fingerprint_manager import FingerprintManager

def graceful_exit(signum, frame):
    print("🛑 Caught signal, exiting...")
    try:
        root.destroy()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

# Create logs folder
os.makedirs("logs", exist_ok=True)

log_path = "logs/webroster.log"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Rotating file handler: 1 MB max, 5 backups
file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# Optional: also log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
    CONFIG = json.load(f)

def get_device_sn(prefix="WBIO"):
    mac = uuid.getnode()
    mac_hex = f"{mac:012X}"[-6:]  # get last 6 characters (uppercase)
    return f"{prefix}{mac_hex}"
def get_cpu_temp():
    try:
        output = os.popen("vcgencmd measure_temp").readline()
        temp_str = output.replace("temp=", "").replace("'C\n", "")
        return f"{float(temp_str):.1f}"
    except:
        return "?"

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

def get_git_version(path="/home/mindware/webroster-bio"):
    try:
        return subprocess.check_output(["git", "-C", path, "rev-parse", "--short", "HEAD"]).decode().strip()
    except:
        return "unknown"
    
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "unknown"

SN=get_device_sn()

TIMEZONE_OFFSET = CONFIG.get("TIMEZONE_OFFSET", -6)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bioterminal.log"),
        logging.StreamHandler()
    ]
)

class AttendanceApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Webroster Bio")
        self.root.attributes("-fullscreen", True)
        logging.info("Starting AttendanceApp")
        logging.info(f"Device SN: {SN}")
        self.idle_timeout_seconds = 120  # 2 minutes
        self._last_activity = time.time()
        self._screensaver_active = False
        self._screensaver_disabled = False
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

        self.child_windows = []

        self.root.bind("<Button>", self.reset_idle_timer)
        self.root.bind("<Key>", self.reset_idle_timer)

        self.fingerprint = FingerprintManager(update_callback=self.update_status)
        self.fingerprint.refresh_history = self.update_attendance_history

        self.status_label = tk.Label(root, text="Touch to begin", font=("Helvetica", 24))
        self.status_label.place(relx=0.5, rely=0.25, anchor="center")

        self.sync_status_icon = tk.Label(self.root, text="Sync", font=("Arial", 18), bg="white")
        self.sync_status_icon.place(x=5, y=5)
        self.update_sync_status_icon()

        self.history_frame = tk.Frame(self.root, bg="black")
        self.history_frame.pack(pady=(10, 0))

        self.history_labels = []  # Will hold Label widgets
        self.max_history = 2      # Number of events to show

        self.fingerprint.start_fingerprint_listener()

        self.main_clock_label = tk.Label(
            self.root,
            text="00:00:00",
            font=("Arial", 38),
            fg="gray25",
        )
        self.main_clock_label.place(relx=0.5, rely=0.8, anchor="center")
        self._update_main_clock()

        logo_path = os.path.join(os.path.dirname(__file__), "logo500px.png")
        logo_img = Image.open(logo_path)
        logo_img = logo_img.resize((120, 120), Image.Resampling.LANCZOS)
        self.logo_photo = ImageTk.PhotoImage(logo_img)

        self.logo_label = tk.Label(self.root, image=self.logo_photo, bd=0)
        self.logo_label.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)  # bottom-right corner

        admin_button = tk.Button(root, text="⚙️ Admin", font=("Arial", 14), command=self.on_admin)
        admin_button.place(x=10, y=root.winfo_screenheight() - 60)  # 10px from left, near bottom

        self.history_box = tk.Frame(self.root, bg="white", bd=2, relief="ridge")
        self.history_box.place(x=20, anchor="sw", rely=1.0, y=-100)

        #TODO: quitar boton
        if CONFIG.get("debug", False):
            tk.Button(root, text="Exit", font=("Arial", 12), command=root.quit).place(x=400, y=10)

        self.root.after(1000, self.check_idle_timeout)

    def play_sound(self, filename):
        try:
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"⚠️ Failed to play sound {filename}: {e}")


    def _update_main_clock(self):
        now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)
        self.main_clock_label.config(text=now.strftime("%H:%M:%S"))
        self.root.after(1000, self._update_main_clock)

    def is_sync_service_running(self):
        for proc in psutil.process_iter(attrs=["cmdline"]):
            try:
                if any("sync_service.py" in part for part in proc.info['cmdline']):
                    return True
            except Exception:
                continue
        return False
    
    def update_sync_status_icon(self):
        running = self.is_sync_service_running()
        self.sync_status_icon.config(text="Sync" if running else "Offline!", fg="green" if running else "red")
        self.root.after(10000, self.update_sync_status_icon)  # Check every 10 seconds
    
    def check_idle_timeout(self):
        if not self._screensaver_active and (time.time() - self._last_activity > self.idle_timeout_seconds):
            if self._screensaver_disabled:
                logging.info("Screensaver disabled, not showing")
                return
            logging.info("Idle timeout reached, showing screensaver")         
            self.show_screensaver()

        self.root.after(1000, self.check_idle_timeout)  # Loop again every second

    def reset_idle_timer(self, event=None):
        self._last_activity = time.time()
        if self._screensaver_active:
            self.hide_screensaver()
    

    def show_screensaver(self):
        if self._screensaver_disabled:
            logging.info("Screensaver disabled")
            return
        logging.info("Showing screensaver")

        for win in list(self.child_windows):  # make a copy
            try:
                win.grab_release()
                win.destroy()
            except:
                pass
        self.child_windows.clear()
        
        if not hasattr(self, 'screensaver'):
            self.screensaver = tk.Toplevel(self.root)
            self.screensaver.attributes('-fullscreen', True)
            self.screensaver.attributes('-topmost', True)
            self.screensaver.overrideredirect(True)
            self.screensaver.configure(bg="black")
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            self.screensaver.geometry(f"{screen_w}x{screen_h}+0+0")
            logging.info(f"Screensaver geometry: {screen_w}x{screen_h}+0+0")
            
            # Load images from folder
            photo_folder = os.path.join(os.path.dirname(__file__), "screensaver_photos")
            image_paths = sorted(glob.glob(os.path.join(photo_folder, "*.jpg")) + glob.glob(os.path.join(photo_folder, "*.png")))
            logging.info(f"Found {len(image_paths)} images in {photo_folder}")
            self.slideshow_images = []
            for path in image_paths:
                img = Image.open(path)
                img = img.resize((480, 320), Image.Resampling.LANCZOS)
                self.slideshow_images.append(ImageTk.PhotoImage(img))

            if not self.slideshow_images:
                fallback = tk.Label(self.screensaver, text="🖼️ No images found", fg="white", bg="black", font=("Arial", 24))
                fallback.pack(expand=True)
                return

            
            # Create the image display label
            self.slideshow_index = 0
            if hasattr(self, 'slideshow_label'):
                self.slideshow_label.destroy()

            self.slideshow_label = tk.Label(self.screensaver, image=self.slideshow_images[0], bg="black")
            self.slideshow_label.place(x=0, y=0, relwidth=1.0, relheight=1.0)           

            # Main message
            label = tk.Label(
                self.screensaver,
                text="Webroster Bio",
                fg="white",
                bg="black",
                font=("Arial", 32)
            )
            label.pack(expand=True)

            # ⏰ Clock label in bottom-right
            self.clock_label = tk.Label(self.screensaver, fg="white", bg="black", font=("Arial", 40))
            self.clock_label.pack(side="bottom", anchor="se", padx=20, pady=10)

            self._update_clock()

            self.screensaver.bind("<Button>", self.reset_idle_timer)
            self.screensaver.bind("<Key>", self.reset_idle_timer)

        self._screensaver_active = True
        self.screensaver.deiconify()

        self._run_slideshow()

    def _run_slideshow(self):
        if not self.slideshow_images:
            return

        self.slideshow_index = (self.slideshow_index + 1) % len(self.slideshow_images)
        self.slideshow_label.config(image=self.slideshow_images[self.slideshow_index])
        logging.info(f"🖼️ Showing image {self.slideshow_index}")

        self.screensaver.after(5000, self._run_slideshow)  # change every 5 sec

    def hide_screensaver(self):
        logging.info("Hiding screensaver")
        if hasattr(self, 'screensaver'):
            self.screensaver.withdraw()
        self._screensaver_active = False

    def _update_clock(self):
        try:
            now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)
            self.clock_label.config(text=now.strftime("%H:%M:%S"))
        except Exception as e:
            print("⚠️ Clock update error:", e)

        self.root.after(1000, self._update_clock)   
                    
    def update_status(self, text, auto_clear=True, delay_ms=10000):
        self.status_label.config(text=text)

        # 👇 Hide screensaver if active
        if self._screensaver_active:
            self.hide_screensaver()

        # 👇 Reset idle timer (important when user interacts via fingerprint)
        self._last_activity = time.time()

        if auto_clear:
            if hasattr(self, '_reset_status_after_id'):
                self.root.after_cancel(self._reset_status_after_id)

            self._reset_status_after_id = self.root.after(delay_ms, self._reset_status)

    def _reset_status(self):
        self.status_label.config(text="Listo para escanear huellas...")

    def get_user_list(self):
        users = self.fingerprint.db.conn.execute("SELECT idagente, name FROM users ORDER BY name").fetchall()
        enriched = []

        for idagente, name in users:
            finger_ids = self.fingerprint.db.get_finger_ids_by_user(idagente)
            if finger_ids:
                status = "✅"
            else:
                status = "❌"
            display = f"{status} {name}"
            enriched.append((idagente, display))

        return enriched


    def on_scan(self):
        self.update_status("🔍 Scanning...")
        logging.info("Scanning for fingerprint")
        self.fingerprint.identify_fingerprint()

    def update_attendance_history(self):
        for label in self.history_labels:
            label.destroy()

        self.history_labels.clear()

        rows = self.fingerprint.db.conn.execute(
            "SELECT u.name, e.timestamp FROM events e "
            "JOIN users u ON u.idagente = e.user_id "
            "ORDER BY e.timestamp DESC LIMIT 3"
        ).fetchall()

        for i, (name, ts) in enumerate(reversed(rows)):
            time_str = ts.split("T")[1][:5]  # HH:MM
            text = f"✅ {name} — {time_str}"

            label = tk.Label(self.history_box, text=text, font=("Arial", 14),
                            fg="black", bg="white", anchor="w", justify="left")
            label.pack(fill="x", padx=10, pady=2)
            self.history_labels.append(label)


    def on_admin(self):
        logging.info("Admin setup initiated")
        #self._screensaver_disabled = True

        def check_pin():
            entered = pin_entry.get()
            if entered == "1234":
                logging.info("Admin PIN accepted")
                pin_window.grab_release()  # ✅ release grab before destroying
                pin_window.destroy()
                self.show_admin_menu()
            else:
                error_label.config(text="❌ Incorrect PIN", fg="red")
                logging.warning("Incorrect PIN entered")
                pin_entry.delete(0, tk.END)

        pin_window = tk.Toplevel(self.root)
        self.child_windows.append(pin_window)
        pin_window.title("Enter Admin PIN")
        pin_window.geometry("280x180")
        pin_window.transient(self.root)         # ✅ Tie it to the root window
        pin_window.grab_set()                   # ✅ Grab input focus (blocks root)
        pin_window.focus_force()                # ✅ Force focus to stay
        pin_window.protocol("WM_DELETE_WINDOW", lambda: (self._set_screensaver_enabled(), pin_window.destroy()))

        tk.Label(pin_window, text="Enter 4-digit PIN:", font=("Arial", 16)).pack(pady=10)
        pin_entry = tk.Entry(pin_window, show="*", font=("Arial", 18), justify="center", width=10)
        pin_entry.pack(pady=5)
        pin_entry.focus_set()

        self.root.after(100, lambda: self.show_numeric_keypad(pin_entry, on_done=check_pin))

        error_label = tk.Label(pin_window, font=("Arial", 14))
        error_label.pack()

        tk.Button(pin_window, text="Submit", font=("Arial", 14), command=check_pin).pack(pady=10)
        pin_window.bind('<Return>', lambda event: check_pin())

        self.root.wait_window(pin_window)  # ✅ Pause here until pin_window is closed

    def show_admin_menu(self):
        self.admin_window = tk.Toplevel(self.root)
        self.child_windows.append(self.admin_window)
        self.admin_window.title("Admin Menu")
        self.admin_window.geometry("480x320+0+0")
        self.admin_window.overrideredirect(True)
        self.admin_window.attributes("-topmost", True)
        #self.admin_window.grab_set()
        self.admin_window.focus_force()
        self.admin_window.protocol("WM_DELETE_WINDOW", self.close_admin_window)

        tk.Label(self.admin_window, text="Opciones de Admin", font=("Arial", 20)).pack(pady=10)

        btn_frame = tk.Frame(self.admin_window)
        btn_frame.pack(expand=True)

        tk.Button(btn_frame, text="Users", font=("Arial", 14), width=20,
                command=self.manage_users_gui).pack(pady=5)

        # System Status Panel
        status_frame = tk.LabelFrame(self.admin_window, text="System Status", padx=10, pady=10)
        status_frame.pack(padx=10, pady=10, fill="x")

        def get_system_status():
            try:

                used = self.fingerprint.db.count_all_fingerprints()
                max_capacity = 127

                return {
                    "Serial No.": f"{get_device_sn()}",
                    "CPU Temp": f"{get_cpu_temp()} °C",
                    "Memory": get_memory_usage(),
                    "Disk": get_disk_usage(),
                    "Uptime": get_uptime(),
                    "IP": get_local_ip(),
                    "Version": get_git_version(),
                    "Sync": "Sync" if self.is_sync_service_running() else "Offline!",
                    "Fingerprints": f"{used} / {max_capacity}"
                }
            except Exception as e:
                return {"Error": str(e)}

        def update_system_status():
            try:
                status = get_system_status()
                print("System status:", status)  # Debug
                for key, val in status.items():
                    if key in labels:
                        labels[key].config(text=f"{key}: {val}")
                        if key == "Sync":
                            labels[key].config(fg="green" if val == "Sync" else "red")
                        elif key == "Fingerprints":
                            try:
                                count, maxval = map(int, val.split("/"))
                                if count >= maxval:
                                    labels[key].config(fg="red")
                                elif count > maxval * 0.75:
                                    labels[key].config(fg="orange")
                                else:
                                    labels[key].config(fg="blue")
                            except:
                                labels[key].config(fg="black")
            except Exception as e:
                print("Status update error:", e)

        labels = {}
        for k in ["SN", "CPU Temp", "Memory", "Disk", "Uptime", "IP", "Version", "Sync", "Fingerprints"]:
            labels[k] = tk.Label(status_frame, text=f"{k}: ...", anchor="w", font=("Arial", 10))
            labels[k].pack(anchor="w")

        update_system_status()

        tk.Button(self.admin_window, text="✖ Close", font=("Arial", 12),
                command=self.close_admin_window).place(x=380, y=270)

    def close_admin_window(self):
        self._set_screensaver_enabled()
        self.fingerprint.start_fingerprint_listener()  # ✅ Resume reader
        self.admin_window.destroy()

    def manage_users_gui(self):
        try:
            self.admin_window.grab_release()
        except:
            pass

        self.user_display_mode = "all"  # initialize filter mode

        user_win = tk.Toplevel(self.root)
        self.child_windows.append(user_win)
        user_win.title("Manage Users")
        user_win.geometry("480x320+0+0")
        user_win.overrideredirect(True)
        user_win.attributes("-topmost", True)
        user_win.focus_force()
        user_win.after(200, lambda: user_win.grab_set())
        user_win.protocol("WM_DELETE_WINDOW", lambda: (self._set_screensaver_enabled(), user_win.destroy(), self.child_windows.remove(user_win)))

        status_label = tk.Label(user_win, text="👉 Tap a user to begin", font=("Arial", 14), fg="blue")
        status_label.pack(pady=(10, 5))

        list_frame = tk.Frame(user_win)
        list_frame.pack(pady=5, expand=True, fill="both")

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        user_listbox = tk.Listbox(list_frame, font=("Arial", 14), height=6, yscrollcommand=scrollbar.set)
        user_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=user_listbox.yview)

        # Load user data with fingerprint status once
        full_user_list = [
            {
                "idagente": u[0],
                "name": u[1],
                "has_fp": self.fingerprint.db.count_fingerprints_by_user(u[0]) > 0
            }
            for u in self.get_user_list()
        ]

        def refresh_user_list():
            user_listbox.delete(0, tk.END)
            for u in full_user_list:
                if self.user_display_mode == "pending" and u["has_fp"]:
                    continue
                icon = "✖" if not u["has_fp"] else "✅"
                user_listbox.insert(tk.END, f"{u['name']}")

        def toggle_user_filter():
            self.user_display_mode = "pending" if self.user_display_mode == "all" else "all"
            filter_btn.config(text="Show All" if self.user_display_mode == "pending" else "Show Only Pending")
            refresh_user_list()

        filter_btn = tk.Button(user_win, text="Show Only Pending", font=("Arial", 12), command=toggle_user_filter)
        filter_btn.pack(pady=(0, 5))

        def get_selected_user():
            index = user_listbox.curselection()
            if not index:
                return None
            # Match listbox index to full_user_list based on current filter
            visible_users = [
                u for u in full_user_list if self.user_display_mode != "pending" or not u["has_fp"]
            ]
            return visible_users[index[0]]["idagente"]

        def start_enroll():
            idagente = get_selected_user()
            if idagente:
                agente_name = self.fingerprint.db.get_user(idagente)[1]
                user_win.grab_release()
                user_win.destroy()
                self.child_windows.remove(user_win)
                self.root.after(50, lambda: self.show_enrollment_flow(idagente, agente_name))

        def delete_fingerprints():
            selected = user_listbox.curselection()
            if not selected:
                status_label.config(text="⚠️ Please select a user", fg="red")
                return

            idagente = get_selected_user()
            if not idagente:
                status_label.config(text="⚠️ User not found", fg="red")
                return

            status_label.config(text="Deleting fingerprints...", fg="orange")
            user_win.update_idletasks()

            try:
                self.fingerprint.stop_fingerprint_listener()
                self.fingerprint.delete_fingerprints_for_user(idagente)
                self.fingerprint.start_fingerprint_listener()

                status_label.config(text="✅ Fingerprints deleted", fg="green")
                user_win.after(2500, lambda: user_win.destroy(), self.child_windows.remove(user_win))

            except Exception as e:
                status_label.config(text=f"💥 Error: {str(e)}", fg="red")

        action_frame = tk.Frame(user_win)
        action_frame.pack(pady=5)

        tk.Button(action_frame, text="Start Enrollment", font=("Arial", 14),
                width=22, command=start_enroll).pack(pady=2)

        tk.Button(action_frame, text="Delete Fingerprints", font=("Arial", 14),
                width=22, fg="red", command=delete_fingerprints).pack(pady=2)

        tk.Button(user_win, text="✖ Close", font=("Arial", 12),
                command=lambda: (self._set_screensaver_enabled(), user_win.destroy(), self.child_windows.remove(user_win))).place(x=380, y=280)

        refresh_user_list()  # initial display



    def show_enrollment_flow(self, idagente, name):
        #self._screensaver_disabled = True
        self.fingerprint.stop_fingerprint_listener()  # ✅ Stop listener before enrollment

        enroll_win = tk.Toplevel(self.root)
        self.child_windows.append(enroll_win)
        enroll_win.title("Enrollment Process")
        enroll_win.geometry("480x320+0+0")
        enroll_win.overrideredirect(True)
        enroll_win.attributes("-topmost", True)
        enroll_win.grab_set()
        enroll_win.focus_force()

        def finish():
            enroll_win.destroy()
            self.child_windows.remove(enroll_win)
            self.fingerprint.start_fingerprint_listener()  # ✅ Restart listener after
            self.manage_users_gui()

        instruction = tk.Label(enroll_win, text="Preparando captura...", font=("Arial", 18), wraplength=460)
        instruction.pack(pady=40)

        status = tk.Label(enroll_win, text="", font=("Arial", 16))
        status.pack(pady=10)

        cancel_btn = tk.Button(enroll_win, text="✖ Cerrar", font=("Arial", 12), command=finish)
        cancel_btn.pack(side="bottom", pady=10)
        
        def update_instruction(text):
            instruction.config(text=text)

        def update_status(text):
            status.config(text=text)

        def finish():
            enroll_win.destroy()
            self.child_windows.remove(enroll_win)
            self.fingerprint.start_fingerprint_listener()  # ✅ Restart listener after
            self.manage_users_gui()

        def run_enrollment():
            try:
                update_instruction("Coloca el dedo en el lector...")
                result = self.fingerprint.enroll_new_fingerprint_for_user(
                    idagente, name,
                    on_update=update_instruction,
                    on_status=update_status
                )
                if result:
                    update_instruction("✅ Huella registrada con éxito\nPresiona '✖ Cancelar' para volver")
                else:
                    update_instruction("⚠️ No se pudo registrar la huella\nPresiona '✖ Cancelar' para volver")
            except Exception as e:
                logging.exception("Enrollment error")
                update_instruction("💥 Error: " + str(e) + "\nPresiona '✖ Cancelar' para volver")

        print("Starting enrollment thread")
        threading.Thread(target=run_enrollment, daemon=True).start()


    def _set_screensaver_enabled(self):
        self._screensaver_disabled = False

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

    def show_numeric_keypad(self, target_entry, on_done=None):
        keypad = tk.Toplevel(self.root)
        self.child_windows.append(keypad)
        keypad.title("Numeric Keypad")
        keypad.grab_set()
        keypad.transient(self.root)         # ✅ Tie to root window
        keypad.attributes("-topmost", True)
        keypad.focus_force()
        keypad.resizable(False, False)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = 360
        win_h = 160
        x = (screen_w - win_w) // 2
        y = screen_h - win_h - 20
        keypad.geometry(f"{win_w}x{win_h}+{x}+{y}")

        def append_char(char):
            target_entry.insert(tk.END, char)

        def backspace():
            current = target_entry.get()
            target_entry.delete(0, tk.END)
            target_entry.insert(0, current[:-1])

        def submit():
            if on_done:
                on_done()
            keypad.grab_release()       # ✅ Release grab before closing
            keypad.destroy()

        keypad_frame = tk.Frame(keypad)
        keypad_frame.pack(expand=True)

        # Row 1: 1–5
        for i, digit in enumerate(['1', '2', '3', '4', '5']):
            tk.Button(keypad_frame, text=digit, font=("Arial", 14), width=3, height=1,
                    command=lambda d=digit: append_char(d)).grid(row=0, column=i, padx=2, pady=2)

        # Row 2: 6–0
        for i, digit in enumerate(['6', '7', '8', '9', '0']):
            tk.Button(keypad_frame, text=digit, font=("Arial", 14), width=3, height=1,
                    command=lambda d=digit: append_char(d)).grid(row=1, column=i, padx=2, pady=2)

        # Row 3: Backspace + Enter
        tk.Button(keypad_frame, text="←", font=("Arial", 14), width=9, height=1,
                command=backspace).grid(row=2, column=0, columnspan=2, padx=2, pady=4)

        tk.Button(keypad_frame, text="Enter", font=("Arial", 14), width=15, height=1,
                command=submit).grid(row=2, column=2, columnspan=3, padx=2, pady=4)

        # ✅ Prevent closing with window manager (optional for security)
        keypad.protocol("WM_DELETE_WINDOW", lambda: None)

        # ✅ Block until keypad closes
        self.root.wait_window(keypad)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window initially
    def start_app():
        root.deiconify()  # Show main window
        AttendanceApp(root)

    root.after(2000, start_app)
    root.mainloop()