# 📚 Library Management System

A modern, cross-platform desktop application for managing a library's books, members, and loans — built with **Python**, **Tkinter**, and **SQLite**.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![GUI](https://img.shields.io/badge/GUI-Tkinter-orange)

---

## ✨ Features

### 📖 Book Management
- Add, edit, delete, and search books
- Track multiple copies per book (total vs. available)
- ISBN, author, year, and copy-count tracking
- Real-time search across title, author, and ISBN
- Color-coded availability status
- 🔒 Prevents deletion of books with active loans

### 👥 Member Management
- Add, edit, delete, and search members
- Track name, email, phone, and join date
- Real-time search across all fields
- 🔒 Prevents deletion of members with active loans

### 🔄 Loan Management
- Borrow books with searchable, scrollable selection lists
- Configurable loan duration (default: 14 days)
- **Renew loans** with a configurable extension period (up to 3 renewals)
- Return books with one click
- Auto-detect **overdue** loans
- Filter to show only active loans
- Status indicators: ● Active · ⚠ Overdue · ✓ Returned

### 🎨 Modern UI
- Clean, colorful interface with a consistent color palette
- Striped table rows for easy reading
- Tab-based navigation (Books · Members · Loans)
- Cross-platform fonts (SF Pro on macOS, Segoe UI on Windows)
- Aligned column headers and cells
- Emoji icons for visual clarity

---

## 📸 Screenshots

> _Add your screenshots here_

```
┌─────────────────────────────────────────────┐
│   📚 Books    👥 Members    🔄 Loans         │
├─────────────────────────────────────────────┤
│   🔎 Search...        [Add] [Edit] [Delete] │
├─────────────────────────────────────────────┤
│   ID │ Title      │ Author  │ Available    │
│   01 │ 1984       │ Orwell  │ ● Available  │
│   02 │ Dune       │ Herbert │ ● Available  │
└─────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Component         | Technology                |
|-------------------|---------------------------|
| Language          | Python 3.8+               |
| GUI Framework     | Tkinter (ttk)             |
| Database          | SQLite 3                  |
| Architecture      | MVC (Model–View–Controller)|
| Packaging         | PyInstaller (optional)    |

---

## 📁 Project Structure

```
LibraryApp/
├── main.py          # Application entry point
├── database.py      # SQLite connection & schema initialization
├── models.py        # Data-access layer (BookModel, MemberModel, LoanModel)
├── ui.py            # Tkinter UI (tabs, dialogs, styling)
├── library.db       # SQLite database (auto-generated on first run)
├── requirements.txt # Python dependencies (optional)
└── README.md
```

### Architecture

The project follows a clean **separation of concerns**:

- **`database.py`** — handles SQLite connection and schema setup
- **`models.py`** — all SQL queries live here (no SQL in the UI)
- **`ui.py`** — pure Tkinter UI; calls model methods for data
- **`main.py`** — bootstraps the DB and launches the app

---

## 🚀 Installation & Usage

### Prerequisites
- **Python 3.8 or newer**
- `tkinter` and `sqlite3` (both ship with Python standard library)

> On most Linux distributions you may need to install Tkinter separately:
> ```bash
> sudo apt-get install python3-tk     # Debian / Ubuntu
> sudo dnf install python3-tkinter    # Fedora
> ```

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/LibraryApp.git
cd LibraryApp
```

### 2. (Optional) Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate     # macOS / Linux
venv\Scripts\activate        # Windows
```

### 3. (Optional) Install extras for full features
The core app runs on the standard library alone. Two optional packages unlock
more; without them the app still runs and degrades gracefully:

```bash
pip install -r requirements.txt   # openpyxl → Excel import/export · Pillow → book labels
```

### 4. Run the app
```bash
python3 main.py          # or:  python3 -m library_app
```
The first launch creates the database automatically (see **Where Your Data Lives** below).

> **macOS note:** run with a Python whose **Tk ≥ 8.6**
> (check: `python3 -c "import tkinter; print(tkinter.TkVersion)"`).
> Apple's system Python (`/usr/bin/python3`) ships **Tk 8.5**, which renders a
> **black/blank window**. Use a Python from [python.org](https://python.org),
> Homebrew, or conda instead.

---

## 📦 Building a Standalone Desktop App

Ready-made build scripts in the project root wrap **PyInstaller** and bundle
everything (Tkinter, `openpyxl`, `Pillow`).

> ⚠️ **Build on the OS you're targeting.** PyInstaller is **not** a cross-compiler:
> running it on macOS produces a macOS `.app`; to get a Windows `.exe` you must
> run the build **on Windows**.

### macOS → `GHCC Library.app`
```bash
bash build.sh            # or:  chmod +x build.sh && ./build.sh
```
- Auto-selects a Python with **Tk ≥ 8.6** (avoids the black-window bug) and
  aborts with guidance if only Tk 8.5 is found.
- Output: **`dist/GHCC Library.app`** — launch with `open "dist/GHCC Library.app"`.

### Windows → `GHCC Library.exe`
Copy the project to a Windows machine, then **double-click `build.bat`**
(or run `build.bat` from a terminal).
- Output: **`dist\GHCC Library.exe`** — a single double-clickable file.

Both scripts: print the Python/Tk version → install build deps → clean old
`build/`, `dist/`, `*.spec` → run PyInstaller (`--windowed`; Windows also `--onefile`).

> 💡 Add an icon with `--icon app.icns` (macOS) / `--icon app.ico` (Windows) inside the script.
> If antivirus flags the Windows one-file `.exe`, remove `--onefile` from
> `build.bat` to get a `dist\GHCC Library\` folder instead.

---

## 🗄️ Where Your Data Lives

The SQLite database (and `library_app.log`) location is chosen automatically:

| How you run it | Database location |
|---|---|
| **Packaged app** — macOS `.app` | `~/Library/Application Support/GHCCLibrary/library.db` |
| **Packaged app** — Windows `.exe` | `%APPDATA%\GHCCLibrary\library.db` |
| **From source** (`python3 main.py`) | project root — `./library.db` |
| **`LIBRARY_APP_DB_PATH` env var set** | that exact path (overrides all of the above) |

> The packaged app and run-from-source mode use **separate** database files, so
> data added in one won't appear in the other.

**Point the app at a specific database:**
```bash
# macOS / Linux
LIBRARY_APP_DB_PATH="/path/to/library.db" open "dist/GHCC Library.app"

