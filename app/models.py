from pydantic import BaseModel, ConfigDict, Field, EmailStr, conint, constr
from datetime import datetime, timedelta
from decimal import Decimal

class UserAdd(BaseModel):
    name: constr(max_length=100)
    age: conint(ge=18, le=100)
    email: EmailStr
    phone: constr(max_length=100) | None = None

class User(UserAdd):
    id: int
    promocode_id: int | None = None
    balance: Decimal
    model_config = ConfigDict(from_attributes=True)

class PromoAdd(BaseModel):
    code: constr(max_length=10)
    expires_at: datetime = Field(default=datetime.now())
    discount: conint(ge=1, le=99)

class Promo(PromoAdd):
    id: int
    model_config = ConfigDict(from_attributes=True)

class TableAdd(BaseModel):
    table_number: conint(ge=1)
    price: Decimal
    seats: conint(ge=1, le=6)

class Table(TableAdd):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ReservationAdd(BaseModel):
    user_id: int
    table_number: int
    start_time: datetime = Field(default=datetime.now() + timedelta(hours=1))
    end_time: datetime = Field(default=datetime.now() + timedelta(hours=2))

class Reservation(ReservationAdd):
    id: int
    price: Decimal
    model_config = ConfigDict(from_attributes=True)

class CompletedReservation(Reservation):
    name: constr(max_length=100)
    age: conint(ge=18, le=100)
    email: EmailStr
    phone: constr(max_length=100) | None = None
    promocode_id: int | None
    model_config = ConfigDict(from_attributes=True)