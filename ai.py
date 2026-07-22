from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel



app = FastAPI()

'''
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
     CORSMiddleware,
     allow_origins=["*"],
     allow_methods=["*"],
     allow_headers=["*"],
)
'''

list_of_dict = []
# items jo list_of_dict ke andar rahengi
'''
{
    'id':1,
    'title':'stage1',
    'done':True
},{
    'id':2,
    'title':'stage2',
    'done':True
},
{
    'id':3,
    'title':'stage3',
    'done':True
}
'''

# 1. Server basics (Stage 0-1){
# @app.get("/")
# async def root():
#     return {"message": "Hello World"}

@app.get("/")
async def root():
    return{ "name": "Task API", "version": "1.0", "endpoints": ["/tasks"] }

@app.get("/health")
async def health_check():
    return{"status":'ok'}
#
# } 1. Server basics (Stage 0-1)



# 2. Read/GET pattern (Stage 2) — ye pattern baar baar use hoga
# list pe loop karo
# har item ka 'id' check karo, diye gaye id se match karta hai kya
# match mile to wo item return karo
# loop khatam hone ke baad bhi match na mile to 404 raise karo
@app.get('/tasks')
async def tasks():
    return list_of_dict

@app.get("/tasks/{id}")
async def read_item(id:int):
    for items in list_of_dict:
            if items['id'] == id:
                return items
    raise HTTPException(status_code=404, detail=f"Task {id} not found")

# 4. Pydantic model (Stage 3) — request body ka "shape" define karta hai
class TaskCreate(BaseModel):
    title:str

@app.post('/tasks',status_code=201)
async def create_item(item: TaskCreate):
    if not item.title.strip():
        raise HTTPException(status_code=400, detail='Title cannot be empty')
    
    new_id = max((task['id'] for task in list_of_dict),default=0) +1
    newobj = {
        'id':new_id,
        'title':item.title,
        'done':False
    }
    list_of_dict.append(newobj)
    return  newobj

# Stage 4 Update

class TaskUpdate(BaseModel):
    title : str
    done : bool

@app.put('/tasks/{id}')
async def update_task(id:int, item:TaskUpdate):
    for items in list_of_dict:
            if items['id'] == id:
                items['title'] = item.title
                items['done'] = item.done
                return items
    raise HTTPException (status_code=404, detail=f"task {id} not found")

# Stage 4 DELETE

@app.delete('/tasks/{id}',status_code=204)
async def delete_task(id:int):
    for items in list_of_dict:
        if items['id'] == id:
            list_of_dict.remove(items)
            return 
    raise HTTPException(status_code=404, detail=f"task {id} not found")


'''
# 1. Create a task
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Test task"}'

# 2. Update it (use the id you got from step 1)
curl -i -X PUT http://localhost:8000/tasks/<ID> -H "Content-Type: application/json" -d '{"title":"Updated task","done":true}'

# 3. Confirm via GET
curl -i http://localhost:8000/tasks

# 4. Delete it
curl -i -X DELETE http://localhost:8000/tasks/<ID>

# 5. Confirm it's gone
curl -i http://localhost:8000/tasks/<ID>
'''