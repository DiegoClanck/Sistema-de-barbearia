import pytest

from barbershop import create_app
from barbershop.database import db


@pytest.fixture()
def app():
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret-with-at-least-thirty-two-bytes",
        }
    )
    yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username, password):
    response = client.post("/api/auth/login", json={"usuario": username, "senha": password})
    return response.get_json()["token"]


@pytest.fixture()
def admin_headers(client):
    return {"Authorization": f"Bearer {login(client, 'admin', 'admin123')}"}


@pytest.fixture()
def client_headers(client):
    return {"Authorization": f"Bearer {login(client, 'joao', '123456')}"}
