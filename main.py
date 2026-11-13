from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from fastapi.responses import FileResponse

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    text = Column(String)

Base.metadata.create_all(engine)

class NoteIn(BaseModel):
    text: str

app = FastAPI()

@app.post("/notes")
def create_note(note: NoteIn):
    with SessionLocal() as db:
        new_note = Note(text=note.text)
        db.add(new_note)
        db.commit()
        db.refresh(new_note)
        return {"id": new_note.id, "text": new_note.text}

@app.get("/notes")
def list_notes():
    with SessionLocal() as db:
        notes = db.query(Note).all()
        return [{"id": n.id, "text": n.text} for n in notes]    


@app.put("/notes/{note_id}")
def update_note(note_id: int, note: NoteIn):
    with SessionLocal() as db:
        existing = db.get(Note, note_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Note not found")
        existing.text = note.text
        db.commit()
        return {"id": existing.id, "text": existing.text}

@app.delete("/notes/{note_id}")
def delete_note(note_id: int):
    with SessionLocal() as db:
        existing = db.get(Note, note_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Note not found")
        db.delete(existing)
        db.commit()
        return {"deleted": note_id}    

@app.get("/")
def home():
    return FileResponse("index.html")    