# 🚀 Usage Instructions

This section covers how to use the Webroster Biometric Terminal once it's set up.

---

## 🖥️ Starting the Application

1. Activate your Python virtual environment:

```bash
cd ~/webroster-bio
source venv/bin/activate
```

2. Run the GUI:

```bash
python3 main.py
```

The main screen will show the system status and wait for fingerprint scans.

---

## 👤 Enrolling a New User

1. Tap the **Admin** button.
2. Enter the 4-digit PIN (default: `1234`).
3. In the Admin Menu, choose **Users**.
4. Select a user from the list and tap **Start Enrollment**.
5. Follow on-screen instructions to scan the fingerprint 3 times.

✅ The fingerprint will be saved locally and associated with that user.

---

## 🖐️ Clocking In

Once enrolled:

- Users simply place their finger on the sensor.
- If matched, a success message and timestamp are shown.
- An audio confirmation is played.

If the fingerprint is not recognized:

- An error sound and message will appear.

---

## 🧠 Admin Menu Features

- **Users**: View list of employees and enroll/delete fingerprints.
- **System Status**: See temperature, memory, disk, IP, fingerprint count.
- **Close**: Exit admin mode and return to idle screen.

---

## 🔄 Sync Behavior

The sync service will:
- Send new check-in events to the ADMS server (`/iclock/cdata`)
- Receive and process remote commands (`/iclock/getrequest`)
- Upload logs for remote monitoring

Make sure the device has internet access and can reach the configured backend.

---

## 🎵 Audio Feedback

- ✅ Success: `checada_correcta.wav`
- ❌ Error or unrecognized: `error_checada.wav`
- 🛑 Canceled actions or retries also have custom sounds.

Place all `.wav` files in the `audios/` folder.

---

📖 Continue to: [05-sync-and-api.md → Sync & ADMS API](05-sync-and-api.md)
