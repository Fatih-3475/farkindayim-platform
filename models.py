from extensions import db
from flask_login import UserMixin
from sqlalchemy import Index
from datetime import datetime

# Haber Tablosu
class Haber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(300), nullable=False)
    link = db.Column(db.String(2000), nullable=False, unique=True)
    ozet = db.Column(db.Text, nullable=True) 
    resim_url = db.Column(db.String(2000), nullable=True)
    yayin_tarihi = db.Column(db.DateTime, nullable=True)
    icerik = db.Column(db.Text, nullable=True) 
    def __repr__(self): return f'<Haber {self.baslik}>'

# Kullanıcı Tablosu

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_adi = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    sifre_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Integer, default=1)


# Bağış Tablosu
class Bagis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    miktar = db.Column(db.Integer, nullable=False) 
    tarih = db.Column(db.DateTime, nullable=False, default=db.func.now())
    stripe_session_id = db.Column(db.String(100), unique=True, nullable=False) 
    durum = db.Column(db.String(20), nullable=False, default='Beklemede') 

    def __repr__(self):
        return f"Bagis('{self.kullanici_id}', '{self.miktar}', '{self.durum}')"
    # Haklar Tablosu
class Haklar(db.Model):
    __tablename__ = "haklar"

    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(300), nullable=False)
    ozet = db.Column(db.Text, nullable=True)
    resim_url = db.Column(db.String(2000), nullable=True)
    icerik = db.Column(db.Text, nullable=True)
    olusturulma_tarihi = db.Column(db.DateTime, nullable=False, default=db.func.now())

    def __repr__(self):
        return f"<Haklar {self.baslik}>"
# models.py
class UserLogs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=db.func.now())
    #iletisim
class Iletisim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_soyad = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    mesaj = db.Column(db.Text, nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
