import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Haber
from config import Config


MEDIA_NS = "{http://search.yahoo.com/mrss/}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9"
}


def icerigi_kaziyarak_bul(haber_url):
    try:
        response = requests.get(
            haber_url,
            headers=HEADERS,
            timeout=(10, 30)
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        paragraflar = soup.find_all("p")

        temiz = [
            p.get_text().strip()
            for p in paragraflar
            if len(p.get_text().strip()) > 30
        ]

        return "\n\n".join(temiz) if temiz else "İçerik bulunamadı."

    except requests.exceptions.ReadTimeout:
        print("⏳ Haber içeriği geç cevap verdi, atlandı.")
        return "İçerik geç cevap verdi."

    except Exception as e:
        print(f"İçerik çekme hatası: {e}")
        return "İçerik çekme hatası."


def rss_verilerini_cek_ve_kaydet():
    print(f">>> RSS Bağlanılıyor: {Config.RSS_URL}")

    try:
        response = requests.get(
            Config.RSS_URL,
            headers=HEADERS,
            timeout=(10, 30)
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        yeni = 0

        for item in items:
            try:
                link = item.findtext("link")
                if not link:
                    continue

               
                if Haber.query.filter_by(link=link).first():
                    continue

                baslik = item.findtext("title", "").strip()

          
                description_html = item.findtext("description", "")
                soup_desc = BeautifulSoup(description_html, "html.parser")
                ozet = soup_desc.get_text().strip()[:500]

           
                resim_url = "/static/images/placeholder.png"

           
                enclosure = item.find("enclosure")
                if enclosure is not None and enclosure.attrib.get("url"):
                    resim_url = enclosure.attrib.get("url")

             
                media_content = item.find(f"{MEDIA_NS}content")
                if media_content is not None and media_content.attrib.get("url"):
                    resim_url = media_content.attrib.get("url")

              
                media_thumb = item.find(f"{MEDIA_NS}thumbnail")
                if media_thumb is not None and media_thumb.attrib.get("url"):
                    resim_url = media_thumb.attrib.get("url")
                    
                image_tag = item.find("image")
                if image_tag is not None and image_tag.text:
                    resim_url = image_tag.text.strip()


                
                img_tag = soup_desc.find("img")
                if img_tag:
                    if img_tag.get("data-src"):
                        resim_url = img_tag.get("data-src")
                    elif img_tag.get("srcset"):
                        resim_url = img_tag.get("srcset").split(",")[0].split(" ")[0]
                    elif img_tag.get("src"):
                        resim_url = img_tag.get("src")

               
                if resim_url.startswith("//"):
                    resim_url = "https:" + resim_url

             
                pub_date = item.findtext("pubDate")
                try:
                    yayin_tarihi = parsedate_to_datetime(pub_date)
                except:
                    yayin_tarihi = datetime.now()

                icerik = icerigi_kaziyarak_bul(link)

                haber = Haber(
                    baslik=baslik,
                    link=link,
                    ozet=ozet,
                    resim_url=resim_url,
                    yayin_tarihi=yayin_tarihi,
                    icerik=icerik
                )

                db.session.add(haber)
                db.session.flush()
                yeni += 1

            except IntegrityError:
                db.session.rollback()
                continue

            except Exception as e:
                db.session.rollback()
                print("Tek haber hatası:", e)
                continue

        db.session.commit()
        print(f">>> RSS TAMAMLANDI: {yeni} yeni haber eklendi")

    except requests.exceptions.ReadTimeout:
        print("⏳ RSS geç cevap verdi, bu tur atlandı.")

    except Exception as e:
        db.session.rollback()
        print(f"!!! KRİTİK RSS HATASI: {e}")