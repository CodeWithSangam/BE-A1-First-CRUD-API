# ==============================
# IMPORTS
# ==============================

from fastapi import FastAPI, Depends, HTTPException  # FastAPI creates the API; Depends handles dependencies; HTTPException sends API errors.
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # HTTPBearer reads the "Bearer <token>" Authorization header.
from pydantic import BaseModel, EmailStr  # BaseModel validates request data; EmailStr validates email format.
from supabase import create_client  # Creates a connection to Supabase.
from dotenv import load_dotenv  # Loads environment variables from the .env file.
from src.routes.triage import router as triage_router  # Imports the triage router and gives it a shorter name.
import inngest  # Provides background-job/event functionality.
import inngest.fast_api  # Connects Inngest functions with FastAPI.
import psycopg  # PostgreSQL database driver.
import os  # Reads environment variables and operating-system settings.
import uuid  # Generates unique IDs for reports.


# ==============================
# ENVIRONMENT VARIABLES
# ==============================

load_dotenv()  # Loads values from the .env file into the environment.

SUPABASE_URL = os.getenv("SUPABASE_URL")  # Reads the Supabase project URL from the environment.
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Reads the Supabase API key from the environment.
DATABASE_URL = os.getenv("DATABASE_URL")  # Reads the PostgreSQL connection string from the environment.

if not SUPABASE_URL or not SUPABASE_KEY:  # Checks that the required Supabase settings exist.
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")  # Stops startup with a clear error.

if not DATABASE_URL:  # Checks that the PostgreSQL connection string exists.
    raise RuntimeError("DATABASE_URL must be set in .env")  # Stops startup with a clear error.


# ==============================
# APPLICATION SETUP
# ==============================

app = FastAPI(title="Task & Report API", version="1.0")  # Creates the FastAPI application.

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)  # Creates the Supabase client used by authentication functions.

inngest_client = inngest.Inngest(app_id="report-api")  # Creates the Inngest client for background jobs.

security = HTTPBearer()  # Tells FastAPI to expect an Authorization: Bearer <token> header.


# ==============================
# DATABASE SETUP
# ==============================

connection = psycopg.connect(DATABASE_URL)  # Opens a connection to PostgreSQL.

