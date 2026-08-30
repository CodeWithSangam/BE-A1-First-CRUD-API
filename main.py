from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv
import os
from fastapi import Header, Depends

# helps in loading the env file
load_dotenv()
import psycopg
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.routes.triage import router as triage_router
app = FastAPI()
app.include_router(triage_router)
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)


class AuthCredentials(BaseModel):
    email: str
    password: str



security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials  # yahan seedha token milega, "Bearer " nikaalne ki zaroorat nahi
    try:
        response = supabase.auth.get_user(token)
        return {
            "id": response.user.id,
            "email": response.user.email,
            "ac_created_date": response.user.created_at
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
@app.post('/auth/logout',status_code=204)
async def logout(current_user = Depends(get_current_user)):
    supabase.auth.sign_out()
    return

@app.post('/auth/signup', status_code=201)
async def sign_up(item: AuthCredentials):
    if not item.email.strip() or not item.password.strip():
        raise HTTPException(status_code=400, detail="Email and password required")
    response = supabase.auth.sign_up({"email": item.email, "password": item.password})
    # fix: response.user is Supabase's own object, not a plain dict.
    # Converting it to a dict keeps the response safe and predictable as JSON.
    return {"user": response.user.model_dump()}


@app.post('/auth/login')
async def sign_in(item: AuthCredentials):
    if not item.email.strip() or not item.password.strip():
        raise HTTPException(status_code=400, detail="Email and password required")
    try:
        response = supabase.auth.sign_in_with_password({"email": item.email, "password": item.password})
        # fix: the old code returned the whole 'response' object twice under two keys.
        # We actually need to reach INSIDE response.session to get the two real token strings.
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
@app.get('/public/info')
async def public_info():
    return { "message": "Welcome stranger! This info is public." }

@app.get('/protected/profile')
async def get_profile(current_user = Depends(get_current_user)):
    return current_user
@app.get('/protected/dashboard')
async def get_dashboard(current_user = Depends(get_current_user)):
    return {"message": f"Welcome, {current_user['email']}"}
# Connect to Postgres using the connection string stored in .env (DATABASE_URL)
connection = psycopg.connect(os.getenv("DATABASE_URL"))
# Create a cursor - this is what we use to run SQL commands and fetch results
cursor = connection.cursor()

# Create the tasks table only if it doesn't already exist
# SERIAL = auto-incrementing integer (Postgres equivalent of SQLite's INTEGER PRIMARY KEY)
# BOOLEAN = a real true/false type (Postgres has this natively, unlike SQLite's 0/1)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT,
    done BOOLEAN
)
""")

# Check how many rows already exist in the table
cursor.execute("SELECT COUNT (*) FROM tasks")
row_count = cursor.fetchone()[0]  # fetchone() returns a tuple like (0,), so we grab index 0

# Only seed example tasks if the table is empty - prevents duplicates on every restart
# Note: psycopg uses %s as the placeholder, NOT ? (that was SQLite's syntax)
if row_count == 0:
    cursor.executemany(
        "INSERT INTO tasks (title, done) VALUES (%s, %s)",
        [("Buy groceries", False), ("Walk the dog", True), ("Read a book", False)]
    )

# Save changes permanently to the database (required after INSERT/UPDATE/DELETE)
connection.commit()


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
async def tasks(search: str = None, done: bool = None):
    # These lists will collect WHERE conditions and their matching values dynamically
    conditions = []
    values = []

    # If a search term was given, add a LIKE condition (%s placeholder, not ?)
    if search:
        conditions.append("title LIKE %s")
        values.append(f"%{search}%")

    # If a 'done' filter was given (True or False, not just "not empty"), add an equality condition
    if done is not None:
        conditions.append("done = %s")
        values.append(done)

    # Start with the base query, then attach WHERE clauses only if any conditions were collected
    query = "SELECT * FROM tasks"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY title"

    # Run the query, passing all collected values as one tuple
    cursor.execute(query, tuple(values))
    tasks_list = cursor.fetchall()  # returns a list of tuples, one tuple per row

    # Convert each raw tuple into a readable dictionary for the JSON response
    result = []
    for row in tasks_list:
        row = {"id": row[0], "title": row[1], "done": bool(row[2])}
        result.append(row)
    return result

@app.get('/stats')
async def get_stats():
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total = cursor.fetchone()[0]
    # done = 1 also works in Postgres, but done = TRUE is more correct for a real boolean column
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE done = TRUE")
    done = cursor.fetchone()[0]
    return {"total": total, "done": done, "open": total - done}


@app.get('/tasks/{id}')
async def read_item(id: int):
    # %s placeholder instead of ? - this is the psycopg/Postgres syntax
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (id,))
    row = cursor.fetchone()  # returns one tuple, or None if no match
    if row is None:
        raise HTTPException(status_code=404, detail=f'Task {id} not found.')
    else:
        row = {"id": row[0], "title": row[1], "done": bool(row[2])}
    return row

# Stage 3: create with validation
class TaskCreate(BaseModel):
    title: str

@app.post('/tasks', status_code=201)
async def create_task(item: TaskCreate):
    # Validate BEFORE touching the database
    if not item.title.strip():
        raise HTTPException(status_code=400, detail="Title can't be empty")

    # RETURNING id asks Postgres to hand back the id it just generated for this row
    # (psycopg has no cursor.lastrowid like sqlite3 does - RETURNING is the Postgres way)
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id",
        (item.title, False)
    )
    new_id = cursor.fetchone()[0]  # fetch the id that RETURNING gave back
    connection.commit()

    return {"id": new_id, "title": item.title, "done": False}


# UPDATE & DELETE
# Stage 4: full CRUD
class TaskUpdate(BaseModel):
    title: str
    done: bool


@app.put('/tasks/{id}')
async def update_task(id: int, item: TaskUpdate):
    # Order of values must match order of %s placeholders: title, done, id
    cursor.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s",
        (item.title, item.done, id)
    )
    connection.commit()
    # rowcount tells us how many rows were affected - 0 means the id didn't exist
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"task {id} not found")
    return {"id": id, "title": item.title, "done": item.done}

# DELETE
@app.delete('/tasks/{id}', status_code=204)
async def delete_task(id: int):
    cursor.execute("DELETE FROM tasks WHERE id = %s", (id,))
    connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f'Task {id} not found')
    return