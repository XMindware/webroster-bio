# ⚙️ Installation Guide

This section explains how to set up the software for the Webroster Biometric Terminal on a fresh Raspberry Pi OS (with Desktop).

---

## 🧾 Prerequisites

Make sure you have:
- Raspberry Pi OS (32-bit, with Desktop)
- A connected display (LCD or HDMI)
- Internet connection (Ethernet or Wi-Fi)
- Access to a terminal or SSH

---

## 📥 1. Clone the Project

```bash
git clone https://github.com/XMindware/webroster-bio.git
cd webroster-bio
```

---

## 🐍 2. Set Up Python Virtual Environment

```bash
sudo apt update
sudo apt install python3-venv python3-pip -y

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

This installs all required dependencies including:
- Adafruit fingerprint library
- Serial communication
- GUI tools (Tkinter, Pygame)
- System monitoring tools (psutil)

---

## 📺 3. Install LCD Driver (if using GPIO TFT)

```bash
git clone https://github.com/goodtft/LCD-show.git
cd LCD-show
sudo ./LCD35-show
```

This will reboot your Pi and enable the display.

---

## 🔊 4. Configure Audio Output (optional)

To force audio to the 3.5mm jack:

```bash
sudo raspi-config
# Navigate to: Advanced Options → Audio → Force 3.5mm output
```

Test with:

```bash
aplay /usr/share/sounds/alsa/Front_Center.wav
```

---

## 🔧 5. Enable Serial Communication

If using a UART fingerprint sensor:

```bash
sudo raspi-config
# → Interface Options → Serial
# → Disable login shell, but enable serial port hardware
```

If using USB-based sensor: no changes needed.

---

## 📁 6. Prepare folders

Create folders for logs and sound files:

```bash
mkdir logs
mkdir audios
```

Place your `.wav` sound files in the `audios/` folder.

---

## 🧪 7. Run the Application

```bash
source venv/bin/activate
python3 main.py
```

You should see the GUI on your screen. When the fingerprint reader is connected, the system will attempt to initialize and display status updates.

---

## 🔁 Optional: Set Up as a Boot Service

To make the system start automatically on boot, continue to [08-advanced.md → Autostart & Services](08-advanced.md)

---

📖 Continue to: [04-usage.md → Usage Instructions](04-usage.md)
