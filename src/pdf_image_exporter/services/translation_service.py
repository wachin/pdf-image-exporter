"""Qt translation loading."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files

from PyQt6.QtCore import QLocale, QTranslator
from PyQt6.QtWidgets import QApplication


@dataclass(frozen=True)
class Language:
    """A language exposed by the application."""

    code: str
    name: str


def available_languages() -> tuple[Language, ...]:
    """Return languages currently exposed by the GUI."""

    return (
        Language("system", "System"),
        Language("en", "English"),
        Language("es", "Español"),
    )


def normalized_language_code(code: str) -> str:
    """Normalize settings values to a supported language code."""

    supported = {language.code for language in available_languages()}
    if code in supported:
        return code
    return "system"


def effective_language_code(code: str) -> str:
    """Resolve ``system`` to the current locale language."""

    normalized = normalized_language_code(code)
    if normalized != "system":
        return normalized
    locale_name = QLocale.system().name().split("_", 1)[0]
    return locale_name if locale_name in {"en", "es"} else "en"


def install_translator(app: QApplication, code: str) -> QTranslator | None:
    """Install a Qt translator when a compiled `.qm` file is available."""

    language = effective_language_code(code)
    if language == "en":
        return None

    qm_path = files("pdf_image_exporter.translations").joinpath(f"app_{language}.qm")
    translator = QTranslator(app)
    if translator.load(str(qm_path)):
        app.installTranslator(translator)
        return translator
    return None
