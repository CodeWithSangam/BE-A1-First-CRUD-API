from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel

app = FastAPI()


list_of_dict = [
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
    return list_of_dict

@app.get('/tasks/{id}')
async def read_item(id:int):
    for items in list_of_dict:
        if items['id'] == id:
            return items
    raise HTTPException(status_code=404, detail=f"Task {id} not found")


# Stage 3: create with validation
class TaskCreate(BaseModel):
    title:str

@app.post('/tasks',status_code=201)
async def create_task(item:TaskCreate):
    if not item.title.strip():
        raise HTTPException(status_code=400,detail="Title can'nt be empty")

    new_id = max((task['id'] for task in list_of_dict),default=0)+1
    new_obj = {
        'id':new_id,
        'title':item.title,
        'done':False
    }
    list_of_dict.append(new_obj)
    return new_obj


# UPDATE & DELETE
# Stage 4: full CRUD
class TaskUpdate(BaseModel):
    title:str
    done:bool


@app.put('/tasks/{id}')
async def update_task(id:int, item:TaskUpdate):
    for items in list_of_dict:
            if items['id'] == id:
                items['title'] = item.title
                items['done'] = item.done
                return items
    raise HTTPException (status_code=404, detail=f"task {id} not found")

# DELETE
@app.delete('/tasks/{id}',status_code=204)
async def delete_task(id:int):
    for items in list_of_dict:
        if items['id'] == id:
            list_of_dict.remove(items)
            return 
    raise HTTPException(status_code=404,detail=f'Task {id} not found')

