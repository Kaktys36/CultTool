import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json
from datetime import datetime
import time
import re

# -------------------------------------------------------------------
# 1. НАСТРОЙКИ И СЕКРЕТЫ
# -------------------------------------------------------------------

try:
    google_creds = st.secrets["google_sheets"]
    TELEGRAM_BOT_TOKEN = st.secrets["telegram"]["bot_token"]
    TELEGRAM_CHAT_ID = st.secrets["telegram"]["chat_id"]
    USE_REAL_SERVICES = True
except (KeyError, FileNotFoundError, AttributeError):
    USE_REAL_SERVICES = False
    st.warning("⚠️ Секреты не найдены. Работаем в демонстрационном режиме.")

# -------------------------------------------------------------------
# 2. ФУНКЦИИ РАБОТЫ С GOOGLE SHEETS
# -------------------------------------------------------------------

def get_google_client():
    if not USE_REAL_SERVICES:
        return None
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds_dict = {
        "type": google_creds["type"],
        "project_id": google_creds["project_id"],
        "private_key_id": google_creds["private_key_id"],
        "private_key": google_creds["private_key"],
        "client_email": google_creds["client_email"],
        "client_id": google_creds["client_id"],
        "auth_uri": google_creds["auth_uri"],
        "token_uri": google_creds["token_uri"],
        "auth_provider_x509_cert_url": google_creds["auth_provider_x509_cert_url"],
        "client_x509_cert_url": google_creds["client_x509_cert_url"]
    }
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def load_catalog_from_sheets():
    if not USE_REAL_SERVICES:
        return get_demo_catalog()
    try:
        client = get_google_client()
        sheet = client.open_by_key(google_creds["spreadsheet_id"]).sheet1
        data = sheet.get_all_records()
        if not data:
            st.error("Таблица пуста. Использую демо-данные.")
            return get_demo_catalog()
        catalog = []
        for row in data:
            catalog.append({
                "name": row.get("Название", "Без названия"),
                "description": row.get("Описание", ""),
                "price": float(row.get("Цена", 0)),
                "quantity": int(row.get("Количество", 0)),
                "image": row.get("Фото", "https://via.placeholder.com/150?text=Инструмент")
            })
        return catalog
    except Exception as e:
        st.error(f"Ошибка загрузки каталога: {e}. Использую демо-данные.")
        return get_demo_catalog()

def get_demo_catalog():
    return [
        {"name": "Перфоратор Bosch", "description": "Мощный, 1500 Вт", "price": 1200, "quantity": 5,
         "image": "https://via.placeholder.com/150?text=Инструмент"},
        {"name": "Бетономешалка", "description": "Объём 200 л", "price": 2500, "quantity": 3,
         "image": "https://via.placeholder.com/150?text=Инструмент"},
        {"name": "Шуруповёрт Makita", "description": "Аккумуляторный, 18В", "price": 900, "quantity": 8,
         "image": "https://via.placeholder.com/150?text=Инструмент"},
        {"name": "Сварочный аппарат", "description": "Инверторный, 200А", "price": 3000, "quantity": 2,
         "image": "https://via.placeholder.com/150?text=Инструмент"},
        {"name": "Лестница-стремянка", "description": "Алюминиевая, 6 ступеней", "price": 700, "quantity": 10,
         "image": "https://via.placeholder.com/150?text=Инструмент"},
    ]

def save_order_to_sheets(order_data):
    if not USE_REAL_SERVICES:
        return True
    try:
        client = get_google_client()
        try:
            sheet = client.open_by_key(google_creds["spreadsheet_id"]).worksheet("Заказы")
        except:
            sheet = client.open_by_key(google_creds["spreadsheet_id"]).add_worksheet(title="Заказы", rows=100, cols=20)
        if not sheet.get_all_records():
            header = ["Дата", "Имя", "Телефон", "Инструменты", "Дата начала", "Дата конца", "Комментарий", "Статус"]
            sheet.append_row(header)
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            order_data["name"],
            order_data["phone"],
            ", ".join(order_data["tools"]),
            order_data["start_date"],
            order_data["end_date"],
            order_data["comment"],
            "Новый"
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения заказа: {e}")
        return False

# -------------------------------------------------------------------
# 3. ФУНКЦИЯ ОТПРАВКИ В TELEGRAM
# -------------------------------------------------------------------

