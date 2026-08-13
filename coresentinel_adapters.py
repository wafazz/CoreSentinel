#!/usr/bin/env python3
"""
CoreSentinel Host Adapter Layer
Makes CoreSentinel assistant-agnostic: one vendor-neutral Core (Memory, Governance,
Context, Verification, Telemetry) projected onto each AI coding host's native transport.

    Claude Code | Cursor | Gemini CLI | Codex | Antigravity | Copilot | Windsurf | Generic
                                    |
                            CoreSentinel Core
"""

import os
import sys
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = SCRIPT_DIR / "memory"
REGISTRY_FILE = SCRIPT_DIR / "adapters.json"

MANAGED_MARKER = "<!-- CORESENTINEL:MANAGED -->"
ADAPTER_VERSION = "1.0.0"
SERVICES = ["memory", "governance", "context", "verification", "telemetry"]

CAP_ICON = {"native": "◉ native", "file": "◈ file", "cli": "◇ cli", "none": "· none"}


def read_core_version():
    path = SCRIPT_DIR / "VERSION"
    try:
        return path.read_text(encoding="utf-8-sig").strip() or "unknown"
    except OSError as e:
        print(f"[!] VERSION file unreadable ({e}) — reported as 'unknown'", file=sys.stderr)
        return "unknown"


def load_registry():
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading adapter registry: {e}", file=sys.stderr)
        return {"adapters": []}


def get_adapters():
    return load_registry().get("adapters", [])


def find_adapter(adapter_id):
    key = (adapter_id or "").lower().replace("_", "-")
    for a in get_adapters():
        if a["id"] == key or a["name"].lower() == key or a["id"].split("-")[0] == key:
            return a
    return None


def resolve_path(raw, target_dir="."):
    if not raw:
        return None
    if raw.startswith("~"):
        return Path(os.path.expanduser(raw))
    return (Path(target_dir).resolve() / raw.lstrip("./")).resolve()


# ---------------------------------------------------------------- detection

def detect_adapter(adapter, target_dir="."):
    """Return (installed, active, evidence) for a single host adapter."""
    evidence = []
    installed = False
    for marker in adapter.get("detect", []):
        p = resolve_path(marker, target_dir)
        if p and p.exists():
            installed = True
            evidence.append(str(p))

    active = False
    for var in adapter.get("detect_env", []):
        if os.environ.get(var):
            active = True
            evidence.append(f"env:{var}")

    return installed, active, evidence


def detect_hosts(target_dir="."):
    print_header("Host Adapter Detection")
    print(f"  Scan Root         : {os.path.abspath(target_dir)}")
    print(f"  Adapter Layer     : v{ADAPTER_VERSION}")
    print("  " + "-" * 60)

    detected = []
    for adapter in get_adapters():
        installed, active, evidence = detect_adapter(adapter, target_dir)
        if active:
            status, icon = "ACTIVE", "[◉]"
        elif installed:
            status, icon = "INSTALLED", "[✓]"
        else:
            status, icon = "NOT FOUND", "[ ]"
        print(f"  {icon} {adapter['name']:<26} : {status:<10} ({adapter['id']})")
        if evidence:
            print(f"      └─ {evidence[0]}")
        if installed or active:
            detected.append(adapter)

    print("  " + "-" * 60)
    print(f"  Hosts Detected    : {len(detected)}/{len(get_adapters())}")
    if detected:
        print("  Sync Command      : coresentinel adapter sync " + detected[0]["id"])
    print("=" * 64 + "\n")
    return detected


# ---------------------------------------------------------------- listing

def print_header(title):
    print("\n" + "=" * 64)
    print(f"  🛡️  CoreSentinel Adapter Layer — {title}")
    print("=" * 64)


