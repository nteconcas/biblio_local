from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from models import Book, Copy, db
from utils import clean_isbn, is_valid_isbn, create_session_with_retry
import json

catalog_bp = Blueprint('catalog', __name__)

@catalog_bp.route('/catalog')
@login_required
def catalog():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    base_query = Book.query.order_by(Book.id.desc())
    
    if query:
        base_query = Book.query.filter(
            (Book.title.ilike(f'%{query}%')) |
            (Book.author.ilike(f'%{query}%')) |
            (Book.isbn == query)
        ).order_by(Book.title.asc())
    
    pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items
    
    return render_template('catalog.html', 
                           books=books, 
                           pagination=pagination,
                           results=[], 
                           last_query=query)

@catalog_bp.route('/search_brasilapi', methods=['POST'])
@login_required
def search_brasilapi():
    query = request.form.get('query', '').strip()
    if not query:
        flash('Digite um ISBN para buscar.', 'error')
        return redirect(url_for('catalog.catalog'))
    
    isbn_clean = clean_isbn(query)
    if not is_valid_isbn(isbn_clean):
        flash(f'❌ ISBN inválido.', 'error')
        return redirect(url_for('catalog.catalog'))
    
    try:
        session = create_session_with_retry()
        url = f"https://brasilapi.com.br/api/isbn/v1/{isbn_clean}"
        resp = session.get(url, timeout=15)
        
        if resp.status_code == 404:
            flash('📚 Livro não encontrado.', 'info')
            return redirect(url_for('catalog.catalog'))
        
        resp.raise_for_status()
        data = resp.json()
        
        authors_list = data.get('authors', [])
        author = ', '.join([str(a) for a in (authors_list if isinstance(authors_list, list) else [authors_list]) if a]) or 'Autor desconhecido'
        
        year = None
        if data.get('published'):
            try: year = int(str(data['published'])[:4])
            except: pass
        
        cover_raw = data.get('cover', '') or ''
        # Forçar HTTPS na URL da capa para evitar mixed-content
        if cover_raw.startswith('http://'):
            cover_raw = cover_raw.replace('http://', 'https://', 1)

        results = [{
            'title': data.get('title', 'Título desconhecido'),
            'author': author, 'isbn': isbn_clean, 'year': year,
            'publisher': data.get('publisher', ''),
            'cover_url': cover_raw,
            'synopsis': (data.get('synopsis', '') or '')[:200] + ('...' if len(data.get('synopsis', '') or '') > 200 else '')
        }]
    except Exception as e:
        flash(f'❌ Erro na busca: {type(e).__name__}', 'error')
        results = []
    
    return render_template('catalog.html', books=Book.query.all(), results=results, last_query=query)

@catalog_bp.route('/add_from_api', methods=['POST'])
@login_required
def add_from_api():
    title = request.form.get('title', '').strip()
    b = Book(
        title=title, 
        author=request.form.get('author', ''),
        isbn=clean_isbn(request.form.get('isbn', '')),
        publication_year=int(y) if (y:=request.form.get('year','')) and y.isdigit() else None,
        publisher=request.form.get('publisher', ''),
        cover_url=request.form.get('cover_url', '')
    )
    db.session.add(b)
    db.session.commit()
    
    qty = request.form.get('quantity', '1')
    try: qty = int(qty)
    except: qty = 1

    for i in range(qty):
        code = f"LIV{b.id:04d}-{i+1:02d}"
        db.session.add(Copy(book_id=b.id, barcode=code))
    
    db.session.commit()
    flash(f'✅ Livro "{title}" cadastrado!', 'success')
    return redirect(url_for('catalog.catalog'))

@catalog_bp.route('/add_book_manual', methods=['POST'])
@login_required
def add_book_manual():
    title = request.form.get('title', '').strip()
    if not title:
        flash('Título é obrigatório.', 'error')
        return redirect(url_for('catalog.catalog'))
    
    b = Book(
        title=title,
        author=request.form.get('author', ''),
        genre=request.form.get('genre', ''),
        classification=request.form.get('classification', ''),
        isbn=clean_isbn(request.form.get('isbn', '')),
        observations=request.form.get('observations', ''),
        publication_year=int(y) if (y:=request.form.get('year','')) and y.isdigit() else None,
        publisher=request.form.get('publisher', '')
    )
    db.session.add(b)
    db.session.commit()
    
    qty = request.form.get('quantity', '1')
    try: qty = int(qty)
    except: qty = 1

    for i in range(qty):
        code = f"LIV{b.id:04d}-{i+1:02d}"
        while Copy.query.filter_by(barcode=code).first():
            code += "A"
        db.session.add(Copy(book_id=b.id, barcode=code))
    
    db.session.commit()
    flash(f'✅ Livro "{title}" cadastrado!', 'success')
    return redirect(url_for('catalog.catalog'))

