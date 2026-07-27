from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
import sqlite3

connection = sqlite3.connect("tasks.db",check_same_thread=False)
cursor = connection.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks(
    id INTEGER PRIMARY KEY,
    title TEXT,
    done INTEGER
    )
""")
cursor.execute("SELECT COUNT (*) FROM tasks")
row_count = cursor.fetchone()[0]
if row_count == 0:
    cursor.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)",[("Buy groceries",0)
                ,("Walk the dog",1),("Read a book",0)])
connection.commit() 

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
    cursor.execute("SELECT * FROM tasks")
    tasks_list = cursor.fetchall()
    result = []
    for row in tasks_list:
        row = {"id": row[0], "title": row[1], "done": bool(row[2])}
        result.append(row)
    return result


@app.get('/tasks/{id}')
async def read_item(id:int):
    cursor.execute("SELECT * FROM tasks WHERE id = ?",(id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404,detail=f'Task {id} not found.')
    else:   
        row = {"id": row[0], "title": row[1], "done": bool(row[2])}
    return row

# Stage 3: create with validation
class TaskCreate(BaseModel):
    title:str

@app.post('/tasks',status_code=201)
async def create_task(item:TaskCreate):
    if not item.title.strip():
        raise HTTPException(status_code=400, detail="Title can't be empty")
    cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)",(item.title, 0 ))
    connection.commit()
    new_id = cursor.lastrowid
    return {"id": new_id, "title": item.title, "done": False}


# UPDATE & DELETE
# Stage 4: full CRUD
class TaskUpdate(BaseModel):
    title:str
    done:bool


@app.put('/tasks/{id}')
async def update_task(id:int, item:TaskUpdate):
                cursor.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?",(item.title,item.done,id))
                connection.commit()
                if cursor.rowcount == 0:
                     raise HTTPException (status_code=404, detail=f"task {id} not found")
                return {"id": id, "title": item.title, "done": item.done}
    
# DELETE
@app.delete('/tasks/{id}',status_code=204)
async def delete_task(id:int):
            cursor.execute("DELETE FROM tasks WHERE id = ?",(id,))
            connection.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404,detail=f'Task {id} not found')
            return 

