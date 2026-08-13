"""
Language, package manager and framework detection.

Framework tables key on the **exact package that means the framework is in use**,
not on a word that appears inside its name:

    symfony/framework-bundle   means Symfony
    symfony/console            does not — Laravel depends on it

    next                       means Next.js
    next-auth                  does not

That distinction is the whole difference between a detector and a guess.
"""

from pathlib import Path

from coresentinel_core.project.discovery.base import (
    finding, read_json, read_text, normalize_package,
    node_dependencies, php_dependencies, python_dependencies,
    rust_dependencies, go_dependencies, ruby_dependencies)

# (manifest, language). Order matters only for reporting.
LANGUAGE_MARKERS = [
    ("package.json", "Node/TypeScript"),
    ("tsconfig.json", "Node/TypeScript"),
    ("pyproject.toml", "Python"),
    ("requirements*.txt", "Python"),
    ("setup.py", "Python"),
    ("composer.json", "PHP"),
    ("Cargo.toml", "Rust"),
    ("go.mod", "Go"),
    ("Gemfile", "Ruby"),
    ("pom.xml", "Java"),
    ("build.gradle", "Java"),
    ("build.gradle.kts", "Kotlin"),
    ("Package.swift", "Swift"),
    ("mix.exs", "Elixir"),
    ("pubspec.yaml", "Dart"),
    ("*.csproj", "C#"),
    ("*.sln", "C#"),
]

# lockfile -> package manager. A lockfile is proof the manager was actually run;
# the manifest alone only proves someone intended to.
PACKAGE_MANAGERS = [
    ("package-lock.json", "npm"),
    ("yarn.lock", "yarn"),
    ("pnpm-lock.yaml", "pnpm"),
    ("bun.lockb", "bun"),
    ("composer.lock", "composer"),
    ("poetry.lock", "poetry"),
    ("Pipfile.lock", "pipenv"),
    ("uv.lock", "uv"),
    ("pdm.lock", "pdm"),
    ("Cargo.lock", "cargo"),
    ("go.sum", "go modules"),
    ("Gemfile.lock", "bundler"),
    ("mix.lock", "hex"),
    ("pubspec.lock", "pub"),
]

NODE_FRAMEWORKS = {
    "next": "Next.js", "nuxt": "Nuxt", "astro": "Astro", "react": "React",
    "react-dom": "React", "vue": "Vue", "svelte": "Svelte", "@angular/core": "Angular",
    "@remix-run/react": "Remix", "solid-js": "SolidJS",
    "express": "Express", "@nestjs/core": "NestJS", "fastify": "Fastify",
    "koa": "Koa", "hono": "Hono", "@hapi/hapi": "hapi",
    "tailwindcss": "Tailwind CSS", "bootstrap": "Bootstrap",
    "prisma": "Prisma", "@prisma/client": "Prisma", "typeorm": "TypeORM",
    "sequelize": "Sequelize", "drizzle-orm": "Drizzle", "mongoose": "Mongoose",
    "@inertiajs/react": "Inertia", "@inertiajs/vue3": "Inertia",
    "electron": "Electron", "svelte-kit": "SvelteKit", "@sveltejs/kit": "SvelteKit",
}

PHP_FRAMEWORKS = {
    "laravel/framework": "Laravel",
    "symfony/framework-bundle": "Symfony",
    "slim/slim": "Slim",
    "cakephp/cakephp": "CakePHP",
    "yiisoft/yii2": "Yii",
    "codeigniter4/framework": "CodeIgniter",
    "livewire/livewire": "Livewire",
    "inertiajs/inertia-laravel": "Inertia",
    "filament/filament": "Filament",
    "doctrine/orm": "Doctrine ORM",
}

PYTHON_FRAMEWORKS = {
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
    "starlette": "Starlette", "pyramid": "Pyramid", "tornado": "Tornado",
    "sqlalchemy": "SQLAlchemy", "celery": "Celery", "pydantic": "Pydantic",
    "djangorestframework": "Django REST Framework", "litestar": "Litestar",
    "streamlit": "Streamlit", "aiohttp": "aiohttp",
}

RUST_FRAMEWORKS = {
    "actix-web": "Actix Web", "rocket": "Rocket", "axum": "Axum",
    "warp": "Warp", "tokio": "Tokio", "diesel": "Diesel", "sqlx": "SQLx",
}