# Windows (PowerShell)
$env:LIBRARY_APP_DB_PATH="C:\path\to\library.db"; & ".\dist\GHCC Library.exe"
```

---

## 📖 How to Use

### 1. Adding Books
1. Open the **Books** tab
2. Click **➕ Add Book**
3. Enter title, author, ISBN, year, and total copies
4. Click **Save**

### 2. Adding Members
1. Open the **Members** tab
2. Click **➕ Add Member**
3. Enter name (email and phone are optional)
4. Click **Save**

### 3. Borrowing a Book
1. Open the **Loans** tab
2. Click **📖 Borrow**
3. Search and select a book from the list
4. Search and select a member
5. Set the loan period (default: 14 days)
6. Click **✓ Borrow**

### 4. Renewing a Loan
1. Select an active loan in the **Loans** tab
2. Click **🔁 Renew**
3. Enter extension days
4. Click **✓ Renew**

> Maximum **3 renewals** allowed per loan (configurable in `models.py`).

### 5. Returning a Book
1. Select an active loan
2. Click **↩ Return**

---

## 🗄️ Database Schema

### `books`
| Column            | Type    | Notes                  |
|-------------------|---------|------------------------|
| id                | INTEGER | Primary key            |
| title             | TEXT    | Required               |
| author            | TEXT    | Required               |
| isbn              | TEXT    | Unique, optional       |
| year              | INTEGER | Optional               |
| total_copies      | INTEGER | Default 1              |
| available_copies  | INTEGER | Auto-managed           |

### `members`
| Column   | Type    | Notes                |
|----------|---------|----------------------|
| id       | INTEGER | Primary key          |
| name     | TEXT    | Required             |
| email    | TEXT    | Unique, optional     |
| phone    | TEXT    | Optional             |
| joined   | TEXT    | Auto: today          |

### `loans`
| Column        | Type    | Notes                       |
|---------------|---------|-----------------------------|
| id            | INTEGER | Primary key                 |
| book_id       | INTEGER | FK → books(id)              |
| member_id     | INTEGER | FK → members(id)            |
| borrowed_on   | TEXT    | Default: today              |
| due_on        | TEXT    | Calculated                  |
| returned_on   | TEXT    | NULL while active           |
| renewals      | INTEGER | Default 0, max 3            |

---

## ⚙️ Configuration

Edit constants in `library_app/config.py` to customize:

```python
DEFAULT_LOAN_DAYS   = 14    # Default loan duration
MAX_RENEWALS        = 3     # Max renewals allowed per loan
DEFAULT_RENEW_DAYS  = 7     # Days added per renewal
DEFAULT_COUNTRY_CODE = "91" # Prefix for WhatsApp reminder links
WHATSAPP_TEMPLATE   = "..." # Reminder message body
```

> Tip: set the `LIBRARY_APP_DB_PATH` environment variable to control where the
> database file is stored (see **Where Your Data Lives**).

---

## 🐛 Troubleshooting

**Black / blank window on macOS?**
You're running with **Tk 8.5** (Apple's system Python). Use a Python with
**Tk ≥ 8.6** (python.org / Homebrew / conda). The `build.sh` script picks one
automatically; for running from source, check with
`python3 -c "import tkinter; print(tkinter.TkVersion)"`.

**Database error / corrupted DB?**
Delete the `library.db` file and restart — it will be recreated. Find it via the
**Where Your Data Lives** table above (e.g. `~/Library/Application Support/GHCCLibrary/`
for the packaged macOS app).

**Tkinter not found on Linux?**
```bash
sudo apt-get install python3-tk
```

**App looks different on macOS vs Windows?**
The app uses the `clam` ttk theme for consistency, but native fonts are used per-platform.

---

## 🗺️ Roadmap

- [ ] Export reports to CSV / PDF
- [ ] Fine calculation for overdue loans
- [ ] User authentication (admin / librarian roles)
- [ ] Dark mode toggle
- [ ] Email notifications for due/overdue books
- [ ] Barcode scanning support
- [ ] Multi-language support
- [ ] Cloud-sync option

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Asher Gabriel Jose**

- GitHub: [@your-username](https://github.com/your-username)

---

## ⭐ Show your support

If you found this project helpful, please give it a ⭐ on GitHub!

---

_Built with ❤️ using Python & Tkinter_
