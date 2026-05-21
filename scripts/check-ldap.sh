#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
from urllib.parse import urlparse
import shutil
import subprocess


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


if shutil.which("ldapsearch") is None:
    print("STATUS=error")
    print("ERROR=ldapsearch nao encontrado")
    raise SystemExit(1)

path = Path(".env")
if not path.exists():
    print("STATUS=error")
    print("ERROR=.env nao encontrado")
    raise SystemExit(1)

values = read_env(path)
required = ["AD_SERVER", "AD_BIND_DN", "AD_BIND_PASSWORD", "AD_BASE_DN"]
missing = [key for key in required if not values.get(key)]
if missing:
    print("STATUS=error")
    print("ERROR=variaveis AD obrigatorias ausentes: " + ",".join(missing))
    raise SystemExit(1)

parsed = urlparse(values["AD_SERVER"])
port = parsed.port or (636 if parsed.scheme == "ldaps" else 389)
print(f"TARGET_SCHEME={parsed.scheme}")
print(f"TARGET_PORT={port}")
print(f"TARGET_HOST_CONFIGURED={bool(parsed.hostname)}")

command = [
    "ldapsearch",
    "-x",
    "-LLL",
    "-H",
    values["AD_SERVER"],
    "-D",
    values["AD_BIND_DN"],
    "-w",
    values["AD_BIND_PASSWORD"],
    "-b",
    values["AD_BASE_DN"],
    "-s",
    "base",
    "(objectClass=*)",
    "defaultNamingContext",
]

result = subprocess.run(command, capture_output=True, text=True, timeout=20)
if result.returncode == 0:
    print("LDAP_BIND=ok")
    raise SystemExit(0)

combined = result.stderr + "\n" + result.stdout
for secret in (
    values.get("AD_BIND_PASSWORD", ""),
    values.get("AD_BIND_DN", ""),
    values.get("AD_BASE_DN", ""),
    parsed.hostname or "",
):
    if secret:
        combined = combined.replace(secret, "[redacted]")

print("LDAP_BIND=error")
for line in combined.splitlines()[:8]:
    if line.strip():
        print(line[:220])
raise SystemExit(result.returncode)
PY