cursor = connection.cursor()  # Creates a cursor used to execute SQL queries.

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        done BOOLEAN NOT NULL DEFAULT FALSE
    )
    """
)  # Creates the tasks table if it does not already exist.

cursor.execute("SELECT COUNT(*) FROM tasks")  # Counts the existing tasks.

row_count = cursor.fetchone()[0]  # Gets the count from the first value of the returned tuple.

if row_count == 0:  # Adds sample data only when the table is empty.
    cursor.executemany(
        "INSERT INTO tasks (title, done) VALUES (%s, %s)",
        [
            ("Buy groceries", False),
            ("Walk the dog", True),
            ("Read a book", False),
        ],
    )  # Inserts three example tasks using PostgreSQL parameter placeholders.

connection.commit()  # Saves the table creation and seed data permanently.


# ==============================
# IN-MEMORY REPORT STORAGE
# ==============================

reports = {}  # Stores report information temporarily in memory; data disappears when the server restarts.


# ==============================
# PYDANTIC REQUEST MODELS
# ==============================

class ReportRequest(BaseModel):  # Defines the request body expected when creating a report.
    topic: str  # Stores the topic for which the report should be generated.


class AuthCredentials(BaseModel):  # Defines the request body used by signup and login.
    email: EmailStr  # Requires a valid email address.
    password: str  # Stores the user's password.


class TaskCreate(BaseModel):  # Defines the request body used to create a task.
    title: str  # Stores the task title.


class TaskUpdate(BaseModel):  # Defines the request body used to update a task.
    title: str  # Stores the new task title.
    done: bool  # Stores the new completed/not-completed status.


# ==============================
# INNGEST BACKGROUND FUNCTIONS
# ==============================

@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    """
    Purpose:
    This is a simple Inngest background function used to test
    that the Inngest event system is working correctly.
    """
    await ctx.step.sleep("wait-a-moment", 5)  # Waits for 5 seconds as a demonstration of background work.
    return "Hello from the background!"  # Returns a message after the background job finishes.


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,  # 2 retries = 3 total attempts
)
async def make_report(ctx: inngest.Context) -> str:
    """
    Purpose:
    This background function receives a report/requested event,
    performs the slow report-building work, and updates the report status.
    Retries 2 times on failure (3 total attempts).
    """
    await ctx.step.sleep("do-the-slow-work", 8)  # Simulates slow report generation for 8 seconds.

    async def build():
        """Purpose: Builds the report and changes its status from pending to done."""
        report_id = ctx.event.data["id"]  # Gets the report ID from the Inngest event.
        topic = ctx.event.data["topic"]  # Gets the report topic from the Inngest event.

        # Fail case — topic "fail" triggers an error to demonstrate retry behavior.
        if topic == "fail":
            raise Exception("The report oven is broken!")

        reports[report_id] = {  # Updates the report stored in memory.
            "id": report_id,
            "topic": topic,
            "status": "done",
            "result": f"Report on '{topic}' is ready!",
        }
        return "done"

    await ctx.step.run("build-report", build)  # Runs the report-building operation as an Inngest step.
    return "complete"
# ==============================
# REPORT ENDPOINTS
# ==============================

@app.post("/reports", status_code=202)
async def create_report(item: ReportRequest):
    """
    Purpose:
    Creates a report request immediately and sends an event to Inngest
    so the slow report generation can happen in the background.
    """
    if not item.topic.strip():  # Checks whether the topic is empty or contains only spaces.
        raise HTTPException(status_code=400, detail="topic is required")  # Returns a client error for invalid input.

    report_id = str(uuid.uuid4())  # Creates a unique ID for the new report.

    reports[report_id] = {  # Saves the initial report state.
        "id": report_id,  # Stores the generated report ID.
        "topic": item.topic.strip(),  # Stores the cleaned topic.
        "status": "pending",  # Marks the report as waiting for background processing.
    }

    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": item.topic.strip()},
        )
    )  # Sends an event that triggers the make_report background function.

    return {"id": report_id, "status": "pending"}  # Immediately tells the client that the request was accepted.


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    """
    Purpose:
    Returns the current status and result of a previously requested report.
    """
    report = reports.get(report_id)  # Looks for the report using its ID.

    if not report:  # Checks whether the report exists.
        raise HTTPException(status_code=404, detail="Report not found")  # Returns 404 when the report does not exist.

    return report  # Sends the report information to the client.


# ==============================
# AUTHENTICATION DEPENDENCY
# ==============================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Purpose:
    Reads the Bearer access token from the request, verifies it with Supabase,
    and returns the authenticated user's basic information.

    This function is used as a dependency on protected endpoints.
    """
    token = credentials.credentials  # Gets only the token; HTTPBearer already removed the "Bearer " prefix.

    try:  # Starts error handling because token verification can fail.
        response = supabase.auth.get_user(token)  # Asks Supabase to verify the access token and return the user.

        if not response.user:  # Makes sure Supabase actually returned a user.
            raise HTTPException(status_code=401, detail="Invalid or expired token")  # Rejects requests without a valid user.

        return {  # Returns only the user information needed by the API.
            "id": response.user.id,  # Returns the authenticated user's unique ID.
            "email": response.user.email,  # Returns the authenticated user's email.
            "created_at": response.user.created_at,  # Returns when the user account was created.
        }

    except HTTPException:  # Keeps our own 401 error unchanged.
        raise  # Re-raises the existing HTTP exception.

    except Exception:  # Catches unexpected Supabase/token errors.
        raise HTTPException(status_code=401, detail="Invalid or expired token")  # Converts them into a safe authentication error.


# ==============================
# AUTHENTICATION ENDPOINTS
# ==============================

@app.post("/auth/signup", status_code=201)
async def sign_up(item: AuthCredentials):
    """
    Purpose:
    Creates a new user account in Supabase Authentication.
    """
    if not item.email.strip() or not item.password.strip():  # Checks that email and password contain actual text.
        raise HTTPException(status_code=400, detail="Email and password required")  # Rejects incomplete signup requests.

    try:  # Starts error handling for the Supabase signup operation.
        response = supabase.auth.sign_up(
            {"email": item.email.strip(), "password": item.password}
        )  # Sends the signup request to Supabase.

        return {"user": response.user.model_dump() if response.user else None}  # Converts the Supabase user object into JSON-safe data.

    except Exception:  # Catches errors such as an existing email or Supabase failure.
        raise HTTPException(status_code=400, detail="Unable to create account")  # Returns a safe error message to the client.


