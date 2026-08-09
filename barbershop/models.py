from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    subscriber = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    schedule = db.relationship("WorkSchedule", back_populates="professional", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        data = {"id": self.id, "nome": self.name, "usuario": self.username, "tipo": self.role, "ativo": self.active}
        if self.role == "cliente":
            data["assinante"] = self.subscriber
        if self.schedule:
            data["jornada"] = self.schedule.to_dict()
        return data


class WorkSchedule(db.Model):
    __tablename__ = "work_schedules"

    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    weekdays = db.Column(db.String(20), nullable=False, default="0,1,2,3,4,5")

    professional = db.relationship("User", back_populates="schedule")

    def weekday_set(self):
        return {int(day) for day in self.weekdays.split(",") if day != ""}

    def to_dict(self):
        return {
            "inicio": self.start_time.strftime("%H:%M"),
            "fim": self.end_time.strftime("%H:%M"),
            "dias_semana": sorted(self.weekday_set()),
        }


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price_cents = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.name,
            "duracao_minutos": self.duration_minutes,
            "preco": self.price_cents / 100,
            "disponivel": self.active,
        }


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    professional_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    ends_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="agendado", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    client = db.relationship("User", foreign_keys=[client_id])
    professional = db.relationship("User", foreign_keys=[professional_id])
    service = db.relationship("Service")

    def to_dict(self):
        return {
            "id": self.id,
            "cliente": {"id": self.client.id, "nome": self.client.name},
            "profissional": {"id": self.professional.id, "nome": self.professional.name},
            "servico": self.service.to_dict(),
            "inicio": self.starts_at.strftime("%Y-%m-%d %H:%M"),
            "fim": self.ends_at.strftime("%Y-%m-%d %H:%M"),
            "status": self.status,
        }
