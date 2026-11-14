import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pwdlib import PasswordHash
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.middleware.sessions import SessionMiddleware

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./app.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)


class Note(Base):
    __tablename__ = "user_notes"
    id = Column(Integer, primary_key=True)
    text = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))


Base.metadata.create_all(engine)

password_hash = PasswordHash.recommended()


class NoteIn(BaseModel):
    text: str


class UserIn(BaseModel):
    username: str
    password: str


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


def current_user_id(request: Request):
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user_id


@app.get("/")
def home():
    return FileResponse("index.html")


@app.post("/signup")
def signup(user: UserIn, request: Request):
    with SessionLocal() as db:
        if db.query(User).filter_by(username=user.username).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        new_user = User(
            username=user.username,
            password_hash=password_hash.hash(user.password),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        request.session["user_id"] = new_user.id
        return {"username": new_user.username}


@app.post("/login")
def login(user: UserIn, request: Request):
    with SessionLocal() as db:
        existing = db.query(User).filter_by(username=user.username).first()
        if existing is None or not password_hash.verify(user.password, existing.password_hash):
            raise HTTPException(status_code=401, detail="Wrong username or password")
        request.session["user_id"] = existing.id
        return {"username": existing.username}


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/me")
def me(request: Request):
    user_id = current_user_id(request)
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Not logged in")
        return {"username": user.username}


@app.post("/notes")
def create_note(note: NoteIn, request: Request):
    user_id = current_user_id(request)
    with SessionLocal() as db:
        new_note = Note(text=note.text, user_id=user_id)
        db.add(new_note)
        db.commit()
        db.refresh(new_note)
        return {"id": new_note.id, "text": new_note.text}


@app.get("/notes")
def list_notes(request: Request):
    user_id = current_user_id(request)
    with SessionLocal() as db:
        notes = db.query(Note).filter_by(user_id=user_id).all()
        return [{"id": n.id, "text": n.text} for n in notes]


@app.put("/notes/{note_id}")
def update_note(note_id: int, note: NoteIn, request: Request):
    user_id = current_user_id(request)
    with SessionLocal() as db:
        existing = db.get(Note, note_id)
        if existing is None or existing.user_id != user_id:
            raise HTTPException(status_code=404, detail="Note not found")
        existing.text = note.text
        db.commit()
        return {"id": existing.id, "text": existing.text}


@app.delete("/notes/{note_id}")
def delete_note(note_id: int, request: Request):
    user_id = current_user_id(request)
    with SessionLocal() as db:
        existing = db.get(Note, note_id)
        if existing is None or existing.user_id != user_id:
            raise HTTPException(status_code=404, detail="Note not found")
        db.delete(existing)
        db.commit()
        return {"deleted": note_id}