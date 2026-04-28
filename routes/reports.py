from flask import Blueprint, render_template, redirect, url_for, flash, make_response
from flask_login import login_required
from sqlalchemy.orm import joinedload
from models import Book, User, Loan, Copy, db
import csv, io

reports_bp = Blueprint('reports', __name__)

from datetime import datetime

@reports_bp.route('/report/book/<int:book_id>')
@login_required
def report_book(book_id):
    book = db.session.get(Book, book_id)
    if not book: return redirect(url_for('catalog.catalog'))
    copy_ids = [c.id for c in book.copies]
    history = Loan.query.filter(Loan.copy_id.in_(copy_ids)).options(
        joinedload(Loan.user), joinedload(Loan.copy)
    ).order_by(Loan.loan_date.desc()).all()
    return render_template('report_book.html', book=book, history=history, now=datetime.now())

@reports_bp.route('/report/user/<int:user_id>')
@login_required
def report_user(user_id):
    user = db.session.get(User, user_id)
    if not user: return redirect(url_for('admin.users'))
    history = Loan.query.filter_by(user_id=user.id).options(
        joinedload(Loan.copy).joinedload(Copy.book)
    ).order_by(Loan.loan_date.desc()).all()
    stats = {
        'total': len(history),
        'returned': len([l for l in history if l.status == 'returned']),
        'active': len([l for l in history if l.status == 'active']),
        'fines': sum(l.fine for l in history if l.fine)
    }
    return render_template('report_user.html', user=user, history=history, stats=stats)

@reports_bp.route('/report/export/user/<int:user_id>.csv')
@login_required
def export_user_report(user_id):
    user = db.session.get(User, user_id)
    if not user: return redirect(url_for('admin.users'))
    history = Loan.query.filter_by(user_id=user.id).options(
        joinedload(Loan.copy).joinedload(Copy.book)
    ).order_by(Loan.loan_date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Data Retirada', 'Data Devolução', 'Livro', 'Código', 'Status', 'Multa (R$)'])
    for l in history:
        writer.writerow([
            l.loan_date.strftime('%d/%m/%Y %H:%M'),
            l.return_date.strftime('%d/%m/%Y %H:%M') if l.return_date else '-',
            l.copy.book.title, l.copy.barcode,
            'Devolvido' if l.status == 'returned' else 'Ativo',
            f'{l.fine:.2f}' if l.fine else '0.00'
        ])
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{user.username}.csv'
    return response

@reports_bp.route('/report_portal')
@login_required
def report_portal():
    return render_template('report_portal.html')

@reports_bp.route('/report/export/catalog.csv')
@login_required
def export_catalog():
    books = Book.query.options(joinedload(Book.copies)).all()
    output = io.StringIO()
    output.write('\ufeff') # BOM for Excel UTF-8
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Título', 'Autor', 'ISBN', 'Gênero', 'Classificação', 'Ano', 'Cópias'])
    for b in books:
        writer.writerow([b.title, b.author or '-', b.isbn or '-', b.genre or '-', b.classification or '-', b.publication_year or '-', len(b.copies)])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=acervo_completo.csv'
    return response

@reports_bp.route('/report/export/users.csv')
@login_required
def export_users():
    users = User.query.all()
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID', 'Nome', 'Matrícula', 'Perfil'])
    for u in users:
        writer.writerow([u.id, u.username, u.registration_number or '-', u.role])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=usuarios.csv'
    return response

@reports_bp.route('/report/export/loans.csv')
@login_required
def export_loans():
    loans = Loan.query.options(joinedload(Loan.user), joinedload(Loan.copy).joinedload(Copy.book)).all()
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Leitor', 'Matrícula', 'Livro', 'Código', 'Data Retirada', 'Data Devolução', 'Status', 'Multa'])
    for l in loans:
        writer.writerow([
            l.user.username if l.user else 'Removido',
            l.user.registration_number if l.user else '-',
            l.copy.book.title if l.copy and l.copy.book else 'Removido',
            l.copy.barcode if l.copy else '-',
            l.loan_date.strftime('%d/%m/%Y %H:%M'),
            l.return_date.strftime('%d/%m/%Y %H:%M') if l.return_date else '-',
            'Devolvido' if l.status == 'returned' else 'Ativo',
            f'{l.fine:.2f}' if l.fine else '0.00'
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=movimentacao.csv'
    return response
