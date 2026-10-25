def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_engine_registry(client):
    response = client.get("/api/v1/engines")
    assert response.status_code == 200
    assert any(item["id"] == "image" for item in response.json()["engines"])


def test_rejects_non_image(client):
    response = client.post(
        "/api/v1/image/analyze",
        files={"file": ("not-image.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_rejects_empty_file(client):
    response = client.post(
        "/api/v1/image/analyze",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400
