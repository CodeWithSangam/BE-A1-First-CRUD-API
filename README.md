# Task API — FlyRank Internship, Week 2 (Assignment A1)

A simple CRUD (Create, Read, Update, Delete) API for managing a to-do list, built with **FastAPI** (Python). The API stores tasks in memory, exposes interactive documentation via **Swagger UI**, and includes a lightweight HTML/JavaScript frontend that consumes the live API.

This project was built as part of the FlyRank Backend AI Engineering internship track, Week 2 assignment: "Build your first CRUD API."

---

## Tech Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI
- **Server:** Uvicorn
- **Data storage:** In-memory Python list (no database — resets on server restart)
- **Frontend:** Plain HTML, CSS, and JavaScript (`fetch` API), connected live to the backend

---

## How to Install & Run

Clone the repository and run the following commands from the project folder:

```bash
pip install fastapi uvicorn
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`.

To use the frontend, open `index.html` directly in your browser (double-click the file, or use a Live Server extension) while the backend is running.

---

## API Endpoints

| Method | Endpoint         | Description                                  | Success Status | Error Status |
|--------|------------------|-----------------------------------------------|-----------------|---------------|
| GET    | `/`              | Root endpoint — describes the API             | 200             | —             |
| GET    | `/health`        | Health check — confirms the server is alive    | 200             | —             |
| GET    | `/tasks`         | Returns the full list of tasks                 | 200             | —             |
| GET    | `/tasks/{id}`    | Returns a single task by ID                    | 200             | 404 if not found |
| POST   | `/tasks`         | Creates a new task (`title` required in body)  | 201             | 400 if title is missing/empty |
| PUT    | `/tasks/{id}`    | Updates an existing task's `title` and `done`  | 200             | 404 if not found |
| DELETE | `/tasks/{id}`    | Deletes a task by ID                           | 204             | 404 if not found |

All error responses return a JSON body in the form:
```json
{ "error": "Task 99 not found" }
```

---

## Example Request (curl)

**Creating a new task:**

```bash
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
```

**Response:**

```
HTTP/1.1 201 Created
content-type: application/json

{"id":6,"title":"Buy milk","done":false}
```

---

## Swagger UI

Interactive API documentation is available at:

```
http://localhost:8000/docs
```

FastAPI generates this automatically from the code — no extra setup required. Every endpoint listed above can be tested directly from this page using the **"Try it out"** button.

**Screenshot:**
<img width="1178" height="702" alt="image" src="https://github.com/user-attachments/assets/c9b3434d-47db-4162-924a-c2110bb6feaa" />

---

## Frontend

A minimal frontend (`index.html`) is included to demonstrate the full CRUD cycle visually:

- View all tasks
- Add a new task
- Mark a task as done/undone (via checkbox — triggers a `PUT` request)
- Delete a task

The frontend also displays the **live request and response** for every action (method, path, request body, status code, and response JSON), so the full request/response cycle is visible in real time.

To use it: start the backend server first, then open `index.html` in a browser.

---

## Notes on In-Memory Storage

Tasks are stored in a Python list in memory. This means:
- All data is lost when the server restarts.
- This is intentional for this stage of the assignment — persistent storage (a database) is introduced in a later week.

---

## Project Structure

```
flyrank-todo-api/
├── main.py              # FastAPI backend — all CRUD endpoints
├── index.html            # Frontend that consumes the API
├── README.md
└── swagger-screenshot.png
```