@app.post("/auth/login")
async def sign_in(item: AuthCredentials):
    """
    Purpose:
    Authenticates an existing user with Supabase and returns access
    and refresh tokens to the client.
    """
    if not item.email.strip() or not item.password.strip():  # Checks that both credentials are present.
        raise HTTPException(status_code=400, detail="Email and password required")  # Rejects incomplete login requests.

    try:  # Starts error handling for the login operation.
        response = supabase.auth.sign_in_with_password(
            {"email": item.email.strip(), "password": item.password}
        )  # Sends the email and password to Supabase for authentication.

        if not response.session:  # Checks whether Supabase created a login session.
            raise HTTPException(status_code=401, detail="Invalid login credentials")  # Rejects login when no session exists.

        return {  # Returns the actual token strings needed by the client.
            "access_token": response.session.access_token,  # Token used to access protected API endpoints.
            "refresh_token": response.session.refresh_token,  # Token used to obtain a new access token.
        }

    except HTTPException:  # Keeps our own authentication error unchanged.
        raise  # Re-raises the HTTP exception.

    except Exception:  # Catches invalid credentials and unexpected Supabase errors.
        raise HTTPException(status_code=401, detail="Invalid login credentials")  # Returns a standard login failure.


@app.post("/auth/logout", status_code=204)
async def logout(current_user=Depends(get_current_user)):
    """
    Purpose:
    Logs the authenticated user out of the Supabase session.

    Note:
    The access token is already verified by get_current_user.
    """
    try:  # Starts error handling for the logout operation.
        supabase.auth.sign_out()  # Asks Supabase to sign out the current session.
    except Exception:  # Handles an unexpected Supabase logout error.
        raise HTTPException(status_code=500, detail="Unable to logout")  # Returns a server error if logout fails.

    return  # HTTP 204 means there is no response body.


# ==============================
# PUBLIC AND PROTECTED ENDPOINTS
# ==============================

@app.get("/public/info")
async def public_info():
    """
    Purpose:
    Demonstrates a public endpoint that does not require authentication.
    """
    return {"message": "Welcome stranger! This info is public."}  # Returns public information.


@app.get("/protected/profile")
async def get_profile(current_user=Depends(get_current_user)):
    """
    Purpose:
    Demonstrates a protected endpoint.
    Only a request with a valid Supabase access token can reach this function.
    """
    return current_user  # Returns the authenticated user's information.


@app.get("/protected/dashboard")
async def get_dashboard(current_user=Depends(get_current_user)):
    """
    Purpose:
    Demonstrates how a protected endpoint can use information returned
    by the get_current_user dependency.
    """
    return {"message": f"Welcome, {current_user['email']}"}  # Creates a personalized dashboard response.


# ==============================
# GENERAL API ENDPOINTS
# ==============================

@app.get("/")
async def root():
    """
    Purpose:
    Returns basic information about the API.
    """
    return {
        "name": "Task & Report API",
        "version": "1.0",
        "endpoints": ["/tasks", "/reports"],
    }  # Returns basic API information.


@app.get("/health")
async def health_check():
    """
    Purpose:
    Provides a simple health-check endpoint used to verify that the API is running.
    """
    return {"status": "ok"}  # Returns a successful health status.


# ==============================
# TASK READ ENDPOINTS
# ==============================

@app.get("/tasks")
def get_tasks(search: str | None = None, done: bool | None = None):
    """
    Purpose:
    Returns all tasks and optionally filters them by title and completion status.

    This function is synchronous because it uses the synchronous psycopg cursor.
    """
    conditions = []  # Stores SQL WHERE conditions that need to be applied.
    values = []  # Stores values for the SQL placeholders.

    if search:  # Checks whether the client provided a search term.
        conditions.append("title ILIKE %s")  # Adds a case-insensitive title search condition.
        values.append(f"%{search}%")  # Adds wildcard characters so the term can appear anywhere in the title.

    if done is not None:  # Checks whether the client explicitly provided true or false.
        conditions.append("done = %s")  # Adds a completion-status condition.
        values.append(done)  # Adds the boolean value for the condition.

    query = "SELECT id, title, done FROM tasks"  # Starts with the base SQL query.

    if conditions:  # Checks whether any filters were provided.
        query += " WHERE " + " AND ".join(conditions)  # Adds all filters using AND.

    query += " ORDER BY title"  # Sorts the final result alphabetically by title.

    cursor.execute(query, tuple(values))  # Executes the parameterized query safely.

    rows = cursor.fetchall()  # Gets all matching rows from PostgreSQL.

    return [
        {"id": row[0], "title": row[1], "done": bool(row[2])}
        for row in rows
    ]  # Converts database tuples into JSON-friendly dictionaries.


