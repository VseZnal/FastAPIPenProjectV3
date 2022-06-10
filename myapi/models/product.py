from pydantic import BaseModel, Field
from typing import Optional


class Item(BaseModel):
    id: int
    item_name: str
    price: float
    phone: str


class ItemIn(BaseModel):
    item_name: str
    price: float
    phone: str


