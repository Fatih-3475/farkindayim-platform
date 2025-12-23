from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from sqlalchemy import text 
import stripe
import requests
from datetime import datetime
from datetime import date
from sqlalchemy import func
from extensions import db, mail, bcrypt
from models import User, Haber, Bagis, Haklar, UserLogs, Iletisim
from config import Config
from utils import rss_verilerini_cek_ve_kaydet
from retell import Retell
from functools import wraps
from flask import abort
import re

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.is_admin != 1:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# Blueprint
main = Blueprint('main', __name__)
client = Retell(api_key=Config.RETELL_API_KEY)

# --- 1. ANA SAYFA VE HABERLER ---
@main.route('/')
def index():
    haberler = Haber.query.order_by(Haber.yayin_tarihi.desc()).limit(3).all()
    try:
        sql = text("SELECT * FROM haklar ORDER BY olusturulma_tarihi DESC LIMIT 3")
        haklar = db.session.execute(sql).mappings().all()
    except Exception as e:
        print(f"Hata: {e}")
        haklar = []
    return render_template('index.html', haberler=haberler, haklar=haklar)

@main.route('/haberler')
def tum_haberler():
    tum_haberler = Haber.query.order_by(Haber.yayin_tarihi.desc()).all()
    return render_template('haberler.html', haberler=tum_haberler)

@main.route('/haber/<int:haber_id>')
def haber_detay(haber_id):
    haber = Haber.query.get_or_404(haber_id)

    if haber.icerik:
        
        icerik = re.sub(r'\n+', '\n', haber.icerik)

        
        satirlar = icerik.split('\n')

        
        temiz_html = ""
        for s in satirlar:
            s = s.strip()
            if len(s) > 40:  
                temiz_html += f"<p>{s}</p>"

        haber.icerik = temiz_html

    return render_template('haber_detay.html', haber=haber)



# --- 2. HAKKIMI BİLİYORUM ---
@main.route('/hakkimi_biliyorum')
def hakkimi_biliyorum():
    try:
        
        sql = text("SELECT * FROM haklar ORDER BY olusturulma_tarihi DESC")
        haklar = db.session.execute(sql).mappings().all()
    except:
        haklar = []
    return render_template('hakkimi_biliyorum.html', haklar=haklar)



# --- 3. ÜYELİK İŞLEMLERİ (GİRİŞ/KAYIT/ÇIKIŞ) ---
@main.route('/kayit-ol', methods=['GET', 'POST'])
def kayit_ol():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    if request.method == 'POST':
        k_adi = request.form.get('kullanici_adi')
        email = request.form.get('email')
        sifre = request.form.get('sifre')
        
        
        if User.query.filter_by(kullanici_adi=k_adi).first():
            flash('Bu kullanıcı adı zaten alınmış.', 'register_error')
            return redirect(url_for('main.index', kayit_ac='true'))
            
        if User.query.filter_by(email=email).first():
            flash('Bu e-posta adresi zaten kayıtlı.', 'register_error')
            return redirect(url_for('main.index', kayit_ac='true'))
        
        
        yeni_kullanici = User(kullanici_adi=k_adi, email=email, sifre_hash=bcrypt.generate_password_hash(sifre).decode('utf-8'))
        db.session.add(yeni_kullanici)
        db.session.commit()
        
        flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'register_success')
        return redirect(url_for('main.index', kayit_ac='true'))
        
    return redirect(url_for('main.index'))

