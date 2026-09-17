import io
import sqlite3
import base64
import os
import json

import requests
import pandas as pd
import streamlit as st
from PIL import Image


st.set_page_config(
    page_title="Prim AI Automation Hub",
    page_icon="⚡",
    layout="wide",
)


def get_db_connection():
    """เปิดการเชื่อมต่อฐานข้อมูล พร้อมสร้างตารางและข้อมูลตัวอย่างเมื่อจำเป็น"""
    conn = sqlite3.connect("automation_hub.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            promo_price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
        """
    )

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO products (name, price, promo_price, stock)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("Centrum Silver 50+", 750, 590, 100),
                ("Fish Oil 1000mg", 600, 450, 80),
            ],
        )
        conn.commit()

    return conn


def get_secret_or_default(name, default):
    """อ่านค่า secret อย่างปลอดภัย และคืนค่า default หากไม่มีการตั้งค่า"""
    try:
        value = st.secrets[name]
        return value if value else default
    except Exception:
        return default


def decode_result(response):
    """แปลงผลตอบกลับจาก n8n ให้เป็น image bytes, JSON หรือข้อความ"""
    # ตรวจสอบ status code ก่อนอ่านหรือ parse เนื้อหาเสมอ
    if not 200 <= response.status_code < 300:
        raise requests.HTTPError(
            f"n8n ตอบกลับด้วย HTTP {response.status_code}",
            response=response,
        )

    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()

    if content_type.startswith("image/"):
        return {"kind": "image", "bytes": response.content}

    if content_type == "application/json" or content_type.endswith("+json"):
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        data = data if isinstance(data, dict) else payload

        if isinstance(data, dict) and data.get("image_url"):
            image_response = requests.get(str(data["image_url"]), timeout=180)
            if not 200 <= image_response.status_code < 300:
                raise requests.HTTPError(
                    f"ดาวน์โหลดภาพจาก image_url ไม่สำเร็จ: HTTP {image_response.status_code}",
                    response=image_response,
                )
            return {"kind": "image", "bytes": image_response.content}

        if isinstance(data, dict) and data.get("image_base64"):
            encoded = str(data["image_base64"])
            # รองรับกรณีที่ส่งมาเป็น data URL เช่น data:image/png;base64,...
            if "," in encoded and encoded.lower().startswith("data:"):
                encoded = encoded.split(",", 1)[1]
            return {"kind": "image", "bytes": base64.b64decode(encoded)}

        return {"kind": "json", "payload": payload}

    return {"kind": "text", "text": response.text[:3000]}


def render_ai_media_module():
    st.header("🎨 AI Media: Image-to-Image & Content Hub")
    st.write(
        "โมดูลนี้ใช้ AI แก้ไขภาพสินค้าตามคำสั่ง (prompt) ที่ระบุ โดยส่งทั้งภาพต้นฉบับ "
        "และ prompt ไปยัง n8n Webhook แล้วรับภาพที่แก้ไขแล้วกลับมาแสดงผล"
    )

    # โค้ดส่วนนี้เป็น image-to-image ไม่ใช่วิดีโอ หากจะทำวิดีโอต้องใช้ workflow/job endpoint แยก
    uploaded_file = st.file_uploader(
        "อัปโหลดภาพสินค้า",
        type=["jpg", "jpeg", "png"],
        help="รองรับไฟล์ JPG, JPEG และ PNG",
    )

    if uploaded_file is not None:
        st.subheader("ภาพต้นฉบับ")
        st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)

    default_prompt = (
        "Edit this product image while preserving the exact product shape, packaging, "
        "brand, label, logo, text, colors, and proportions. Improve the background and "
        "lighting only, and do not add or remove any product details."
    )
    prompt_edit = st.text_area(
        "Prompt สำหรับการแก้ไขภาพ",
        value=default_prompt,
        height=130,
    )

    webhook_url = get_secret_or_default(
        "N8N_WEBHOOK_URL",
        "https://primshop.app.n8n.cloud/webhook/ai-media-webhook",
    )

    if st.button("ส่งภาพให้ AI แก้ไข", type="primary", disabled=uploaded_file is None):
        image_bytes = uploaded_file.getvalue()

        try:
            with st.spinner("กำลังส่งภาพและ prompt ไปยัง AI ผ่าน n8n..."):
                response = requests.post(
                    webhook_url,
                    data={"prompt": prompt_edit},
                    files={
                        "image": (
                            uploaded_file.name,
                            image_bytes,
                            uploaded_file.type,
                        )
                    },
                    timeout=180,
                )
                result = decode_result(response)

            if result["kind"] == "image":
                result_bytes = result["bytes"]

                # ตรวจสอบว่า bytes ที่ได้รับเป็นภาพจริง แล้วเปิดใหม่เพื่อแสดงผล
                with Image.open(io.BytesIO(result_bytes)) as verified_image:
                    verified_image.verify()
                result_image = Image.open(io.BytesIO(result_bytes))

                # แปลงเป็น PNG เพื่อให้ mime type และชื่อไฟล์ของปุ่มดาวน์โหลดตรงกัน
                png_buffer = io.BytesIO()
                result_image.save(png_buffer, format="PNG")
                result_png_bytes = png_buffer.getvalue()

                st.success("AI แก้ไขภาพสำเร็จ")
                st.image(result_image, caption="ภาพสินค้าที่แก้ไขแล้ว", use_container_width=True)
                st.download_button(
                    "ดาวน์โหลดภาพที่แก้ไขแล้ว",
                    data=result_png_bytes,
                    file_name="ai_edited_product.png",
                    mime="image/png",
                )
                result_image.close()

            elif result["kind"] == "json":
                st.warning("n8n ตอบกลับเป็น JSON แต่ไม่พบ image_url หรือ image_base64")
                st.json(result["payload"])
                st.info(
                    "โปรดตรวจสอบ workflow ให้ส่งภาพกลับโดยตรง หรือส่ง JSON ที่มี "
                    "image_url / image_base64"
                )
            else:
                st.warning("n8n ตอบกลับเป็นข้อความหรือชนิดข้อมูลที่ไม่ใช่ภาพ/JSON")
                st.code(result["text"])

        except requests.exceptions.Timeout:
            st.error("หมดเวลาเชื่อมต่อกับ n8n (timeout) กรุณาลองใหม่อีกครั้ง")
        except requests.exceptions.RequestException as error:
            st.error(f"ไม่สามารถเรียก n8n ได้: {error}")
        except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
            st.error("n8n ตอบกลับมาเป็น JSON ที่อ่านไม่ได้ กรุณาตรวจสอบรูปแบบ response")
        except (ValueError, TypeError) as error:
            st.error(f"ไม่สามารถถอดรหัสผลลัพธ์ภาพได้: {error}")
        except Exception as error:
            st.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {error}")

    with st.expander("การตั้งค่า n8n ที่ต้องใช้"):
        st.markdown(
            """
            Webhook ต้องรับข้อมูลแบบ `multipart/form-data` โดยมี fields ดังนี้:

            - `prompt` เป็นข้อความคำสั่งสำหรับแก้ไขภาพ
            - `image` เป็น binary property ของภาพที่อัปโหลด

            workflow ต้องส่งผลลัพธ์กลับมาเป็นภาพโดยตรง หรือเป็น JSON ในรูปแบบ
            `{image_url: ...}` / `{image_base64: ...}` หาก n8n ใช้ binary property
            ชื่ออื่น ให้เปลี่ยนชื่อ `image` ใน Python ให้ตรงกัน
            """
        )


def main():
    st.title("⚡ Prim AI Automation Hub")
    st.caption("ศูนย์รวมระบบ Automation สำหรับงานออร์เดอร์ คลังสินค้า จัดส่ง และ AI Media")

    menu_items = [
        "📦 1. รับออร์เดอร์ & ตรวจสลิปอัตโนมัติ",
        "🏭 2. ระบบพนักงานจัดของ (Warehouse Staff)",
        "🚚 3. ระบบจัดส่ง & แจ้งเตือนลูกค้า",
        "🎨 4. AI Media: Image-to-Image & Content Hub (Powered by n8n Webhook)",
        "📊 5. คลังสินค้า & จัดการ SKU",
    ]

    selected_module = st.sidebar.radio("เลือกโมดูล", menu_items)

    if selected_module == menu_items[0]:
        st.header(menu_items[0])
        st.success("ระบบพร้อมใช้งาน")
    elif selected_module == menu_items[1]:
        st.header(menu_items[1])
        st.success("ระบบพร้อมใช้งาน")
    elif selected_module == menu_items[2]:
        st.header(menu_items[2])
        st.success("ระบบพร้อมใช้งาน")
    elif selected_module == menu_items[3]:
        render_ai_media_module()
    elif selected_module == menu_items[4]:
        st.header(menu_items[4])
        connection = get_db_connection()
        try:
            products_df = pd.read_sql_query(
                """
                SELECT id, name, price, promo_price, stock
                FROM products
                ORDER BY id
                """,
                connection,
            )
            st.dataframe(products_df, use_container_width=True, hide_index=True)
        finally:
            connection.close()


if __name__ == "__main__":
    main()
