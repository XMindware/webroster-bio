# 🌐 Sync & ADMS API

This section explains how the Webroster Biometric Terminal communicates with a backend server using ZKTeco-compatible endpoints.

---

## 🔄 Sync Flow

The device uses a **push-pull mechanism** to communicate with the backend:

### 1. Push Logs to Server

The device sends unsynced check-ins via:

```
POST /iclock/cdata
```

**Payload includes:**

- `SN`: Serial number of device
- `table`: Attendance logs (e.g., `ATTLOG`)
- `data`: Event entries like:
  ```
  2	2024-01-15 07:32:00	1
  ```

### 2. Poll for Commands

The device periodically calls:

```
POST /iclock/getrequest
```

**Request includes:**

- `SN`: Serial number
- Device status info (memory, uptime, etc.)

The server responds with queued commands, e.g.:

- `DATA UPDATE USERINFO ...`
- `CONTROL DEVICE 03000000` → used to reboot the device
- `DATA DELETE USER ...`

---

## 🛠️ Accepted Commands

| Command Type         | Description                         |
|----------------------|-------------------------------------|
| `UPDATE USERINFO`    | Add/update a user in local DB       |
| `DELETE USER`        | Remove a user and fingerprint data  |
| `CONTROL DEVICE`     | Restart or sync control             |

Example response from `getrequest`:

```
C:57229:DATA UPDATE USERINFO PIN=148772	Name=Juan Pérez	...
C:57230:CONTROL DEVICE 03000000
```

---

## 🧪 Server-Side API (Laravel Example)

Server should:
- Accept logs at `/iclock/cdata`
- Respond with commands at `/iclock/getrequest`
- Log, store, and process attendance events
- Provide authentication for known serial numbers (optional)

---

## 🧼 Uploading Device Logs

The device can also send internal logs (`webroster.log`) using:

```
POST /iclock/getrequest
Content-Type: multipart/form-data
Payload: { file: ..., sn: ... }
```

Useful for debugging and remote support.

---

## 🌐 Device Serial Number

The serial number (SN) is derived from the MAC address:

```python
def get_device_sn(prefix="WBIO"):
    mac = uuid.getnode()
    mac_hex = f"{mac:012X}"[-6:]
    return f"{prefix}{mac_hex}"
```

---

📖 Continue to: [06-troubleshooting.md → Common Issues & Fixes](06-troubleshooting.md)
