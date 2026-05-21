#!/usr/bin/env python3
from pathlib import Path
from urllib.parse import urlparse


REQUIRED = [
    "APP_ENV",
    "APP_PORT",
    "AD_DOMAIN",
    "AD_BASE_DN",
    "AD_SERVER",
    "AD_BIND_DN",
    "AD_BIND_PASSWORD",
    "AD_USE_LDAPS",
    "AD_TLS_REQUIRE_CERT",
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET",
    "SESSION_SECRET",
    "ENCRYPTION_KEY",
    "APP_BOOTSTRAP_ADMIN_TOKEN",
]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    path = Path(".env")
    if not path.exists():
        print("STATUS=error")
        print("ERROR=.env nao encontrado")
        return 1

    values = read_env(path)
    missing = [key for key in REQUIRED if not values.get(key)]
    errors: list[str] = []
    warnings: list[str] = []

    parsed = urlparse(values.get("AD_SERVER", ""))
    scheme = parsed.scheme
    use_ldaps = values.get("AD_USE_LDAPS", "").lower() == "true"
    require_cert = values.get("AD_TLS_REQUIRE_CERT", "").lower() == "true"
    app_env = values.get("APP_ENV", "development").lower()
    allow_insecure_prod = values.get("ALLOW_INSECURE_LDAP_IN_PRODUCTION", "false").lower() == "true"
    audit_database_enabled = values.get("AUDIT_DATABASE_ENABLED", "true").lower() == "true"

    if missing:
        errors.append("Variaveis obrigatorias ausentes: " + ", ".join(missing))
    if scheme not in {"ldap", "ldaps"}:
        errors.append("AD_SERVER deve iniciar com ldap:// ou ldaps://")
    if use_ldaps and scheme != "ldaps":
        errors.append("AD_USE_LDAPS=true, mas AD_SERVER nao usa ldaps://")
    if not use_ldaps and scheme == "ldaps":
        errors.append("AD_USE_LDAPS=false, mas AD_SERVER ainda usa ldaps://")
    if not use_ldaps:
        warnings.append("LDAP simples sem TLS deve ser usado apenas temporariamente ou em rede controlada")
    if app_env == "production" and not use_ldaps and not allow_insecure_prod:
        errors.append("Producao exige LDAPS, salvo override explicito")
    if app_env == "production" and use_ldaps and not require_cert:
        errors.append("Producao com LDAPS exige validacao de certificado")
    if app_env == "production" and not audit_database_enabled:
        errors.append("Producao exige auditoria persistente habilitada")
    if use_ldaps and require_cert:
        cert_path = values.get("AD_CA_CERT_PATH", "")
        local_cert = (
            Path("docker/secrets") / cert_path.removeprefix("/run/secrets/")
            if cert_path.startswith("/run/secrets/")
            else Path(cert_path)
        )
        if not local_cert.exists():
            errors.append("Certificado CA configurado nao encontrado localmente")

    print("STATUS=" + ("error" if errors else "ok"))
    print("AD_SERVER_SCHEME=" + (scheme or "nao_configurado"))
    print("AD_SERVER_PORT=" + str(parsed.port or (636 if scheme == "ldaps" else 389)))
    print("MISSING_COUNT=" + str(len(missing)))
    print("ERROR_COUNT=" + str(len(errors)))
    for error in errors:
        print("ERROR=" + error)
    print("WARNING_COUNT=" + str(len(warnings)))
    for warning in warnings:
        print("WARNING=" + warning)
    print("PRODUCTION_READY=" + str(not errors).lower())
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
