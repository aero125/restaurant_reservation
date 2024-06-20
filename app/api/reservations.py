from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from app.api.tables import TablesService
from app.api.users import UsersService
from app.db import DatabaseManager
from app.models import CompletedReservation, Reservation, ReservationAdd

router = APIRouter()


class ReservationsService(DatabaseManager):
    def get_reservations(self, limit: int, skip: int) -> List[Reservation]:
        query = "SELECT id, user_id, table_id, start_time, end_time, price FROM reservations LIMIT %s OFFSET %s"
        params = (limit, skip)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Reservations not found")
        try:
            return [
                Reservation(
                    id=row[0],
                    user_id=row[1],
                    table_id=row[2],
                    start_time=row[3],
                    end_time=row[4],
                    price=row[5],
                )
                for row in rows
            ]

        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail={"errors": e.errors(), "message": "Validation Error"},
            )

    def get_reservation(self, reservation_id: int) -> List[Reservation]:
        query = "SELECT id, user_id, table_id, start_time, end_time, price FROM reservations WHERE id = %s"
        params = (reservation_id,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Reservation not found")
        try:
            return [
                Reservation(
                    id=row[0],
                    user_id=row[1],
                    table_id=row[2],
                    start_time=row[3],
                    end_time=row[4],
                    price=row[5],
                )
                for row in rows
            ]

        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail={"errors": e.errors(), "message": "Validation Error"},
            )

    def check_reservation(
        self, table_id: int, start_time: datetime, end_time: datetime
    ) -> None:
        """
        Check if a table is available for reservation within the specified time range.

        Args:
            table_id (int): The ID of the table to check for reservation availability.
            start_time (datetime): The start time of the reservation period.
            end_time (datetime): The end time of the reservation period.

        Raises:
            HTTPException: If the table is already reserved for the specified time range.
                        Status code 400 is returned with the detail message indicating
                        that the table is not available for reservation.

        """
        query = "SELECT * FROM reservations \
                WHERE table_id = %s AND (start_time < %s AND end_time > %s)"
        params = (table_id, end_time, start_time)
        rows = self.execute_query(query, params, fetch=True)
        if rows:
            raise HTTPException(
                status_code=400,
                detail="Table is already reserved for the specified time.",
            )

    def create_reservation(self, seats: int, reservation: ReservationAdd) -> dict:
        if reservation.start_time >= reservation.end_time:
            raise HTTPException(
                status_code=400, detail="The start time is greater than the end time."
            )

        if reservation.start_time < datetime.now():
            raise HTTPException(
                status_code=400,
                detail="The reservation start date must not start earlier than the current time.",
            )

        if reservation.start_time + timedelta(hours=1) >= reservation.end_time:
            raise HTTPException(
                status_code=400, detail="Minimum reservation time 1 hour."
            )

        table_service = TablesService()
        price, available_seats = table_service.get_table_info(reservation.table_id)

        if seats > available_seats:
            raise HTTPException(
                status_code=400, detail=f"This table only seats {available_seats}."
            )

        users_service = UsersService()
        balance, discount = users_service.get_balance(reservation.user_id)
        discount_amount = price * (Decimal(discount) / Decimal(100))
        final_price = price - discount_amount
        if final_price > balance:
            raise HTTPException(
                status_code=400, detail="Insufficient money for reservation."
            )

        self.check_reservation(
            reservation.table_id, reservation.start_time, reservation.end_time
        )

        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO reservations (user_id, table_id, start_time, end_time, price) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (
                        reservation.user_id,
                        reservation.table_id,
                        reservation.start_time,
                        reservation.end_time,
                        final_price,
                    ),
                )
                reservation_id = cursor.fetchone()[0]

                cursor.execute(
                    "UPDATE users SET balance = balance - %s WHERE id = %s",
                    (final_price, reservation.user_id),
                )

                conn.commit()
                return {"reservation_id": reservation_id, "status": "created"}

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(e))

        finally:
            self.release_connection(conn)

    def apply_reservation(self, reservation_id: int) -> dict:
        """
        Move a reservation from 'reservations' table to 'reservations_completed' table and delete it.

        Args:
            reservation_id (int): The ID of the reservation to be moved and completed.

        Returns:
            dict: A dictionary containing the IDs of the completed reservation and the original reservation,
                along with a status indicating the operation was successful.
                Example: {
                    "reservation_completed_id": 123,
                    "reservation_id": 456,
                    "status": "moved"
                }

        Raises:
            HTTPException: If the reservation with the specified ID is not found, or if an error occurs
                        during database operations (inserting into 'reservations_completed' or deleting
                        from 'reservations'). The exception detail provides information about the error.
        """
        query = "SELECT r.id, r.user_id, r.table_id, r.start_time, r.end_time, r.price, u.name, u.age, u.email, u.phone, u.promocode_id \
                   FROM reservations r \
                   LEFT JOIN users u ON r.user_id = u.id \
                   WHERE r.id = %s"
        params = (reservation_id,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Reservation not found")
        row = rows[0]
        user_id = row[1]
        table_id = row[2]
        start_time = row[3]
        end_time = row[4]
        price = row[5]
        name = row[6]
        age = row[7]
        email = row[8]
        phone = row[9]
        promocode_id = row[10]

        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO reservations_completed (
                               user_id,
                               table_id,
                               start_time,
                               end_time,
                               price,
                               name,
                               age,
                               email,
                               phone,
                               promocode_id
                               ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (
                        user_id,
                        table_id,
                        start_time,
                        end_time,
                        price,
                        name,
                        age,
                        email,
                        phone,
                        promocode_id,
                    ),
                )
                row = cursor.fetchone()
                reservation_completed_id = row[0]

                cursor.execute(
                    "DELETE FROM reservations WHERE id = %s RETURNING id",
                    (reservation_id,),
                )
                row = cursor.fetchone()
                reservation_id = row[0]

                conn.commit()
                return {
                    "reservation_completed_id": reservation_completed_id,
                    "reservation_id": reservation_id,
                    "status": "moved",
                }

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(e))

        finally:
            self.release_connection(conn)

    def cancel_reservation(self, reservation_id: int) -> dict:
        """
        Cancel a reservation and refund the user's balance.

        Args:
            reservation_id (int): The ID of the reservation to be canceled.

        Returns:
            dict: A dictionary containing the ID of the canceled reservation, the user ID,
                and a status indicating the cancellation was successful.
                Example: {
                    "reservation_id": 123,
                    "user_id": 456,
                    "status": "cancel"
                }

        Raises:
            HTTPException: If the reservation with the specified ID is not found, or if an error occurs
                        during database operations (updating user balance or deleting reservation).
                        The exception detail provides information about the error.
        """
        query = "SELECT user_id, price FROM reservations WHERE id = %s"
        params = (reservation_id,)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(status_code=404, detail="Reservation not found")
        row = rows[0]
        user_id = row[0]
        price = row[1]

        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET balance = balance + %s WHERE id = %s RETURNING id",
                    (price, user_id),
                )
                row = cursor.fetchone()
                user_id = row[0]

                cursor.execute(
                    "DELETE FROM reservations WHERE id = %s RETURNING id",
                    (reservation_id,),
                )
                row = cursor.fetchone()
                reservation_id = row[0]

                conn.commit()
                return {
                    "reservation_id": reservation_id,
                    "user_id": user_id,
                    "status": "cancel",
                }

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(e))

        finally:
            self.release_connection(conn)


