from sqlmodel import Session, select

from app.models import WaitingList, WaitingListCreate


def get_waiting_list_by_email(*, session: Session, email: str) -> WaitingList | None:
    statement = select(WaitingList).where(WaitingList.email == email)
    return session.exec(statement).first()


def create_waiting_list_entry(
    *, session: Session, waiting_list_in: WaitingListCreate
) -> WaitingList:
    db_obj = WaitingList.model_validate(waiting_list_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj
