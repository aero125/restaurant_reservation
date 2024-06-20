import string
from datetime import datetime, timedelta
from random import choice, randint
from typing import Annotated

import names
from fastapi import APIRouter, HTTPException, Query

from app.db import DatabaseManager

router = APIRouter()


class TestDataService(DatabaseManager):
    def fill_databese(self, count: int) -> dict:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT table_number from tables ORDER BY id DESC LIMIT 1"
                )
                row = cursor.fetchone()
                table_count = row[0] if row else 0

                for _ in range(count):
                    name = names.get_first_name()
                    age = randint(20, 60)
                    email = f"{name}@example.com"
                    phone = f"{randint(88001112233, 88009112233)}"
                    promocode_id = None
                    balance = choice(list(range(1000, 10000, 1000)))
                    cursor.execute(
                        "INSERT INTO users (name, age, email, phone, promocode_id, balance) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (email) DO NOTHING RETURNING id",
                        (name, age, email, phone, promocode_id, balance),
                    )
                    conn.commit()

                    code = "".join(
                        choice(string.ascii_uppercase + string.digits)
                        for _ in range(10)
                    )
                    created_at = datetime.now()
                    expires_at = datetime.now() + timedelta(hours=randint(1, 100))
                    discount = randint(10, 90)
                    cursor.execute(
                        "INSERT INTO promocodes (code, created_at, expires_at, discount) VALUES (%s, %s, %s, %s) ON CONFLICT (code) DO NOTHING RETURNING id",
                        (code, created_at, expires_at, discount),
                    )
                    conn.commit()
                    table_count += 1
                    cursor.execute(
                        "SELECT table_number from tables ORDER BY id DESC LIMIT 1"
                    )
                    row = cursor.fetchone()
                    price = choice(list(range(1000, 10000, 1000)))
                    seats = randint(4, 6)
                    cursor.execute(
                        "INSERT INTO tables (table_number, price, seats) VALUES (%s, %s, %s) ON CONFLICT (table_number) DO NOTHING RETURNING id",
                        (table_count, price, seats),
                    )
                    conn.commit()

                return {"status": "ok", "count": count}

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(e))

        finally:
            self.release_connection(conn)


service = TestDataService()


@router.get("/fill_databese/", response_model=dict)
def fill_databese(count: Annotated[int, Query(gt=0, le=1000)] = 100):
    return service.fill_databese(count)