def list_adapters():
    registry = load_registry()
    adapters = registry.get("adapters", [])
    print_header("Registered Host Adapters")
    print(f"  Registry Version  : {registry.get('version', ADAPTER_VERSION)}")
    print(f"  Registered Hosts  : {len(adapters)}")
    print("  " + "-" * 60)
    print(f"  {'HOST':<24} {'FORMAT':<10} {'TRANSPORT':<14} STATUS")
    print("  " + "-" * 60)

    for a in adapters:
        installed, active, _ = detect_adapter(a)
        status = "ACTIVE" if active else ("INSTALLED" if installed else "-")
        print(f"  {a['name']:<24} {a['format']:<10} {a['transport']:<14} {status}")

    print("\n  Capability Matrix (Core service ➔ host consumption channel):")
    print("  " + "-" * 60)
    header = f"  {'HOST':<24}" + "".join(f"{s[:7].upper():<10}" for s in SERVICES)
    print(header)
    for a in adapters:
        caps = a.get("capabilities", {})
        row = f"  {a['name']:<24}"
        for s in SERVICES:
            row += f"{CAP_ICON.get(caps.get(s, 'none'), '· none'):<10}"
        print(row)

    print("\n  Legend: ◉ native  ◈ rules file  ◇ coresentinel CLI  · unsupported")
    print("=" * 64 + "\n")


def show_adapter(adapter_id, target_dir="."):
    adapter = find_adapter(adapter_id)
    if not adapter:
        print(f"\n[!] Unknown adapter '{adapter_id}'. Run: coresentinel adapter list\n")
        return False

    installed, active, evidence = detect_adapter(adapter, target_dir)
    print_header(f"Adapter Card: {adapter['name']}")
    print(f"  Adapter ID        : {adapter['id']}")
    print(f"  Vendor            : {adapter['vendor']}")
    print(f"  Surface           : {adapter['surface']}")
    print(f"  Transport         : {adapter['transport']} ({adapter['format']})")
    print(f"  Detection Status  : {'ACTIVE' if active else ('INSTALLED' if installed else 'NOT FOUND')}")
    print("  " + "-" * 60)
    print("  Bind Targets:")
    print(f"     • Global Scope  : {adapter.get('global_path') or '(not supported by host)'}")
    print(f"     • Project Scope : {adapter.get('project_path') or '(not supported by host)'}")
    print("  " + "-" * 60)
    print("  Core Service Bindings:")
    caps = adapter.get("capabilities", {})
    for s in SERVICES:
        print(f"     • {s.capitalize():<14} : {CAP_ICON.get(caps.get(s, 'none'), '· none')}")
    print("  " + "-" * 60)
    print(f"  Host Extensions   : {', '.join(adapter.get('extensions', [])) or 'None'}")
    if evidence:
        print(f"  Detection Evidence: {evidence[0]}")
    print(f"  Notes             : {adapter.get('notes', '-')}")
    print("=" * 64 + "\n")
    return True


# ---------------------------------------------------------------- core payload

def read_identity():
    identity = {"name": "Iris", "role": "Universal coding agent"}
    identity_file = SCRIPT_DIR / "00-identity.md"
    if not identity_file.exists():
        print(f"[!] 00-identity.md not found — falling back to default identity '{identity['name']}'", file=sys.stderr)
        return identity
    try:
        text = identity_file.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"[!] Cannot read 00-identity.md ({e}) — falling back to default identity", file=sys.stderr)
        return identity
    name = re.search(r"^-\s*Name:\s*\*\*(.+?)\*\*", text, re.M)
    role = re.search(r"^-\s*Role:\s*(.+)$", text, re.M)
    if name:
        identity["name"] = name.group(1).strip()
    if role:
        identity["role"] = role.group(1).replace("**", "").strip()
    return identity


def collect_protocols():
    protocols = []
    for path in sorted(SCRIPT_DIR.glob("[0-9][0-9]-*.md")):
        title = path.stem
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"[!] Protocol '{path.name}' unreadable ({e}) — indexed by filename only", file=sys.stderr)
            protocols.append({"file": path.name, "title": title})
            continue
        for line in text.splitlines():
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                break
        protocols.append({"file": path.name, "title": title})
    return protocols


