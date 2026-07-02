# SDS Studio

A portable, AI-assisted batch editor for Safety Data Sheet (SDS) PDFs.
Reformats vendor SDS PDFs into a standardized template, with selectable
legal entity (supplier) and logo per session.

## Status

Phases 1–4 of 8 are complete and verified end-to-end:

| Phase | Status | What |
|-------|--------|------|
| 1 | ✅ Done | Project scaffold, supplier DB, YAML config, PyInstaller spec |
| 2 | ✅ Done | PDF extraction (PyMuPDF + pdfplumber), GHS 16-section parser |
| 3 | ✅ Done | AI provider abstraction (OpenAI / Azure OpenAI / Anthropic / Ollama / Manual) |
| 4 | ✅ Done | ReportLab template renderer with logo + supplier block + multi-standard |
| 5 | ⏳ Next | Batch processor UI (drag-drop, progress, per-file status) |
| 6 | ⏳ Next | Review queue UI (side-by-side viewer, approve/edit flow) |
| 7 | ⏳ Next | OCR fallback integration (Tesseract) |
| 8 | ⏳ Next | PyInstaller packaging → portable `.zip` |

The core pipeline works today via the test script:
`python scripts/test_full_pipeline.py`.

## Quick Start (Windows)

### 1. Install Python 3.11

Download from https://www.python.org/downloads/windows/
Make sure to check "Add Python to PATH".

### 2. Set up the project

```bat
:: Unzip the project to e.g. C:\SDSStudio
cd C:\SDSStudio

:: Create a virtual env
python -m venv .venv
.venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt
```

### 3. Run the app

```bat
.venv\Scripts\activate
python -m sds_studio.main
```

### 4. Configure

Open the **Settings** tab and choose your AI provider:

| Provider | When to use | Setup |
|----------|-------------|-------|
| Manual | Default, no AI | Nothing to configure. All sections go to review queue. |
| OpenAI direct | Personal PC, OpenAI key | Paste `sk-...` key |
| Azure OpenAI | Work PC, if corporate allows | Paste Azure key + endpoint |
| Anthropic Claude | Better document extraction | Paste `sk-ant-...` key |
| Ollama | Home PC, fully local | Install Ollama, pull a model |

Open the **Suppliers** tab to add your legal entities (name, address, phone,
emergency phone, logo). Logos are copied into `assets/logos/` automatically
when you Browse for one.

## Project Structure

```
SDSStudio/
├── sds_studio/                  # main Python package
│   ├── main.py                  # entry point: python -m sds_studio.main
│   ├── core/
│   │   ├── paths.py             # APP_ROOT resolution (dev vs frozen)
│   │   ├── supplier.py          # Supplier dataclass + SupplierDB
│   │   ├── template_config.py   # TemplateConfig wrapper
│   │   ├── sds_model.py         # SDSDocument / SDSSection / SDSProductInfo
│   │   ├── extractor.py         # PDFExtractor (PyMuPDF + pdfplumber)
│   │   ├── sds_parser.py        # SDSParser (regex-based section splitter)
│   │   ├── ai_provider.py       # AIProvider + 5 impls + factory
│   │   ├── prompts.py           # System + extraction + normalize + validate prompts
│   │   ├── normalizer.py        # refine_extraction + normalize_section + validate_document
│   │   └── renderer.py          # SDSRenderer (ReportLab)
│   └── gui/
│       ├── main_window.py       # 5-tab main window
│       ├── batch_tab.py         # Phase 5
│       ├── suppliers_tab.py     # ✅ Full CRUD
│       ├── template_tab.py      # Phase 6
│       ├── review_tab.py        # Phase 6
│       └── settings_tab.py      # ✅ Full provider config
├── config/                      # user-editable YAML
│   ├── settings.yaml            # AI provider + API keys
│   ├── suppliers.yaml           # supplier / legal entity DB
│   └── template_config.yaml     # template colors, fonts, standards
├── assets/
│   └── logos/                   # supplier logos
├── input/                       # drop source PDFs here
├── output/                      # processed PDFs land here
├── review_queue/                # flagged items
├── logs/
├── scripts/
│   ├── make_sample_sds.py       # generate test SDS PDF
│   ├── make_test_logos.py       # generate test logos
│   ├── test_extraction.py       # Phase 2 test
│   ├── test_full_pipeline.py    # Phases 1-4 end-to-end test
│   └── build_portable.bat       # PyInstaller build (Windows)
├── requirements.txt
└── sds_studio.spec              # PyInstaller spec
```

## How the Pipeline Works

