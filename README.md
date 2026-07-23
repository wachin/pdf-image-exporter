# PDF Image Exporter

PDF Image Exporter is a GNU/Linux desktop application for converting PDF pages
to image files with Poppler's `pdftocairo`.

This repository currently contains an early implementation: a modular
Python/PyQt6 application with a safe Poppler process layer, PDF inspection via
`pdfinfo`, page-range parsing, output naming, conversion planning, built-in
profiles, persistent settings, logging, unit tests, and a minimal GUI.

## Requirements

- Python 3.11 or newer
- PyQt6
- `poppler-utils` (`pdftocairo` and `pdfinfo`)

On Debian or Ubuntu:

```bash
sudo apt install python3 python3-pyqt6 poppler-utils
```

## Run from source

```bash
PYTHONPATH=src python3 -m pdf_image_exporter
```

CLI smoke usage:

```bash
PYTHONPATH=src pdf-image-exporter-cli input.pdf --format png --dpi 300
```

## Current status

The project is in early development. See `ROADMAP.md` for completed and pending
items. The current GUI can add PDFs, add a folder of PDFs, optionally discover
PDFs recursively, accept PDF drag and drop, reorder documents to control queue
priority, inspect page count and size, select a built-in profile, select
PNG/JPEG/TIFF, choose DPI, select page ranges, choose an output folder, convert
one page at a time through `QProcess`, run a bounded conversion queue, pause
after running pages finish, retry failed pages, show progress, cancel active
conversion processes, stop after the currently running page batch, persist basic
settings, choose the output-file conflict policy, and show an in-app log viewer.

Current built-in profiles include screen/messaging, web, social media, screen
reading, print, lossless archive, light JPEG, thumbnails, and OCR-oriented
output. User-editable profile management is still pending.

## Development checks

```bash
PYTHONPATH=src pytest
PYTHONPATH=src mypy src
PYTHONPATH=src python3 -m compileall src tests
```

## Security and privacy

The application runs offline and does not include telemetry, analytics,
automatic updates, cloud services, or document upload features. PDF files are
treated as untrusted input and rendered by Poppler. Keep Poppler updated through
your distribution security updates.

Passwords are not logged or stored. Poppler command-line tools accept passwords
as process arguments, which can be visible to local process-list observers on
some systems; broad password UI support remains pending until this limitation is
documented in the application.

## License

GPL-3.0-or-later.