@catalog_bp.route('/add_copy/<int:book_id>', methods=['POST'])
@login_required
def add_copy(book_id):
    book = db.session.get(Book, book_id)
    if not book: return redirect(url_for('catalog.catalog'))
    
    last_copy = Copy.query.filter(Copy.book_id == book_id).order_by(Copy.id.desc()).first()
    next_num = 1
    if last_copy and '-' in last_copy.barcode:
        try: next_num = int(last_copy.barcode.split('-')[-1]) + 1
        except: next_num = len(book.copies) + 1
    
    code = f"LIV{book.id:04d}-{next_num:02d}"
    while Copy.query.filter_by(barcode=code).first():
        next_num += 1
        code = f"LIV{book.id:04d}-{next_num:02d}"
        
    db.session.add(Copy(book_id=book.id, barcode=code))
    db.session.commit()
    flash('✅ Nova cópia adicionada!', 'success')
    return redirect(url_for('catalog.catalog'))

@catalog_bp.route('/edit_book/<int:book_id>', methods=['POST'])
@login_required
def edit_book(book_id):
    book = db.session.get(Book, book_id)
    if not book: return redirect(url_for('catalog.catalog'))
    
    book.title = request.form.get('title', '').strip()
    book.author = request.form.get('author', '').strip()
    book.genre = request.form.get('genre', '').strip()
    book.classification = request.form.get('classification', '').strip()
    book.observations = request.form.get('observations', '').strip()
    book.isbn = clean_isbn(request.form.get('isbn', ''))
    
    year = request.form.get('year', '')
    if year and year.isdigit():
        book.publication_year = int(year)
        
    db.session.commit()
    flash('✅ Livro atualizado com sucesso!', 'success')
    return redirect(url_for('catalog.catalog'))

@catalog_bp.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        flash('❌ Livro não encontrado.', 'error')
        return redirect(url_for('catalog.catalog'))
    
    title = book.title
    db.session.delete(book)
    db.session.commit()
    flash(f'🗑️ Obra "{title}" excluída com sucesso!', 'success')
    return redirect(url_for('catalog.catalog'))

@catalog_bp.route('/decommission_copy/<int:copy_id>', methods=['POST'])
@login_required
def decommission_copy(copy_id):
    copy = db.session.get(Copy, copy_id)
    if not copy:
        flash('❌ Exemplar não encontrado.', 'error')
        return redirect(url_for('catalog.catalog'))
    
    if copy.status == 'loaned':
        flash('❌ Não é possível dar baixa em um exemplar que está emprestado.', 'error')
        return redirect(url_for('catalog.catalog'))
        
    copy.status = 'decommissioned'
    db.session.commit()
    flash(f'✅ Baixa efetuada no exemplar {copy.barcode}!', 'success')
    return redirect(url_for('catalog.catalog'))

@catalog_bp.route('/activate_copy/<int:copy_id>', methods=['POST'])
@login_required
def activate_copy(copy_id):
    copy = db.session.get(Copy, copy_id)
    if not copy:
        flash('❌ Exemplar não encontrado.', 'error')
        return redirect(url_for('catalog.catalog'))
        
    copy.status = 'available'
    db.session.commit()
    flash(f'✅ Exemplar {copy.barcode} reativado!', 'success')
    return redirect(url_for('catalog.catalog'))


@catalog_bp.route('/api/search_books')
@login_required
def api_search_books():
    query = request.args.get('q', '').strip()
    results = []
    
    if not query:
        # Retorna últimos 10 livros cadastrados se não houver query
        books = Book.query.order_by(Book.id.desc()).limit(10).all()
        for b in books:
            available = [c for c in b.copies if c.status == 'available']
            results.append({
                'type': 'title', 'book_id': b.id, 'title': b.title,
                'author': b.author, 'isbn': b.isbn,
                'available_copies': len(available),
                'copies': [{'barcode': c.barcode, 'status': c.status} for c in b.copies]
            })
        return jsonify(results)

    # Busca por barcode exato
    copy = Copy.query.filter_by(barcode=query).first()
    if copy:
        results.append({
            'type': 'barcode', 'barcode': copy.barcode,
            'book_id': copy.book_id, 'title': copy.book.title,
            'author': copy.book.author, 'status': copy.status, 'copy_id': copy.id
        })
    
    # Busca por título (LIKE)
    books = Book.query.filter(Book.title.ilike(f'%{query}%')).limit(10).all()
    for b in books:
        available = [c for c in b.copies if c.status == 'available']
        results.append({
            'type': 'title', 'book_id': b.id, 'title': b.title,
            'author': b.author, 'isbn': b.isbn,
            'available_copies': len(available),
            'copies': [{'barcode': c.barcode, 'status': c.status} for c in b.copies[:5]]
        })
    
    # Remove duplicatas por título
    seen = set()
    unique = []
    for r in results:
        key = r.get('title') or r.get('barcode')
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return jsonify(unique[:10])

