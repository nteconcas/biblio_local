import os
from dotenv import load_dotenv
from flask import Flask, redirect, url_for
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db, login_manager
from models import User, AppSettings
from routes.auth import auth_bp
from routes.catalog import catalog_bp
from routes.loans import loans_bp
from routes.admin import admin_bp
from routes.reports import reports_bp
from routes.labels import labels_bp

load_dotenv()

def create_app():
    app = Flask(__name__)

    # ── Proxy Fix ──────────────────────────────────────────────
    # Render / Heroku / qualquer PaaS termina o TLS no proxy reverso
    # e repassa a requisição via HTTP interno.  Sem este middleware
    # o Flask gera urls com http:// nos redirects e no url_for(),
    # o que faz o navegador marcar a página como "insegura".
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,       # X-Forwarded-For   (IP real do cliente)
        x_proto=1,     # X-Forwarded-Proto (https)
        x_host=1,      # X-Forwarded-Host  (domínio real)
        x_port=1       # X-Forwarded-Port  (443)
    )
    
    # Prioridade para DATABASE_URL (comum em Heroku/Render)
    # Senão, monta a string a partir das variáveis individuais
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    if not db_url:
        user = os.environ.get('DB_USER', 'postgres')
        pwd = os.environ.get('DB_PASSWORD', 'postgres')
        host = os.environ.get('DB_HOST', 'localhost')
        port = os.environ.get('DB_PORT', '5432')
        name = os.environ.get('DB_NAME', 'biblio_db')
        db_url = f"postgresql://{user}:{pwd}@{host}:{port}/{name}"

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-altere-em-producao')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PREFERRED_URL_SCHEME'] = 'https'

    # Inicializar extensões
    db.init_app(app)
    login_manager.init_app(app)

    # Registrar Blueprints (sem prefixo para manter compatibilidade com templates)
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(labels_bp)

    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.now()}

    @app.after_request
    def set_security_headers(response):
        # Força o navegador a usar HTTPS em todas as requisições futuras
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # Atualiza automaticamente recursos http:// para https://
        response.headers['Content-Security-Policy'] = "upgrade-insecure-requests"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id)) if user_id else None

    @app.route('/')
    def index_redirect():
        if current_user.is_authenticated:
            return redirect(url_for('loans.loans_page'))
        return redirect(url_for('auth.login'))

    # Inicialização do Banco de Dados com Retry (para Docker)
    import time
    with app.app_context():
        max_retries = 5
        for i in range(max_retries):
            try:
                db.create_all()
                break
            except Exception as e:
                if i == max_retries - 1:
                    print(f"Erro fatal ao conectar no banco: {e}")
                    raise e
                print(f"Aguardando banco de dados... (tentativa {i+1}/{max_retries})")
                time.sleep(3)

        # Atualização automática de esquema (Migração manual simples)
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash TYPE VARCHAR(256)'))
            db.session.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash DROP NOT NULL'))
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN registration_number VARCHAR(30) UNIQUE'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Criar admin padrão
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
        # Configurações padrão
        defaults = [
            ('max_books_per_user', '3'),
            ('max_renewals', '2'),
            ('loan_days', '7'),
            ('fine_per_day', '0.50')
        ]
        for key, val in defaults:
            if not AppSettings.query.filter_by(key=key).first():
                db.session.add(AppSettings(key=key, value=val))
        db.session.commit()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000, host='0.0.0.0')