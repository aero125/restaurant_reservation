from datetime import datetime, timedelta

from app.db import DatabaseManager


class DatabaseInitializer(DatabaseManager):
    def create_tables(self):
        self.create_promocodes_table()
        self.create_users_table()
        self.create_tables_table()
        self.create_reservations_table()
        self.create_reservations_completed_table()
        self.create_partition(2024)

    def create_promocodes_table(self):
        self.execute_query(
            """
            CREATE TABLE IF NOT EXISTS promocodes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(10) UNIQUE NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                discount SMALLINT NOT NULL
            );
            """
        )

    def create_users_table(self):
        self.execute_query(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                age SMALLINT NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(20),
                promocode_id INT REFERENCES promocodes(id) ON DELETE SET NULL,
                balance NUMERIC(15, 2) NOT NULL DEFAULT 0.0
            );
            """
        )

    def create_tables_table(self):
        self.execute_query(
            """
            CREATE TABLE IF NOT EXISTS tables (
                id SERIAL PRIMARY KEY,
                table_number INT UNIQUE NOT NULL,
                price NUMERIC(15, 2) NOT NULL,
                seats INT NOT NULL
            );
            """
        )

    def create_reservations_table(self):
        self.execute_query(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                table_id INT REFERENCES tables(id) ON DELETE CASCADE,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                price NUMERIC(15, 2) NOT NULL
            );
            """
        )

    def create_reservations_completed_table(self):
        self.execute_query(
            """
            CREATE TABLE IF NOT EXISTS reservations_completed (
                id SERIAL,
                user_id INT,
                table_id INT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                price NUMERIC(15, 2) NOT NULL,
                name VARCHAR(100) NOT NULL,
                age SMALLINT NOT NULL,
                email VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                promocode_id INT,
                PRIMARY KEY (id, start_time)
            ) PARTITION BY RANGE (start_time);
            """
        )

    def create_partition(self, year):
        for month in range(1, 13):
            start_date = datetime(year, month, 1)
            next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = next_month.strftime("%Y-%m-%d")
            partition_name = f"reservations_completed_{year}{month:02d}"

            self.execute_query(
                f"""
                CREATE TABLE IF NOT EXISTS {partition_name}
                PARTITION OF reservations_completed
                FOR VALUES FROM ('{start_date_str}') TO ('{end_date_str}');
            """
            )


def init_db():
    db_initializer = DatabaseInitializer()
    db_initializer.create_tables()
