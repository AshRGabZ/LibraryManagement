# Build Prompt — GHCC Library Management System

> A single, self-contained specification you can hand to an engineer or an AI
> coding assistant to build this application from scratch with the same
> features, options, and architecture. Copy everything in the block below.
>
> Tip: if handing this to an AI assistant, ask it to scaffold the file tree
> first, then implement layer-by-layer (domain → data → services → ui), testing
> each feature as it goes.

## Recommended build model

This application was built end-to-end with **Claude Code** (Anthropic's official
CLI coding agent), using the **Claude Opus 4 family** (e.g. `claude-opus-4`).
To reproduce it faithfully, use a frontier coding model with strong multi-file
and long-context reasoning:

| Goal | Model | Notes |
|---|---|---|
| **Best quality** (recommended) | **Claude Opus 4.x** (`claude-opus-4-…`) | Handles the full layered architecture, idempotent migrations, and cross-platform edge cases in one pass. |
| **Faster / lower cost** | Claude Sonnet 4.x (`claude-sonnet-4-…`) | Great for most of the build; may need a few more iterations on the trickier UI widgets. |
| **Quick edits only** | Claude Haiku 4.x | Not recommended for the initial build of a project this size. |

Practical guidance for the build session:
- Use an **agentic coding tool** (Claude Code, or any IDE assistant that can
  read/write files and run commands) — not a single chat turn. The app is
  ~25–40 files across the layers below.
- Work **iteratively**: scaffold the tree, then implement domain → data →
  services → ui, and **test each feature** (headless/script-level where possible)
  before moving on.
- Keep the **whole spec in context**; implement the cross-platform robustness
  rules (Windows emoji/strftime, macOS Tk ≥ 8.6, dialog screen-clamping) as you
  build the relevant pieces, not as an afterthought.

---

