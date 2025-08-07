from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class BookCreate(BaseModel):
    title: str
    author: str
    publication_year: int = Field(..., ge=1450, le=datetime.now().year)
    genre: str
    isbn: str
    
    @validator('isbn')
    def validate_isbn(cls, v):
        # basic isbn validation - remove spaces and check length
        isbn_clean = v.replace('-', '').replace(' ', '')
        if len(isbn_clean) not in [10, 13]:
            raise ValueError('ISBN must be 10 or 13 characters')
        return isbn_clean

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    publication_year: int
    genre: str
    isbn: str

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    publication_year: Optional[int] = Field(None, ge=1450, le=datetime.now().year)
    genre: Optional[str] = None
    isbn: Optional[str] = None