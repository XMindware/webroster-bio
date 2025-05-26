# 🧩 Local Architecture Overview

This section describes how the components of the Webroster Biometric Terminal work together within the device.

---

## 🖼️ High-Level Overview

```text
┌────────────┐     ┌───────────────────┐     ┌────────────────────┐
│  User Scan │ →→  │ FingerprintManager│ →→  │ SQLite Local DB    │
└────────────┘     └───────────────────┘     └────────────────────┘
                         ↓                           ↓
                   ┌─────────────┐             ┌──────────────┐
                   │ Tkinter GUI │ ← Updates ← │ Event Logger │
                   └─────────────┘             └──────────────┘
                         ↓
                 ┌─────────────────┐
                 │ Sync Service    │ →→ Push to Webroster ADMS
                 └─────────────────┘
```

---

## 📁 Folder Structure

| Folder/File               | Purpose                                      |
|---------------------------|----------------------------------------------|
| `main.py`                 | Launches GUI and initializes app             |
| `fingerprint_manager.py`  | Handles sensor logic and local database      |
| `db.py`                   | Encapsulates all SQLite queries              |
| `sync_service.py`         | Runs independently to sync with the backend  |
| `audios/`                 | `.wav` files for sound feedback              |
| `logs/`                   | Local application logs                       |
| `scripts/`                | Tools for setup/reset (e.g., wipe DB)        |

---

## 📦 Core Components

### `FingerprintManager`

- Detects and enrolls fingerprints
- Interfaces with `adafruit_fingerprint` library
- Stores templates in sensor + metadata in SQLite

### `db.py`

- Handles all queries to `attendance.db`
- Tables: `users`, `fingerprints`, `events`

### `main.py`

- Tkinter GUI: touch interface for check-in/admin
- Starts listener thread for scan events
- Handles enrollment and fingerprint deletion

---

## 🔁 Sync Service (`sync_service.py`)

- Independently launched via systemd
- Polls for new commands from the ADMS server
- Pushes new events and logs periodically
- Reboots device if instructed remotely

---

## 🔊 Audio System

- Plays `.wav` files via Pygame when:
  - Fingerprint matched
  - Error occurred
  - Admin actions are triggered

---

## 🧠 Configuration Highlights

- Serial port detection is automatic (USB or UART)
- LCD overlays are activated in `/boot/config.txt`
- Screensaver shows local images if idle
- Unique SN is derived from MAC address

---

📖 Continue to: [08-advanced.md → Autostart & Deployment](08-advanced.md)