def count_anti_patterns():
    path = SCRIPT_DIR / "anti-patterns.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return len(json.load(f).get("anti_patterns", []))
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"[!] Anti-pattern database unreadable ({e}) — Core payload will report 0 rules", file=sys.stderr)
        return 0


def read_gates():
    path = MEMORY_DIR / "gates.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("gates", {})
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"[!] Quality gate state unreadable ({e}) — Core payload will use the default gate order", file=sys.stderr)
        return {}


def memory_layer_counts():
    layers = {}
    for name in ["working", "session", "project", "longterm", "failures", "patterns"]:
        path = MEMORY_DIR / f"{name}.json"
        count = 0
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                count = len(data.get("facts", [])) if isinstance(data, dict) else len(data)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                print(f"[!] Memory layer '{name}' unreadable ({e}) — reported as 0 entries", file=sys.stderr)
        layers[name] = count
    return layers


def build_core_payload(compact=False):
    """Render the vendor-neutral CoreSentinel Core as host-agnostic markdown."""
    identity = read_identity()
    protocols = collect_protocols()
    gates = read_gates()
    layers = memory_layer_counts()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    core_dir = str(SCRIPT_DIR)

    lines = []
    lines.append(MANAGED_MARKER)
    lines.append(f"<!-- Generated by CoreSentinel Adapter Layer v{ADAPTER_VERSION} on {stamp}. "
                 "Regenerate with: coresentinel adapter sync <host> --apply -->")
    lines.append("")
    lines.append("# CoreSentinel Core — Universal AI Agent Governance Layer")
    lines.append("")
    lines.append(f"You are **{identity['name']}**. Role: {identity['role']}.")
    lines.append(f"CoreSentinel Core lives at: `{core_dir}`")
    lines.append("")
    lines.append("## Non-Negotiable Governance Rules")
    lines.append("- Never claim work is done without evidence. Run `coresentinel verify` and cite its output.")
    lines.append("- Never mutate governance, security, or identity rules directly — file a proposal via "
                 "`coresentinel evolve propose` and wait for human approval.")
    lines.append("- Read files before editing them. Match existing code style exactly. No unrequested refactors.")
    lines.append(f"- Respect the anti-pattern database ({count_anti_patterns()} rules) at `anti-patterns.json`.")
    lines.append("- Record every architectural choice with `coresentinel decision add`.")
    lines.append("")
    lines.append("## Quality Gates")
    if gates:
        lines.append("Ordered gates — each must reach PASS or WAIVED before the next begins:")
        lines.append("")
        lines.append("`" + " ➔ ".join(gates.keys()) + "`")
    else:
        lines.append("`Plan ➔ Architecture ➔ Security ➔ Implementation ➔ Test ➔ Review ➔ Verification ➔ Deployment`")
    lines.append("")
    lines.append("## Memory Contract")
    lines.append("Load context from the CoreSentinel layered memory engine, never from assumption:")
    lines.append("")
    for name, count in layers.items():
        lines.append(f"- `memory/{name}.json` — {count} recorded entr{'y' if count == 1 else 'ies'}")
    lines.append("")
    lines.append("Facts carry confidence scores: `>= 0.90` Known, `>= 0.50` Assumed, below that Unknown. "
                 "Never present an Assumed fact as verified.")
    lines.append("")
    lines.append("## Verification & Telemetry Commands")
    lines.append("```bash")
    lines.append(f'cd "{core_dir}"')
    # Rendered with the interpreter that is actually running on this machine.
    # These lines are instructions an agent follows verbatim, and bare `python`
    # does not exist on macOS or on Linux installs that ship only python3 — the
    # agent was being handed a command that could not run.
    for command, description in [
            ("verify", "Evidence-Based Verification Suite"),
            ("gate status", "Quality Gates pipeline state"),
            ("score --explain", "Health scorecard with the basis for every number"),
            ("memory show", "Layered memory & confidence matrix"),
            ("audit list", "AI accountability audit trail"),
            ("adapter export", "Host-agnostic context bundle (JSON)")]:
        lines.append(f'"{sys.executable}" coresentinel.py {command:<16} # {description}')
    lines.append("```")
    lines.append("")
    lines.append("A verification check that reports UNKNOWN did not run and is not a pass. "
                 "Never describe an UNKNOWN or INDETERMINATE result as verified.")
    lines.append("")

    if not compact:
        lines.append("## Protocol Index")
        lines.append("")
        for p in protocols:
            lines.append(f"- `{p['file']}` — {p['title']}")
        lines.append("")

    lines.append("## Squad Contracts")
    lines.append("17 specialist contracts with explicit input/output artifacts and authority boundaries are defined in "
                 "`squad-contracts.json`. Inspect with `coresentinel squad show <name>` before delegating work.")
    lines.append("")
    return "\n".join(lines)


