from fastapi import FastAPI

from jotter.notes.api import router as notes_router

app = FastAPI(title="Jotter")
app.include_router(notes_router)
