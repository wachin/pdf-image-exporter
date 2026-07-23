# Packaging

## Debian and Ubuntu

Install build tools:

```bash
sudo apt install devscripts debhelper dh-python pybuild-plugin-pyproject \
  python3-all python3-pyqt6 python3-pytest python3-setuptools \
  qt6-tools-dev-tools poppler-utils lintian appstream desktop-file-utils
```

Check build dependencies:

```bash
dpkg-checkbuilddeps
```

Build the binary package:

```bash
dpkg-buildpackage -b -us -uc
```

Review the result:

```bash
lintian ../*.changes
```

The Debian package builds translations from `.ts` sources with `lrelease` during
`debian/rules override_dh_auto_build`. The generated `.qm` files are not
committed to the source tree.

The package depends on the system `poppler-utils` package. It does not download
dependencies during build and does not provide an internal updater.

## Metadata Validation

Validate desktop and AppStream files:

```bash
desktop-file-validate src/pdf_image_exporter/resources/desktop/io.github.pdfimageexporter.PDFImageExporter.desktop
appstreamcli validate --no-net src/pdf_image_exporter/resources/metainfo/io.github.pdfimageexporter.PDFImageExporter.metainfo.xml
```
