from sqlalchemy import inspect

from backend.database.engine import engine


def main():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("[CHECK] Tablas encontradas en la base de datos:")
    for table in tables:
        print(f" - {table}")


if __name__ == "__main__":
    main()