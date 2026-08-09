from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import func

from .database import db
from .models import Appointment, Service, User, WorkSchedule


api = Blueprint("api", __name__)
ACTIVE_APPOINTMENT_STATUSES = ("agendado", "confirmado")
VALID_STATUSES = {"agendado", "confirmado", "concluido", "cancelado"}


def payload():
    return request.get_json(silent=True) or {}


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @jwt_required()
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user or not user.active:
                return jsonify(erro="Usuário inválido ou inativo"), 401
            if user.role not in roles:
                return jsonify(erro="Você não tem permissão para esta operação"), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def parse_datetime(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None


def validate_slot(professional, starts_at, ends_at, ignore_id=None):
    schedule = professional.schedule
    if not schedule:
        return "O profissional ainda não possui uma jornada configurada"
    if starts_at.weekday() not in schedule.weekday_set():
        return "O profissional não trabalha neste dia da semana"
    if starts_at.time() < schedule.start_time or ends_at.time() > schedule.end_time or starts_at.date() != ends_at.date():
        return "O horário está fora da jornada do profissional"

    conflict = Appointment.query.filter(
        Appointment.professional_id == professional.id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.starts_at < ends_at,
        Appointment.ends_at > starts_at,
    )
    if ignore_id:
        conflict = conflict.filter(Appointment.id != ignore_id)
    if conflict.first():
        return "O horário conflita com outro agendamento"
    return None


@api.post("/auth/login")
def login():
    data = payload()
    user = User.query.filter_by(username=str(data.get("usuario", "")).strip()).first()
    if not user or not user.active or not user.check_password(str(data.get("senha", ""))):
        return jsonify(erro="Credenciais inválidas"), 401
    token = create_access_token(identity=str(user.id), additional_claims={"tipo": user.role})
    return jsonify(token=token, usuario=user.to_dict())


@api.post("/clientes")
def create_client():
    data = payload()
    name = str(data.get("nome", "")).strip()
    username = str(data.get("usuario", "")).strip().lower()
    password = str(data.get("senha", ""))
    if not name or not username or len(password) < 6:
        return jsonify(erro="Nome, usuário e senha de pelo menos 6 caracteres são obrigatórios"), 400
    if User.query.filter_by(username=username).first():
        return jsonify(erro="Este nome de usuário já está em uso"), 409
    user = User(name=name, username=username, role="cliente", subscriber=bool(data.get("assinante", False)))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(usuario=user.to_dict()), 201


@api.get("/servicos")
def list_services():
    services = Service.query.filter_by(active=True).order_by(Service.name).all()
    return jsonify(servicos=[service.to_dict() for service in services])


@api.post("/servicos")
@roles_required("admin")
def create_service():
    data = payload()
    name = str(data.get("nome", "")).strip()
    duration = data.get("duracao_minutos")
    price = data.get("preco")
    if not name or not isinstance(duration, int) or duration <= 0 or not isinstance(price, (int, float)) or price < 0:
        return jsonify(erro="Informe nome, duração positiva e preço não negativo"), 400
    service = Service(name=name, duration_minutes=duration, price_cents=round(price * 100), active=bool(data.get("disponivel", True)))
    db.session.add(service)
    db.session.commit()
    return jsonify(servico=service.to_dict()), 201


@api.patch("/servicos/<int:service_id>")
@roles_required("admin")
def update_service(service_id):
    service = db.session.get(Service, service_id)
    if not service:
        return jsonify(erro="Serviço não encontrado"), 404
    data = payload()
    if "nome" in data and str(data["nome"]).strip():
        service.name = str(data["nome"]).strip()
    if "duracao_minutos" in data:
        if not isinstance(data["duracao_minutos"], int) or data["duracao_minutos"] <= 0:
            return jsonify(erro="A duração deve ser um inteiro positivo"), 400
        service.duration_minutes = data["duracao_minutos"]
    if "preco" in data:
        if not isinstance(data["preco"], (int, float)) or data["preco"] < 0:
            return jsonify(erro="O preço não pode ser negativo"), 400
        service.price_cents = round(data["preco"] * 100)
    if "disponivel" in data:
        service.active = bool(data["disponivel"])
    db.session.commit()
    return jsonify(servico=service.to_dict())


@api.get("/profissionais")
def list_professionals():
    users = User.query.filter_by(role="profissional", active=True).order_by(User.name).all()
    return jsonify(profissionais=[user.to_dict() for user in users])


@api.post("/profissionais")
@roles_required("admin")
def create_professional():
    data = payload()
    name = str(data.get("nome", "")).strip()
    username = str(data.get("usuario", "")).strip().lower()
    password = str(data.get("senha", ""))
    if not name or not username or len(password) < 6:
        return jsonify(erro="Nome, usuário e senha de pelo menos 6 caracteres são obrigatórios"), 400
    if User.query.filter_by(username=username).first():
        return jsonify(erro="Este nome de usuário já está em uso"), 409
    user = User(name=name, username=username, role="profissional")
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(WorkSchedule(professional_id=user.id, start_time=datetime.strptime("09:00", "%H:%M").time(), end_time=datetime.strptime("18:00", "%H:%M").time(), weekdays="0,1,2,3,4,5"))
    db.session.commit()
    return jsonify(profissional=user.to_dict()), 201


@api.put("/profissionais/<int:professional_id>/jornada")
@roles_required("admin")
def update_schedule(professional_id):
    professional = db.session.get(User, professional_id)
    if not professional or professional.role != "profissional":
        return jsonify(erro="Profissional não encontrado"), 404
    data = payload()
    try:
        start = datetime.strptime(data.get("inicio", ""), "%H:%M").time()
        end = datetime.strptime(data.get("fim", ""), "%H:%M").time()
        weekdays = sorted({int(day) for day in data.get("dias_semana", [])})
    except (TypeError, ValueError):
        return jsonify(erro="Use horários HH:MM e dias da semana de 0 (segunda) a 6 (domingo)"), 400
    if start >= end or not weekdays or any(day < 0 or day > 6 for day in weekdays):
        return jsonify(erro="Jornada inválida"), 400
    schedule = professional.schedule or WorkSchedule(professional_id=professional.id)
    schedule.start_time, schedule.end_time = start, end
    schedule.weekdays = ",".join(map(str, weekdays))
    db.session.add(schedule)
    db.session.commit()
    return jsonify(jornada=schedule.to_dict())


@api.post("/agendamentos")
@roles_required("cliente", "admin")
def create_appointment():
    data = payload()
    user = current_user()
    client_id = user.id if user.role == "cliente" else data.get("cliente_id")
    client = db.session.get(User, client_id) if isinstance(client_id, int) else None
    professional = db.session.get(User, data.get("profissional_id")) if isinstance(data.get("profissional_id"), int) else None
    service = db.session.get(Service, data.get("servico_id")) if isinstance(data.get("servico_id"), int) else None
    starts_at = parse_datetime(data.get("data_hora"))
    if not client or client.role != "cliente" or not professional or professional.role != "profissional" or not service or not service.active:
        return jsonify(erro="Cliente, profissional ou serviço inválido"), 400
    if not starts_at or starts_at <= datetime.now():
        return jsonify(erro="Informe uma data futura no formato YYYY-MM-DD HH:MM"), 400
    ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    error = validate_slot(professional, starts_at, ends_at)
    if error:
        return jsonify(erro=error), 409
    appointment = Appointment(client_id=client.id, professional_id=professional.id, service_id=service.id, starts_at=starts_at, ends_at=ends_at)
    db.session.add(appointment)
    db.session.commit()
    return jsonify(agendamento=appointment.to_dict()), 201


@api.get("/agendamentos")
@roles_required("cliente", "profissional", "admin")
def list_appointments():
    user = current_user()
    query = Appointment.query
    if user.role == "cliente":
        query = query.filter_by(client_id=user.id)
    elif user.role == "profissional":
        query = query.filter_by(professional_id=user.id)
    status = request.args.get("status")
    if status in VALID_STATUSES:
        query = query.filter_by(status=status)
    appointments = query.order_by(Appointment.starts_at.desc()).all()
    return jsonify(agendamentos=[appointment.to_dict() for appointment in appointments])


@api.patch("/agendamentos/<int:appointment_id>/status")
@roles_required("cliente", "profissional", "admin")
def update_appointment_status(appointment_id):
    appointment = db.session.get(Appointment, appointment_id)
    user = current_user()
    if not appointment:
        return jsonify(erro="Agendamento não encontrado"), 404
    new_status = payload().get("status")
    allowed = {"admin": VALID_STATUSES, "profissional": {"confirmado", "concluido", "cancelado"}, "cliente": {"cancelado"}}
    owns_appointment = user.role == "admin" or (user.role == "cliente" and appointment.client_id == user.id) or (user.role == "profissional" and appointment.professional_id == user.id)
    if not owns_appointment:
        return jsonify(erro="Você não tem acesso a este agendamento"), 403
    if new_status not in allowed[user.role]:
        return jsonify(erro="Transição de status não permitida"), 400
    appointment.status = new_status
    db.session.commit()
    return jsonify(agendamento=appointment.to_dict())


@api.get("/admin/dashboard")
@roles_required("admin")
def dashboard():
    completed = Appointment.query.filter_by(status="concluido")
    revenue_cents = completed.join(Service).with_entities(func.coalesce(func.sum(Service.price_cents), 0)).scalar()
    return jsonify(
        total_clientes=User.query.filter_by(role="cliente", active=True).count(),
        total_assinantes=User.query.filter_by(role="cliente", active=True, subscriber=True).count(),
        total_profissionais=User.query.filter_by(role="profissional", active=True).count(),
        agendamentos_pendentes=Appointment.query.filter(Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES)).count(),
        atendimentos_concluidos=completed.count(),
        faturamento=round(revenue_cents / 100, 2),
    )
