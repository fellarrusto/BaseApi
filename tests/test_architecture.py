"""
Enforces the layer boundaries described in AGENTS.md.

Static check (no app dependencies needed): run with `pytest`.
"""
import ast
from pathlib import Path
from typing import Iterator, List, Optional

APP_DIR = Path(__file__).resolve().parent.parent / "app"
TESTS_DIR = APP_DIR.parent / "tests"

DRIVERS = ["pymongo", "motor", "bson", "asyncpg"]
HTTP_CLIENTS = ["httpx", "requests", "aiohttp"]

# layer folder -> import prefixes it must never use
FORBIDDEN_IMPORTS = {
    "api": [
        "app.db", "app.repositories", "app.models", "app.integrations", "app.jobs",
        *DRIVERS, *HTTP_CLIENTS,
    ],
    "services": ["app.db", "app.api", "app.jobs", "fastapi", "starlette", *DRIVERS, *HTTP_CLIENTS],
    "repositories": [
        "app.db.mongo_storage", "app.db.postgres_storage",
        "app.api", "app.services", "app.integrations", "app.schemas", "app.jobs",
        "fastapi", *DRIVERS, *HTTP_CLIENTS,
    ],
    # Job handlers are entry points like routers: they only call services
    "jobs": [
        "app.api", "app.decorators", "app.repositories", "app.db", "app.integrations",
        "fastapi", *DRIVERS, *HTTP_CLIENTS,
    ],
    "integrations": ["app.api", "app.services", "app.repositories", "app.db", "app.jobs", "fastapi", *DRIVERS],
    "schemas": [
        "app.api", "app.services", "app.repositories", "app.db", "app.integrations", "app.models", "app.jobs",
        *DRIVERS,
    ],
    "models": ["app.api", "app.services", "app.repositories", "app.db", "app.integrations", "app.schemas", "app.jobs"],
    "decorators": [
        "app.api", "app.repositories", "app.db", "app.integrations", "app.models", "app.jobs",
        *DRIVERS, *HTTP_CLIENTS,
    ],
    "core": [
        "app.api", "app.decorators", "app.services", "app.repositories", "app.db", "app.integrations", "app.jobs",
        "fastapi", *DRIVERS, *HTTP_CLIENTS,
    ],
}

# Decorators every endpoint must have, right under the @router.<method>(...) line
ROUTE_DECORATORS = ["handle_errors", "audit_log"]
# Optional decorator: when used, it must come right after ROUTE_DECORATORS
AUTH_DECORATOR = "require_auth"


def _imported_modules(tree: ast.AST) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module
            yield from (f"{node.module}.{alias.name}" for alias in node.names)


def _matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def _python_files(layer: str) -> Iterator[Path]:
    return (APP_DIR / layer).rglob("*.py")


def _decorator_name(node: ast.expr) -> Optional[str]:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_route_decorator(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "router"
    )


def test_layers_respect_import_boundaries() -> None:
    violations: List[str] = []
    for layer, forbidden in FORBIDDEN_IMPORTS.items():
        for path in _python_files(layer):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for module in _imported_modules(tree):
                if any(_matches(module, prefix) for prefix in forbidden):
                    violations.append(f"{path.relative_to(APP_DIR.parent)}: imports {module}")
    assert not violations, "Layer boundary violations (see AGENTS.md):\n" + "\n".join(sorted(set(violations)))


def test_services_use_only_public_repository_methods() -> None:
    # Protected helpers (_find_many, _storage, ...) keep filters inside repositories
    violations: List[str] = []
    for path in _python_files("services"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr.startswith("_")
                and isinstance(node.value, ast.Name)
                and node.value.id.endswith("_repository")
            ):
                violations.append(f"{path.relative_to(APP_DIR.parent)}:{node.lineno}: {node.value.id}.{node.attr}")
    assert not violations, "Services must call repository domain methods only:\n" + "\n".join(violations)


def test_endpoints_use_mandatory_decorators() -> None:
    violations: List[str] = []
    for path in _python_files("api"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef) or not node.decorator_list:
                continue
            if not _is_route_decorator(node.decorator_list[0]):
                continue
            names = [_decorator_name(d) for d in node.decorator_list[1:]]
            mandatory_ok = names[:len(ROUTE_DECORATORS)] == ROUTE_DECORATORS
            auth_ok = AUTH_DECORATOR not in names or names.index(AUTH_DECORATOR) == len(ROUTE_DECORATORS)
            if not (mandatory_ok and auth_ok):
                violations.append(f"{path.relative_to(APP_DIR.parent)}:{node.lineno}: {node.name}")
    assert not violations, (
        "Endpoints must be decorated with @router.<method>, @handle_errors, @audit_log "
        "and optionally @require_auth (in this order):\n" + "\n".join(violations)
    )


def _function_names(tree: ast.AST) -> List[str]:
    return [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def test_every_endpoint_has_tests() -> None:
    # app/api/v1/x_router.py -> tests/api/v1/test_x_router.py with a test_<endpoint>_* per endpoint
    violations: List[str] = []
    for path in (APP_DIR / "api").rglob("*_router.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        endpoints = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.decorator_list and _is_route_decorator(node.decorator_list[0])
        ]
        test_path = TESTS_DIR / path.relative_to(APP_DIR).parent / f"test_{path.name}"
        if not test_path.exists():
            violations.append(f"{path.relative_to(APP_DIR.parent)}: missing {test_path.relative_to(APP_DIR.parent)}")
            continue
        test_names = _function_names(ast.parse(test_path.read_text(encoding="utf-8")))
        for endpoint in endpoints:
            if not any(name.startswith(f"test_{endpoint}_") for name in test_names):
                violations.append(f"{test_path.relative_to(APP_DIR.parent)}: no test_{endpoint}_* test")
    assert not violations, "Endpoints without tests (see Testing in AGENTS.md):\n" + "\n".join(violations)