@app.get("/stats")
def get_stats():
    """
    Purpose:
    Returns the total number of tasks, completed tasks, and open tasks.
    """
    cursor.execute("SELECT COUNT(*) FROM tasks")  # Counts all tasks.
    total = cursor.fetchone()[0]  # Gets the total task count.

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE done = TRUE")  # Counts completed tasks.
    done = cursor.fetchone()[0]  # Gets the completed-task count.

    return {
        "total": total,
        "done": done,
        "open": total - done,
    }  # Returns all task statistics.


@app.get("/tasks/{task_id}")
def read_task(task_id: int):
    """
    Purpose:
    Finds and returns one task using its database ID.
    """
    cursor.execute(
        "SELECT id, title, done FROM tasks WHERE id = %s",
        (task_id,),
    )  # Searches PostgreSQL for the requested task ID.

    row = cursor.fetchone()  # Gets one matching row or None when no row exists.

    if row is None:  # Checks whether PostgreSQL found a task.
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found.",
        )  # Returns 404 when the task does not exist.

    return {
        "id": row[0],
        "title": row[1],
        "done": bool(row[2]),
    }  # Converts the database row into a JSON response.


# ==============================
# TASK CREATE / UPDATE / DELETE
# ==============================

@app.post("/tasks", status_code=201)
def create_task(item: TaskCreate):
    """
    Purpose:
    Creates a new task in PostgreSQL and returns the newly generated ID.
    """
    title = item.title.strip()  # Removes unnecessary spaces from the beginning and end of the title.

    if not title:  # Checks whether the cleaned title is empty.
        raise HTTPException(status_code=400, detail="Title can't be empty")  # Rejects an empty task title.

    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id",
        (title, False),
    )  # Inserts the task and asks PostgreSQL to return its generated ID.

    new_id = cursor.fetchone()[0]  # Reads the generated ID from PostgreSQL.

    connection.commit()  # Permanently saves the new task.

    return {
        "id": new_id,
        "title": title,
        "done": False,
    }  # Returns the newly created task.


@app.put("/tasks/{task_id}")
def update_task(task_id: int, item: TaskUpdate):
    """
    Purpose:
    Updates the title and completion status of an existing task.
    """
    title = item.title.strip()  # Removes unnecessary spaces from the new title.

    if not title:  # Checks whether the new title is empty.
        raise HTTPException(status_code=400, detail="Title can't be empty")  # Rejects an empty title.

    cursor.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s",
        (title, item.done, task_id),
    )  # Updates the task matching the supplied ID.

    if cursor.rowcount == 0:  # Checks whether PostgreSQL updated any row.
        connection.rollback()  # Clears the unsuccessful transaction before returning the error.
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found",
        )  # Returns 404 when the task does not exist.

    connection.commit()  # Permanently saves the update.

    return {
        "id": task_id,
        "title": title,
        "done": item.done,
    }  # Returns the updated task.


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """
    Purpose:
    Deletes an existing task from PostgreSQL using its ID.
    """
    cursor.execute(
        "DELETE FROM tasks WHERE id = %s",
        (task_id,),
    )  # Deletes the task matching the supplied ID.

    if cursor.rowcount == 0:  # Checks whether any task was actually deleted.
        connection.rollback()  # Clears the unsuccessful transaction before returning the error.
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found",
        )  # Returns 404 when the task does not exist.

    connection.commit()  # Permanently saves the deletion.

    return  # HTTP 204 intentionally returns no response body.


# ==============================
# ROUTER AND INNGEST REGISTRATION
# ==============================

app.include_router(triage_router)  # Adds all endpoints defined inside the triage router to this FastAPI application.

inngest.fast_api.serve(
    app,
    inngest_client,
    [say_hello, make_report],
)  # Registers the Inngest functions with FastAPI; note that the extra comma in [say_hello, , make_report] was fixed.
