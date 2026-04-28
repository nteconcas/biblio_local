from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from models import Loan, User, Copy, Book, db
from utils import get_settings

loans_bp = Blueprint('loans', __name__)

@loans_bp.route('/loans')
@login_required
def loans_page():
    settings = get_settings()
    active_loans = Loan.query.filter_by(status='active').options(
        joinedload(Loan.user), joinedload(Loan.copy).joinedload(Copy.book)
    ).order_by(Loan.due_date.asc()).all()
    
    users = User.query.filter(User.role != 'admin').all()
    now = datetime.now()
    
    loans_with_status = []
    for loan in active_loans:
        # Pula se usuário, cópia ou livro foi removido do banco (integridade)
        if not loan.user or not loan.copy or not loan.copy.book:
            continue
            
        is_late = loan.due_date < now
        # Calcula diferença absoluta em dias
        delta = loan.due_date - now
        days_left = delta.days if not is_late else abs(delta.days)
        
        loans_with_status.append({
            'loan': loan, 'is_late': is_late, 'days_left': days_left,
            'can_renew': loan.renewals < settings['max_renewals']
        })
    
    # Estatísticas rápidas
    total_books = Book.query.count()
    total_users = User.query.filter_by(role='member').count()
    late_count = sum(1 for item in loans_with_status if item['is_late'])

    stats = {
        'total_books': total_books,
        'total_users': total_users,
        'active_loans': len(loans_with_status),
        'late_loans': late_count
    }

    return render_template('dashboard.html', 
                           active_loans=loans_with_status, 
                           users=users, 
                           now=now, 
                           settings=settings,
                           stats=stats)

@loans_bp.route('/borrow', methods=['POST'])
@login_required
def borrow():
    settings = get_settings()
    try:
        user_input = request.form.get('user_search', '').strip()
        user_id = request.form.get('user_id', '').strip()
        if user_id and user_id.isdigit():
            user = db.session.get(User, int(user_id))
        elif user_input:
            if user_input.isdigit():
                user = db.session.get(User, int(user_input))
            else:
                user = User.query.filter_by(username=user_input).first()
        else:
            user = None
        
        if not user:
            flash('❌ Usuário não encontrado.', 'error')
            return redirect(url_for('loans.loans_page'))
        
        active_count = Loan.query.filter_by(user_id=user.id, status='active').count()
        if active_count >= settings['max_books_per_user']:
            flash(f'⚠️ Limite de empréstimos atingido.', 'error')
            return redirect(url_for('loans.loans_page'))
        
        barcode_val = request.form.get('barcode_search', '').strip()
        copy = Copy.query.filter_by(barcode=barcode_val).first()
        
        if not copy:
            flash('❌ Cópia não encontrada.', 'error')
            return redirect(url_for('loans.loans_page'))
        if copy.status != 'available':
            status_map = {'loaned': 'Emprestado', 'decommissioned': 'Baixa', 'borrowed': 'Emprestado'}
            status_desc = status_map.get(copy.status, copy.status)
            flash(f'⚠️ Exemplar indisponível para empréstimo (Status: {status_desc}).', 'error')
            return redirect(url_for('loans.loans_page'))
        
        loan = Loan(
            user_id=user.id, copy_id=copy.id,
            due_date=datetime.now() + timedelta(days=settings['loan_days'])
        )
        copy.status = 'borrowed'
        db.session.add(loan)
        db.session.commit()
        
        flash(f'✅ Emprestado para {user.username}!', 'success')
    except Exception as e:
        flash(f'❌ Erro: {e}', 'error')
    return redirect(url_for('loans.loans_page'))

@loans_bp.route('/renew/<int:loan_id>')
@login_required
def renew_loan(loan_id):
    settings = get_settings()
    loan = db.session.get(Loan, loan_id)
    if not loan or loan.status != 'active':
        flash('❌ Não encontrado.', 'error')
        return redirect(url_for('loans.loans_page'))
    
    if loan.renewals >= settings['max_renewals']:
        flash(f'⚠️ Limite de renovações atingido.', 'error')
        return redirect(url_for('loans.loans_page'))
    
    loan.due_date = datetime.now() + timedelta(days=settings['loan_days'])
    loan.renewals += 1
    db.session.commit()
    return redirect(url_for('loans.loans_page'))

@loans_bp.route('/return', methods=['POST'])
@login_required
def return_book():
    settings = get_settings()
    barcode_val = request.form.get('barcode', '').strip()
    copy = Copy.query.filter_by(barcode=barcode_val).first()
    if not copy or copy.status == 'available':
        flash('❌ Inválido ou já devolvido.', 'error')
        return redirect(url_for('loans.loans_page'))
    
    loan = Loan.query.filter_by(copy_id=copy.id, status='active').first()
    if not loan:
        flash('❌ Empréstimo não encontrado.', 'error')
        return redirect(url_for('loans.loans_page'))
    
    loan.return_date = datetime.now()
    days_late = (loan.return_date - loan.due_date).days
    loan.fine = days_late * settings['fine_per_day'] if days_late > 0 else 0.0
    loan.status = 'returned'
    copy.status = 'available'
    db.session.commit()
    flash('📥 Devolução registrada.', 'success')
    return redirect(url_for('loans.loans_page'))
