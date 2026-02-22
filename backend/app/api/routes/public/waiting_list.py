from fastapi import APIRouter
from sqlalchemy.exc import IntegrityError

from app import crud_waiting_list
from app.api.deps import SessionDep
from app.models import Message, WaitingListCreate

router = APIRouter(prefix="/public/waiting-list", tags=["public-waiting-list"])


@router.post("/", response_model=Message)
def create_waiting_list_entry(
    session: SessionDep, waiting_list_in: WaitingListCreate
) -> Message:
    email = str(waiting_list_in.email).strip().lower()
    existing_entry = crud_waiting_list.get_waiting_list_by_email(
        session=session, email=email
    )
    if existing_entry:
        return Message(message="Ya te tenemos registrado.")

    try:
        crud_waiting_list.create_waiting_list_entry(
            session=session,
            waiting_list_in=WaitingListCreate(
                email=email,
                interest=waiting_list_in.interest,
            ),
        )
    except IntegrityError:
        session.rollback()
        return Message(message="Ya te tenemos registrado.")

    return Message(message="Registro recibido. Gracias por unirte a la waiting list.")