GO_FRAMEWORKS = {
    "github.com/gin-gonic/gin": "Gin",
    "github.com/labstack/echo/v4": "Echo",
    "github.com/gofiber/fiber/v2": "Fiber",
    "github.com/go-chi/chi/v5": "chi",
    "gorm.io/gorm": "GORM",
}

RUBY_FRAMEWORKS = {
    "rails": "Ruby on Rails", "sinatra": "Sinatra", "hanami": "Hanami",
}


# Source extensions are evidence in their own right: a tree full of .py files is
# a Python project whether or not anyone wrote a manifest. Weaker than a manifest
# only because a handful of files may be tooling rather than the project itself.
SOURCE_LANGUAGES = {
    ".py": "Python", ".ts": "Node/TypeScript", ".tsx": "Node/TypeScript",
    ".js": "Node/TypeScript", ".jsx": "Node/TypeScript", ".php": "PHP",
    ".rb": "Ruby", ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".cs": "C#", ".swift": "Swift", ".ex": "Elixir", ".exs": "Elixir", ".dart": "Dart",
}

MIN_SOURCE_FILES_FOR_LANGUAGE = 3


def detect_languages(root, files=None):
    root = Path(root)
    found, seen = [], set()

    for marker, language in LANGUAGE_MARKERS:
        matches = sorted(root.glob(marker)) if "*" in marker else (
            [root / marker] if (root / marker).exists() else [])
        for path in matches:
            if language in seen:
                continue
            seen.add(language)
            found.append(finding("language", language, path.name,
                                 locator="manifest present", confidence=0.98))

    if files:
        counts = {}
        for name in files:
            language = SOURCE_LANGUAGES.get(Path(name).suffix)
            if language:
                counts[language] = counts.get(language, 0) + 1
        for language, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
            if language in seen or count < MIN_SOURCE_FILES_FOR_LANGUAGE:
                continue
            seen.add(language)
            found.append(finding("language", language, "source tree",
                                 locator=f"{count} source file(s)", confidence=0.9))

    return found


def detect_package_managers(root):
    root = Path(root)
    return [finding("package_manager", manager, lockfile, locator="lockfile present",
                    confidence=0.98)
            for lockfile, manager in PACKAGE_MANAGERS if (root / lockfile).exists()]


def _framework_findings(dependencies, table, manifest):
    found, seen = [], set()
    for package, meta in dependencies.items():
        label = table.get(package)
        if not label or label in seen:
            continue
        seen.add(label)
        found.append(finding("framework", label, manifest,
                             locator=f"{meta['section']}['{package}']",
                             detail=meta.get("version"), confidence=0.97))
    return found


def detect_frameworks(root):
    root = Path(root)
    found = []
    found += _framework_findings(node_dependencies(root), NODE_FRAMEWORKS, "package.json")
    found += _framework_findings(php_dependencies(root), PHP_FRAMEWORKS, "composer.json")
    found += _framework_findings({normalize_package(k): v
                                  for k, v in python_dependencies(root).items()},
                                 PYTHON_FRAMEWORKS, "python dependencies")
    found += _framework_findings(rust_dependencies(root), RUST_FRAMEWORKS, "Cargo.toml")
    found += _framework_findings(go_dependencies(root), GO_FRAMEWORKS, "go.mod")
    found += _framework_findings(ruby_dependencies(root), RUBY_FRAMEWORKS, "Gemfile")
    return found


def detect_runtime_versions(root):
    """Declared runtime floors, where a manifest states one."""
    root = Path(root)
    found = []

    engines = read_json(root / "package.json").get("engines")
    if isinstance(engines, dict) and engines.get("node"):
        found.append(finding("runtime", f"Node {engines['node']}", "package.json",
                             locator="engines.node", confidence=0.98))

    php = php_dependencies(root).get("php")
    if php:
        found.append(finding("runtime", f"PHP {php.get('version')}", "composer.json",
                             locator="require['php']", confidence=0.98))

    pyproject = read_text(root / "pyproject.toml")
    for line in pyproject.splitlines():
        if line.strip().startswith("requires-python"):
            found.append(finding("runtime", f"Python {line.split('=', 1)[1].strip().strip(chr(34))}",
                                 "pyproject.toml", locator="requires-python", confidence=0.98))
            break

    for line in read_text(root / "go.mod").splitlines():
        if line.strip().startswith("go "):
            found.append(finding("runtime", f"Go {line.strip().split()[1]}", "go.mod",
                                 locator="go directive", confidence=0.98))
            break

    return found
