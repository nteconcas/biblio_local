from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import User, AppSettings, Copy, Loan, Book, db
from utils import get_settings
from sqlalchemy.orm import joinedload
import barcode, io, base64
from barcode.writer import ImageWriter

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users')
@login_required
def users():
    return render_template('users.html', users=User.query.all())

@admin_bp.route('/add_user', methods=['POST'])
@login_required
def add_user():
    username = request.form.get('username', '').strip()
    registration = request.form.get('registration', '').strip()
    pwd = request.form.get('password', '').strip()
    role = request.form.get('role', 'member')
    
    if not username:
        flash('Nome do usuário é obrigatório.', 'error')
        return redirect(url_for('admin.users'))
    
    if User.query.filter_by(username=username).first():
        flash('Usuário já existe.', 'error')
        return redirect(url_for('admin.users'))

    u = User(username=username, registration_number=registration or None, role=role)
    if pwd:
        u.set_password(pwd)
    elif role in ['admin', 'librarian']:
        flash('Administradores precisam de senha.', 'error')
        return redirect(url_for('admin.users'))

    db.session.add(u)
    db.session.commit()
    flash('Usuário criado com sucesso!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/edit_user/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    u = db.session.get(User, user_id)
    if not u: return redirect(url_for('admin.users'))
    
    username = request.form.get('username', '').strip()
    registration = request.form.get('registration', '').strip()
    pwd = request.form.get('password', '').strip()
    role = request.form.get('role', 'member')
    
    if not username:
        flash('Nome é obrigatório.', 'error')
        return redirect(url_for('admin.users'))
        
    # Verifica se já existe outro usuário com mesmo nome
    other = User.query.filter(User.username == username, User.id != user_id).first()
    if other:
        flash('Nome de usuário já em uso.', 'error')
        return redirect(url_for('admin.users'))

    u.username = username
    u.registration_number = registration or None
    u.role = role
    if pwd:
        u.set_password(pwd)
        
    db.session.commit()
    flash(f'✅ Usuário "{username}" atualizado!', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/settings')
@login_required
def settings():
    if current_user.role not in ['admin', 'librarian']:
        return redirect(url_for('loans.loans_page'))
    return render_template('settings.html', settings=get_settings())

@admin_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    for key in ['max_books_per_user', 'max_renewals', 'loan_days', 'fine_per_day']:
        val = request.form.get(key)
        if val: AppSettings.set(key, val)
    flash('Configurações atualizadas!', 'success')
    return redirect(url_for('admin.settings'))

# Removidas rotas redundantes de etiquetas (agora em labels.py)


@admin_bp.route('/api/search_users')
@login_required
def api_search_users():
    query = request.args.get('q', '').strip()
    from sqlalchemy import or_
    
    base_query = User.query.filter(User.role != 'admin')
    
    if query:
        # Busca por Nome ou Matrícula
        filters = [
            User.username.ilike(f'%{query}%'),
            User.registration_number.ilike(f'%{query}%')
        ]
        # Adiciona busca por ID se for número
        if query.isdigit():
            filters.append(User.id == int(query))
            
        users = base_query.filter(or_(*filters)).limit(10).all()
    else:
        # Lista padrão
        users = base_query.order_by(User.id.desc()).limit(10).all()
    
    return jsonify([{
        'id': u.id, 'username': u.username, 'role': u.role, 'registration_number': u.registration_number,
        'active_loans': Loan.query.filter_by(user_id=u.id, status='active').count()
    } for u in users])
