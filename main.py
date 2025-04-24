from PIL import Image, ImageTk
import tkinter as tk
import threading
import time
import os
import json
import uuid
from datetime import datetime, timedelta
from fingerprint_manager import FingerprintManager
import logging
import glob
from PIL import Image, ImageTk


with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
    CONFIG = json.load(f)

def get_device_sn(prefix="WBIO"):
    mac = uuid.getnode()
    mac_hex = f"{mac:012X}"[-6:]  # get last 6 characters (uppercase)
    return f"{prefix}{mac_hex}"


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
        self.idle_timeout_seconds = 20  # change as needed
        self._last_activity = time.time()
        self._screensaver_active = False

        self.root.bind("<Button>", self.reset_idle_timer)
        self.root.bind("<Key>", self.reset_idle_timer)

        self.fingerprint = FingerprintManager(update_callback=self.update_status)
        self.fingerprint.refresh_history = self.update_attendance_history

        self.status_label = tk.Label(root, text="Touch to begin", font=("Helvetica", 24))
        self.status_label.place(relx=0.5, rely=0.25, anchor="center")

        self.offline_label = tk.Label(root, text="", font=("Arial", 28), fg="red")
        self.offline_label.pack(pady=60)

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

    def _update_main_clock(self):
        now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)
        self.main_clock_label.config(text=now.strftime("%H:%M:%S"))
        self.root.after(1000, self._update_main_clock)

    def check_idle_timeout(self):
        if not self._screensaver_active and (time.time() - self._last_activity > self.idle_timeout_seconds):
            logging.info("⏳ Idle timeout reached — showing screensaver")
            #self.show_screensaver()

        self.root.after(1000, self.check_idle_timeout)  # Loop again every second

    def reset_idle_timer(self, event=None):
        self._last_activity = time.time()
        if self._screensaver_active:
            self.hide_screensaver()
    

    def show_screensaver(self):
        logging.info("Showing screensaver")
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
        if not self._screensaver_active or not self.slideshow_images:
            return
        # Set next image
        self.slideshow_index = (self.slideshow_index + 1) % len(self.slideshow_images)
        self.slideshow_label.config(image=self.slideshow_images[self.slideshow_index])
        # Schedule next slide in 10 seconds
        self.root.after(10000, self._run_slideshow)

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

        if "Offline" in text or "sync failed" in text:
            self.offline_label.config(text="📴", fg="red")
        else:
            self.offline_label.config(text="")


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
        def check_pin():
            entered = pin_entry.get()
            if entered == "1234":
                logging.info("Admin PIN accepted")
                pin_window.destroy()
                self.show_admin_menu()
            else:
                error_label.config(text="❌ Incorrect PIN", fg="red")
                logging.warning("Incorrect PIN entered")
                pin_entry.delete(0, tk.END)

        pin_window = tk.Toplevel(self.root)
        pin_window.title("Enter Admin PIN")
        pin_window.geometry("280x180")
        pin_window.grab_set()
        pin_window.attributes("-topmost", True)
        pin_window.focus_force()

        tk.Label(pin_window, text="Enter 4-digit PIN:", font=("Arial", 16)).pack(pady=10)
        pin_entry = tk.Entry(pin_window, show="*", font=("Arial", 18), justify="center", width=10)
        pin_entry.pack(pady=5)
        pin_entry.focus_set()
        self.root.after(100, lambda: self.show_numeric_keypad(pin_entry, on_done=check_pin))

        error_label = tk.Label(pin_window, font=("Arial", 14))
        error_label.pack()

        tk.Button(pin_window, text="Submit", font=("Arial", 14), command=check_pin).pack(pady=10)
        pin_window.bind('<Return>', lambda event: check_pin())

    def show_admin_menu(self):
        admin_window = tk.Toplevel(self.root)
        admin_window.title("Admin Menu")
        admin_window.geometry("400x300")
        admin_window.grab_set()
        admin_window.attributes("-topmost", True)
        admin_window.focus_force()

        tk.Label(admin_window, text="Admin Options", font=("Arial", 16)).pack(pady=10)

        # Standard sync + enroll options
        tk.Button(admin_window, text="Sync Attendance", font=("Arial", 14),
                command=lambda: self.fingerprint.push_unsynced_logs()).pack(pady=5)

        tk.Button(admin_window, text="Enroll New User", font=("Arial", 14),
                command=self.prompt_enroll).pack(pady=5)

        # 👇 New Enroll Fingerprint Option
        tk.Button(admin_window, text="Users", font=("Arial", 14),
          command=self.manage_users_gui).pack(pady=5)

        tk.Button(admin_window, text="Close", command=admin_window.destroy).pack(pady=10)

    def manage_users_gui(self):
        user_win = tk.Toplevel(self.root)
        user_win.title("Manage Users")
        user_win.geometry("320x280")
        user_win.grab_set()
        user_win.attributes("-topmost", True)
        user_win.focus_force()

        users = self.get_user_list()
        if not users:
            tk.Label(user_win, text="No users found", font=("Arial", 14)).pack(pady=20)
            return

        tk.Label(user_win, text="Tap a user:", font=("Arial", 14)).pack(pady=10)

        # Create scrollable list
        list_frame = tk.Frame(user_win)
        list_frame.pack(pady=5, expand=True, fill="both")

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        user_listbox = tk.Listbox(list_frame, font=("Arial", 14), height=10, yscrollcommand=scrollbar.set)
        for u in users:
            user_listbox.insert(tk.END, u[1])
        user_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=user_listbox.yview)

        def get_selected_user():
            index = user_listbox.curselection()
            if not index:
                return None
            return users[index[0]][0]  # idagente

        def start_enroll():
            idagente = get_selected_user()
            if idagente:
                agente_name = self.fingerprint.db.get_user(idagente)[1]
                self.fingerprint.enroll_new_fingerprint_for_user(idagente, agente_name)
                user_win.destroy()

        def delete_fingerprints():
            idagente = get_selected_user()
            if idagente:
                self.fingerprint.delete_fingerprints_for_user(idagente)
                self.update_status(f"🗑️ Deleted fingerprints for user {idagente}")
                user_win.destroy()

        tk.Button(user_win, text="Start Enrollment", font=("Arial", 14), command=start_enroll).pack(pady=10)
        tk.Button(user_win, text="Delete Fingerprints", font=("Arial", 14), fg="red", command=delete_fingerprints).pack(pady=5)


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
            
    def enroll_fingerprint_gui(self):
        enroll_win = tk.Toplevel(self.root)
        enroll_win.title("Enroll Finger for User")
        enroll_win.geometry("400x200")
        enroll_win.grab_set()
        enroll_win.attributes("-topmost", True)
        enroll_win.focus_force()

        users = self.get_user_list()

        if not users:
            tk.Label(enroll_win, text="No users found", font=("Arial", 14)).pack(pady=20)
            return

        tk.Label(enroll_win, text="Select user to enroll fingerprint:", font=("Arial", 14)).pack(pady=10)

        selected = tk.StringVar()
        selected.set(users[0][1])  # Use display name with finger IDs

        dropdown = tk.OptionMenu(enroll_win, selected, *[u[1] for u in users])
        dropdown.config(font=("Arial", 12))
        dropdown.pack(pady=5)

        def enroll_selected():
            raw = selected.get()
            idagente = int(raw.split(" - ")[0])  # Extract ID
            self.fingerprint.enroll_new_fingerprint_for_user(idagente)
            enroll_win.destroy()


        tk.Button(enroll_win, text="Start Enrollment", font=("Arial", 14), command=enroll_selected).pack(pady=15)



    def prompt_enroll(self):
        enroll_prompt = tk.Toplevel(self.root)
        enroll_prompt.title("Enroll Finger")
        enroll_prompt.geometry("300x200")
        enroll_prompt.grab_set()
        enroll_prompt.attributes("-topmost", True)
        enroll_prompt.focus_force()
        logging.info("Enrollment prompt opened")

        tk.Label(enroll_prompt, text="Enter ID (0–127):", font=("Arial", 14)).pack(pady=10)
        id_entry = tk.Entry(enroll_prompt, font=("Arial", 18), justify="center")
        id_entry.pack(pady=5)
        id_entry.focus_set()
        self.root.after(100, lambda: self.show_numeric_keypad(id_entry, on_done=enroll_action))

        error = tk.Label(enroll_prompt, font=("Arial", 12))
        error.pack()

        def enroll_action():
            try:
                pos_id = int(id_entry.get())
                if not (0 <= pos_id <= 127):
                    raise ValueError("Out of range")

                enroll_prompt.destroy()
                self.fingerprint.enroll_fingerprint(pos_id)

            except ValueError:
                error.config(text="❗ Invalid ID", fg="red")

    def show_numeric_keypad(self, target_entry, on_done=None):
        keypad = tk.Toplevel(self.root)
        keypad.title("Numeric Keypad")
        keypad.grab_set()

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = 320
        win_h = 280
        x = (screen_w - win_w) // 2
        y = screen_h - 220 - 100
        keypad.geometry(f"{win_w}x{win_h}+{x}+{y}")
        keypad.attributes("-topmost", True)
        keypad.focus_force()

        def append_char(char):
            target_entry.insert(tk.END, char)

        def backspace():
            current = target_entry.get()
            target_entry.delete(0, tk.END)
            target_entry.insert(0, current[:-1])

        def clear():
            target_entry.delete(0, tk.END)

        keys = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['C', '0', '←']]

        keypad_frame = tk.Frame(keypad)
        keypad_frame.pack(expand=True)

        for r, row in enumerate(keys):
            for c, key in enumerate(row):
                action = (lambda x=key: clear() if x == 'C' else backspace() if x == '←' else append_char(x))
                tk.Button(keypad_frame, text=key, width=5, height=2, font=("Arial", 12), command=action).grid(row=r, column=c, padx=4, pady=4)

        def done():
            if on_done:
                on_done()
            keypad.destroy()

        tk.Button(keypad_frame, text="Enter", width=26, font=("Arial", 12), command=done).grid(
            row=4, column=0, columnspan=3, pady=10
        )

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window initially
    def start_app():
        root.deiconify()  # Show main window
        AttendanceApp(root)

    root.after(2000, start_app)
    root.mainloop()