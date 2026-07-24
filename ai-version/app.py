from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, field_validator

app = FastAPI(
    title="Task CRUD API",
    description="A beginner-friendly CRUD API built with FastAPI.",
    version="1.0.0"
)


class TaskCreate(BaseModel):
    title: str
    completed: bool = False

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned_title = value.strip()

        if not cleaned_title:
            raise ValueError("Title must not be empty")

        return cleaned_title


class TaskResponse(BaseModel):
    id: int
    title: str
    completed: bool


tasks: list[dict] = [
    {
        "id": 1,
        "title": "Learn FastAPI",
        "completed": False
    },
    {
        "id": 2,
        "title": "Build a CRUD API",
        "completed": False
    }
]

next_task_id = 3


def find_task(task_id: int) -> dict:
    for task in tasks:
        if task["id"] == task_id:
            return task

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Task not found"
    )


@app.get("/")
def home():
    return {
        "message": "Welcome to the Task CRUD API",
        "documentation": "/docs",
        "alternative_documentation": "/redoc"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.get(
    "/tasks",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK
)
def get_all_tasks():
    return tasks


@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK
)
def get_single_task(task_id: int):
    return find_task(task_id)


@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED
)
def create_task(task_data: TaskCreate):
    global next_task_id

    new_task = {
        "id": next_task_id,
        "title": task_data.title,
        "completed": task_data.completed
    }

    tasks.append(new_task)
    next_task_id += 1

    return new_task


@app.put(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK
)
def update_task(task_id: int, task_data: TaskCreate):
    existing_task = find_task(task_id)

    existing_task["title"] = task_data.title
    existing_task["completed"] = task_data.completed

    return existing_task


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_task(task_id: int):
    existing_task = find_task(task_id)

    tasks.remove(existing_task)

    return Response(status_code=status.HTTP_204_NO_CONTENT)