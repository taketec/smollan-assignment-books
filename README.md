## smollan-assignment-books
# Create/Update: Combine create and update operations into a single endpoint.
    • If the book with the same isbn or the same combination of title, author, and publication_year exists, update the book details.✅
    • If no such book exists, create a new book with a new id.✅
    • Validate that the ISBN is unique.✅
    • Validate that the publication year is within a reasonable range (e.g., 1450 to the current year).✅

# Read: Retrieve all books.
    • Support pagination.✅
    • Support sorting by title, author, or publication year.✅
    • Support filtering by genre or author.✅
    • Add a websocket to connect, which will fetch books updated in real-time and add and remove and update the response.✅

# Constraints
    • Use only the JSON file for data storage.✅
    • Ensure thread safety when reading and writing to the JSON file.✅
    • Implement proper error handling and validation.✅
    • Provide meaningful responses for each operation.✅
