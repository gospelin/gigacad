from application import app


def test_index_route():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to Aunty Anne's International School" in response.data
