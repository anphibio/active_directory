from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


SENSITIVE_FIELDS = {
    "ad_bind_password",
    "database_url",
    "jwt_secret",
    "session_secret",
    "encryption_key",
    "app_bootstrap_admin_token",
    "workstation_status_token",
}

REQUIRED_AD_FIELDS = {
    "ad_domain": "AD_DOMAIN",
    "ad_base_dn": "AD_BASE_DN",
    "ad_server": "AD_SERVER",
    "ad_bind_dn": "AD_BIND_DN",
    "ad_bind_password": "AD_BIND_PASSWORD",
}


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8080, alias="APP_PORT")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8080, alias="API_PORT")
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:4173,http://127.0.0.1:4173",
        alias="CORS_ALLOWED_ORIGINS",
    )
    trusted_proxy_cidrs: str = Field(default="", alias="TRUSTED_PROXY_CIDRS")
    ad_domain: str = Field(default="", alias="AD_DOMAIN")
    ad_base_dn: str = Field(default="", alias="AD_BASE_DN")
    ad_default_user_ou: str = Field(default="", alias="AD_DEFAULT_USER_OU")
    ad_default_group_ou: str = Field(default="", alias="AD_DEFAULT_GROUP_OU")
    ad_default_computer_ou: str = Field(default="", alias="AD_DEFAULT_COMPUTER_OU")
    ad_server: str = Field(default="", alias="AD_SERVER")
    ad_bind_dn: str = Field(default="", alias="AD_BIND_DN")
    ad_bind_password: SecretStr = Field(default=SecretStr(""), alias="AD_BIND_PASSWORD")
    ad_login_domain: str = Field(default="", alias="AD_LOGIN_DOMAIN")
    ad_role_admin_group_dn: str = Field(default="", alias="AD_ROLE_ADMIN_GROUP_DN")
    ad_role_operator_group_dn: str = Field(default="", alias="AD_ROLE_OPERATOR_GROUP_DN")
    ad_role_viewer_group_dn: str = Field(default="", alias="AD_ROLE_VIEWER_GROUP_DN")
    ad_role_auditor_group_dn: str = Field(default="", alias="AD_ROLE_AUDITOR_GROUP_DN")
    ad_search_timeout_seconds: int = Field(default=30, alias="AD_SEARCH_TIMEOUT_SECONDS")
    ad_use_ldaps: bool = Field(default=True, alias="AD_USE_LDAPS")
    ad_tls_require_cert: bool = Field(default=True, alias="AD_TLS_REQUIRE_CERT")
    ad_ca_cert_path: str = Field(default="/run/secrets/ad_ca_cert", alias="AD_CA_CERT_PATH")
    allow_insecure_ldap_in_production: bool = Field(
        default=False, alias="ALLOW_INSECURE_LDAP_IN_PRODUCTION"
    )
    require_ldaps_for_writes: bool = Field(default=True, alias="REQUIRE_LDAPS_FOR_WRITES")
    database_url: SecretStr = Field(default=SecretStr(""), alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    jwt_secret: SecretStr = Field(default=SecretStr(""), alias="JWT_SECRET")
    session_secret: SecretStr = Field(default=SecretStr(""), alias="SESSION_SECRET")
    encryption_key: SecretStr = Field(default=SecretStr(""), alias="ENCRYPTION_KEY")
    app_bootstrap_admin_token: SecretStr = Field(
        default=SecretStr(""), alias="APP_BOOTSTRAP_ADMIN_TOKEN"
    )
    workstation_status_token: SecretStr = Field(
        default=SecretStr(""), alias="WORKSTATION_STATUS_TOKEN"
    )
    workstation_status_enabled: bool = Field(default=True, alias="WORKSTATION_STATUS_ENABLED")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    protected_group_patterns: str = Field(
        default=(
            "Domain Admins,Enterprise Admins,Schema Admins,Administrators,"
            "Account Operators,Server Operators,Backup Operators"
        ),
        alias="PROTECTED_GROUP_PATTERNS",
    )
    report_output_dir: str = Field(default="/app/reports", alias="REPORT_OUTPUT_DIR")
    report_retention_days: int = Field(default=90, alias="REPORT_RETENTION_DAYS")
    audit_log_level: str = Field(default="info", alias="AUDIT_LOG_LEVEL")
    audit_database_enabled: bool = Field(default=True, alias="AUDIT_DATABASE_ENABLED")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def missing_ad_variables(self) -> list[str]:
        missing: list[str] = []
        for field_name, env_name in REQUIRED_AD_FIELDS.items():
            value = getattr(self, field_name)
            if isinstance(value, SecretStr):
                is_empty = not value.get_secret_value()
            else:
                is_empty = not str(value).strip()
            if is_empty:
                missing.append(env_name)
        return missing

    def safe_summary(self) -> dict[str, str | bool | int | list[str]]:
        missing_ad_variables = self.missing_ad_variables()
        return {
            "app_env": self.app_env,
            "app_port": self.app_port,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "cors_allowed_origins_configured": bool(self.cors_allowed_origins),
            "trusted_proxy_cidrs_configured": bool(self.trusted_proxy_cidrs),
            "ad_domain_configured": bool(self.ad_domain),
            "ad_base_dn_configured": bool(self.ad_base_dn),
            "ad_default_user_ou_configured": bool(self.ad_default_user_ou),
            "ad_default_group_ou_configured": bool(self.ad_default_group_ou),
            "ad_default_computer_ou_configured": bool(self.ad_default_computer_ou),
            "ad_server_configured": bool(self.ad_server),
            "ad_bind_dn_configured": bool(self.ad_bind_dn),
            "ad_bind_password_configured": bool(self.ad_bind_password.get_secret_value()),
            "ad_login_domain_configured": bool(self.ad_login_domain),
            "ad_role_admin_group_dn_configured": bool(self.ad_role_admin_group_dn),
            "ad_role_operator_group_dn_configured": bool(self.ad_role_operator_group_dn),
            "ad_role_viewer_group_dn_configured": bool(self.ad_role_viewer_group_dn),
            "ad_role_auditor_group_dn_configured": bool(self.ad_role_auditor_group_dn),
            "ad_search_timeout_seconds": self.ad_search_timeout_seconds,
            "ad_use_ldaps": self.ad_use_ldaps,
            "ad_tls_require_cert": self.ad_tls_require_cert,
            "ad_ca_cert_path_configured": bool(self.ad_ca_cert_path),
            "allow_insecure_ldap_in_production": self.allow_insecure_ldap_in_production,
            "require_ldaps_for_writes": self.require_ldaps_for_writes,
            "database_url_configured": bool(self.database_url.get_secret_value()),
            "redis_url_configured": bool(self.redis_url),
            "jwt_secret_configured": bool(self.jwt_secret.get_secret_value()),
            "session_secret_configured": bool(self.session_secret.get_secret_value()),
            "encryption_key_configured": bool(self.encryption_key.get_secret_value()),
            "app_bootstrap_admin_token_configured": bool(
                self.app_bootstrap_admin_token.get_secret_value()
            ),
            "workstation_status_enabled": self.workstation_status_enabled,
            "workstation_status_token_configured": bool(
                self.workstation_status_token.get_secret_value()
            ),
            "access_token_expire_minutes": self.access_token_expire_minutes,
            "protected_group_patterns_configured": bool(self.protected_group_patterns),
            "report_output_dir": self.report_output_dir,
            "report_retention_days": self.report_retention_days,
            "audit_log_level": self.audit_log_level,
            "audit_database_enabled": self.audit_database_enabled,
            "log_format": self.log_format,
            "missing_ad_variables": missing_ad_variables,
            "ad_ready_for_connection_test": len(missing_ad_variables) == 0,
        }

    def protected_groups(self) -> list[str]:
        return [
            item.strip().lower()
            for item in self.protected_group_patterns.split(",")
            if item.strip()
        ]

    def ad_role_group_dns(self) -> dict[str, str]:
        return {
            "admin": self.ad_role_admin_group_dn,
            "operator": self.ad_role_operator_group_dn,
            "viewer": self.ad_role_viewer_group_dn,
            "auditor": self.ad_role_auditor_group_dn,
        }

    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]

    def trusted_proxy_networks(self) -> list[str]:
        return [item.strip() for item in self.trusted_proxy_cidrs.split(",") if item.strip()]

    def production_errors(self) -> list[str]:
        errors: list[str] = []
        if self.app_env.lower() == "production":
            if not self.ad_use_ldaps and not self.allow_insecure_ldap_in_production:
                errors.append("Production requires LDAPS unless explicitly overridden.")
            if self.ad_use_ldaps and not self.ad_tls_require_cert:
                errors.append("Production LDAPS requires certificate validation.")
            if not self.audit_database_enabled:
                errors.append("Production requires persistent audit database.")
            if not any(self.ad_role_group_dns().values()):
                errors.append("Producao exige mapeamento de grupos AD para perfis da aplicacao.")
            if not self.workstation_status_token.get_secret_value():
                errors.append("Producao exige WORKSTATION_STATUS_TOKEN.")
            if self.workstation_status_token.get_secret_value() == "change-me":
                errors.append("Producao exige WORKSTATION_STATUS_TOKEN diferente do padrao.")
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()
