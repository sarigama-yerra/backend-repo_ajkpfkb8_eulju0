"""
Database Schemas for Social App

Each Pydantic model corresponds to a MongoDB collection (lowercased class name).
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# Auth/User
class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(..., min_length=6, description="Plain on input; hashed before storage")
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=280)

class PublicUser(BaseModel):
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

# Social content
class Post(BaseModel):
    author_id: str
    content: str = Field(..., min_length=1, max_length=1000)
    image_url: Optional[str] = None

class Comment(BaseModel):
    post_id: str
    author_id: str
    content: str = Field(..., min_length=1, max_length=500)

class Like(BaseModel):
    post_id: str
    user_id: str

# For responses
class PostOut(BaseModel):
    id: str
    author: PublicUser
    content: str
    image_url: Optional[str] = None
    likes: int = 0
    comments_count: int = 0
    created_at: datetime

class CommentOut(BaseModel):
    id: str
    author: PublicUser
    content: str
    created_at: datetime
