from datetime import datetime
import shutil
import requests
import logging
import os

def upload_latest_log():
    adms_url = f"{ADMS_URL}/iclock/upload-log"  # adjust if needed

    try:
        # Ensure log folder exists
        os.makedirs("logs", exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        original_log = "logs/webroster.log"
        renamed_log = f"logs/webroster-{today}.log"

        # Rotate the log file: rename current and create a new one
        if os.path.exists(original_log):
            shutil.copy2(original_log, renamed_log)  # make a copy
            open(original_log, 'w').close()  # clear the original log

        with open(renamed_log, "rb") as f:
            headers = {
                "User-Agent": "Mindware_bioterminal",
                "Accept": "*/*",
                "Connection": "close"
            }

            logging.info(f"📤 Uploading log file: {renamed_log} to {adms_url}")
            response = requests.post(
                adms_url,
                files={"file": (os.path.basename(renamed_log), f)},
                data={"sn": get_device_sn()},
                headers=headers
            )

        if response.status_code == 200:
            logging.info("✅ Log file uploaded successfully.")
            # Optional: delete after upload
            os.remove(renamed_log)
        else:
            logging.warning(f"⚠️ Upload failed: {response.status_code} - {response.text}")

    except Exception as e:
        logging.exception("💥 Exception during log upload")
