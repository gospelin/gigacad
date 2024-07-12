import pytest
from application import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Where Practical Learning Meets Knowledge and Confidence" in response.data
    assert (
        b"We are committed to providing a transformative education experience"
        in response.data
    )
