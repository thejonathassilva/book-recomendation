from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Gender = Literal["M", "F", "Outro"]


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    birth_date: date
    gender: Gender
    region: str = Field(min_length=1, max_length=100)


class UserProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    birth_date: date | None = None
    gender: Gender | None = None
    region: str | None = Field(None, min_length=1, max_length=100)


class UserOut(BaseModel):
    user_id: int
    name: str
    email: str
    birth_date: date
    gender: str
    region: str

    model_config = {"from_attributes": True}


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BookOut(BaseModel):
    book_id: int
    title: str
    author: str | None
    category_id: int | None
    category_name: str | None = None
    price: Decimal | None
    cover_url: str | None
    description: str | None = None

    model_config = {"from_attributes": True}


class RecommendationItem(BaseModel):
    book: BookOut
    score: float


class CategoryWeightUpdate(BaseModel):
    weight: float = Field(gt=0, le=5.0)


class PurchaseCreate(BaseModel):
    book_id: int = Field(ge=1)
    quantity: int = Field(default=1, ge=1, le=50)


class PurchaseOut(BaseModel):
    purchase_id: int
    user_id: int
    book_id: int
    purchase_date: datetime
    price_paid: Decimal | None
    quantity: int

    model_config = {"from_attributes": True}


class PurchaseListItem(BaseModel):
    purchase_id: int
    user_id: int
    book_id: int
    purchase_date: datetime
    price_paid: Decimal | None
    quantity: int
    book_title: str | None = None
    book_author: str | None = None
