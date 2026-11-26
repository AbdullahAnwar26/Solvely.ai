"""Source guards for the AI boundary (AD-1, AD-9, AD-12)."""
import ast
import pathlib
import re

API_ROOT = pathlib.Path(__file__).resolve().parents[1]
GEMINI_ADAPTER = API_ROOT / "ai" / "providers" / "gemini.py"
SKIPPED_DIRS = {
    ".venv", "venv", "tests", "node_modules", "__pycache__", "staticfiles", "migrations"
}
MODEL_LITERAL = re.compile(r"gemini-", re.IGNORECASE)


def application_files():
    for path in API_ROOT.rglob("*.py"):
        relative = path.relative_to(API_ROOT)
        if any(part in SKIPPED_DIRS or part.startswith(".") for part in relative.parts[:-1]):
            continue
        yield path


def imports_genai(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == "google.genai" or alias.name.startswith("google.genai.")
                   for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "google.genai" or module.startswith("google.genai."):
                return True
            if module == "google" and any(alias.name == "genai" for alias in node.names):
                return True
        elif isinstance(node, ast.Call):
            # importlib.import_module("google.genai") and __import__("google.genai")
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and (
                    arg.value == "google.genai" or arg.value.startswith("google.genai.")
                ):
                    return True
    return False


def test_scan_finds_application_code():
    files = {p.relative_to(API_ROOT).as_posix() for p in application_files()}
    assert "ai/providers/gemini.py" in files
    assert "ai/service.py" in files
    assert not any(f.startswith("tests/") for f in files)


def test_only_the_gemini_adapter_imports_google_genai():
    offenders = [
        path.relative_to(API_ROOT).as_posix()
        for path in application_files()
        if path != GEMINI_ADAPTER
        and imports_genai(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    ]
    assert offenders == []
    assert imports_genai(ast.parse(GEMINI_ADAPTER.read_text(encoding="utf-8")))


def test_import_detector_catches_every_form():
    for source in (
        "import google.genai",
        "import google.genai.types as t",
        "from google import genai",
        "from google.genai import types",
        "import importlib\nimportlib.import_module('google.genai')",
    ):
        assert imports_genai(ast.parse(source)), source
    assert not imports_genai(ast.parse("import google.auth"))


def test_no_model_id_literal_in_application_code():
    offenders = []
    for path in application_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if MODEL_LITERAL.search(line):
                offenders.append(f"{path.relative_to(API_ROOT).as_posix()}:{number}")
    # Config files too, except the documented .env.example.
    for name in ("pyproject.toml", "requirements.txt", "requirements-dev.txt"):
        config = API_ROOT / name
        if config.exists() and MODEL_LITERAL.search(config.read_text(encoding="utf-8")):
            offenders.append(name)
    assert offenders == []


def test_settings_have_no_default_model():
    settings_source = (API_ROOT / "config" / "settings.py").read_text(encoding="utf-8")
    assert 'GEMINI_MODEL = env("GEMINI_MODEL", default="")' in settings_source


def test_env_example_documents_the_model_without_a_key():
    text = (API_ROOT / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^GEMINI_API_KEY=$", text, re.MULTILINE)
    assert re.search(r"^GEMINI_MODEL=$", text, re.MULTILINE)
    assert re.search(r"^AI_PROVIDER=gemini$", text, re.MULTILINE)
