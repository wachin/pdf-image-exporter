# PDF Image Exporter Roadmap

## Environment Snapshot

- Python: 3.11.2
- PyQt6: 6.4.2
- Qt: 6.4.2
- `pdftocairo`: 22.12.0 at `/usr/bin/pdftocairo`
- `pdfinfo`: 22.12.0 at `/usr/bin/pdfinfo`
- `dpkg-buildpackage`: 1.21.23
- `lintian`: 2.116.3+deb12u1
- `appstreamcli`: 0.16.1
- `desktop-file-validate`: installed
- `pylupdate6`: 6.4.2
- `lrelease`: 5.15.8
- `pytest`: 7.2.1
- `black`: 23.1.0
- `mypy`: 1.0.1
- `ruff`: not installed in this environment

## Poppler Capabilities Observed

`pdftocairo` 22.12.0 supports the image outputs required for the first milestone:

- PNG: `-png`
- JPEG: `-jpeg`, `-jpegopt <string>`
- TIFF: `-tiff`, `-tiffcompression none|packbits|jpeg|lzw|deflate`
- Page selection: `-f`, `-l`, `-o`, `-e`, `-singlefile`
- Resolution: `-r`, `-rx`, `-ry`
- Pixel scaling: `-scale-to`, `-scale-to-x`, `-scale-to-y`
- Crop options: `-x`, `-y`, `-W`, `-H`, `-sz`, `-cropbox`
- Color options: `-mono`, `-gray`, `-icc`
- PNG transparency: `-transp`
- Rendering: `-antialias <string>`
- Password arguments: `-opw`, `-upw`

`pdfinfo` 22.12.0 supports:

- Page count and document metadata.
- Per-page bounding boxes with `-box` plus `-f` and `-l`.
- ISO dates with `-isodates`.
- Password arguments: `-opw`, `-upw`.

Password limitation: Poppler command-line tools accept passwords as command
arguments, which can expose them to process-list observers on some systems.
The application must never log or store passwords and should document this
external-tool limitation before exposing password support broadly.

## Architecture Decision

The source tree uses a `src/` layout. Core modules are independent from Qt
widgets where practical, while process execution for the GUI is isolated in
services that use `QProcess` with argument lists and no shell. The GUI consumes
models and service signals instead of building command strings itself.

## Verification Log

- Latest check after queue/profile/settings/logging work:
  - `pytest`: passed, 23 tests.
  - `mypy src`: passed, no issues in 30 source files.
  - `python3 -m compileall src tests`: passed.
  - Qt offscreen smoke test with temporary XDG paths: created `MainWindow`,
    loaded 11 built-in profiles and restored page expression `all`.
- Latest check after bounded queue runner work:
  - `pytest`: passed, 26 tests.
  - `mypy src tests/unit/test_conversion_queue_runner.py`: passed, no issues in
    31 source files.
  - `python3 -m compileall src tests`: passed.
  - Real Poppler smoke test through `ConversionQueueRunner`: generated a PDF in
    `/tmp`, converted page 1 at 72 DPI and confirmed the PNG exists.
- Latest check after folder import and manual queue ordering:
  - `pytest`: passed, 29 tests.
  - `mypy src tests/unit/test_conversion_queue_runner.py`: passed, no issues in
    32 source files.
  - Qt offscreen smoke test: created `MainWindow`, loaded 11 profiles and
    restored folder-recursion setting.
- Latest check after stop-after-current queue control:
  - targeted `pytest tests/unit/test_conversion_queue_runner.py tests/unit/test_queue.py`:
    passed, 9 tests.
  - `mypy src tests/unit/test_conversion_queue_runner.py`: passed, no issues in
    32 source files.
- Latest check after GUI conflict policy selector:
  - targeted `pytest tests/unit/test_conflicts.py tests/unit/test_queue.py tests/unit/test_settings_service.py`:
    passed, 9 tests.
  - `mypy src tests/unit/test_conversion_queue_runner.py`: passed, no issues in
    32 source files.
  - Qt offscreen smoke test: conflict selector exposes 4 policies and defaults
    to `cancel`.
- Latest check after first preview implementation:
  - `pytest tests/unit/test_thumbnail_service.py`: passed.
  - `mypy src tests/unit/test_conversion_queue_runner.py`: passed, no issues in
    33 source files.
  - Qt offscreen smoke test: created `MainWindow` with preview controls.
  - Real Poppler smoke test through `ThumbnailService`: generated a temporary
    thumbnail for a one-page PDF and cleaned the cache.
- Latest check after mixed page-size preview indicators:
  - `pytest tests/unit/test_pdfinfo.py`: passed, 2 tests.
  - `mypy src tests/unit/test_conversion_queue_runner.py`: passed, no issues in
    33 source files.
  - Real `pdfinfo -box -f 1 -l N` smoke test confirmed per-page size output.
  - Async `PdfInfoService` smoke test returned 2 page sizes for a 2-page PDF.
- Latest check after user profile storage:
  - `pytest tests/unit/test_profiles.py tests/unit/test_profile_store.py`:
    passed, 4 tests.
  - `mypy src tests/unit/test_conversion_queue_runner.py`: passed, no issues in
    34 source files.
  - Qt offscreen smoke test: loaded 11 built-in profiles and profile action
    buttons.