def render_for_adapter(adapter, payload):
    """Wrap the neutral core payload in the host's native rules format."""
    fmt = adapter.get("format", "markdown")
    if fmt == "mdc":
        frontmatter = (
            "---\n"
            "description: CoreSentinel Universal AI Agent Governance Core\n"
            "globs: **/*\n"
            "alwaysApply: true\n"
            "---\n\n"
        )
        return frontmatter + payload
    return payload


# ---------------------------------------------------------------- sync

def sync_adapter(adapter_id, scope="global", apply_changes=False, force=False, target_dir="."):
    adapter = find_adapter(adapter_id)
    if not adapter:
        print(f"\n[!] Unknown adapter '{adapter_id}'. Run: coresentinel adapter list\n")
        return False

    raw_path = adapter.get("global_path") if scope == "global" else adapter.get("project_path")
    if not raw_path:
        other = "project" if scope == "global" else "global"
        print(f"\n[!] {adapter['name']} does not support {scope} scope. Retry with --scope {other}.\n")
        return False

    dest = resolve_path(raw_path, target_dir)
    compact = adapter["id"] == "windsurf"
    payload = render_for_adapter(adapter, build_core_payload(compact=compact))

    print_header(f"Sync Core ➔ {adapter['name']}")
    print(f"  Adapter ID        : {adapter['id']}")
    print(f"  Bind Scope        : {scope}")
    print(f"  Target File       : {dest}")
    print(f"  Render Format     : {adapter['format']}{' (compact profile)' if compact else ''}")
    print(f"  Payload Size      : {len(payload.encode('utf-8'))} bytes")
    print("  " + "-" * 60)

    exists = dest.exists()
    managed = False
    if exists:
        try:
            managed = MANAGED_MARKER in dest.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  [!] Cannot read existing target ({e}) — treating it as unmanaged")

    if exists and not managed and not force:
        print(f"  [✗] BLOCKED — target exists and is not CoreSentinel-managed.")
        print(f"      Hand-authored host rules will not be silently overwritten.")
        print(f"      Review the file, then re-run with --force to back it up and replace it.")
        print("=" * 64 + "\n")
        return False

    if not apply_changes:
        print("  [!] DRY RUN — nothing written. Re-run with --apply to bind.")
        print("  " + "-" * 60)
        preview = payload.splitlines()[:14]
        print("  Payload Preview:")
        for line in preview:
            print(f"      {line}")
        print(f"      ... ({len(payload.splitlines())} lines total)")
        print("=" * 64 + "\n")
        return True

    backup = None
    if exists and not managed:
        backup = dest.with_suffix(dest.suffix + ".coresentinel.bak")
        shutil.copy2(dest, backup)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(payload, encoding="utf-8")

    print(f"  [✓] SYNCED — CoreSentinel Core bound to {adapter['name']}")
    if backup:
        print(f"      └─ Previous file backed up to: {backup}")
    print("=" * 64 + "\n")
    return True


