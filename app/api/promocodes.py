from datetime import datetime, timedelta
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import EmailStr, ValidationError

from app.db import DatabaseManager
from app.models import Promo, PromoAdd

router = APIRouter()


class PromocodesService(DatabaseManager):
    def get_promos(self, limit: int, skip: int) -> List[Promo]:
        query = "SELECT id, code, created_at, expires_at, discount FROM promocodes LIMIT %s OFFSET %s"
        params = (limit, skip)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Promocodes not found")
        try:
            return [
                Promo(
                    id=row[0],
                    code=row[1],
                    created_at=row[2],
                    expires_at=row[3],
                    discount=row[4],
                )
                for row in rows
            ]

        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail={"errors": e.errors(), "message": "Validation Error"},
            )

    def get_promo(self, promo_id: int) -> List[Promo]:
        query = "SELECT id, code, created_at, expires_at, discount FROM promocodes WHERE id = %s"
        params = (promo_id,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Promocode not found")
        try:
            return [
                Promo(
                    id=row[0],
                    code=row[1],
                    created_at=row[2],
                    expires_at=row[3],
                    discount=row[4],
                )
                for row in rows
            ]

        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail={"errors": e.errors(), "message": "Validation Error"},
            )

    def create_promo(self, promo: PromoAdd) -> dict:
        now = datetime.now()
        if promo.expires_at <= now + timedelta(minutes=10):
            raise HTTPException(
                status_code=400,
                detail="The promo code expires too short. Must be at least 10 minutes",
            )

        query = "INSERT INTO promocodes (code, created_at, expires_at, discount) VALUES (%s, %s, %s, %s) ON CONFLICT (code) DO NOTHING RETURNING id"
        params = (promo.code, now, promo.expires_at, promo.discount)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=400, detail="Duplicate promocode")

        promo_id = rows[0][0]
        return {"promo_id": promo_id, "status": "created"}

    def update_promo(self, promo: PromoAdd) -> dict:
        now = datetime.now()
        if promo.expires_at <= now + timedelta(minutes=10):
            raise HTTPException(
                status_code=400,
                detail="The promo code expires too short. Must be at least 10 minutes",
            )

        now = datetime.now()
        query = "UPDATE promocodes SET (code, created_at, expires_at, discount) = (%s, %s, %s, %s) WHERE code = %s RETURNING id"
        params = (promo.code, now, promo.expires_at, promo.discount, promo.code)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(
                status_code=400, detail="Promocode with this code was not found"
            )
        promo_id = rows[0][0]
        return {"promo_id": promo_id, "status": "updated"}

    def apply_promo(self, email: EmailStr, promocode: str) -> dict:
        """
        Apply a promotional code to a user identified by their email.

        Args:
            email (str): The email address of the user to apply the promo code.
            promocode (str): The promotional code to apply.

        Returns:
            dict: A dictionary containing the user ID and status of the operation.
                Example: {'user_id': 12345, 'status': 'updated'}

        Raises:
            HTTPException: If the promotional code has expired, user with the provided
                        email is not found, or an error occurs during the database update.

        """
        promocode_id, expires_at = self.get_promocode(promocode)
        if datetime.now() >= expires_at:
            raise HTTPException(status_code=400, detail="Promocode has expired")

        query = "SELECT 1 FROM users WHERE email = %s"
        params = (email,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(
                status_code=404, detail="User with this email was not found"
            )

        query = "UPDATE users SET promocode_id = %s WHERE email = %s RETURNING id"
        params = (promocode_id, email)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=400, detail="Error updating users record")
        user_id = rows[0][0]
        return {"user_id": user_id, "status": "updated"}

    def get_promocode(self, promocode: str) -> tuple[int, datetime]:
        """
        Retrieve details of a promotional code from the database.

        Args:
            promocode (str): The promotional code to retrieve details for.

        Returns:
            tuple[int, datetime]: A tuple containing the promotional code ID and its expiration datetime.
                                Example: (123, datetime.datetime(2024, 6, 30, 0, 0))

        Raises:
            HTTPException: If the promotional code is not found in the database.

        """
        query = "SELECT id, expires_at FROM promocodes WHERE code = %s"
        params = (promocode,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Promocode not found")
        promo_id = rows[0][0]
        expires_at = rows[0][1]
        return promo_id, expires_at

    def delete_promo(self, promocode: str) -> dict:
        query = "DELETE FROM promocodes WHERE code = %s RETURNING id"
        params = (promocode,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(
                status_code=404, detail="Promocode with this code was not found"
            )
        promo_id = rows[0][0]
        return {"promo_id": promo_id, "status": "deleted"}


service = PromocodesService()


@router.get("/promos/", response_model=List[Promo])
def get_promos(
    limit: Annotated[int, Query(gt=0, le=1000)] = 10,
    skip: Annotated[int, Query(ge=0, le=1000)] = 0,
):
    return service.get_promos(limit, skip)


@router.get("/promo/{promo_id}", response_model=List[Promo])
def get_promo(promo_id: int):
    return service.get_promo(promo_id)


@router.post("/promo/", response_model=dict)
def create_promo(promo: PromoAdd = Depends()):
    return service.create_promo(promo)


@router.put("/promo/", response_model=dict)
def update_promo(promo: PromoAdd = Depends()):
    return service.update_promo(promo)


@router.post("/apply_promo/", response_model=dict)
def apply_promo(email: EmailStr, promocode: Annotated[str, Query(max_length=10)]):
    return service.apply_promo(email, promocode)


@router.delete("/promo/", response_model=dict)
def delete_promo(promocode: Annotated[str, Query(max_length=10)]):
    return service.delete_promo(promocode)
