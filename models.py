from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    registration_number = db.Column(db.String(30), unique=True)
    password_hash = db.Column(db.String(256), nullable=True) # Null for readers (offline)
    role = db.Column(db.String(20), default='member')

    def set_password(self, pwd): self.password_hash = generate_password_hash(pwd)
    def check_password(self, pwd): return check_password_hash(self.password_hash, pwd)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(255))
    isbn = db.Column(db.String(20))
    publication_year = db.Column(db.Integer)
    genre = db.Column(db.String(100))
    classification = db.Column(db.String(100))
    observations = db.Column(db.Text)
    cover_url = db.Column(db.String(300))
    publisher = db.Column(db.String(100))
    copies = db.relationship('Copy', backref='book', lazy=True, cascade='all, delete-orphan')

class Copy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    barcode = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='available')

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    copy_id = db.Column(db.Integer, db.ForeignKey('copy.id'), nullable=False)
    loan_date = db.Column(db.DateTime, default=datetime.now)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime)
    fine = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='active')
    renewals = db.Column(db.Integer, default=0)
    
    user = db.relationship('User', backref='loans')
    copy = db.relationship('Copy', backref=db.backref('loans', cascade='all, delete-orphan'))

class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)
    
    @staticmethod
    def get(key, default=None):
        s = AppSettings.query.filter_by(key=key).first()
        return s.value if s else default
    
    @staticmethod
    def set(key, value):
        s = AppSettings.query.filter_by(key=key).first()
        if s:
            s.value = str(value)
        else:
            db.session.add(AppSettings(key=key, value=str(value)))
        db.session.commit()
