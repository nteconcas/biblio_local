from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required
from models import Book, Copy, db
import barcode
from barcode.writer import ImageWriter
import io

labels_bp = Blueprint('labels', __name__)

@labels_bp.route('/labels')
@login_required
def labels_page():
    # Retorna lista de livros para seleção de etiquetas
    books = Book.query.order_by(Book.title).all()
    return render_template('labels.html', books=books)

@labels_bp.route('/api/generate_labels', methods=['POST'])
@login_required
def generate_labels():
    copy_ids = request.form.getlist('copy_ids')
    if not copy_ids:
        flash('Selecione ao menos um item para gerar etiquetas.', 'error')
        return redirect(url_for('labels.labels_page'))
    
    layout = request.form.get('layout', '3x10')
    copies = Copy.query.filter(Copy.id.in_(copy_ids)).all()
    return render_template('print_labels.html', copies=copies, layout=layout)

@labels_bp.route('/barcode/<code>')
def get_barcode(code):
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(code, writer=ImageWriter())
    buffer = io.BytesIO()
    ean.write(buffer)
    return Response(buffer.getvalue(), mimetype='image/png')
