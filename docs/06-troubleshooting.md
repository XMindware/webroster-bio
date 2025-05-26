# 🛠️ Common Issues & Troubleshooting

If something doesn't work as expected, this section will help you diagnose and solve the most common issues with the Webroster Biometric Terminal.

---

## 🔌 Fingerprint Sensor Not Detected

**Symptoms:**
- `❌ Error inicializando el sensor`
- Log says `Failed to read data from sensor`

**Solutions:**
- Make sure the sensor is connected to `/dev/ttyUSB0` or `/dev/ttyUSB1`
- Test with `minicom` or `python test.py` to verify low-level connectivity
- Check power supply stability — some sensors need solid 5V
- Try switching USB ports

---

## 💡 Display Not Showing GUI

**Symptoms:**
- Black screen or boot messages only

**Solutions:**
- If using GPIO TFT (e.g., goodtft), rerun:
  ```bash
  sudo ./LCD35-show
  ```
- Check `/boot/config.txt` for correct display overlay:
  ```
  dtoverlay=tft35a:rotate=90
  ```

---

## 🔇 No Audio Feedback

**Symptoms:**
- No sound for check-in, errors, or admin prompts

**Solutions:**
- Run `aplay /usr/share/sounds/alsa/Front_Center.wav`
- Set output to analog with:
  ```bash
  sudo raspi-config → Audio → Force 3.5mm
  ```
- Use a powered speaker or USB audio adapter if signal is too weak

---

## 🔄 Sync Not Working

**Symptoms:**
- Events not uploaded
- Logs not received by server

**Solutions:**
- Check internet connection
- Confirm that `webroster-sync.service` is running:
  ```bash
  systemctl status webroster-sync.service
  ```
- Ensure backend endpoints `/iclock/cdata` and `/iclock/getrequest` are reachable

---

## 🧪 Debug Tips

- Check `logs/webroster.log` for activity
- Run `python3 main.py` manually to see console output
- Use `sqlite3 attendance.db` to inspect local data

---

## 🧼 Resetting Local Data

To delete all local users and fingerprint templates:

```bash
python3 scripts/wipe_all_data.py
```

Make sure `fingerprint_manager` is not actively running when this is executed.

---

📖 Continue to: [07-local-architecture.md → Local Architecture Overview](07-local-architecture.md)
