from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import aiofiles
from typing import List, Optional

app = FastAPI()

# cors stuff
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# file stuff
DATA_FILE = "books.json"
file_lock = asyncio.Lock()
ws_lock = asyncio.Lock()
connected_ws = []

async def read_books_from_file():
    async with file_lock:
        try:
            async with aiofiles.open(DATA_FILE, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error reading file: {e}")
            return []

async def write_books_to_file(books):
    async with file_lock:
        try:
            async with aiofiles.open(DATA_FILE, 'w') as f:
                await f.write(json.dumps(books, indent=2))
        except Exception as e:
            print(f"Error writing file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save data")

async def get_next_book_id():
    books = await read_books_from_file()
    if not books:
        return 1
    max_id = 0
    for book in books:
        if book.get('id', 0) > max_id:
            max_id = book['id']
    return max_id + 1

async def check_isbn_exists(isbn, exclude_id=None):
    books = await read_books_from_file()
    for book in books:
        if book.get('isbn') == isbn and book.get('id') != exclude_id:
            return True
    return False

async def find_existing_book(title, author, year, isbn):
    books = await read_books_from_file()
    for i, book in enumerate(books):
        # check by isbn first
        if book.get('isbn') == isbn:
            return i, book
        # then check by title + author + year combo
        if (book.get('title') == title and 
            book.get('author') == author and 
            book.get('publication_year') == year):
            return i, book
    return None, None

async def notify_ws_clients(message):
    if not connected_ws:
        return
    
    async with ws_lock:
        disconnected = []
        for ws in connected_ws:
            try:
                await ws.send_json(message)
            except:
                disconnected.append(ws)
        
        # remove disconnected clients
        for ws in disconnected:
            connected_ws.remove(ws)

@app.get("/books")
async def get_books(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    genre: Optional[str] = None,
    author: Optional[str] = None
):
    books = await read_books_from_file()
    
    # filtering
    if genre:
        books = [book for book in books if book.get('genre', '').lower() == genre.lower()]
    if author:
        books = [book for book in books if book.get('author', '').lower() == author.lower()]
    
    # sorting
    if sort_by == 'title':
        books.sort(key=lambda x: x.get('title', '').lower())
    elif sort_by == 'author':
        books.sort(key=lambda x: x.get('author', '').lower())
    elif sort_by == 'publication_year':
        books.sort(key=lambda x: x.get('publication_year', 0))
    
    # pagination
    total = len(books)
    start = (page - 1) * limit
    end = start + limit
    books_page = books[start:end]
    
    return {
        "books": books_page,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

async def find_existing_book(title, author, year, isbn):
    books = await read_books_from_file()
    isbn_match = None
    combo_match = None
    
    for i, book in enumerate(books):
        if book.get('isbn') == isbn:
            isbn_match = (i, book)
        if (book.get('title') == title and 
            book.get('author') == author and 
            book.get('publication_year') == year):
            combo_match = (i, book)
    
    # If both match but are different books, that's an error
    if isbn_match and combo_match and isbn_match[0] != combo_match[0]:
        raise HTTPException(
            status_code=400, 
            detail="Conflict: ISBN matches one book, but title/author/year matches a different book"
        )
    
    # Return whichever match we found
    return isbn_match or combo_match or (None, None)


@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    books = await read_books_from_file()
    
    book_index = None
    for i, book in enumerate(books):
        if book.get('id') == book_id:
            book_index = i
            break
    
    if book_index is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    deleted_book = books.pop(book_index)
    await write_books_to_file(books)
    
    # notify websocket clients
    await notify_ws_clients({
        "action": "deleted",
        "book": deleted_book
    })
    
    return {"message": "Book deleted successfully"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async with ws_lock:
        connected_ws.append(websocket)
    
    try:
        # send current books when client connects
        books = await read_books_from_file()
        await websocket.send_json({
            "action": "initial_load",
            "books": books
        })
        
        # keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        async with ws_lock:
            if websocket in connected_ws:
                connected_ws.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)