@main.route('/giris-yap', methods=['GET', 'POST'])
def giris_yap():

    
    if current_user.is_authenticated:
        if current_user.is_admin == 1:
            return redirect(url_for('main.admin'))
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        kullanici = User.query.filter_by(
            kullanici_adi=request.form.get('kullanici_adi')
        ).first()

        if not kullanici:
            flash('Kullanıcı adı veya şifre yanlış.', 'login_error')
            return redirect(url_for('main.index'))

        if not bcrypt.check_password_hash(
            kullanici.sifre_hash,
            request.form.get('sifre')
        ):
            flash('Kullanıcı adı veya şifre yanlış.', 'login_error')
            return redirect(url_for('main.index'))

        if kullanici.is_active == 0:
            flash('Hesabınız pasif durumdadır.', 'login_error')
            return redirect(url_for('main.index'))

      
        login_user(kullanici)

      
        log = UserLogs(
            username=kullanici.kullanici_adi,
            action='Giriş yaptı',
            ip_address=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()

        if kullanici.is_admin == 1:
            return redirect(url_for('main.admin'))

        flash('Başarıyla giriş yapıldı!', 'login_success')
        return redirect(url_for('main.index'))

    return redirect(url_for('main.index'))
@main.route('/cikis-yap')
def cikis_yap():

    if current_user.is_authenticated:
        log = UserLogs(
            username=current_user.kullanici_adi,
            action='Çıkış yaptı',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

    logout_user()
    return redirect(url_for('main.index'))

# --- ŞİFRE SIFIRLAMA ---
@main.route('/sifre-sifirlama-talebi', methods=['POST'])
def sifre_sifirlama_talebi():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()

    if user:
        try:
            msg = Message(
                "Şifre Sıfırlama Talebi",
                sender=Config.MAIL_USERNAME,
                recipients=[user.email]
            )
            link = url_for('main.index', sifre_sifirla='true', email=user.email, _external=True)
            msg.body = f"""
Merhaba {user.kullanici_adi},

Şifreni değiştirmek istersen buradan yapabilirsin:
{link}

Eğer bu işlemi sen başlatmadıysan, bu maili güvenle yok sayabilirsin.

Sevgiler,
Farkındayım Ekibi
"""
            mail.send(msg)
            flash('Şifre sıfırlama bağlantısı e-posta adresinize gönderildi!', 'success')
        except Exception as e:
            print(f"E-posta hatası: {e}")
            flash('Şifre sıfırlama e-postası gönderilemedi.', 'danger')
    else:
        flash('Şifre sıfırlama bağlantısı e-posta adresinize gönderildi (Kayıtlıysa).', 'info')

    return redirect(url_for('main.index'))

@main.route('/sifre-degistir', methods=['POST'])
def sifre_degistir():
    email = request.form.get('email')
    yeni_sifre = request.form.get('yeni_sifre')
    
    user = User.query.filter_by(email=email).first()
    
    if user:
        
        user.sifre_hash = bcrypt.generate_password_hash(yeni_sifre).decode('utf-8')
        db.session.commit()
        
        flash('Şifreniz başarıyla güncellendi! Şimdi giriş yapabilirsiniz.', 'login_success')
        
        return redirect(url_for('main.index', giris_ac='true'))
    else:
        
        flash('Bir hata oluştu. Kullanıcı bulunamadı.', 'login_error')
        return redirect(url_for('main.index', giris_ac='true'))
# --- 4. İLETİŞİM VE API'LER ---
@main.route('/iletisim', methods=['GET', 'POST'])
def iletisim():
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad')
        email = request.form.get('email')
        mesaj_icerik = request.form.get('mesaj')

        if not ad_soyad or not email or not mesaj_icerik:
            flash("Tüm alanları doldurun ❌", "danger")
            return redirect(url_for('main.iletisim'))

       
        yeni_mesaj = Iletisim(
            ad_soyad=ad_soyad,
            email=email,
            mesaj=mesaj_icerik
        )
        db.session.add(yeni_mesaj)
        db.session.commit()

        try:
            msg = Message(
                subject=f"Yeni Mesaj - {ad_soyad}",
                sender=Config.MAIL_USERNAME,
                recipients=[Config.MAIL_USERNAME]
            )
            msg.body = f"Mesaj: {mesaj_icerik}\nEmail: {email}"
            mail.send(msg)
        except Exception as e:
            print("Mail hatası:", e)

        flash("Mesaj başarıyla gönderildi ✅", "success")
        return redirect(url_for('main.iletisim'))

    return render_template('iletisim.html')


@main.route("/api/start-call", methods=["POST"])
def start_call():
    try:
        call_response = client.call.create_web_call(agent_id="agent_2e7e6d031e5d10bef435c1c3fc")
        return jsonify({"access_token": call_response.access_token})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/birlik-noktasi/<string:sehir_adi>')
@login_required
def sehir_sonuc(sehir_adi):
   
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    search_params = {
        'query': f"cafe in {sehir_adi}",
        'language': 'tr',
        'key': Config.GOOGLE_API_KEY
    }

    try:
        search_res = requests.get(search_url, params=search_params).json()
        
        mekan_listesi = []
        if search_res.get('status') == 'OK':
            
            for place in search_res.get('results', [])[:50]: 
                place_id = place.get('place_id')
                
               
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    'place_id': place_id,
                    'fields': 'name,formatted_address,rating,geometry,wheelchair_accessible_entrance,url', 
                    'key': Config.GOOGLE_API_KEY
                }
                
                detail_res = requests.get(details_url, params=details_params).json()
                detail = detail_res.get('result', {})

                is_accessible = detail.get('wheelchair_accessible_entrance')
                
                
                if is_accessible is not True:
                    continue 

                
                durum_metni = "Tekerlekli sandalyeye uygun"
                durum_class = "text-success"

                mekan_listesi.append({
                    'isim': detail.get('name', place.get('name')),
                    'adres': detail.get('formatted_address', place.get('formatted_address')),
                    'puan': detail.get('rating', '0'),
                    'lat': detail['geometry']['location']['lat'],
                    'lng': detail['geometry']['location']['lng'],
                    'durum': durum_metni,
                    'durum_class': durum_class,
                    'maps_url': detail.get('url'),
                    'place_id': place_id
                })

        sehir_koordinatlari = {
            'istanbul': {'lat': 41.0082, 'lng': 28.9784},
            'ankara': {'lat': 39.9334, 'lng': 32.8597},
            'izmir': {'lat': 38.4237, 'lng': 27.1428},
            'bursa': {'lat': 40.1885, 'lng': 29.0610}
        }
        merkez = sehir_koordinatlari.get(sehir_adi.lower(), {'lat': 41.0082, 'lng': 28.9784})

        return render_template('sehir-sonuc.html',
                               mekanlar=mekan_listesi,
                               sehir=sehir_adi.capitalize(),
                               merkez=merkez,
                               google_api_key=Config.GOOGLE_API_KEY)

    except Exception as e:
        print(f"HATA: {e}")
        return render_template('sehir-sonuc.html',
                               mekanlar=[],
                               sehir=sehir_adi,
                               merkez={'lat': 41.0082, 'lng': 28.9784},
                               google_api_key=Config.GOOGLE_API_KEY,
                               hata_mesaji="Veriler alınırken hata oluştu.")

# --- STATİK SAYFALAR VE STRIPE ---
@main.route('/bagis-basarili')
@login_required
def bagis_basarili():
    
    son_bagis = Bagis.query.filter_by(kullanici_id=current_user.id, durum='Beklemede')\
                           .order_by(Bagis.tarih.desc()).first()

    if son_bagis:
        
        son_bagis.durum = 'Başarılı'
        db.session.commit()
        
        
        flash("Bağışınız başarıyla alındı! Desteğiniz için teşekkürler.", 'donation_success')
    else:
      
        flash("İşlem tamamlandı.", 'donation_success')

    return redirect(url_for('main.index'))

@main.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html')

@main.route('/rotalar')
@login_required
def rotalar():
    return render_template('rotalar.html')

@main.route('/haklarim')
def haklarim():
    return render_template('haklarim.html')

@main.route('/gizlilik')
def gizlilik():
    return render_template('gizlilik.html')

@main.route('/kullanim-kosullari')
def kullanim_kosullari():
    return render_template('kullanim_kosullari.html')

@main.route('/cerez')
def cerez():
    return render_template('cerez.html')

@main.route('/bagislarim')
@login_required
def bagislarim():
    
    bagis_gecmisi = Bagis.query.filter_by(kullanici_id=current_user.id)\
                               .order_by(Bagis.tarih.desc()).all()
    
    return render_template('bagislarim.html', bagislar=bagis_gecmisi)


@main.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
       
        if 'mevcut_sifre' in request.form:
            mevcut = request.form.get('mevcut_sifre')
            yeni = request.form.get('yeni_sifre')
            tekrar = request.form.get('yeni_sifre_tekrar')

            if not bcrypt.check_password_hash(current_user.sifre_hash, mevcut):
                flash('Mevcut şifrenizi yanlış girdiniz.', 'login_error')
            elif yeni != tekrar:
                flash('Yeni şifreler birbiriyle uyuşmuyor.', 'login_error')
            else:
                current_user.sifre_hash = bcrypt.generate_password_hash(yeni).decode('utf-8')
                db.session.commit()
                flash('Şifreniz başarıyla değiştirildi!', 'login_success')

       
        elif 'profil_guncelle' in request.form:
            yeni_ad = request.form.get('kullanici_adi')
            yeni_mail = request.form.get('email')

           
            mevcut_mu = User.query.filter_by(email=yeni_mail).first()
            if yeni_mail != current_user.email and mevcut_mu:
                 flash('Bu e-posta adresi zaten kullanımda.', 'login_error')
            else:
                current_user.kullanici_adi = yeni_ad
                current_user.email = yeni_mail 
                db.session.commit()
                flash('Profil bilgileriniz güncellendi.', 'login_success')

        return redirect(url_for('main.profil'))

    return render_template('profil.html')
    
# --- EKSİK OLAN RSS GÜNCELLEME ROTASI ---
@main.route('/rss-guncelle')
def rss_guncelle():
  
    try:
        rss_verilerini_cek_ve_kaydet()
        flash("Haberler başarıyla güncellendi!", "success")
    except Exception as e:
        print(f"Hata: {e}")
        flash("Haberler güncellenirken hata oluştu.", "danger")
        
    return redirect(url_for('main.index'))



@main.route('/create-checkout_session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
       
        secilen_miktar = request.form.get('bagis_miktari')
        
       
        if secilen_miktar == 'diger':
            miktar = request.form.get('ozel_miktar')
        else:
            miktar = secilen_miktar

        
        if not miktar or int(miktar) <= 0:
            flash("Lütfen geçerli bir bağış miktarı girin.", "donation_error")
            return redirect(url_for('main.index'))

        
        stripe.api_key = Config.STRIPE_API_KEY
        domain_url = request.host_url.rstrip('/') 
        
      
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'try',
                    'product_data': {
                        'name': 'Farkındayım Bağışı',
                        'images': ['https://via.placeholder.com/300?text=Bagis'],
                    },
                    'unit_amount': int(miktar) * 100, 
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=domain_url + url_for('main.bagis_basarili'),
            cancel_url=domain_url + url_for('main.index'),
            customer_email=current_user.email, 
            client_reference_id=str(current_user.id)   )
        
       
        yeni_bagis = Bagis(
            kullanici_id=current_user.id,
            miktar=int(miktar) * 100,
            stripe_session_id=session.id,
            durum='Beklemede'
        )
        db.session.add(yeni_bagis)
        db.session.commit()

       
        return redirect(session.url, code=303)

    except Exception as e:
        print(f"Stripe Hatası: {e}")
        flash("Ödeme sistemi başlatılamadı.", "donation_error")
        
        return redirect(url_for('main.index')) 
        
# --- ADMİN HABER ---

@main.route("/admin")
@main.route("/admin/")
@login_required
@admin_required
def admin():
    today = date.today()

   
    gunluk_kurus = db.session.query(func.sum(Bagis.miktar)) \
        .filter(
            func.date(Bagis.tarih) == today,
            Bagis.durum == 'Başarılı'
        ).scalar() or 0

    aylik_kurus = db.session.query(func.sum(Bagis.miktar)) \
        .filter(
            func.extract('year', Bagis.tarih) == today.year,
            func.extract('month', Bagis.tarih) == today.month,
            Bagis.durum == 'Başarılı'
        ).scalar() or 0

    yillik_kurus = db.session.query(func.sum(Bagis.miktar)) \
        .filter(
            func.extract('year', Bagis.tarih) == today.year,
            Bagis.durum == 'Başarılı'
        ).scalar() or 0

    return render_template(
      "admin/index.html",
      gunluk_tl=gunluk_kurus // 100,
      aylik_tl=aylik_kurus // 100,
     yillik_tl=yillik_kurus // 100
)




@main.route('/admin/haberler')
@login_required
@admin_required
def admin_haberler():
    haberler = Haber.query.order_by(Haber.yayin_tarihi.desc()).all()
    return render_template('admin/haberler.html', haberler=haberler)


@main.route('/admin/haber/ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_haber_ekle():
    if request.method == 'POST':
        yeni_haber = Haber(
            baslik=request.form['baslik'],
            link=request.form['link'],
            ozet=request.form['ozet'],
            resim_url=request.form['resim_url'],
            icerik=request.form['icerik'],
            yayin_tarihi=datetime.utcnow()
        )
        db.session.add(yeni_haber)
        db.session.commit()
        flash('Haber eklendi ✅', 'success')
        return redirect(url_for('main.admin_haberler'))

    return render_template('admin/haber_ekle.html')


@main.route('/admin/haber/duzenle/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_haber_duzenle(id):
    haber = Haber.query.get_or_404(id)

    if request.method == 'POST':
        haber.baslik = request.form['baslik']
        haber.link = request.form['link']
        haber.ozet = request.form['ozet']
        haber.resim_url = request.form['resim_url']
        haber.icerik = request.form['icerik']
        db.session.commit()
        flash('Haber güncellendi ✅', 'success')
        return redirect(url_for('main.admin_haberler'))

    return render_template('admin/haber_duzenle.html', haber=haber)


@main.route('/admin/haber/sil/<int:id>')
@login_required
@admin_required
def admin_haber_sil(id):
    haber = Haber.query.get_or_404(id)
    db.session.delete(haber)
    db.session.commit()
    flash('Haber silindi 🗑️', 'success')
    return redirect(url_for('main.admin_haberler'))

# --- HAK DETAY (ORTAK KULLANIM İÇİN TEKİL TANIM) ---
@main.route('/hak_detay/<int:id>')
def hak_detay(id):
    
    hak = Haklar.query.get_or_404(id)
    return render_template('hak_detay.html', hak=hak)
    
# --- ADMİN HAKLAR ---
@main.route('/admin/haklar')
@login_required
@admin_required
def admin_haklar():
    haklar = Haklar.query.order_by(
        Haklar.olusturulma_tarihi.desc()
    ).all()

    return render_template('admin/haklar.html', haklar=haklar)
    
@main.route('/admin/hak/duzenle/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_hak_duzenle(id):
    hak = Haklar.query.get_or_404(id)

    if request.method == 'POST':
        hak.baslik = request.form['baslik']
        hak.ozet = request.form['ozet']
        hak.resim_url = request.form['resim_url']
        hak.icerik = request.form['icerik']

        db.session.commit()
        flash('Hak güncellendi ✅', 'success')
        return redirect(url_for('main.admin_haklar'))

    return render_template('admin/hak_duzenle.html', hak=hak)
    
@main.route('/admin/hak/sil/<int:id>')
@login_required
@admin_required
def admin_hak_sil(id):
    hak = Haklar.query.get_or_404(id)
    db.session.delete(hak)
    db.session.commit()

    flash('Hak silindi 🗑️', 'success')
    return redirect(url_for('main.admin_haklar'))
    
@main.route('/admin/hak/ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_hak_ekle():
    if request.method == 'POST':
        yeni_hak = Haklar(
            baslik=request.form['baslik'],
            ozet=request.form['ozet'],
            resim_url=request.form['resim_url'],
            icerik=request.form['icerik'],
            olusturulma_tarihi=datetime.utcnow()
        )
        db.session.add(yeni_hak)
        db.session.commit()

        flash('Hak eklendi ✅', 'success')
        return redirect(url_for('main.admin_haklar'))

    return render_template('admin/hak_ekle.html')
# ADMİN BAĞIŞ#
@main.route('/admin/bagislar')
@login_required
@admin_required
def admin_bagislar():
    bagislar = db.session.query(
        Bagis,
        User.kullanici_adi,
        User.email
    ).join(User, User.id == Bagis.kullanici_id) \
     .order_by(Bagis.tarih.desc()) \
     .all()

    return render_template('admin/bagislar.html', bagislar=bagislar)
# =============================
# ADMİN - KULLANICI YÖNETİMİ
# =============================

@main.route('/admin/kullanicilar')
@login_required
@admin_required
def admin_kullanicilar():
    
    kullanicilar = User.query.filter_by(is_active=1).order_by(User.id.desc()).all()
    return render_template('admin/kullanicilar.html', kullanicilar=kullanicilar)


@main.route('/admin/kullanici/ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_kullanici_ekle():
    if request.method == 'POST':
        k_adi = request.form['kullanici_adi']
        email = request.form['email']
        sifre = request.form['sifre']
        is_admin = 1 if request.form.get('is_admin') else 0

      
        if User.query.filter(
            (User.kullanici_adi == k_adi) | (User.email == email)
        ).first():
            flash('Kullanıcı adı veya email zaten var', 'danger')
            return redirect(url_for('main.admin_kullanici_ekle'))

        yeni = User(
            kullanici_adi=k_adi,
            email=email,
            sifre_hash=bcrypt.generate_password_hash(sifre).decode('utf-8'),
            is_admin=is_admin,
            is_active=1   )
        db.session.add(yeni)
        db.session.commit()

        flash('Kullanıcı eklendi ✅', 'success')
        return redirect(url_for('main.admin_kullanicilar'))

    return render_template('admin/kullanici_ekle.html')


@main.route('/admin/kullanici/sil/<int:id>')
@login_required
@admin_required
def admin_kullanici_sil(id):
    kullanici = User.query.get_or_404(id)

   
    if kullanici.id == current_user.id:
        flash('Kendini silemezsin ❌', 'danger')
        return redirect(url_for('main.admin_kullanicilar'))

    
    kullanici.is_active = 0
    db.session.commit()

    flash('Kullanıcı pasif hale getirildi ✅', 'success')
    return redirect(url_for('main.admin_kullanicilar'))
# =============================
# ADMİN - KULLANICI LOG KAYITLARI
# =============================

@main.route('/admin/loglar')
@login_required
@admin_required
def admin_loglar():
    loglar = UserLogs.query.order_by(UserLogs.timestamp.desc()).all()
    return render_template('admin/loglar.html', loglar=loglar)


@main.route('/admin/iletisim')
@login_required
@admin_required
def admin_iletisim():
    mesajlar = Iletisim.query.order_by(Iletisim.tarih.desc()).all()
    return render_template('admin/iletisim.html', mesajlar=mesajlar)
@main.route('/admin/iletisim/sil/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_iletisim_sil(id):
    mesaj = Iletisim.query.get_or_404(id)
    db.session.delete(mesaj)
    db.session.commit()
    flash('Mesaj silindi ✅', 'success')
    return redirect(url_for('main.admin_iletisim'))
