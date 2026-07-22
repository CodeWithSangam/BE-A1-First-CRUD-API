from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel

app = FastAPI()


# Stage 0 : Hello Server
# @app.get('/')
# async def root(status_code=200):
#     return {'message':'Hello Server'}   

# Stage 1: root and health endpoints

@app.get('/')
async def root():
    return { "name": "Task API", "version": "1.0", "endpoints": ["/tasks"] }

@app.get('/health')
async def health_check():
    return{'status':'ok'}