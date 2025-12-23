import os
from flask import Flask
from config import Config
from extensions import db, mail, bcrypt, login_manager
from routes import main
from models import User, Bagis
from apscheduler.schedulers.background import BackgroundScheduler
from utils import rss_verilerini_cek_ve_kaydet
from flask_login import current_user
from routes import main


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Extensions
    db.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Login ayarları
    login_manager.login_view = 'main.giris_yap'
    login_manager.login_message = "Bu sayfayı görmek için lütfen giriş yapın."

    # Blueprint
    app.register_blueprint(main)

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Context processor
    @app.context_processor
    def inject_vars():
        bakiye = 0
        if current_user.is_authenticated:
            try:
                bagislar = Bagis.query.filter_by(
                    kullanici_id=current_user.id,
                    durum='Başarılı'
                ).all()
                if bagislar:
                    bakiye = int(sum(b.miktar for b in bagislar) / 100)
            except:
                pass

        return dict(
            current_user=current_user,
            cuzdan_bakiye=bakiye
        )

    return app


# ===========================
# MAIN
# ===========================
if __name__ == "__main__":

    app = create_app()

    # DB tabloları
    with app.app_context():
        db.create_all()

    # RSS job
    def scheduled_rss_job():
        with app.app_context():
            print("⏳ Otomatik RSS taraması başladı...")
            rss_verilerini_cek_ve_kaydet()
            print("✅ Otomatik RSS taraması bitti.")

    # 🔒 DEBUG MODE DOUBLE-RUN FIX
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            scheduled_rss_job,
            trigger="interval",
            minutes=10,
            id="rss_job",
            replace_existing=True
        )
        scheduler.start()
        print("🟢 Scheduler başlatıldı")

    # Flask start
    app.run(debug=True)
