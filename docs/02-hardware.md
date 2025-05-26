# 🔧 Hardware Setup

This section outlines the components required to build a fully working Webroster Biometric Terminal and how to connect them.

---

## 📦 Required Components

| Component                         | Description                                      |
|----------------------------------|---------------------------------------------------|
| **Raspberry Pi 4** or 3B+        | Recommended for performance and connectivity      |
| **3.5" TFT LCD (XPT2046)**       | Touchscreen interface (HDMI or GPIO-based)        |
| **AS608 Fingerprint Sensor**     | UART or USB version                               |
| **USB to Serial Adapter**        | Needed if using the TTL (UART) version of AS608   |
| **MicroSD Card (16GB or larger)**| With Raspberry Pi OS (Desktop edition)            |
| **3.5mm or USB Speaker**         | For audio feedback                                |
| **5V Power Supply (2.5A or more)**| Stable power for Pi and peripherals              |

---

## 🧪 Optional Components

- **Case/enclosure** for durability
- **Heatsinks or fan** for heavy-duty deployments
- **RTC module** for accurate offline timekeeping

---

## 📷 Wiring the AS608 Fingerprint Sensor

If using the **UART version (recommended for stability)**:

| Sensor Wire | Connects To         |
|-------------|---------------------|
| Red         | 5V on Raspberry Pi  |
| Black       | GND                 |
| Green       | TX → USB-Serial RX  |
| White       | RX → USB-Serial TX  |

> Use a USB-to-Serial adapter (FTDI, CH340, CP2102, etc.). Connect to Pi’s USB port.

If using the **USB version**, just plug it into a Pi USB port. It should appear as `/dev/ttyUSB0`.

---

## 🖥️ Connecting the 3.5" TFT Display

If you're using a GPIO-connected TFT (e.g., waveshare/goodtft):

1. Run:
   ```bash
   git clone https://github.com/goodtft/LCD-show.git
   cd LCD-show
   sudo ./LCD35-show
