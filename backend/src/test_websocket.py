import pytest
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_data():
    # reset books.json before each test
    with open("books.json", "w") as f:
        json.dump([], f)
    yield

def test_websocket_connection():
    with client.websocket_connect("/ws") as websocket:
        # should receive initial book list when connecting
        data = websocket.receive_json()
        assert data["action"] == "initial_load"
        assert data["books"] == []

def test_websocket_initial_load_with_existing_books():
    # create some books first
    book_data = {
        "title": "Existing Book",
        "author": "Existing Author",
        "publication_year": 2023,
        "genre": "Fiction",
        "isbn": "1111111111"
    }
    client.post("/books", json=book_data)
    
    # connect to websocket
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data["action"] == "initial_load"
        assert len(data["books"]) == 1
        assert data["books"][0]["title"] == "Existing Book"

def test_websocket_create_notification():
    with client.websocket_connect("/ws") as websocket:
        # skip initial load message
        initial_data = websocket.receive_json()
        assert initial_data["action"] == "initial_load"
        
        # create a book via HTTP API
        book_data = {
            "title": "New Book",
            "author": "New Author", 
            "publication_year": 2023,
            "genre": "Mystery",
            "isbn": "2222222222"
        }
        client.post("/books", json=book_data)
        
        # should receive websocket notification
        notification = websocket.receive_json()
        assert notification["action"] == "created"
        assert notification["book"]["title"] == "New Book"
        assert notification["book"]["id"] == 1

def test_websocket_update_notification():
    # create initial book
    initial_book = {
        "title": "Original Title", 
        "author": "Original Author",
        "publication_year": 2022,
        "genre": "Drama",
        "isbn": "3333333333"
    }
    client.post("/books", json=initial_book)
    
    with client.websocket_connect("/ws") as websocket:
        # skip initial load
        websocket.receive_json()
        
        # update the book
        updated_book = {
            "title": "Updated Title",
            "author": "Updated Author",
            "publication_year": 2023, 
            "genre": "Comedy",
            "isbn": "3333333333"  # same ISBN
        }
        client.post("/books", json=updated_book)
        
        # should receive update notification
        notification = websocket.receive_json()
        assert notification["action"] == "updated"
        assert notification["book"]["title"] == "Updated Title"
        assert notification["book"]["id"] == 1

def test_websocket_delete_notification():
    # create book first
    book_data = {
        "title": "Book to Delete",
        "author": "Delete Author",
        "publication_year": 2023,
        "genre": "Action", 
        "isbn": "4444444444"
    }
    create_response = client.post("/books", json=book_data)
    book_id = create_response.json()["id"]
    
    with client.websocket_connect("/ws") as websocket:
        # skip initial load
        websocket.receive_json()
        
        # delete the book
        client.delete(f"/books/{book_id}")
        
        # should receive delete notification
        notification = websocket.receive_json() 
        assert notification["action"] == "deleted"
        assert notification["book"]["title"] == "Book to Delete"
        assert notification["book"]["id"] == book_id

def test_multiple_websocket_connections():
    with client.websocket_connect("/ws") as ws1, client.websocket_connect("/ws") as ws2:
        # both should receive initial load
        ws1.receive_json()
        ws2.receive_json()
        
        # create a book
        book_data = {
            "title": "Multi Client Book",
            "author": "Multi Author",
            "publication_year": 2023,
            "genre": "Thriller",
            "isbn": "5555555555"
        }
        client.post("/books", json=book_data)
        
        # both websockets should receive the notification
        notification1 = ws1.receive_json()
        notification2 = ws2.receive_json()
        
        assert notification1["action"] == "created"
        assert notification2["action"] == "created"
        assert notification1["book"]["title"] == "Multi Client Book"
        assert notification2["book"]["title"] == "Multi Client Book"

def test_websocket_survives_http_errors():
    with client.websocket_connect("/ws") as websocket:
        # skip initial load
        websocket.receive_json()
        
        # try to create book with invalid data (should fail)
        invalid_book = {
            "title": "Invalid Book",
            "author": "Invalid Author",
            "publication_year": 2030,  # invalid year
            "genre": "Fiction", 
            "isbn": "6666666666"
        }
        response = client.post("/books", json=invalid_book)
        assert response.status_code == 422
        
        # websocket should still be alive, create a valid book
        valid_book = {
            "title": "Valid Book",
            "author": "Valid Author",
            "publication_year": 2023,
            "genre": "Fiction",
            "isbn": "7777777777"
        }
        client.post("/books", json=valid_book)
        
        # should receive notification for valid book
        notification = websocket.receive_json()
        assert notification["action"] == "created"
        assert notification["book"]["title"] == "Valid Book"