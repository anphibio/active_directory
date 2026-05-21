from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


@contextmanager
def database_connection() -> Iterator[object]:
    import psycopg

    settings = get_settings()
    database_url = settings.database_url.get_secret_value()
    with psycopg.connect(database_url) as connection:
        yield connection


def _ensure_migration_table(connection: object) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )


def _applied_versions(connection: object) -> set[str]:
    _ensure_migration_table(connection)
    with connection.cursor() as cursor:
        cursor.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cursor.fetchall()}


def available_migrations() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_migrations() -> list[str]:
    settings = get_settings()
    if not settings.audit_database_enabled:
        return []

    applied: list[str] = []
    with database_connection() as connection:
        versions = _applied_versions(connection)
        for migration in available_migrations():
            version = migration.stem
            if version in versions:
                continue
            sql = migration.read_text(encoding="utf-8")
            with connection.cursor() as cursor:
                cursor.execute(sql)
                cursor.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT DO NOTHING",
                    (version,),
                )
            connection.commit()
            applied.append(version)
    return applied


def init_database() -> bool:
    try:
        applied = apply_migrations()
        if applied:
            print(
                '{"event":"database_migrations_applied","versions":"'
                + ",".join(applied)
                + '"}',
                flush=True,
            )
        return True
    except Exception as exc:
        print(f'{{"event":"database_init_failed","error":"{exc.__class__.__name__}"}}', flush=True)
        return False
