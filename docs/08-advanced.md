# ⚙️ Autostart & Deployment

This section explains how to prepare your Webroster Biometric Terminal for deployment in the field, including autostart configuration and cloning the setup.

---

## 🔁 Autostart on Boot

To start the GUI and sync service automatically when the device boots:

### 1. Create systemd service for GUI

```bash
sudo nano /etc/systemd/system/webroster-bio-ui.service
```

Paste the following:

```ini
[Unit]
Description=Webroster Bio GUI
After=network.target

[Service]
User=mindware
WorkingDirectory=/home/mindware/webroster-bio
ExecStart=/home/mindware/webroster-bio/venv/bin/python3 main.py
Restart=always

[Install]
WantedBy=graphical.target
```

Enable it:

```bash
sudo systemctl enable webroster-bio-ui.service
```

---

### 2. Create systemd service for Sync

```bash
sudo nano /etc/systemd/system/webroster-sync.service
```

Paste the following:

```ini
[Unit]
Description=Webroster Sync Service
After=network.target

[Service]
User=mindware
WorkingDirectory=/home/mindware/webroster-bio
ExecStart=/home/mindware/webroster-bio/start_sync.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl enable webroster-sync.service
```

---

## 🧬 Creating a Deployable Image

Once you have a working prototype, clone it to replicate on new devices.

### 1. Create Image (from development Raspberry Pi)

```bash
sudo dd if=/dev/mmcblk0 of=webroster.img bs=4M status=progress
```

> Replace `/dev/mmcblk0` with your actual device (check with `lsblk`)

---

### 2. Write Image on Another SD (on macOS)

Use `diskutil list` to find the disk ID (e.g., `/dev/disk3`), then:

```bash
diskutil unmountDisk /dev/disk3
sudo dd if=webroster.img of=/dev/rdisk3 bs=4m
```

---

### 3. Shrinking Image (Optional)

To fit on smaller SD cards (e.g., 32GB):

- Use `PiShrink` or `pishrink.sh`
- Use `gparted` to shrink filesystem before cloning

---

## 🧪 Final Deployment Checklist

- [ ] Fingerprint sensor tested
- [ ] GUI and sync start on boot
- [ ] LCD driver and display working
- [ ] Audio output tested
- [ ] SN properly recognized
- [ ] Connectivity to ADMS verified

---

🎉 Your device is now ready for production use!
