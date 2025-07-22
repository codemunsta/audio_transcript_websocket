from app.models import TodoItem
from app.handler import WebSocketConnection

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException

app = FastAPI()
todos = []  # In-memory "database"
app.mount("/Users/mac/codebase/demoapp/audio", StaticFiles(directory="audio_uploads"), name="audio")

html = open("app/templates/stream_audio_new.html").read()
html_2 = open("app/templates/stream_text.html").read()


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the ToDo API",
        "urls": {
            "/todos/": "Get all ToDos",
            "/todos/create/": "Create a new todo",
            "/todos/{todo_id}/": "Get a todo by ID",
            "/todos/delete/{todo_id}/": "Delete a todo by ID",
            "/ws-test/{page}/": "Frontend WebSocket demo choices are 'audio' or 'text_stream'",
            "/ws": "ws://localhost:8000/ws for WebSocket communication",
        }
    }


@app.get("/ws-test/{page}/")
async def websocket_demo(page: str):
    if page == "audio":
        return HTMLResponse(html)
    if page == "text_stream":
        return HTMLResponse(html_2)
    else:
        raise HTTPException(status_code=404, detail="Page not found")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection = WebSocketConnection(websocket)
    await connection.connect()
    try:
        while True:
            message = await websocket.receive()

            if "text" in message:
                data = message["text"]
                await connection.respond(data)

            elif "bytes" in message:
                data = message["bytes"]
                await connection.handle_incoming_bytes(data)

    except WebSocketDisconnect:
        await connection.disconnect()


@app.get("/todos/", response_model=list[TodoItem])
def get_todos():
    return todos


@app.post("/todos/create/", response_model=TodoItem)
def create_todo(todo: TodoItem):
    todos.append(todo)
    return todo


@app.get("/todos/{todo_id}", response_model=TodoItem)
def get_todo(todo_id: int):
    for todo in todos:
        if todo.id == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="ToDo not found")


@app.delete("/todos/{todo_id}", response_model=TodoItem)
def delete_todo(todo_id: int):
    for i, todo in enumerate(todos):
        if todo.id == todo_id:
            return todos.pop(i)
    raise HTTPException(status_code=404, detail="ToDo not found")
