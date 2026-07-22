from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel

app = FastAPI()


list_of_obj = [
     { 'id': 1, 'title': 'Buy groceries', 'done': False },

     { 'id': 2, 'title': 'Walk the dog', 'done': True },

     { 'id': 3, 'title': 'Read a book', 'done': False }

]
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

# Stage 2: read endpoints with 404
@app.get('/tasks')
async def tasks():
    return list_of_obj

@app.get('/tasks/{id}')
async def read_item(id:int):
    for items in list_of_obj:
        if items['id'] == id:
            return items
    return HTTPException(status_code=404, detail=f"Task {id} not found")