def send_telegram_notification(order_data):
    if not USE_REAL_SERVICES:
        return False
    try:
        message = (
            f"🔔 *Новый заказ!*\n\n"
            f"👤 Имя: {order_data['name']}\n"
            f"📞 Телефон: {order_data['phone']}\n"
            f"🛠 Инструменты: {', '.join(order_data['tools'])}\n"
            f"📅 С {order_data['start_date']} по {order_data['end_date']}\n"
            f"💬 Комментарий: {order_data['comment']}"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Ошибка отправки в Telegram: {e}")
        return False

# -------------------------------------------------------------------
# 4. CSS ДЛЯ ВСПЛЫВАЮЩЕГО ФОТО (ПОЯВЛЯЕТСЯ ПРИ НАВЕДЕНИИ)
# -------------------------------------------------------------------

def inject_hover_zoom_css():
    st.markdown("""
    <style>
    /* Карточка инструмента */
    .tool-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        background: white;
        transition: 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        position: relative;
        cursor: pointer;
        overflow: visible;
    }
    .tool-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border-color: #4CAF50;
    }
    .tool-card .tool-image {
        width: 100%;
        height: 150px;
        object-fit: cover;
        border-radius: 6px;
        transition: 0.3s;
        display: block;
    }
    /* Увеличенное фото (всплывающее) - по умолчанию скрыто */
    .tool-card .hover-zoom {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) scale(0.8);
        z-index: 9999;
        max-width: 70vw;
        max-height: 70vh;
        border-radius: 12px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        opacity: 0;
        pointer-events: none;
        transition: all 0.25s ease-in-out;
        border: 4px solid white;
        background: white;
        padding: 5px;
    }
    /* Тёмный фон (оверлей) */
    .tool-card .hover-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.6);
        z-index: 9998;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.25s ease-in-out;
    }
    /* При наведении на карточку показываем увеличенное фото и оверлей */
    .tool-card:hover .hover-zoom {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1);
        pointer-events: auto;
    }
    .tool-card:hover .hover-overlay {
        opacity: 1;
        pointer-events: auto;
    }
    /* Стили для текста внутри карточки */
    .tool-card .tool-name {
        font-weight: bold;
        font-size: 1.2rem;
        margin-top: 10px;
    }
    .tool-card .tool-desc {
        color: #555;
        font-size: 0.9rem;
    }
    .tool-card .tool-price {
        color: #2E7D32;
        font-weight: bold;
        margin-top: 5px;
    }
    .tool-card .tool-quantity {
        font-size: 0.8rem;
        color: #888;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------------
# 5. ОТОБРАЖЕНИЕ КАТАЛОГА С ВСПЛЫВАЮЩИМИ ФОТО
# -------------------------------------------------------------------

def display_catalog(catalog):
    st.header("📦 Наш каталог")
    st.markdown("**Наведите на карточку, чтобы увидеть увеличенное фото инструмента.**")

    # Строим HTML-контейнер со всеми карточками и единой JS-логикой
    html = """
    <div id="catalog-container" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
    """
    for idx, item in enumerate(catalog):
        image_url = item.get("image", "https://via.placeholder.com/150?text=Инструмент")
        quantity = item.get("quantity", 0)
        status_color = "green" if quantity > 0 else "red"
        status_text = "В наличии" if quantity > 0 else "Нет в наличии"

        # Каждая карточка с уникальным ID и атрибутом data-image для JS
        html += f"""
        <div class="tool-card" data-image="{image_url}" style="border:1px solid #ddd; border-radius:8px; padding:15px; background:white; box-shadow:0 2px 4px rgba(0,0,0,0.05); transition:0.2s; cursor:pointer; position:relative;">
            <img src="{image_url}" style="width:100%; height:150px; object-fit:cover; border-radius:6px; display:block; margin-bottom:8px;">
            <div style="font-weight:bold; font-size:1.2rem;">{item['name']}</div>
            <div style="color:#555; font-size:0.9rem;">{item['description']}</div>
            <div style="color:#2E7D32; font-weight:bold; margin-top:5px;">{item['price']} руб/сутки</div>
            <div style="font-size:0.8rem; color:#888;">Осталось: <span style="color:{status_color};">{quantity}</span> шт.</div>
            <div style="font-size:0.8rem; color:{status_color};">{status_text}</div>
        </div>
        """
    html += """
    </div>

    <!-- Единый оверлей и увеличенное изображение (показывается через JS) -->
    <div id="hover-overlay" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:9998; display:none; pointer-events:none;"></div>
    <img id="hover-zoom-image" src="" alt="Увеличенное фото" style="position:fixed; top:50%; left:50%; transform:translate(-50%, -50%) scale(0.8); z-index:9999; max-width:70vw; max-height:70vh; border-radius:12px; box-shadow:0 20px 60px rgba(0,0,0,0.5); border:4px solid white; background:white; padding:5px; display:none; transition: all 0.25s ease-in-out;">

    <script>
        const cards = document.querySelectorAll('.tool-card');
        const overlay = document.getElementById('hover-overlay');
        const zoomImg = document.getElementById('hover-zoom-image');

        cards.forEach(card => {
            card.addEventListener('mouseenter', function(e) {
                const imgSrc = this.dataset.image;
                zoomImg.src = imgSrc;
                overlay.style.display = 'block';
                zoomImg.style.display = 'block';
                // Небольшая задержка, чтобы сработала анимация (scale от 0.8 к 1)
                setTimeout(() => {
                    zoomImg.style.transform = 'translate(-50%, -50%) scale(1)';
                }, 10);
            });
            card.addEventListener('mouseleave', function(e) {
                overlay.style.display = 'none';
                zoomImg.style.display = 'none';
                zoomImg.style.transform = 'translate(-50%, -50%) scale(0.8)';
            });
        });
    </script>
    """

    # Вставляем HTML-компонент с высотой в 1px (чтобы не занимал лишнее место)
    # Но нам нужно, чтобы он был вставлен в поток, поэтому используем обычный st.markdown с unsafe_allow_html=True
    # Однако для надёжности используем st.components.v1.html с фиксированной высотой.
    # Так как содержимое динамическое, используем высоту, адаптивную под количество карточек.
    # Рассчитаем приблизительную высоту: 3 колонки, каждая карточка ~ 350px, плюс отступы.
    # Но мы можем задать "auto" через JS? Лучше просто использовать st.markdown, но там не работает JS.
    # Используем st.components.v1.html с высотой, чтобы JS точно выполнялся.
    # Чтобы не гадать с высотой, добавим контейнер с классом и используем JS для определения высоты.

    # Проще: используем st.markdown с html, но тогда JS может не сработать из-за ограничений.
    # В Streamlit Cloud рекомендуется использовать st.components.v1.html.
    # Сделаем так:
    st.components.v1.html(html, height=400 + len(catalog)*100, scrolling=True)

# -------------------------------------------------------------------
# 6. ФОРМА ЗАКАЗА
# -------------------------------------------------------------------

def order_form(catalog):
    st.header("📝 Оформить заказ")
    st.markdown("Заполните форму, и мы свяжемся с вами для подтверждения.")
    with st.form("order_form"):
        tool_names = [item["name"] for item in catalog]
        selected_tools = st.multiselect(
            "Выберите инструменты (можно несколько):",
            options=tool_names,
            help="Укажите, что вам нужно"
        )
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Дата начала аренды", min_value=datetime.today())
        with col2:
            end_date = st.date_input("Дата окончания аренды", min_value=start_date)
        col3, col4 = st.columns(2)
        with col3:
            name = st.text_input("Ваше имя *", placeholder="Иван")
        with col4:
            phone = st.text_input("Телефон *", placeholder="+7 (123) 456-78-90")
        comment = st.text_area("Комментарий (дополнительные пожелания)", placeholder="Укажите время доставки и т.п.")
        submitted = st.form_submit_button("Отправить заявку 🚀")
        if submitted:
            errors = []
            if not selected_tools:
                errors.append("Выберите хотя бы один инструмент.")
            if not name.strip():
                errors.append("Введите имя.")
            if not phone.strip():
                errors.append("Введите телефон.")
            if start_date > end_date:
                errors.append("Дата начала не может быть позже даты окончания.")
            if errors:
                for err in errors:
                    st.error(err)
            else:
                order_data = {
                    "name": name.strip(),
                    "phone": phone.strip(),
                    "tools": selected_tools,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "comment": comment.strip()
                }
                saved = save_order_to_sheets(order_data)
                if USE_REAL_SERVICES:
                    notified = send_telegram_notification(order_data)
                    if saved and notified:
                        st.success("✅ Заказ успешно отправлен! Мы свяжемся с вами в ближайшее время.")
                    elif saved and not notified:
                        st.warning("Заказ сохранён, но уведомление не отправлено (проверьте настройки Telegram).")
                    else:
                        st.error("Произошла ошибка при сохранении заказа. Попробуйте позже.")
                else:
                    st.success("✅ Заказ принят (демо-режим). В реальном режиме данные будут записаны в Google Sheets.")
                    st.info("Данные заказа: " + json.dumps(order_data, ensure_ascii=False, indent=2))

# -------------------------------------------------------------------
# 7. ОСНОВНОЙ ИНТЕРФЕЙС
# -------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Прокат инструментов",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    # Подключаем CSS с эффектом всплывающего фото
    inject_hover_zoom_css()

    st.title("🔨 Прокат строительного инструмента")
    st.markdown("**Арендуйте качественный инструмент по выгодным ценам!**")
    st.markdown("---")

    catalog = load_catalog_from_sheets()
    display_catalog(catalog)

    st.markdown("---")
    order_form(catalog)

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #888; font-size: 0.8rem;">
            © 2026 Прокат инструментов. Все права защищены.<br>
            Телефон для связи: <a href="tel:+71234567890">+7 (123) 456-78-90</a>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()