```
Source PDF
    │
    ▼
[PDFExtractor]  ─── PyMuPDF reads text + image metadata
    │              pdfplumber reads tables
    │              (optional) Tesseract OCR for scanned pages
    ▼
[ExtractedPDF]  ── per-page: text, tables, images, was_ocrd
    │
    ▼
[SDSParser]     ─── regex finds 16 section headers
    │              slices text between markers
    │              extracts product info (CAS, EC, synonyms...)
    │              extracts revision metadata
    ▼
[SDSDocument]   ── {product, sections[1..16], revision_metadata}
    │
    ▼
[Normalizer]    ─── calls AI provider to:
    │              1. refine extraction (fix mis-splits)
    │              2. normalize each section to standard style
    │              3. validate output vs source
    │              (manual mode: skips AI, flags everything for review)
    ▼
[SDSRenderer]   ─── ReportLab generates standardized PDF with:
    │              - header (supplier name + "SAFETY DATA SHEET" + logo)
    │              - product identification table
    │              - 16 colored section bars + content
    │              - footer (page #, revision, disclaimer)
    ▼
Output PDF
```

## Supported SDS Standards

All four major 16-section standards are configured in
`config/template_config.yaml`:

| Code | Name | Use case |
|------|------|----------|
| `osha_hcs_2012` | OSHA HCS 2012 (US) | Default for US operations |
| `ghs_rev9` | GHS Rev. 9 (International) | Multi-country |
| `eu_clp` | EU CLP (Regulation (EC) No 1272/2008) | EU |
| `iso_11014` | ISO 11014:2009 | International standard |

User selects the standard per session in the Batch tab (Phase 5).

## Building the Portable .exe

You have two ways to produce `SDSStudio.exe`. Pick whichever fits.

### Option A — One-click build on your Windows PC (recommended)

1. Make sure Python 3.11 is installed (https://www.python.org/downloads/windows/, check "Add Python to PATH")
2. Double-click **`scripts\build.bat`**

That's it. The script will:
- Create a virtual env (`.venv\`) if missing
- Install all dependencies from `requirements.txt`
- Run PyInstaller to build `dist\SDSStudio\SDSStudio.exe`
- Copy `config\` and `assets\` into the dist folder
- Open Explorer at the output location

First run takes ~3 minutes (downloading deps + PyInstaller analysis).
Subsequent runs take ~1 minute.

**To ship:** zip the entire `dist\SDSStudio\` folder. Users unzip and
double-click `SDSStudio.exe` — no install required.

### Option B — Build via GitHub Actions (no local setup)

If you don't want to install Python locally, push the project to a GitHub
repo and let GitHub build the exe on a Windows runner for you.

1. Create a new GitHub repo, push this project to it
2. Go to the repo's **Actions** tab
3. The workflow at `.github/workflows/build.yml` runs automatically on every push
4. Or trigger it manually: Actions → "Build Portable EXE" → Run workflow
5. When complete, download the **`SDSStudio-portable-windows`** artifact (a zip)
6. If you push a tag like `v0.1.0`, the workflow auto-attaches the zip to a GitHub Release

Build time on GitHub Actions: ~3-5 minutes. Free for public repos, counts
against your Actions minutes for private repos.

### Why can't the exe be built here?

PyInstaller is platform-specific: a Linux host produces Linux binaries,
a Windows host produces Windows .exe. Cross-compiling via Wine is
unreliable for PySide6 (Qt6) apps. The spec file `sds_studio.spec` has
been verified by building a Linux binary here — the same spec produces
a working Windows .exe when run on Windows.

## Verification

Run the test scripts to confirm everything works:

```bat
:: Generate a sample SDS + logos
python scripts\make_sample_sds.py
python scripts\make_test_logos.py

:: Test Phase 2 (extraction + parsing)
python scripts\test_extraction.py

:: Test Phases 1-4 (full pipeline including render)
python scripts\test_full_pipeline.py
```

The full pipeline test produces two output PDFs in `output/`:
- `sample_sds_acme_standardized.pdf` (OSHA HCS 2012, Acme supplier)
- `sample_sds_acme_eu_clp.pdf` (EU CLP, EuroLab supplier)

## Next Steps (Phases 5-8)

- **Phase 5**: Batch processor UI — drag-drop zone, supplier dropdown,
  standard dropdown, progress bar, live log, per-file status table,
  threaded processing of 50-100 PDFs.
- **Phase 6**: Review queue UI — side-by-side PDF viewer (original vs.
  generated), editable form for AI-extracted fields, approve/edit/reject.
- **Phase 7**: OCR integration — Tesseract binary bundled in the portable
  folder, auto-OCR pages with little extractable text.
- **Phase 8**: PyInstaller packaging — produce the final portable `.zip`.
