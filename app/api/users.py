from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import ValidationError, EmailStr
from typing import List, Annotated
from datetime import datetime
from decimal import Decimal
from app.db import DatabaseManager
from app.models import User, UserAdd
from app.api.promocodes import PromocodesService

router = APIRouter()

class UsersService(DatabaseManager):
    def get_users(self, limit: int, skip: int) -> List[User]:
        query = 'SELECT id, name, age, email, phone, promocode_id, balance FROM users LIMIT %s OFFSET %s'
        params = (limit, skip)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Users not found")
        
        try:
            return [User(id=row[0], name=row[1], age=row[2], email=row[3], phone=row[4], promocode_id=row[5], balance=row[6]) for row in rows]
        
        except ValidationError as e:
            raise HTTPException(status_code=422, detail={"errors": e.errors(), "message": "Validation Error"})
        
    def get_user(self, user_id: int) -> List[User]:
        query = 'SELECT id, name, age, email, phone, promocode_id, balance FROM users WHERE id = %s'
        params = (user_id, )
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="User not found")
        
        try:
            return [User(id=row[0], name=row[1], age=row[2], email=row[3], phone=row[4], promocode_id=row[5], balance=row[6]) for row in rows]
        
        except ValidationError as e:
            raise HTTPException(status_code=422, detail={"errors": e.errors(), "message": "Validation Error"})
        
    def create_user(self, user: UserAdd, promocode: str | None = None) -> dict:
        user_promocode_id = None
        promocode_service = PromocodesService()

        if promocode:
            promocode_id, expires_at = promocode_service.get_promocode(promocode)
            if datetime.now() >= expires_at:
                raise HTTPException(status_code=400, detail="Promocode has expired")
            
            user_promocode_id = promocode_id
    
        query = 'INSERT INTO users (name, age, email, phone, promocode_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (email) DO NOTHING RETURNING id'
        params = (user.name, user.age, user.email, user.phone, user_promocode_id)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=400, detail="Duplicate email")
        user_id = rows[0][0]
        return {"user_id": user_id, "status": "created"}
    
    def fauset_user(self, email: EmailStr, amount: Decimal) -> dict:
        query = 'SELECT balance FROM users WHERE email = %s'
        params = (email, )
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="User with this email was not found")
        balance = rows[0][0]
        new_balance = balance + amount

        query = 'UPDATE users SET balance = %s WHERE email = %s RETURNING id'
        params = (new_balance, email)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="User with this email was not found")
        user_id = rows[0][0]
        return {"user_id": user_id, "status": "ok"}

    def update_user(self, user: UserAdd) -> dict:
        query = 'UPDATE users SET (name, age, email, phone) = (%s, %s, %s, %s) WHERE email = %s RETURNING id'
        params = (user.name, user.age, user.email, user.phone, user.email)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="User with this email was not found")
        user_id = rows[0][0]
        return {"user_id": user_id, "status": "updated"}

    def delete_user(self, email: EmailStr) -> dict:
        query = 'DELETE FROM users WHERE email = %s RETURNING id'
        params = (email,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="User with this email was not found")
        user_id = rows[0][0]
        return {"user_id": user_id, "status": "deleted"}


    def get_balance(self, user_id: int) -> tuple[Decimal, int]:
        query = 'SELECT users.balance, promocodes.discount FROM users \
                    LEFT JOIN promocodes ON users.promocode_id = promocodes.id \
                    WHERE users.id = %s'
        params = (user_id, )
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Invalid user_id")
        balance, discount = rows[0]
        if not discount:
            discount = 0
        return balance, discount

service = UsersService()

@router.get("/users/", response_model=List[User])
def get_users(limit: Annotated[int, Query(gt=0, le=1000)] = 10, skip: Annotated[int, Query(ge=0, le=1000)] = 0):
    return service.get_users(limit, skip)

@router.get("/user/{user_id}", response_model=List[User])
def get_user(user_id: int):
    return service.get_user(user_id)

@router.post("/user/", response_model=dict)
def create_user(user: UserAdd = Depends(), promocode: str | None = None):
    return service.create_user(user, promocode)

@router.post("/fauset_user/", response_model=dict)
def fauset_user(email: EmailStr, amount: Decimal):
    return service.fauset_user(email, amount)

@router.put("/user/", response_model=dict)
def update_user(user: UserAdd = Depends()):
    return service.update_user(user)

@router.delete("/user/", response_model=dict)
def delete_user(email: EmailStr):
    return service.delete_user(email)
