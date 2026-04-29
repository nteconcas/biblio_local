from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from models import User
from extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('loans.loans_page'))
            flash('Credenciais inválidas.', 'error')
        except Exception:
            current_app.logger.exception('Falha ao processar login.')
            flash('Erro ao acessar o banco ou validar o login.', 'error')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        pwd = request.form.get('password', '').strip()
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe.', 'error')
        elif not username or not pwd:
            flash('Preencha usuário e senha.', 'error')
        else:
            u = User(username=username, role='member')
            u.set_password(pwd)
            db.session.add(u)
            db.session.commit()
            flash('Conta criada! Faça login.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