# ---------------------------------------------------------------- export

def build_context_bundle(target_dir="."):
    """The CoreSentinel API payload — one normalized bundle any host can consume."""
    identity = read_identity()
    gates = read_gates()
    installed = []
    active = None
    for adapter in get_adapters():
        is_installed, is_active, _ = detect_adapter(adapter, target_dir)
        if is_installed or is_active:
            installed.append(adapter["id"])
        if is_active and not active:
            active = adapter["id"]

    return {
        "coresentinel_api": "1.0",
        "coresentinel_version": read_core_version(),
        "adapter_layer_version": ADAPTER_VERSION,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "core_dir": str(SCRIPT_DIR),
        "host": {
            "active": active,
            "installed": installed,
            "registered": [a["id"] for a in get_adapters()]
        },
        "identity": identity,
        "governance": {
            "protocols": len(collect_protocols()),
            "anti_pattern_rules": count_anti_patterns(),
            "quality_gates": {name: g.get("status", "PENDING") for name, g in gates.items()},
            "evolution_policy": "Human approval required for all rule mutations"
        },
        "memory": {
            "layers": memory_layer_counts(),
            "confidence_thresholds": {"known": 0.90, "assumed": 0.50}
        },
        "verification": {
            "command": "coresentinel verify",
            "evidence_required": ["Code Change", "Test Execution", "Lint", "Security Audit",
                                  "Dependency Audit", "Git Diff"],
            "pass_threshold": 80
        },
        "telemetry": {
            "command": "coresentinel stats",
            "log": "agent-usage-log.json"
        }
    }


def export_context(target_dir=".", as_json=False):
    bundle = build_context_bundle(target_dir)
    if as_json:
        print(json.dumps(bundle, indent=2))
        return bundle

    print_header("Host-Agnostic Context Bundle")
    print(f"  API Contract      : coresentinel_api v{bundle['coresentinel_api']}")
    print(f"  Generated At      : {bundle['generated_at']}")
    print(f"  Active Host       : {bundle['host']['active'] or '(none detected)'}")
    print(f"  Installed Hosts   : {', '.join(bundle['host']['installed']) or '(none)'}")
    print("  " + "-" * 60)
    print(f"  Identity          : {bundle['identity']['name']} — {bundle['identity']['role']}")
    print(f"  Protocols         : {bundle['governance']['protocols']} files")
    print(f"  Anti-Pattern Rules: {bundle['governance']['anti_pattern_rules']}")
    gate_states = bundle["governance"]["quality_gates"]
    passed = sum(1 for s in gate_states.values() if s == "PASS")
    print(f"  Quality Gates     : {passed}/{len(gate_states)} PASS" if gate_states else "  Quality Gates     : (not yet run)")
    print("  " + "-" * 60)
    print("  Memory Layers:")
    for name, count in bundle["memory"]["layers"].items():
        print(f"     • {name:<12} : {count} entries")
    print("  " + "-" * 60)
    print(f"  Verification      : {bundle['verification']['command']} "
          f"(pass >= {bundle['verification']['pass_threshold']}/100)")
    print(f"  Telemetry         : {bundle['telemetry']['command']}")
    print("\n  Emit machine-readable bundle: coresentinel adapter export --json")
    print("=" * 64 + "\n")
    return bundle


if __name__ == "__main__":
    argv = sys.argv[1:]
    cmd = argv[0].lower() if argv else "list"
    if cmd == "list":
        list_adapters()
    elif cmd == "detect":
        detect_hosts()
    elif cmd == "show":
        show_adapter(argv[1] if len(argv) > 1 else "claude-code")
    elif cmd == "sync":
        aid = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else "claude-code"
        sc = argv[argv.index("--scope") + 1] if "--scope" in argv else "global"
        sync_adapter(aid, sc, "--apply" in argv, "--force" in argv)
    elif cmd == "export":
        export_context(".", "--json" in argv)
    else:
        list_adapters()
