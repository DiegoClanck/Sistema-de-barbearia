import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .database import db


jwt = JWTManager()


def create_app(test_config=None):
    app = Flask(__name__)
    database_path = os.path.join(app.instance_path, "barbearia.db")
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY", "desenvolvimento-local-troque-esta-chave-antes-de-publicar"),
        JWT_ACCESS_TOKEN_EXPIRES=60 * 60 * 8,
        JSON_SORT_KEYS=False,
        DEBUG=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from .routes import api

    app.register_blueprint(api, url_prefix="/api")

    @app.get("/")
    def index():
        return jsonify(
            nome="Sistema de Barbearia",
            versao="1.0.0",
            status="online",
            documentacao="Consulte o README.md",
        )

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(erro="Rota não encontrada"), 404

    with app.app_context():
        db.create_all()
        from .seed import seed_database

        seed_database()

    return app
