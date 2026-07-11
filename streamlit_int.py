#import streamlit as st
#import pandas as pd
#import gspread
#from oauth2client.service_account import ServiceAccountCredentials
#import requests
#import json
#from datetime import datetime
#import time
#import re

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
    st.warning("⚠️ Секреты не найдены. Работаем в демонстрационном режиме (без Google Sheets и Telegram).")

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
# 4. CSS ДЛЯ УВЕЛИЧЕНИЯ ИЗОБРАЖЕНИЙ ПРИ НАВЕДЕНИИ
# -------------------------------------------------------------------

def inject_enhanced_css():
    st.markdown("""
    <style>
    .tool-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        background: white;
        transition: 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        position: relative;
        overflow: hidden;
    }
    .tool-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border-color: #4CAF50;
    }
    .tool-card .tool-image {
        transition: 0.3s;
        width: 100%;
        height: 150px;
        object-fit: cover;
        border-radius: 6px;
    }
    .tool-card:hover .tool-image {
        transform: scale(1.05);
    }
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
    .order-form {
        background: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        margin-top: 30px;
        border: 1px solid #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------------
# 5. ОТОБРАЖЕНИЕ КАТАЛОГА
# -------------------------------------------------------------------

def display_catalog(catalog):
    st.header("📦 Наш каталог")
    st.markdown("Наведите на карточку, чтобы увидеть фото крупнее (эффект увеличения).")
    cols = st.columns(3)
    for idx, item in enumerate(catalog):
        col = cols[idx % 3]
        with col:
            image_url = item.get("image", "https://via.placeholder.com/150?text=Инструмент")
            quantity = item.get("quantity", 0)
            status_color = "green" if quantity > 0 else "red"
            status_text = "В наличии" if quantity > 0 else "Нет в наличии"
            card_html = f"""
            <div class="tool-card">
                <img src="{image_url}" class="tool-image" alt="{item['name']}">
                <div class="tool-name">{item['name']}</div>
                <div class="tool-desc">{item['description']}</div>
                <div class="tool-price">{item['price']} руб/сутки</div>
                <div class="tool-quantity">Осталось: <span style="color:{status_color};">{quantity}</span> шт.</div>
                <div style="font-size:0.8rem; margin-top:4px; color:{status_color};">{status_text}</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

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
    inject_enhanced_css()
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