```text
ROLE
You are a senior Python desktop-application architect. Build a complete,
production-quality cross-platform desktop app from scratch following the
specification below. Use clean layered architecture, SOLID principles, ACID
database transactions, dependency injection, and sensible optimizations.
Write idiomatic, well-commented code and test every feature after building it.

═══════════════════════════════════════════════════════════════════════════
PROJECT: "GHCC Library Management System"
A library management desktop app for books, members, and loans.
═══════════════════════════════════════════════════════════════════════════

TECH STACK
- Python 3.9+ (target 3.13). GUI: Tkinter + ttk (theme "clam"). DB: SQLite 3.
- Standard library only for the core. Optional deps, used with graceful
  fallback if absent:
    • openpyxl  → Excel (.xlsx) import/export (fallback to CSV when missing)
    • Pillow    → book-label image generation (show "install Pillow" if missing)
- No other third-party runtime dependencies. tkinter/sqlite3 are stdlib.

ARCHITECTURE — strict layering, one responsibility per layer:
  library_app/
    domain/        frozen @dataclass entities, no persistence logic
    data/          Database (connection/transactions) + schema + repositories
    services/      business logic, validation, transaction boundaries, DI container
    ui/            Tkinter only: theme, reusable widgets, dialogs, tabs, app shell
    config.py, logging_setup.py, seed.py, __main__.py
  main.py          top-level launcher calling library_app.__main__.main()
Rules: SQL lives only in repositories; services own transactions and translate
sqlite errors into domain exceptions; UI never touches SQL. Pass a single
`Services` container (a frozen dataclass built by `Services.build(db)`) into the
UI via dependency injection.

DATABASE (SQLite, WAL mode, PRAGMA foreign_keys=ON, synchronous=NORMAL).
Provide a `Database` class owning one connection with a `transaction()` context
manager (commit on success, rollback on exception). Schema applied idempotently
on startup (CREATE TABLE IF NOT EXISTS + a list of guarded, append-only
migrations that never lose user data).

Tables:
  categories(id PK, name TEXT NOT NULL UNIQUE)
  languages (id PK, name TEXT NOT NULL UNIQUE)
  authors   (id PK, name TEXT NOT NULL UNIQUE)
  books(id PK, title TEXT NOT NULL,
        author_id   INTEGER REFERENCES authors(id)    ON DELETE SET NULL,
        isbn TEXT UNIQUE, year INTEGER,
        category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
        language_id INTEGER REFERENCES languages(id)  ON DELETE SET NULL,
        total_copies INTEGER NOT NULL DEFAULT 1,
        available_copies INTEGER NOT NULL DEFAULT 1)
  members(id PK, name TEXT NOT NULL, email TEXT UNIQUE, phone TEXT,
          joined TEXT DEFAULT today)   + UNIQUE INDEX (name, phone)
  loans(id PK, book_id FK→books RESTRICT, member_id FK→members RESTRICT,
        borrowed_on TEXT, due_on TEXT, returned_on TEXT (NULL=active),
        renew_count INTEGER DEFAULT 0, copy_id FK→book_copies)
  book_copies(id PK, book_id FK→books ON DELETE CASCADE,
              serial_number TEXT NOT NULL UNIQUE,
              status TEXT CHECK(status IN ('available','borrowed','lost','damaged')))
  Indexes on loans(book_id), loans(member_id), loans(returned_on),
  book_copies(book_id), book_copies(status).
Note: author/category/language are FIRST-CLASS entities (own tables + FK),
all OPTIONAL (nullable). Provide a migration that promotes any legacy free-text
author column into the authors table then drops it (SQLite ≥3.35 DROP COLUMN).

DOMAIN ENTITIES (frozen dataclasses with from_row classmethods):
  Author, Category, Language, Member, Book, BookWithDetails(adds author_name,
  category_name, language_name via JOIN), BookCopy, BookCopyWithBorrower,
  Loan, LoanWithDetails. Book has is_available property.

SERVICES (each takes Database via constructor; container wires them):
  AuthorService / CategoryService / LanguageService: add(name) [unique-checked],
    get, list_all(search), delete (NULLs out the FK on books then deletes).
  BookService: add(title, author_id, isbn, year, category_id, language_id,
    total_copies) → creates book + N physical copies with auto serials
    "B<book_id>-01,02,…"; update (cannot drop total below currently-borrowed);
    delete (blocked if active loans); add_or_merge(...) → if a book with the
    SAME (title case-insensitive, author_id, language_id) exists, ADD the copies
    to it instead of creating a duplicate, returns (book_id, merged:bool);
    list_with_details(search, category_id, language_id) [single JOIN query,
    search matches title/author-name/isbn]; per-copy ops (list_copies,
    update_copy_serial unique-checked).
  MemberService: add/update with name required, email optional, phone optional;
    normalize phone to 10 digits (strip +91/+1/leading 0, else ValidationError);
    block duplicate (name, phone); delete blocked if active loans.
  LoanService: DEFAULT_LOAN_DAYS=14; borrow(book_id, member_id, loan_days,
    borrowed_on) → binds an available copy, decrements availability, sets due
    date; renew(loan_id, extra_days) up to MAX_RENEWALS=3 (DEFAULT_RENEW_DAYS=7);
    return_loan; list_all with filters (active-only, date range); overdue is
    derived (due_on < today and not returned).
  StatsService: overall KPIs (totals, active/overdue loans), loans-per-month,
    most-borrowed books/categories/languages, top borrowers (single GROUP BY
    queries).
  NotificationService: build a wa.me WhatsApp deep-link (country code prefix,
    configurable message template) to remind a member of borrowed books.
  LabelService: render a printable book-label image (Pillow) from a copy serial
    + category; probe common system fonts, fall back to PIL default.
  ExportService: write books to .xlsx (styled headers, frozen row, a "Copies"
    sheet) or .csv fallback.
  ImportService: parse + import books AND members from .xlsx/.csv. Two-phase:
    parse_file/parse_members_file (read+validate, no writes) then import_rows/
    import_members. Flexible header aliases; only Title (books) / Name (members)
    required; resolve-or-CREATE categories/languages/authors by name; books use
    add_or_merge so duplicate rows fold into copies; members go through
    MemberService (phone normalize, dup skip); best-effort with per-row error
    reporting; downloadable templates. Excel needs openpyxl; CSV always works.

UI — THEME & WIDGETS
- "Indigo Library" palette (deep indigo header #1e1b4b, primary #4f46e5, light
  canvas #eef1f8, white surfaces, success/warning/danger, zebra rows). ttk
  "clam" theme with fully custom styles. Cross-platform fonts (Helvetica/SF on
  mac, Segoe UI on Windows). Emoji icons throughout.
- Reusable widgets:
    • build_treeview(columns, height, selectmode) → styled Treeview + scrollbar,
      zebra + status tags; supports "extended" multi-select.
    • TreeviewSorter — type-aware column-header sorting.
    • ScrollableFrame — Canvas+inner frame, autohide scrollbar, width-tracking,
      mouse-wheel support. MUST: (a) only scroll when the wheel event widget
      belongs to it (no bleed to a modal dialog on top), (b) NOT scroll when the
      pointer is over an inner Treeview/Listbox/Text (let the inner scroll),
      (c) unbind the global wheel binding on destroy (safe for transient dialogs).
    • SearchableDropdown — combobox-like field with a LIVE-filtering dropdown
      that does NOT steal keyboard focus (implement as an Entry + a Listbox
      place()d in the same toplevel and lifted; do NOT use ttk's posted listbox,
      which grabs the keyboard). Type to filter, click/↓/Enter to pick, a "None"
      row to clear. Used for category/language/author fields.
    • DateEntry + popup calendar (pure stdlib, no tkcalendar). The frameless
      popup must grab on macOS so clicks register, and restore the parent's grab
      on close. Never name an attribute `_root` (shadows Tk's Misc._root).
    • TabHeader (branded banner + live date/time clock), FormDialog, ui_helpers.
- center_window(window, parent, w, h): center over parent BUT clamp to the
  screen size (minus margins) and re-clamp position so a tall dialog's footer is
  never pushed off-screen on small/scaled displays.
- Every dialog: header on top, action buttons reserved at the BOTTOM (packed
  side="bottom" BEFORE the expanding body so they're never clipped), scrollable
  body where forms are long.

UI — TABS & DIALOGS
- App shell (LibraryApp(tk.Tk)): status bar packed bottom-first, a ttk.Notebook
  with tabs "📚 Books", "🔄 Loans", "⚙️ Admin"; live clock in status bar;
  refresh the tab on switch.
- Books tab: hierarchical tree (book row → physical-copy child rows showing
  serial + status/borrower); single Expand-All/Collapse-All toggle button whose
  label flips; live search; category + language filters; Export button; view/
  download Label for a selected copy.
- Loans tab: loans grouped by member; columns include serial and days-left/
  overdue; Borrow / Renew / Return buttons; "active only" checkbox; "borrowed
  between" date-range filter; sortable columns; Expand/Collapse toggle on the
  far right of the filter row.
- Borrow dialog: category+language filters, searchable book picker (shows
  availability + author) and member picker, manual "borrowed on" date (calendar)
  + loan-days field, live summary line; scrollable body with an outer scrollbar.
- Admin tab: sub-notebook with Dashboard / Manage Books / Manage Members.
    • Dashboard: KPI cards, a bar chart of loans-per-month drawn on a Canvas,
      and top-10 ranked lists; wrapped in a ScrollableFrame.
    • Manage Books: a Books table (ALWAYS sorted by ID, multi-select, buttons
      Add Book / Import / Edit / Copies… / Delete) plus three side-by-side
      management panels — Categories, Languages, Authors — each with search +
      list + Add/Delete; the whole panel hosted in a ScrollableFrame with
      generous fixed list heights (never collapse to one row).
    • Manage Members: a Members table (ALWAYS sorted by ID, multi-select,
      buttons Add Member / Import / Edit / Delete).
- BookDialog (Add/Edit): Title + ISBN + Year + Total Copies fields; Author,
  Category, Language each a SearchableDropdown with a "＋ New" inline-create
  button. On Add, call add_or_merge and, when merged, show "added N copies to
  existing book".
- ManageCopiesDialog: per-copy serial editor. RenewDialog. LabelPreviewDialog
  (preview + save as PNG/PDF/JPG).
- Bulk import dialogs (books & members): share a BaseImportDialog with the
  flow — Download Template → Choose File (.xlsx/.csv) → preview table with a
  per-row ✓ OK / ✗ reason status and a ready/issues count → Import → summary
  (new vs merged/added, auto-created authors/categories/languages, skipped rows
  with reasons). Subclasses only declare columns + parse/import/template calls.
- Bulk delete (books & members): multi-select + Delete removes all selected,
  with a confirmation listing names; best-effort (a record with active loans is
  kept and reported); Edit/Copies require exactly one selection.

CROSS-PLATFORM ROBUSTNESS (must implement):
- Windows: NEVER put emoji inside a datetime.strftime() FORMAT string
  (Windows routes it through a locale codec, often cp1252, which can't encode
  emoji → UnicodeEncodeError). Concatenate emoji in Python around an ASCII-only
  strftime instead.
- macOS: the app must run/build with Tk ≥ 8.6 — Tk 8.5 (Apple's system Python)
  renders a black/blank window. Document this.
- All modal dialogs clamp to the screen and keep footers visible (small/scaled
  laptop screens).

CONFIGURATION & DATA PATHS (config.py):
- DB path resolution order: (1) env var LIBRARY_APP_DB_PATH; (2) if frozen
  (PyInstaller sets sys.frozen) → per-user data dir
  (Windows %APPDATA%\GHCCLibrary, macOS ~/Library/Application Support/GHCCLibrary,
  Linux $XDG_DATA_HOME/GHCCLibrary); (3) dev → project-root ./library.db.
- Log file written next to the DB. Window title "📚 GHCC Library Management",
  default geometry 1280x720, min 1000x600.
- Constants: DEFAULT_LOAN_DAYS=14, MAX_RENEWALS=3, DEFAULT_RENEW_DAYS=7,
  DEFAULT_COUNTRY_CODE="91", a WHATSAPP_TEMPLATE with {name}/{book_list}.

SEED DATA (seed.py, idempotent get-or-create, runs via `python -m library_app.seed`):
diverse sample data — ~18 categories, ~10 languages, ~30 books across genres/
languages, ~12 members, ~18 loans spanning states (active/overdue/returned/
renewed). Goes through the service layer so per-copy serials and availability
stay consistent.

PACKAGING:
- PyInstaller, app name "GHCC Library", --windowed.
- Provide build.sh (macOS) that AUTO-SELECTS a Python with Tk ≥ 8.6 (and aborts
  with guidance otherwise), installs pyinstaller+openpyxl+Pillow, cleans
  build/dist/*.spec, builds the .app. Provide build.bat (Windows, --onefile)
  doing the equivalent. Note that PyInstaller is NOT a cross-compiler (build on
  the target OS). .gitignore: build/, dist/, *.spec, __pycache__/, *.pyc,
  library.db*, *.log, .DS_Store, venvs.

QUALITY BAR:
- Layered, DI, ACID transactions, idempotent migrations, single-query JOINs
  (no N+1), graceful degradation for optional deps, friendly validation errors.
- After building each feature, test it (script-level/headless where possible)
  and confirm the UI builds without exceptions.

Deliver the full source tree, requirements.txt, pyproject.toml, README (run
from source, build scripts, DB location table, troubleshooting), build.sh,
build.bat. Make it attractive, sophisticated, and consistent.
```
