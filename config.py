import os

class Config:
    SECRET_KEY = ''
    
    # Veritabanı Bağlantı Adresi
    SQLALCHEMY_DATABASE_URI = ""
    SQLALCHEMY_TRACK_MODIFICATIONS = ""
    
    # E-Posta Gönderme Ayarları
    MAIL_SERVER = ''
    MAIL_PORT = ""
    MAIL_USE_TLS = ""
    MAIL_USERNAME = '' 
    MAIL_PASSWORD = '' 
    
    # API Anahtarları (Google, Stripe, Retell)
    GOOGLE_API_KEY = ""
    STRIPE_API_KEY = ""
    RETELL_API_KEY = ""
    RETELL_AGENT_ID=""
    
    # RSS Kaynak Linki
    RSS_URL = ""
MAIL_SERVER = ''
MAIL_PORT = ""
MAIL_USE_TLS = ""
MAIL_USERNAME = ''  
MAIL_PASSWORD = ''           

RETELL_API_KEY = os.getenv("")
RETELL_AGENT_ID = os.getenv("")