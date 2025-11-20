"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    address: Optional[str] = Field(None, description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")
    brand: Optional[str] = Field("Samsung", description="Brand name")
    image_url: Optional[str] = Field(None, description="Primary image URL")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Average rating")
    stock_qty: Optional[int] = Field(0, ge=0, description="Units available")

class OrderItem(BaseModel):
    product_id: str = Field(..., description="Referenced product _id as string")
    title: str = Field(..., description="Snapshot of product title")
    price: float = Field(..., ge=0, description="Snapshot of price at purchase time")
    quantity: int = Field(..., ge=1, description="Units purchased")
    image_url: Optional[str] = None

class Order(BaseModel):
    """
    Orders collection schema
    Collection name: "order"
    """
    customer_name: str = Field(..., description="Customer full name")
    customer_email: EmailStr = Field(..., description="Customer email")
    shipping_address: str = Field(..., description="Shipping address")
    items: List[OrderItem] = Field(..., description="List of purchased items")
    subtotal: float = Field(..., ge=0)
    shipping: float = Field(0.0, ge=0)
    total: float = Field(..., ge=0)

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
