import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order

app = FastAPI(title="Samsung Shop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Samsung Shop Backend Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Utility to convert ObjectId to string for JSON

def serialize_doc(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# Seed some Samsung products if collection is empty
@app.post("/seed")
def seed_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    count = db["product"].count_documents({})
    if count > 0:
        return {"seeded": False, "message": "Products already exist"}

    sample_products = [
        {
            "title": "Galaxy S24 Ultra",
            "description": "6.8\" QHD+ Dynamic AMOLED 2X, Snapdragon 8 Gen 3, 200MP camera",
            "price": 1299.99,
            "category": "Phones",
            "in_stock": True,
            "brand": "Samsung",
            "image_url": "https://images.samsung.com/is/image/samsung/p6pim/levant/2401/gallery/levant-galaxy-s24-ultra-sm-s928-479333-479333-479333-01-graphite-540x540.jpg",
            "rating": 4.8,
            "stock_qty": 20
        },
        {
            "title": "Galaxy Z Fold5",
            "description": "Foldable 7.6\" AMOLED, flagship performance",
            "price": 1799.0,
            "category": "Phones",
            "in_stock": True,
            "brand": "Samsung",
            "image_url": "https://images.samsung.com/is/image/samsung/p6pim/levant/feature/159705220/levant-feature-galaxy-z-fold5-highlights-kv-537193814?$FB_TYPE_A_JPG$",
            "rating": 4.6,
            "stock_qty": 12
        },
        {
            "title": "Galaxy Buds2 Pro",
            "description": "Hi-Fi sound, ANC, 24-bit audio",
            "price": 229.99,
            "category": "Audio",
            "in_stock": True,
            "brand": "Samsung",
            "image_url": "https://images.samsung.com/is/image/samsung/p6pim/levant/2208/gallery/levant-galaxy-buds2-pro-r510-sm-r510nzaamea-533165865?$FB_TYPE_A_JPG$",
            "rating": 4.5,
            "stock_qty": 50
        },
        {
            "title": "Galaxy Watch6 Classic",
            "description": "Rotating bezel, advanced health tracking",
            "price": 399.99,
            "category": "Wearables",
            "in_stock": True,
            "brand": "Samsung",
            "image_url": "https://images.samsung.com/is/image/samsung/p6pim/levant/2308/gallery/levant-galaxy-watch6-classic-r950-sm-r950nzkamea-537274105?$FB_TYPE_A_JPG$",
            "rating": 4.7,
            "stock_qty": 35
        }
    ]
    for p in sample_products:
        create_document("product", p)
    return {"seeded": True, "count": len(sample_products)}

# Products API
@app.get("/products")
def list_products(category: Optional[str] = None):
    filt = {"brand": "Samsung"}
    if category:
        filt["category"] = category
    docs = get_documents("product", filt)
    return [serialize_doc(d) for d in docs]

# Orders API
@app.post("/orders")
def create_order(order: Order):
    # Basic validation of totals
    calc_subtotal = sum(item.price * item.quantity for item in order.items)
    calc_total = round(calc_subtotal + (order.shipping or 0), 2)
    if round(order.subtotal, 2) != round(calc_subtotal, 2) or round(order.total, 2) != calc_total:
        raise HTTPException(status_code=400, detail="Totals do not match items")

    order_id = create_document("order", order)

    return {"order_id": order_id, "status": "received"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
