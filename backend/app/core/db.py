from sqlmodel import Session, create_engine, select

from app import crud_admin
from app import crud_users as crud
from app.core.config import settings
from app.models import User, UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), pool_pre_ping=True)


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def ping_postgres() -> None:
    with Session(engine) as session:
        session.exec(select(1))


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    crud_admin.seed_admin_roles(session=session)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

    if settings.SYSTEM_ADMIN_EMAIL and settings.SYSTEM_ADMIN_PASSWORD:
        system_admin = crud_admin.get_admin_user_by_email(
            session=session, email=str(settings.SYSTEM_ADMIN_EMAIL)
        )
        if not system_admin:
            system_role = crud_admin.get_admin_role_by_code(
                session=session, code="system"
            )
            if system_role:
                crud_admin.create_admin_user(
                    session=session,
                    email=str(settings.SYSTEM_ADMIN_EMAIL),
                    password=settings.SYSTEM_ADMIN_PASSWORD,
                    role=system_role,
                )
