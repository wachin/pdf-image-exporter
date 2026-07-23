# Translating PDF Image Exporter

Visible GUI strings are written in English in the Python source and extracted
with Qt Linguist tools.

Update translation sources:

```bash
pylupdate6 src/pdf_image_exporter/**/*.py --ts src/pdf_image_exporter/translations/app_es.ts
```

Some shells do not expand `**` by default. In that case, pass the Python files
explicitly or use your editor's Qt Linguist integration.

Edit translations:

```bash
linguist src/pdf_image_exporter/translations/app_es.ts
```

Compile runtime translation files:

```bash
lrelease src/pdf_image_exporter/translations/app_es.ts -qm src/pdf_image_exporter/translations/app_es.qm
lrelease src/pdf_image_exporter/translations/app_en.ts -qm src/pdf_image_exporter/translations/app_en.qm
```

The `.ts` files are source files and should be committed. The generated `.qm`
files are ignored in this repository and should be produced during packaging or
local development when runtime translation testing is needed.
