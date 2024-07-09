from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession


from src.api.tasks.models import Task
from src.api.tasks.schemas import AddTaskSchema, TaskSchema
from src.api.users.models import User
from src.api.users.schemas import UserCreate
from src.core.security.pwdcrypt import verify_password, password_hasher


async def regisrty_user(
        user_in: UserCreate,
        session: AsyncSession
) -> User:
    hashed_password = password_hasher(user_in.password)
    user_data = user_in.model_dump()
    user_data["hashed_password"] = hashed_password
    del user_data["password"]

    try:
        stmt = insert(User).values(**user_data)
        result = await session.execute(stmt)
        await session.commit()

        # Получение сгенерированного ID
        user_id = result.inserted_primary_key[0]

        # Получение пользователя из базы данных по сгенерированному ID
        user_saved = await session.get(User, user_id)
        return user_saved

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


async def get_user(username: str, session: AsyncSession):
    query = select(User).where(User.username == username)
    result = await session.execute(query)
    try:
        db_dict = result.scalars().all()[0].to_read_model()
    except IndexError:
        return False
    return db_dict


async def get_all_user(session: AsyncSession):
    query = select(User)
    result = await session.execute(query)
    try:
        db_dict = result.scalars().all()
    except IndexError:
        return False
    return db_dict


async def authenticate_user(
    username: str,
    password: str,
    session: AsyncSession
):
    user: User = await get_user(username, session)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_all_tasks(session: AsyncSession, user_id: int):
    query = select(Task).where(Task.user_id == user_id)
    result = await session.execute(query)
    result_model = result.scalars().all()
    return result_model


async def add_task(session: AsyncSession, task: AddTaskSchema, user_id: int):
    task = Task(**task.model_dump(), user_id=user_id)
    session.add(task)
    await session.commit()
    return task.to_read_model()
