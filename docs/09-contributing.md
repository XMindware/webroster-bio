# 🤝 Contributing to Webroster Bio

We welcome contributions to improve this project. Whether you're fixing bugs, improving the UI, adding features, or writing documentation—your help is appreciated!

---

## 🧱 Project Structure

```
webroster-bio/
├── main.py                  # Main GUI interface
├── fingerprint_manager.py   # Core fingerprint logic
├── db.py                    # SQLite wrapper
├── sync_service.py          # Background sync daemon
├── audios/                  # Sound files (.wav)
├── logs/                    # Local log files
├── scripts/                 # Utility scripts
├── docs/                    # Markdown documentation
└── requirements.txt         # Python dependencies
```

---

## 🔧 Development Setup

1. Fork the repository
2. Clone your fork:

```bash
git clone https://github.com/XMindware/webroster-bio.git
cd webroster-bio
```

3. Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🚀 Running the App

```bash
source venv/bin/activate
python3 main.py
```

You can also run `sync_service.py` manually for testing:

```bash
python3 sync_service.py
```

---

## 🛠️ Contribution Guidelines

- Follow PEP8 for Python code style
- Keep UI changes responsive to 480x320 screens
- Use descriptive commit messages
- Add or update `docs/` if changing behavior

---

## 🧪 Tests & Debugging

There are currently no automated tests. To test:

- Connect fingerprint sensor
- Use dummy DB or test database
- Monitor `webroster.log` for behavior

---

## 📬 Submitting Pull Requests

1. Push your branch
2. Open a pull request with description of your changes
3. Tag any related issues or feature requests

---

Thank you for helping us build better biometric terminals for everyone!
