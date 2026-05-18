
import requests
import time
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import hashlib
import re
import os

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "8908222173:AAF7EviW88zpc06znI3c38L448AFi6QywH0"
CHANNEL_ID = "@Worldshorts"
# =======================

sent_news = set()

# Функция получения МОСКОВСКОГО времени (UTC+3)
def get_msk_time():
    return datetime.now(timezone(timedelta(hours=3)))

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_news_description(link):
    try:
        page = requests.get(link, timeout=15)
        soup = BeautifulSoup(page.text, 'html.parser')
        
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = clean_text(meta_desc.get('content'))
            if len(desc) > 50:
                return desc[:400]
        
        og_desc = soup.find('meta', {'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            desc = clean_text(og_desc.get('content'))
            if len(desc) > 50:
                return desc[:400]
        
        paragraphs = soup.find_all('p')
        text_parts = []
        for p in paragraphs[:5]:
            text = clean_text(p.get_text())
            if len(text) > 40:
                text_parts.append(text)
            if len(' '.join(text_parts)) > 300:
                break
        
        if text_parts:
            return ' '.join(text_parts)[:400]
        
        return None
    except Exception as e:
        print(f"Ошибка описания: {e}")
        return None

def get_image_url(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        return entry.media_content[0].get('url')
    
    if hasattr(entry, 'link'):
        try:
            page = requests.get(entry.link, timeout=10)
            soup = BeautifulSoup(page.text, 'html.parser')
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                return og_img['content']
        except:
            pass
    return None

def get_source_name(link):
    if 'lenta.ru' in link:
        return '📰 LENTA.RU'
    elif 'rbc.ru' in link:
        return '📊 РБК'
    elif 'ria.ru' in link:
        return '📡 РИА НОВОСТИ'
    else:
        return '📌 ИСТОЧНИК'

def send_greeting():
    """Отправляет приветствие строго по Московскому времени"""
    now = get_msk_time()
    today = now.strftime("%Y-%m-%d")
    hour = now.hour
    
    # Проверяем, было ли сегодня приветствие
    try:
        with open("last_greeting.txt", "r") as f:
            if f.read().strip() == today:
                print(f"⏭️ Приветствие уже было сегодня ({today}) по МСК")
                return False
    except:
        pass
    
    # Выбираем приветствие по МОСКОВСКОМУ времени
    if hour < 12:
        greeting = "🌅 ДОБРОЕ УТРО! ☕\n\n📰 Свежие новости дня:"
    elif hour < 17:
        greeting = "☀️ ДОБРЫЙ ДЕНЬ! 🌤️\n\n📰 Главные новости:"
    else:
        greeting = "🌙 ДОБРЫЙ ВЕЧЕР! ✨\n\n📰 Важные события дня:"
    
    send_message(greeting)
    
    with open("last_greeting.txt", "w") as f:
        f.write(today)
    
    print(f"✅ Приветствие отправлено по МСК ({now.strftime('%H:%M')}): {greeting[:40]}...")
    return True

def get_news():
    feeds = [
        "https://lenta.ru/rss",
        "https://www.rbc.ru/rss/news",
        "https://ria.ru/export/rss2/index.xml"
    ]
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = clean_text(entry.title)
                link = entry.link
                
                news_hash = hashlib.md5(title.encode()).hexdigest()
                if news_hash in sent_news:
                    continue
                
                image_url = get_image_url(entry)
                if not image_url:
                    continue
                
                description = get_news_description(link)
                
                sent_news.add(news_hash)
                if len(sent_news) > 100:
                    sent_news.clear()
                
                return title, description, image_url, link
        except Exception as e:
            print(f"Ошибка RSS: {e}")
            continue
    
    return None, None, None, None

def send_news(title, description, image_url, source_link):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        source_name = get_source_name(source_link)
        
        if description and len(description) > 50:
            caption = f"""{title}

📝 {description}

━━━━━━━━━━━━━━━━━━━━━━

{source_name}

🔗 [Читать полностью]({source_link})

✨ @Worldshorts — коротко о главном"""
        else:
            caption = f"""{title}

━━━━━━━━━━━━━━━━━━━━━━

{source_name}

🔗 [Читать полностью]({source_link})

✨ @Worldshorts — коротко о главном"""
        
        payload = {
            "chat_id": CHANNEL_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload, timeout=20)
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return False

def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка: {e}")

# Показываем текущее Московское время при запуске
msk_now = get_msk_time()
print("=" * 40)
print("✅ НОВОСТНОЙ БОТ ЗАПУЩЕН!")
print(f"📢 Канал: {CHANNEL_ID}")
print(f"🕐 Московское время: {msk_now.strftime('%H:%M:%S')}")
print(f"📅 Дата по МСК: {msk_now.strftime('%d.%m.%Y')}")
print("📰 Поиск новостей раз в 50 минут")
print("🔗 Описание + картинка + ссылка")
print("🌅 Приветствие по МСК (в начале дня)")
print("=" * 40)
print("")

# Отправляем приветствие при запуске (если сегодня ещё не было)
send_greeting()

# Основной цикл
last_greeting_date = None

while True:
    now = get_msk_time()
    current_date = now.strftime("%Y-%m-%d")
    current_hour = now.hour
    
    # Проверяем, наступил ли новый день (отправляем приветствие в 8 утра)
    if current_hour == 8 and last_greeting_date != current_date:
        send_greeting()
        last_greeting_date = current_date
    
    print(f"🔍 [{now.strftime('%H:%M:%S')} МСК] Проверка новостей...")
    
    title, description, image_url, source_link = get_news()
    
    if title and image_url and source_link:
        if send_news(title, description, image_url, source_link):
            print(f"✅ [{now.strftime('%H:%M:%S')} МСК] Отправлено: {title[:50]}...")
        else:
            print(f"❌ Ошибка отправки")
    else:
        print(f"⏳ [{now.strftime('%H:%M:%S')} МСК] Новостей нет, жду 50 минут...")
    
    time.sleep(3000)  # 50 минут
EOF