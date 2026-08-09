from datetime import datetime, timedelta


def next_workday(hour=10):
    candidate = datetime.now() + timedelta(days=1)
    while candidate.weekday() == 6:
        candidate += timedelta(days=1)
    return candidate.replace(hour=hour, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")


def test_login_rejects_invalid_password(client):
    response = client.post("/api/auth/login", json={"usuario": "admin", "senha": "errada"})
    assert response.status_code == 401


def test_client_registration_hashes_password_and_can_login(client):
    response = client.post(
        "/api/clientes",
        json={"nome": "Maria", "usuario": "maria", "senha": "segredo123"},
    )
    assert response.status_code == 201
    assert "senha" not in response.get_json()["usuario"]
    login = client.post("/api/auth/login", json={"usuario": "maria", "senha": "segredo123"})
    assert login.status_code == 200
    assert login.get_json()["token"]


def test_admin_can_create_service(client, admin_headers):
    response = client.post(
        "/api/servicos",
        headers=admin_headers,
        json={"nome": "Pezinho", "duracao_minutos": 15, "preco": 20},
    )
    assert response.status_code == 201
    assert response.get_json()["servico"]["preco"] == 20


def test_client_cannot_create_service(client, client_headers):
    response = client.post(
        "/api/servicos",
        headers=client_headers,
        json={"nome": "Invasão", "duracao_minutos": 15, "preco": 1},
    )
    assert response.status_code == 403


def test_appointment_blocks_overlapping_slot(client, client_headers):
    appointment = {
        "profissional_id": 2,
        "servico_id": 1,
        "data_hora": next_workday(),
    }
    first = client.post("/api/agendamentos", headers=client_headers, json=appointment)
    second = client.post("/api/agendamentos", headers=client_headers, json=appointment)
    assert first.status_code == 201
    assert second.status_code == 409


def test_client_only_sees_own_appointments(client, client_headers):
    client.post(
        "/api/agendamentos",
        headers=client_headers,
        json={"profissional_id": 2, "servico_id": 2, "data_hora": next_workday(11)},
    )
    response = client.get("/api/agendamentos", headers=client_headers)
    assert response.status_code == 200
    assert len(response.get_json()["agendamentos"]) == 1
    assert response.get_json()["agendamentos"][0]["cliente"]["id"] == 3
