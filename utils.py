import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from models import AppSettings

def create_session_with_retry():
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[400, 429, 500, 502, 503, 504], allowed_methods=["GET"])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    return session

def clean_isbn(value):
    if not value: return ""
    return ''.join(c for c in str(value) if c.isdigit())

def is_valid_isbn(isbn):
    return len(isbn) in [10, 13]

def get_settings():
    return {
        'max_books_per_user': int(AppSettings.get('max_books_per_user', 3)),
        'max_renewals': int(AppSettings.get('max_renewals', 2)),
        'loan_days': int(AppSettings.get('loan_days', 7)),
        'fine_per_day': float(AppSettings.get('fine_per_day', 0.50))
    }
