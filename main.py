import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import User, PublicUser, Post, Comment, Like, PostOut, CommentOut

# Auth settings
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI(title="Social Media API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utilities
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    username: str
    password: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    # Fetch user from DB
    if db is None:
        raise HTTPException(500, "Database not connected")
    user_doc = db["user"].find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise credentials_exception
    user_doc["_id"] = str(user_doc["_id"])
    return user_doc


# Health
@app.get("/")
def root():
    return {"message": "Social Media Backend Running"}


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


# Auth Endpoints
@app.post("/auth/signup", response_model=Token)
def signup(user: User):
    if db is None:
        raise HTTPException(500, "Database not connected")
    # unique email/username checks
    if db["user"].find_one({"email": user.email}):
        raise HTTPException(400, "Email already registered")
    if db["user"].find_one({"username": user.username}):
        raise HTTPException(400, "Username already taken")

    data = user.model_dump()
    hashed = get_password_hash(data.pop("password"))
    data["password_hash"] = hashed
    data.pop("password", None)

    user_id = create_document("user", data)
    access_token = create_access_token({"sub": user_id})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/login", response_model=Token)
def login(payload: LoginRequest):
    if db is None:
        raise HTTPException(500, "Database not connected")
    user_doc = db["user"].find_one({"username": payload.username})
    if not user_doc:
        raise HTTPException(400, "Incorrect username or password")
    if not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(400, "Incorrect username or password")
    access_token = create_access_token({"sub": str(user_doc["_id"])})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=PublicUser)
async def me(current_user=Depends(get_current_user)):
    return {
        "id": str(current_user["_id"]),
        "username": current_user.get("username"),
        "email": current_user.get("email"),
        "full_name": current_user.get("full_name"),
        "avatar_url": current_user.get("avatar_url"),
        "bio": current_user.get("bio"),
    }


# Posts
@app.post("/posts", response_model=PostOut)
async def create_post(post: Post, current_user=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(401, "Not authenticated")
    data = post.model_dump()
    data["author_id"] = str(current_user["_id"])  # enforce
    post_id = create_document("post", data)

    out = await get_post_out(post_id)
    return out


@app.get("/posts", response_model=List[PostOut])
async def list_posts(skip: int = 0, limit: int = 20, current_user=Depends(get_current_user)):
    if db is None:
        raise HTTPException(500, "Database not connected")
    docs = db["post"].find({}).sort("created_at", -1).skip(skip).limit(limit)
    result = []
    for d in docs:
        result.append(await build_post_out(d))
    return result


@app.post("/posts/{post_id}/like")
async def like_post(post_id: str, current_user=Depends(get_current_user)):
    if db is None:
        raise HTTPException(500, "Database not connected")
    # ensure post exists
    try:
        _ = db["post"].find_one({"_id": ObjectId(post_id)})
    except Exception:
        raise HTTPException(404, "Post not found")
    exists = db["like"].find_one({"post_id": post_id, "user_id": str(current_user["_id"])})
    if exists:
        db["like"].delete_one({"_id": exists["_id"]})
        return {"liked": False}
    create_document("like", {"post_id": post_id, "user_id": str(current_user["_id"])})
    return {"liked": True}


@app.post("/posts/{post_id}/comments", response_model=CommentOut)
async def add_comment(post_id: str, comment: Comment, current_user=Depends(get_current_user)):
    if db is None:
        raise HTTPException(500, "Database not connected")
    data = comment.model_dump()
    data["post_id"] = post_id
    data["author_id"] = str(current_user["_id"])  # enforce
    comment_id = create_document("comment", data)
    out = await build_comment_out(db["comment"].find_one({"_id": ObjectId(comment_id)}))
    return out


@app.get("/posts/{post_id}/comments", response_model=List[CommentOut])
async def list_comments(post_id: str, skip: int = 0, limit: int = 50, current_user=Depends(get_current_user)):
    if db is None:
        raise HTTPException(500, "Database not connected")
    docs = db["comment"].find({"post_id": post_id}).sort("created_at", -1).skip(skip).limit(limit)
    return [await build_comment_out(d) for d in docs]


# Builders
async def get_post_out(post_id: str) -> PostOut:
    doc = db["post"].find_one({"_id": ObjectId(post_id)})
    return await build_post_out(doc)


async def build_post_out(doc) -> PostOut:
    author_doc = db["user"].find_one({"_id": ObjectId(doc["author_id"])})
    author = PublicUser(
        id=str(author_doc["_id"]),
        username=author_doc.get("username"),
        email=author_doc.get("email"),
        full_name=author_doc.get("full_name"),
        avatar_url=author_doc.get("avatar_url"),
        bio=author_doc.get("bio"),
    )
    pid = str(doc["_id"]) if isinstance(doc.get("_id"), ObjectId) else str(doc.get("_id"))
    likes = db["like"].count_documents({"post_id": pid})
    comments_count = db["comment"].count_documents({"post_id": pid})
    return PostOut(
        id=pid,
        author=author,
        content=doc.get("content"),
        image_url=doc.get("image_url"),
        likes=likes,
        comments_count=comments_count,
        created_at=doc.get("created_at", datetime.now(timezone.utc))
    )


async def build_comment_out(doc) -> CommentOut:
    author_doc = db["user"].find_one({"_id": ObjectId(doc["author_id"])})
    author = PublicUser(
        id=str(author_doc["_id"]),
        username=author_doc.get("username"),
        email=author_doc.get("email"),
        full_name=author_doc.get("full_name"),
        avatar_url=author_doc.get("avatar_url"),
        bio=author_doc.get("bio"),
    )
    return CommentOut(
        id=str(doc["_id"]),
        author=author,
        content=doc.get("content"),
        created_at=doc.get("created_at", datetime.now(timezone.utc))
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
