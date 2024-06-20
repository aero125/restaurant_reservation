from app.db import DatabaseManager


class DatabaseInitializer(DatabaseManager):
    def create_tables(self):
        self.create_promocodes_table()
        self.create_users_table()
        self.create_tables_table()
        self.create_reservations_table()
        self.create_reservations_completed_table()

    def create_promocodes_table(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(10) UNIQUE NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                discount SMALLINT NOT NULL
            );
            """)
        
    def create_users_table(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                age SMALLINT NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(20),
                promocode_id INT REFERENCES promocodes(id) ON DELETE SET NULL,
                balance NUMERIC(15, 2) NOT NULL DEFAULT 0.0
            );
            """)
        
    def create_tables_table(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS tables (
                id SERIAL PRIMARY KEY,
                table_number INT UNIQUE NOT NULL,
                price NUMERIC(15, 2) NOT NULL,
                seats INT NOT NULL
            );
            """)
        
    def create_reservations_table(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS reservations (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                table_id INT REFERENCES tables(id) ON DELETE CASCADE,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                price NUMERIC(15, 2) NOT NULL
            );
            """)
        
    def create_reservations_completed_table(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS reservations_completed (
                id SERIAL PRIMARY KEY,
                user_id INT,
                table_id INT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                price NUMERIC(15, 2) NOT NULL,
                name VARCHAR(100) NOT NULL,
                age SMALLINT NOT NULL,
                email VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                promocode_id INT
            );
            """)
        
        self.execute_query("CREATE INDEX IF NOT EXISTS idx_start_time ON reservations_completed (start_time);")
        self.execute_query("CREATE INDEX IF NOT EXISTS idx_end_time ON reservations_completed (start_time);")

def init_db():
    db_initializer = DatabaseInitializer()
    db_initializer.create_tables()