class CompletedReservationsService(DatabaseManager):
    def get_completed_reservations(
        self, limit: int, skip: int
    ) -> List[CompletedReservation]:
        """
        Retrieve completed reservations with pagination.

        Args:
            limit (int): Maximum number of completed reservations to retrieve.
            skip (int): Number of completed reservations to skip from the beginning.

        Returns:
            List[CompletedReservation]: A list of CompletedReservation objects representing
                                        completed reservations retrieved from the database.

        Raises:
            HTTPException: If no completed reservations are found based on the provided limit and skip,
                        or if there's a validation error while constructing CompletedReservation objects.
                        The exception detail provides information about the error.
        """
        query = "SELECT id, user_id, table_id, start_time, end_time, price, name, age, email, phone, promocode_id FROM reservations_completed LIMIT %s OFFSET %s"
        params = (limit, skip)
        rows = self.execute_query(query, params, fetch=True)
        if not rows:
            raise HTTPException(
                status_code=404, detail="Reservations completed not found"
            )
        try:
            return [
                CompletedReservation(
                    id=row[0],
                    user_id=row[1],
                    table_id=row[2],
                    start_time=row[3],
                    end_time=row[4],
                    price=row[5],
                    name=row[6],
                    age=row[7],
                    email=row[8],
                    phone=row[9],
                    promocode_id=row[10],
                )
                for row in rows
            ]

        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail={"errors": e.errors(), "message": "Validation Error"},
            )


service = ReservationsService()
service_completed = CompletedReservationsService()


@router.get("/reservations/", response_model=List[Reservation])
def get_reservations(
    limit: Annotated[int, Query(gt=0, le=1000)] = 10,
    skip: Annotated[int, Query(ge=0, le=1000)] = 0,
):
    return service.get_reservations(limit, skip)


@router.get("/reservation/{reservation_id}", response_model=List[Reservation])
def get_reservation(reservation_id: int):
    return service.get_reservation(reservation_id)


@router.post("/reservation/", response_model=dict)
def create_reservation(
    seats: Annotated[int, Query(gt=0, le=6)], reservation: ReservationAdd = Depends()
):
    return service.create_reservation(seats, reservation)


@router.post("/apply_reservation/{reservation_id}", response_model=dict)
def apply_reservation(reservation_id: int):
    return service.apply_reservation(reservation_id)


@router.post("/cancel_reservation/{reservation_id}", response_model=dict)
def cancel_reservation(reservation_id: int):
    return service.cancel_reservation(reservation_id)


@router.get("/completed_reservations/", response_model=List[CompletedReservation])
def get_completed_reservations(
    limit: Annotated[int, Query(gt=0, le=1000)] = 10,
    skip: Annotated[int, Query(ge=0, le=1000)] = 0,
):
    return service_completed.get_completed_reservations(limit, skip)
