import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

import config


def run_migration(sql_path: str) -> None:
    sql = Path(sql_path).read_text(encoding="utf-8")
    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        print(f"Applied {sql_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration(sys.argv[1])