- Latest check after i18n infrastructure:
  - `pylupdate6`: updated `app_en.ts` and `app_es.ts` with 78 messages.
  - `lrelease`: generated 78 finished translations for English and Spanish
    `.qm` files locally.
  - Qt translator smoke test: Spanish `.qm` loaded successfully.
  - targeted `pytest tests/unit/test_translation_service.py tests/unit/test_settings_service.py`:
    passed, 3 tests.
  - `mypy src tests/unit/test_conversion_queue_runner.py`: passed, no issues in
    36 source files.
- Latest check after accessibility/error/resource-estimate pass:
  - targeted `pytest tests/unit/test_errors.py tests/unit/test_queue.py`: passed,
    7 tests.
  - `mypy src tests/unit/test_conversion_queue_runner.py`: passed, no issues in
    37 source files.
  - Qt offscreen smoke test confirmed accessible names and shortcuts.
  - `pylupdate6`: added 26 new messages, now 104 translation messages.
  - `lrelease`: generated 104 finished translations for English and Spanish
    `.qm` files locally.
- `pytest`: passed, 11 tests.
- `mypy src`: passed, no issues in 24 source files.
- `python3 -m compileall src tests`: passed.
- `env PYTHONPATH=src python3 -m pdf_image_exporter.cli.main --help`: passed.
- `env PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -c '...'`: created
  `MainWindow` and printed `PDF Image Exporter`.
- Poppler smoke test: generated a one-page A4 PDF in `/tmp` with Qt, verified it
  with `pdfinfo`, converted it with `pdftocairo -png -f 1 -l 1 -singlefile -r 72`,
  and confirmed `/tmp/pdf-image-exporter-smoke-out/smoke-001.png` as a
  595 x 842 PNG.
- `timeout 60s black --check src tests`: Black reported all 29 files unchanged,
  but the process did not exit before `timeout` in this environment and returned
  124. Earlier Black reformatted the four reported files successfully.

## Phase 1: research and design

- [x] Inspect repository and current state.
- [x] Check Python, PyQt6, Poppler and Debian packaging tool versions.
- [x] Capture real `pdftocairo` and `pdfinfo` options.
- [x] Define initial format capability model.
- [x] Define architecture and module boundaries.
- [x] Define initial process strategy using `QProcess`.
- [ ] Define complete Debian packaging strategy.
- [ ] Define complete AppImage strategy.

## Phase 2: core

- [x] Create project structure.
- [x] Add central metadata.
- [x] Implement page range parser and validator.
- [x] Implement dimension and paper-size recognition helpers.
- [x] Implement initial conversion configuration models.
- [x] Implement initial output format definitions.
- [x] Implement safe `pdftocairo` argument builder.
- [x] Implement `pdfinfo` parser and Qt service.
- [x] Implement initial output naming.
- [x] Add initial unit tests.
- [x] Implement full conversion queue independent of GUI.
- [x] Implement conversion planning independent of GUI.
- [x] Implement built-in profiles and JSON import/export.
- [x] Implement collision policies.

## Phase 3: GUI mínima funcional

- [x] Create application bootstrap.
- [x] Create main window.
- [x] Add PDF selection.
- [x] Show page count and page size.
- [x] Select PNG, JPEG or TIFF.
- [x] Select DPI.
- [x] Select output directory.
- [x] Convert each selected page to an independent image.
- [x] Show progress.
- [x] Allow cancellation.
- [x] Add drag and drop.
- [x] Add persistent settings.
- [x] Add in-app log viewer.

## Phase 4: batch avanzado

- [x] Queue with configurable concurrency.
- [x] Pause/resume.
- [x] Retry failed jobs.
- [x] Folder import.
- [x] Recursive PDF discovery.
- [x] Conflict policies.
- [x] Conflict policy selector in GUI.
- [x] Manual priority through visible queue ordering.
- [x] Stop after current job.

## Phase 5: previsualización

- [x] Low-resolution thumbnails on demand.
- [x] Selected page preview.
- [x] Zoom controls.
- [x] Temporary cache cleanup.
- [x] Mixed page-size indicators.

## Phase 6: perfiles y configuración

- [x] Built-in default profile definitions.
- [x] User profiles in XDG config.
- [x] Import/export profile serialization helpers.
- [x] Import/export profiles from GUI.
- [x] Delete user-created profiles from GUI.
- [x] Restore defaults.
- [x] QSettings/XDG settings layer.

## Phase 7: internacionalización

- [x] Translation scaffolding.
- [x] English source strings.
- [x] Spanish `.ts`.
- [x] Translator documentation.
- [x] Runtime language selection.

## Phase 8: accesibilidad y pulido

- [x] Keyboard navigation audit.
- [x] Tab order.
- [x] Accessible names.
- [ ] HiDPI checks.
- [x] Resource estimates.
- [x] User-facing error mapping.

## Phase 9: empaquetado Debian

- [ ] `debian/control`.
- [ ] `debian/rules`.
- [ ] `debian/changelog`.
- [ ] `debian/copyright`.
- [ ] Desktop file.
- [ ] AppStream metadata.
- [ ] Manual page.
- [ ] Autopkgtest.
- [ ] `lintian` validation.

## Phase 10: AppImage

- [ ] AppDir layout.
- [ ] Build script.
- [ ] Runtime dependency checks.
- [ ] Document system-`pdftocairo` strategy.
- [ ] AppImage validation.

## Phase 11: documentación y lanzamiento

- [ ] Complete README.
- [ ] CHANGELOG.
- [ ] CONTRIBUTING.
- [ ] SECURITY.
- [ ] DEVELOPMENT.
- [ ] PACKAGING.
- [ ] Initial screenshots.
- [ ] Release checklist.
