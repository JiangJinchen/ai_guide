"""Apply all idempotent project migrations to PostgreSQL."""

from pathlib import Path

from app.database import engine


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def migrate() -> int:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    statements = []
    for migration_file in migration_files:
        sql = migration_file.read_text(encoding="utf-8")
        statements.extend(
            statement.strip()
            for statement in sql.split(";")
            if statement.strip() and statement.strip().upper() not in {"BEGIN", "COMMIT"}
        )
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
    return len(statements)


if __name__ == "__main__":
    print(f"已执行 {migrate()} 条数据库迁移语句")
