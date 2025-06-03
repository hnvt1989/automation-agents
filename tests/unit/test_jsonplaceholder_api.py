import pytest
import requests

def test_get_post():
    """Test GET request to JSONPlaceholder API for post with ID 1."""
    
    # Make GET request to the endpoint
    response = requests.get('https://jsonplaceholder.typicode.com/posts/1')
    
    # Assert status code is 200 (OK)
    assert response.status_code == 200
    
    # Get response data
    data = response.json()
    
    # Assert the structure and content of the response
    assert isinstance(data, dict), "Response should be a dictionary"
    assert data['id'] == 1, "Post ID should be 1"
    assert data['userId'] == 1, "User ID should be 1"
    assert 'title' in data, "Response should contain a title"
    assert 'body' in data, "Response should contain a body"
    assert isinstance(data['title'], str), "Title should be a string"
    assert isinstance(data['body'], str), "Body should be a string"
    assert len(data['title']) > 0, "Title should not be empty"
    assert len(data['body']) > 0, "Body should not be empty" 