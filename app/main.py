import sqlalchemy
import uvicorn
from typing import Optional, List
import databases
from fastapi import FastAPI
from fastapi_users import models as user_models
from fastapi_users import db as users_db
from fastapi_users.authentication import CookieAuthentication
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.db import SQLAlchemyUserDatabase
import sqlalchemy as sa
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from fastapi.middleware.cors import CORSMiddleware

from app.models.product import *


DATABASE_URL = 'sqlite:///./test.db'
SECRET = '6bef18936ac12a9096e9fe7a3ygh3456368fe1f77746346erg6rt6gt34'

metadata = sqlalchemy.MetaData()

item = sqlalchemy.Table(
    "items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("item_name", sqlalchemy.String),
    sqlalchemy.Column("price", sqlalchemy.Float),
    sqlalchemy.Column("phone", sqlalchemy.String),
)


class User(user_models.BaseUser):
    pass


class UserCreate(user_models.BaseUserCreate):
    pass


class UserUpdate(User, user_models.BaseUserUpdate):
    pass


class UserDB(User, user_models.BaseUserDB):
    pass


database = databases.Database(DATABASE_URL)

Base: DeclarativeMeta = declarative_base()


class UserTable(Base, users_db.SQLAlchemyBaseUserTable):
    pass


engine = sa.create_engine(DATABASE_URL, connect_args={'check_same_thread': False})

metadata.create_all(engine)

users = UserTable.__table__


def get_user_db():
    yield users_db.SQLAlchemyUserDatabase(UserDB, database, users)


cookie_authentication = CookieAuthentication(secret=SECRET, lifetime_seconds=3600)

app = FastAPI()


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserManager(BaseUserManager[UserCreate, UserDB]):
    user_db_model = UserDB
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    # added: defaultcallback actions, just a print().
    async def on_after_register(self, user: UserDB, request: Optional[Request] = None):
        print(f'User {user.id} has registered.')

    async def on_after_forgot_password(self, user: UserDB, token: str, request: Optional[Request] = None):
        print(f'User {user.id} has forgot their password. Reset token: {token}')

    async def on_after_request_verify(self, user: UserDB, token: str, request: Optional[Request] = None):
        print(f'Verification requested for user {user.id}. Verification token: {token}')


def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers(
    get_user_manager,
    [cookie_authentication],
    User,
    UserCreate,
    UserUpdate,
    UserDB,
)


@app.on_event('startup')
async def startup():
    await database.connect()


@app.on_event('shutdown')
async def shutdown():
    await database.disconnect()


app.include_router(
    fastapi_users.get_auth_router(cookie_authentication),
    prefix='/auth/jwt',
    tags=['auth'],
)

app.include_router(
    fastapi_users.get_register_router(), prefix='/auth', tags=['auth']
)

app.include_router(
    fastapi_users.get_reset_password_router(), prefix='/auth', tags=['auth'],
)
app.include_router(fastapi_users.get_users_router(), prefix='/users', tags=['users'])


# ???????????????? ???????????????? ?????????????????? ?? ???????????????????????? ????????????????????????
current_active_verified_user = fastapi_users.current_user(active=True, verified=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)


@app.post("/items/", response_model=Item, tags=["items"])
async def create_item(note: ItemIn, user: User = Depends(current_active_verified_user)):
    query = item.insert().values(item_name=note.item_name,
                                 price=note.price,
                                 phone=note.phone)
    last_record_id = await database.execute(query)
    return {**note.dict(), "id": last_record_id}


@app.delete('/items/{id}', tags=["items"])
async def delete_item(id: int, user: User = Depends(current_superuser)):
    query = item.delete().where(item.c.id == id)
    await database.execute(query)
    return {"detail": "item deleted", "status_code": 204}


@app.get("/items/{id}", response_model=Item, tags=["items"])
async def get_item_by_id(id: int):
    query = item.select().where(item.c.id == id)
    return await database.fetch_one(query)


@app.get('/items', response_model=List[Item], tags=["items"])
async def read_items():
    query = item.select()
    return await database.fetch_all(query)


@app.get('/users', response_model=List[User], tags=["test"])
async def read_items():
    pass
    # no attribute 'select'


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)