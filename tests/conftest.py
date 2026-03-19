import pytest


@pytest.fixture
def sample_user_data():
    return {
        "id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "language_level": "beginner",
    }
