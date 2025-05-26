# 🧠 Introduction

Welcome to the **Webroster Biometric Terminal** project — an open-source, offline-friendly time and attendance solution built on Raspberry Pi.

This system is designed for **secure, local fingerprint authentication**, and can be integrated with **Webroster-style ADMS platforms** using a ZKTeco-compatible protocol.

---

## ✨ Why This Project Exists

Many organizations need an on-site attendance system that:
- ✅ Works **offline** and syncs automatically when connected
- ✅ Uses **biometric validation** (not cards or passwords)
- ✅ Provides a **simple touchscreen interface**
- ✅ Has **open and auditable code**

This project was developed with **field reliability** in mind — particularly for environments where internet access may be unstable or intermittent.

---

## ⚙️ What It Does

- ✅ **Reads fingerprints** using a low-cost sensor (e.g., AS608)
- ✅ **Registers employees** locally with optional backend sync
- ✅ **Stores check-in events** even without internet
- ✅ Plays **audio feedback** for success, failure, or prompts
- ✅ Shows a **touchscreen-friendly interface** on a 3.5” LCD
- ✅ Periodically **pushes data to a central server** using `/iclock/cdata`
- ✅ Accepts **remote commands** from the server using `/iclock/getrequest`

---

## 🧩 Technologies Used

| Component       | Description                                 |
|----------------|---------------------------------------------|
| **Python 3**    | Main language for logic and GUI             |
| **Tkinter**     | Lightweight GUI for touchscreen interaction |
| **SQLite**      | Local storage of users and events           |
| **PySerial**    | Interface with the fingerprint sensor       |
| **Pygame**      | Playback of audio feedback                  |
| **Systemd**     | Optional auto-start services                |

---

## 🔓 Open Design Goals

This project is meant to be:
- **Modifiable** — Easily adapt for new backends or use cases
- **Portable** — Should run on any Raspberry Pi with Python
- **Transparent** — No black-box binaries or vendor lock-in
- **Robust** — Works even without internet or UI interaction

---

📖 Continue to: [02-hardware.md → Hardware Setup](02-hardware.md)
