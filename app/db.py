import os

import psycopg2
from psycopg2 import pool


class DatabaseManager:
    def __init__(self):
        DB_USER = os.getenv("POSTGRES_USER")
        DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
        DB_HOST = "db"
        DB_NAME = os.getenv("POSTGRES_DB")

        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20, dsn=DATABASE_URL
        )

    def get_connection(self):
        return self.connection_pool.getconn()

    def release_connection(self, conn):
        self.connection_pool.putconn(conn)

    def execute_query(
        self, sql_str: str, params: tuple | None = None, fetch: bool = False
    ):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql_str, params or ())
                conn.commit()
                if fetch:
                    return cursor.fetchall()
        finally:
            self.release_connection(conn)
