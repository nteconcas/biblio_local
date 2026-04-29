import os
import time
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

def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')

def get_database_url():
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if db_url:
        if db_url.startswith('postgres://'):
            return db_url.replace('postgres://', 'postgresql://', 1)
        return db_url

    user = os.environ.get('DB_USER', 'postgres')
    pwd = os.environ.get('DB_PASSWORD', 'postgres')
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    name = os.environ.get('DB_NAME', 'biblio_db')
    return f'postgresql://{user}:{pwd}@{host}:{port}/{name}'

def create_app():
    app = Flask(__name__)

    trusted_proxies = int(os.environ.get('TRUST_PROXY_COUNT', '1'))
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=trusted_proxies,
        x_proto=trusted_proxies,
        x_host=trusted_proxies,
        x_port=trusted_proxies
    )
    
    db_url = get_database_url()

    preferred_scheme = os.environ.get('PREFERRED_URL_SCHEME', 'http')
    secure_cookies = env_bool('COOKIE_SECURE', preferred_scheme == 'https')

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-altere-em-producao')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PREFERRED_URL_SCHEME'] = preferred_scheme
    app.config['SESSION_COOKIE_SECURE'] = secure_cookies
    app.config['REMEMBER_COOKIE_SECURE'] = secure_cookies

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
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if env_bool('ENABLE_HTTPS_HEADERS', preferred_scheme == 'https'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = 'upgrade-insecure-requests'
        return response

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id)) if user_id else None

    @app.route('/')
    def index_redirect():
        if current_user.is_authenticated:
            return redirect(url_for('loans.loans_page'))
        return redirect(url_for('auth.login'))

    @app.get('/health')
    def health():
        return {'status': 'ok'}, 200

    # Inicialização do Banco de Dados com Retry (para Docker)
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

        admin_username = os.environ.get('ADMIN_USERNAME', 'admin').strip() or 'admin'
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123').strip() or 'admin123'
        sync_admin_password = env_bool('SYNC_ADMIN_PASSWORD', False)

        # Garante um admin funcional mesmo ao reaproveitar banco remoto existente.
        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            admin = User(username=admin_username, role='admin')
            admin.set_password(admin_password)
            db.session.add(admin)
        elif admin.role == 'admin' and (not admin.password_hash or sync_admin_password):
            admin.set_password(admin_password)

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
    app.run(
        debug=env_bool('FLASK_DEBUG', False),
        port=int(os.environ.get('PORT', '5000')),
        host='0.0.0.0'
    )
