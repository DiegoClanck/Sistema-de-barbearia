from datetime import time

from .database import db
from .models import Service, User, WorkSchedule


def seed_database():
    if User.query.first():
        return

    admin = User(name="Administrador", username="admin", role="admin")
    admin.set_password("admin123")
    barbeiro = User(name="Carlos Barbeiro", username="carlos", role="profissional")
    barbeiro.set_password("123456")
    cliente = User(name="João Silva", username="joao", role="cliente")
    cliente.set_password("123456")
    db.session.add_all([admin, barbeiro, cliente])
    db.session.flush()
    db.session.add(
        WorkSchedule(
            professional_id=barbeiro.id,
            start_time=time(9, 0),
            end_time=time(19, 0),
            weekdays="0,1,2,3,4,5",
        )
    )
    db.session.add_all(
        [
            Service(name="Corte de cabelo", duration_minutes=40, price_cents=4500),
            Service(name="Barba", duration_minutes=30, price_cents=3500),
            Service(name="Corte e barba", duration_minutes=70, price_cents=7500),
        ]
    )
    db.session.commit()
