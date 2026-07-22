import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
SOURCE_ROOT = PROJECT_ROOT / "src" / "llmapt"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_domain_does_not_import_outer_layers() -> None:
    forbidden = ("llmapt.api", "llmapt.application", "llmapt.infrastructure", "llmapt.worker")

    violations = {
        str(path.relative_to(PROJECT_ROOT)): sorted(
            module for module in _imported_modules(path) if module.startswith(forbidden)
        )
        for path in (SOURCE_ROOT / "domain").glob("*.py")
    }

    assert not {path: modules for path, modules in violations.items() if modules}


def test_application_does_not_import_delivery_or_infrastructure() -> None:
    forbidden = ("llmapt.api", "llmapt.infrastructure", "llmapt.worker")

    violations = {
        str(path.relative_to(PROJECT_ROOT)): sorted(
            module for module in _imported_modules(path) if module.startswith(forbidden)
        )
        for path in (SOURCE_ROOT / "application").glob("*.py")
    }

    assert not {path: modules for path, modules in violations.items() if modules}
