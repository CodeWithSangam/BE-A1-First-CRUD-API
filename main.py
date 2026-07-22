from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel

app = FastAPI()


# Stage 0 : Hello Server
@app.get("/")
async def root(status_code=200):
    return {'message':'Hello Server'}   

