from decimal import Decimal
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from app.db import DatabaseManager
from app.models import Table, TableAdd

router = APIRouter()


class TablesService(DatabaseManager):
    def get_tables(self, limit: int, skip: int) -> List[Table]:
        query = "SELECT id, table_number, price, seats FROM tables LIMIT %s OFFSET %s"
        params = (limit, skip)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Tables not found")
        try:
            return [
                Table(id=row[0], table_number=row[1], price=row[2], seats=row[3])
                for row in rows
            ]

        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail={"errors": e.errors(), "message": "Validation Error"},
            )

    def get_table(self, table_id: int) -> List[Table]:
        query = "SELECT id, table_number, price, seats FROM tables WHERE id = %s"
        params = (table_id,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Table not found")
        try:
            return [
                Table(id=row[0], table_number=row[1], price=row[2], seats=row[3])
                for row in rows
            ]

        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail={"errors": e.errors(), "message": "Validation Error"},
            )

    def create_table(self, table: TableAdd) -> dict:
        query = "INSERT INTO tables (table_number, price, seats) VALUES (%s, %s, %s) ON CONFLICT (table_number) DO NOTHING RETURNING id"
        params = (table.table_number, table.price, table.seats)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=400, detail="Table exists")
        table_id = rows[0][0]
        return {"table_id": table_id, "status": "created"}

    def delete_table(self, table_number: int) -> dict:
        query = "SELECT id FROM tables WHERE table_number = %s"
        params = (table_number,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(
                status_code=404, detail="Table with this table_number was not found"
            )
        table_id = rows[0][0]

        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, price FROM reservations WHERE table_id = %s",
                    (table_id,),
                )
                rows = cursor.fetchall()
                for row in rows:
                    user_id = row[0]
                    price = row[1]
                    cursor.execute(
                        "UPDATE users SET balance = balance + %s WHERE id = %s",
                        (price, user_id),
                    )

                cursor.execute(
                    "DELETE FROM tables WHERE id = %s RETURNING id", (table_id,)
                )
                row = cursor.fetchone()
                table_id = row[0]
                conn.commit()
                return {"table_id": table_id, "status": "deleted"}

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(e))

        finally:
            self.release_connection(conn)

    def get_table_info(self, table_id: int) -> tuple[Decimal, int]:
        query = "SELECT price, seats FROM tables WHERE id = %s"
        params = (table_id,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Invalid tables_id")
        price, seats = rows[0]
        return price, seats


service = TablesService()


@router.get("/tables/", response_model=List[Table])
def get_tables(
    limit: Annotated[int, Query(gt=0, le=1000)] = 10,
    skip: Annotated[int, Query(ge=0, le=1000)] = 0,
):
    return service.get_tables(limit, skip)


@router.get("/table/{table_id}", response_model=List[Table])
def get_table(table_id: int):
    return service.get_table(table_id)


@router.post("/table/", response_model=dict)
def create_table(table: TableAdd = Depends()):
    return service.create_table(table)


@router.delete("/table/", response_model=dict)
def delete_table(table_number: int):
    return service.delete_table(table_number)
