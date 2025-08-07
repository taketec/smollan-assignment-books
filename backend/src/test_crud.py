import pytest
import json
import os
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# clean up before each test
@pytest.fixture(autouse=True)
def setup_test_data():
    # reset books.json before each test
    with open("books.json", "w") as f:
        json.dump([], f)
    yield
    # cleanup after test (optional)

def test_create_book():
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "publication_year": 2023,
        "genre": "Fiction",
        "isbn": "1234567890"
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"
    assert data["id"] == 1

def test_get_books_empty():
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert data["books"] == []
    assert data["total"] == 0

def test_get_books_with_data():
    # create a book first
    book_data = {
        "title": "Sample Book",
        "author": "Sample Author", 
        "publication_year": 2022,
        "genre": "Mystery",
        "isbn": "9876543210"
    }
    client.post("/books", json=book_data)
    
    # now get books
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data["books"]) == 1
    assert data["total"] == 1
    assert data["books"][0]["title"] == "Sample Book"

def test_update_book_by_isbn():
    # create original book
    original_book = {
        "title": "Original Title",
        "author": "Original Author",
        "publication_year": 2020,
        "genre": "Drama",
        "isbn": "1111111111"
    }
    client.post("/books", json=original_book)
    
    # update with same ISBN but different details
    updated_book = {
        "title": "Updated Title",
        "author": "Updated Author", 
        "publication_year": 2023,
        "genre": "Comedy",
        "isbn": "1111111111"  # same ISBN
    }
    response = client.post("/books", json=updated_book)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["author"] == "Updated Author"
    assert data["id"] == 1  # same ID

def test_update_book_by_title_author_year():
    # create original book
    original_book = {
        "title": "Same Title",
        "author": "Same Author",
        "publication_year": 2021,
        "genre": "Horror", 
        "isbn": "2222222222"
    }
    client.post("/books", json=original_book)
    
    # update with same title+author+year but different ISBN
    updated_book = {
        "title": "Same Title", 
        "author": "Same Author",
        "publication_year": 2021,
        "genre": "Thriller",
        "isbn": "3333333333"  # different ISBN
    }
    response = client.post("/books", json=updated_book)
    assert response.status_code == 200
    data = response.json()
    assert data["isbn"] == "3333333333"
    assert data["genre"] == "Thriller"
    assert data["id"] == 1  # same ID

def test_delete_book():
    # create a book first
    book_data = {
        "title": "Book to Delete",
        "author": "Delete Author",
        "publication_year": 2023,
        "genre": "Action",
        "isbn": "4444444444"
    }
    create_response = client.post("/books", json=book_data)
    book_id = create_response.json()["id"]
    
    # delete the book
    delete_response = client.delete(f"/books/{book_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Book deleted successfully"
    
    # verify its gone
    get_response = client.get("/books")
    assert get_response.json()["total"] == 0

def test_delete_nonexistent_book():
    response = client.delete("/books/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"

def test_filtering():
    # create books with different genres
    book1 = {
        "title": "Fiction Book",
        "author": "Fiction Author",
        "publication_year": 2023,
        "genre": "Fiction",
        "isbn": "6666666666"
    }
    book2 = {
        "title": "Mystery Book",
        "author": "Mystery Author", 
        "publication_year": 2023,
        "genre": "Mystery",
        "isbn": "7777777777"
    }
    client.post("/books", json=book1)
    client.post("/books", json=book2)
    
    # filter by genre
    response = client.get("/books?genre=Fiction")
    data = response.json()
    assert len(data["books"]) == 1
    assert data["books"][0]["genre"] == "Fiction"

def test_sorting():
    # create books with different years
    book1 = {
        "title": "Older Book",
        "author": "Author A",
        "publication_year": 2020,
        "genre": "Fiction", 
        "isbn": "8888888888"
    }
    book2 = {
        "title": "Newer Book",
        "author": "Author B",
        "publication_year": 2023,
        "genre": "Fiction",
        "isbn": "9999999999"
    }
    client.post("/books", json=book1)
    client.post("/books", json=book2)
    
    # sort by publication year
    response = client.get("/books?sort_by=publication_year")
    data = response.json()
    assert data["books"][0]["publication_year"] == 2020
    assert data["books"][1]["publication_year"] == 2023

def test_invalid_publication_year():
    book_data = {
        "title": "Future Book",
        "author": "Time Traveler",
        "publication_year": 2030,  # invalid year
        "genre": "Sci-Fi",
        "isbn": "1010101010"
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 422  # validation error