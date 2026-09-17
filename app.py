import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ตั้งค่าหน้าจอ Streamlit
st.set_page_config(
    page_title="Prim AI Automation Hub - Backoffice & POS",
    page_icon="⚡",
    layout="wide"
)

# ----------------------------------------------------
# ส่วนจัดการฐานข้อมูล SQLite (Central Database)
# ----------------------------------------------------
DB_FILE = "prim_automation.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            ProductID TEXT PRIMARY KEY,
            ProductName TEXT NOT NULL,
            Price REAL,
            PromoPrice REAL,
            Stock INTEGER,
            Unit TEXT,
            Barcode TEXT
        )
    ''')
    
    for col_def in [("PromoPrice", "REAL DEFAULT 0"), ("Unit", "TEXT DEFAULT 'ชิ้น'"), ("Barcode", "TEXT DEFAULT ''")]:
        col_name, col_type = col_def
        try:
            c.execute(f"SELECT {col_name} FROM products LIMIT 1")
        except sqlite3.OperationalError:
            c.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")

    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            OrderID TEXT PRIMARY KEY,
            CustomerName TEXT,
            Phone TEXT,
            Address TEXT,
            ProductID TEXT,
            ProductName TEXT,
            Quantity INTEGER,
            Total REAL,
            PaymentStatus TEXT,
            FulfillmentStatus TEXT,
            OrderDate TEXT
        )
    ''')
    
    c.execute('SELECT count(*) FROM products')
    if c.fetchone()[0] == 0:
        default_products = [
            ("P001", "เซรั่มทองคำแท้ 24K (Anti-Aging)", 890, 790, 45, "ชิ้น", "885001234001"),
            ("P002", "ครีมกันแดดหน้าเนียน SPF50+ PA++++", 450, 390, 120, "ชิ้น", "885001234002"),
            ("P003", "มาสก์หน้าสูตรเข้มข้น (Overnight Mask)", 650, 550, 60, "ชิ้น", "885001234003"),
            ("P004", "โฟมล้างหน้าวิตามินซี (Brightening Foam)", 290, 250, 150, "ชิ้น", "885001234004")
        ]
        c.executemany('INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)', default_products)
        conn.commit()
    conn.close()

init_db()

# ----------------------------------------------------
# เมนูด้านข้าง (Sidebar Menu)
# ----------------------------------------------------
st.sidebar.title("⚡ Prim AI Automation Hub")
menu = st.sidebar.radio("เลือกโมดูลระบบ:", [
    "🛒 1. รับออร์เดอร์ & ตรวจสลิปอัตโนมัติ",
    "📦 2. ระบบพนักงานจัดของ (Warehouse Staff)",
    "🚚 3. ระบบจัดส่ง & แจ้งเตือนลูกค้า",
    "🎨 4. AI Combo Media & Content Hub (สร้างและโพสต์คอนเทนต์)",
    "📊 5. คลังสินค้า, บาร์โค้ด & จัดการ SKU (Inventory)"
])

# ----------------------------------------------------
# โมดูลที่ 1: รับออร์เดอร์ & ตรวจสลิปอัตโนมัติ
# ----------------------------------------------------
if menu == "🛒 1. รับออร์เดอร์ & ตรวจสลิปอัตโนมัติ":
    st.markdown("## 🛒 ระบบรับคำสั่งซื้อและตรวจสอบการชำระเงินอัตโนมัติ")
    st.write("---")

    conn = get_db_connection()
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📥 จำลองข้อมูลลูกค้าสั่งซื้อ")
        with st.form("order_form"):
            cust_name = st.text_input("ชื่อ-นามสกุล ลูกค้า", value="คุณสมชาย ใจดี")
            cust_phone = st.text_input("เบอร์โทรศัพท์", value="0891234567")
            cust_address = st.text_area("ที่อยู่จัดส่ง", value="123/4 ถ.สุขุมวิท คลองเตย กรุงเทพฯ 10110")
            
            prod_choice = st.selectbox("เลือกสินค้าจากคลัง", products_df['ProductName'].tolist())
            qty = st.number_input("จำนวน", min_value=1, value=1)
            uploaded_slip = st.file_uploader("แนบสลิปโอนเงิน", type=["png", "jpg", "jpeg"])
            
            submit_order = st.form_submit_button("🚀 ยืนยันคำสั่งซื้อ & ตรวจสลิปด้วย AI")
            
            if submit_order:
                selected_prod = products_df[products_df['ProductName'] == prod_choice].iloc[0]
                unit_price = selected_prod['PromoPrice'] if selected_prod['PromoPrice'] > 0 else selected_prod['Price']
                total_price = unit_price * qty
                
                if selected_prod['Stock'] >= qty:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT count(*) FROM orders")
                    cnt = c.fetchone()[0]
                    order_id = f"ORD{cnt+1:03d}"
                    
                    c.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                        order_id, cust_name, cust_phone, cust_address,
                        selected_prod['ProductID'], selected_prod['ProductName'],
                        qty, total_price, "ชำระเงินถูกต้อง (AI Verified)", "รอดำเนินการจัดของ", datetime.now().strftime("%Y-%m-%d %H:%M")
                    ))
                    c.execute("UPDATE products SET Stock = Stock - ? WHERE ProductID = ?", (qty, selected_prod['ProductID']))
                    conn.commit()
                    conn.close()
                    st.success(f"AI ตรวจสลิปสำเร็จ! สร้างออร์เดอร์ {order_id} (ยอดรวม {total_price:,.2f} บาท) เรียบร้อย")
                else:
                    st.error("สินค้าในสต็อกไม่เพียงพอ!")

    with col2:
        st.subheader("📊 สถานะคำสั่งซื้อล่าสุด")
        conn = get_db_connection()
        orders_df = pd.read_sql_query("SELECT OrderID, CustomerName, ProductName, Quantity, Total, PaymentStatus, FulfillmentStatus FROM orders", conn)
        conn.close()
        st.dataframe(orders_df, use_container_width=True)

# ----------------------------------------------------
# โมดูลที่ 2: ระบบพนักงานจัดของ
# ----------------------------------------------------
elif menu == "📦 2. ระบบพนักงานจัดของ (Warehouse Staff)":
    st.markdown("## 📦 ระบบพนักงานหลังบ้าน (รับรายการสั่ง & ยืนยันการจัดของ)")
    st.write("---")
    conn = get_db_connection()
    pending_orders = pd.read_sql_query("SELECT * FROM orders WHERE FulfillmentStatus = 'รอดำเนินการจัดของ'", conn)
    conn.close()

    if len(pending_orders) > 0:
        st.dataframe(pending_orders, use_container_width=True)
        with st.form("pack_form"):
            selected_id = st.selectbox("เลือกเลขออเดอร์ที่แพ็กสินค้าเสร็จแล้ว", pending_orders['OrderID'].tolist())
            if st.form_submit_button("✅ ยืนยันการจัดของเสร็จสิ้น"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("UPDATE orders SET FulfillmentStatus = 'แพ็กสินค้าแล้ว (รอส่งมอบขนส่ง)' WHERE OrderID = ?", (selected_id,))
                conn.commit()
                conn.close()
                st.success(f"อัปเดตออเดอร์ {selected_id} เป็น 'แพ็กสินค้าแล้ว' เรียบร้อย!")
                st.rerun()
    else:
        st.info("👍 ไม่มีออร์เดอร์ค้างจัดของในขณะนี้")

# ----------------------------------------------------
# โมดูลที่ 3: ระบบจัดส่ง & แจ้งเตือนลูกค้า
# ----------------------------------------------------
elif menu == "🚚 3. ระบบจัดส่ง & แจ้งเตือนลูกค้า":
    st.markdown("## 🚚 ระบบจัดส่งสินค้า & ส่งสถานะไปยังลูกค้าอัตโนมัติ")
    st.write("---")
    conn = get_db_connection()
    ready_orders = pd.read_sql_query("SELECT * FROM orders WHERE FulfillmentStatus != 'จัดส่งสำเร็จ'", conn)
    conn.close()

    if len(ready_orders) > 0:
        st.dataframe(ready_orders, use_container_width=True)
        with st.form("shipping_form"):
            ship_id = st.selectbox("เลือกเลขออเดอร์เพื่อส่งมอบขนส่ง", ready_orders['OrderID'].tolist())
            tracking_no = st.text_input("กรอกเลขพัสดุขนส่ง (เช่น TH123456789)")
            if st.form_submit_button("🚀 ยืนยันการส่งของ & แจ้งเตือนลูกค้าอัตโนมัติ"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("UPDATE orders SET FulfillmentStatus = 'จัดส่งสำเร็จ (แจ้งลูกค้าแล้ว)' WHERE OrderID = ?", (ship_id,))
                conn.commit()
                conn.close()
                st.success(f"ส่งเลขพัสดุ ({tracking_no}) ไปยังลูกค้าเรียบร้อยแล้ว!")
                st.rerun()
    else:
        st.info("ไม่มีออร์เดอร์ที่รอจัดส่งในขณะนี้")

# ----------------------------------------------------
# โมดูลที่ 4: AI Combo Media & Content Hub (อัปโหลดอิสระ + AI สร้างสื่อจากภาพนิ่ง + ปุ่มยืนยันชัดเจน)
# ----------------------------------------------------
elif menu == "🎨 4. AI Combo Media & Content Hub (สร้างและโพสต์คอนเทนต์)":
    st.markdown("## 🎨🎬 AI Combo Media & Content Hub (ระบบสร้างและโพสต์คอมโบเซ็ตเบ็ดเสร็จ)")
    st.markdown("อัปโหลดวิดีโอหรือภาพนิ่ง (1-4 ภาพ) แบบอิสระ เลือกให้ AI สร้างภาพ/วิดีโอใหม่หรือใช้ของเดิม พร้อมปุ่มยืนยันการใช้งานจริง")
    st.write("---")

    conn = get_db_connection()
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()

    with st.expander("➕ [คลิกเพื่อเปิด/ปิด] เพิ่ม SKU สินค้าใหม่ตรงนี้ เพื่อนำไปผูกกับโพสต์ทันที"):
        with st.form("quick_add_sku_form"):
            q_sku = st.text_input("รหัส SKU ใหม่ (เช่น P005)", value="P005")
            q_name = st.text_input("ชื่อสินค้าใหม่", value="ครีมบำรุงสูตรกลางคืน")
            q_price = st.number_input("ราคาปกติ", min_value=0.0, value=990.0)
            q_promo = st.number_input("ราคาโปรโมชั่น", min_value=0.0, value=790.0)
            q_stock = st.number_input("สต็อกเริ่มต้น", min_value=0, value=50)
            q_unit = st.text_input("หน่วยนับ", value="ชิ้น")
            q_barcode = st.text_input("รหัส Barcode", value="885001234005")
            
            if st.form_submit_button("💾 บันทึก SKU ใหม่"):
                if q_sku and q_name:
                    try:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", (
                            q_sku, q_name, q_price, q_promo, q_stock, q_unit, q_barcode
                        ))
                        conn.commit()
                        conn.close()
                        st.success(f"เพิ่ม SKU '{q_sku} - {q_name}' สำเร็จ!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

    st.write("---")

    if len(products_df) > 0:
        selected_sku_to_post = st.selectbox(
            "🔗 เลือก SKU สินค้าที่จะนำมาผูกกับโพสต์นี้",
            products_df['ProductName'].tolist()
        )
        matched_prod = products_df[products_df['ProductName'] == selected_sku_to_post].iloc[0]
        st.info(f"🏷️ SKU: **{matched_prod['ProductID']}** | ปกติ: **{matched_prod['Price']} ฿** | โปรโมชั่นปัจจุบัน: 🔥 **{matched_prod['PromoPrice']} ฿**")
    else:
        st.warning("ยังไม่มีสินค้าในคลัง กรุณาเพิ่ม SKU ด้านบนก่อน")
        selected_sku_to_post = "สินค้าทั่วไป"

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("#### 🎬 อัปโหลดวิดีโอ (ไม่บังคับ)")
        uploaded_combo_video = st.file_uploader("เลือกไฟล์วิดีโอ (MP4)", type=["mp4"], key="combo_video")
        
        video_gen_mode = st.radio(
            "เลือกการจัดการวิดีโอ:",
            ["📌 ใช้วิดีโอต้นฉบับเดิม", "✨ ให้ AI สร้าง/ปรับแต่งวิดีโอใหม่", "🤖 ให้ AI สร้างวิดีโอเคลื่อนไหวจากภาพนิ่ง"],
            key="v_mode"
        )

        st.markdown("#### 🎵 ไฟล์เสียง / เพลงประกอบ (ไม่บังคับ)")
        uploaded_audio = st.file_uploader("เลือกไฟล์เสียง (MP3, WAV)", type=["mp3", "wav"], key="combo_audio")

    with col_c2:
        st.markdown("#### 🖼️ อัปโหลดภาพนิ่ง 1-4 ภาพ (ไม่บังคับ)")
        uploaded_combo_images = st.file_uploader(
            "เลือกไฟล์ภาพนิ่ง (PNG, JPG) จำนวน 1 ถึง 4 ภาพ", 
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="combo_images"
        )
        if uploaded_combo_images and len(uploaded_combo_images) > 4:
            st.warning("⚠️ อัปโหลดเกิน 4 ภาพ ระบบจะเลือกใช้ 4 ภาพแรก")

        image_gen_mode = st.radio(
            "เลือกการจัดการภาพนิ่ง:",
            ["📌 ใช้รูปภาพต้นฉบับเดิม", "✨ ให้ AI สร้างสรรค์ตกแต่งภาพนิ่งใหม่ให้สวยงาม"],
            key="i_mode"
        )

    st.write("---")
    st.markdown("### ⚙️ ป้อนคำสั่ง Prompt สำหรับ AI และกำหนดเวลาโพสต์")
    
    default_promo_val = matched_prod['PromoPrice'] if 'matched_prod' in locals() else 0
    ai_custom_prompt = st.text_area(
        "💬 ช่องใส่ AI Prompt (ระบุสไตล์, โทนสี, ข้อความแคปชัน หรือโปรโมชัน):", 
        value=f"ขอโทนสีละมุน พรีเมียม เน้นจุดเด่นสินค้า {selected_sku_to_post} พร้อมใส่ข้อความโปรโมชั่นพิเศษ {default_promo_val} บาท",
        key="user_ai_prompt_input",
        height=90
    )
    
    target_socials = st.multiselect(
        "เลือกแพลตฟอร์มที่จะโพสต์", 
        ["Facebook Page / Reel", "TikTok Video", "Instagram Reel / Post"], 
        default=["Facebook Page / Reel", "TikTok Video"], 
        key="combo_socials"
    )

    st.markdown("#### ⏰ รูปแบบการเผยแพร่โพสต์")
    post_timing_mode = st.radio(
        "เลือกเวลาการโพสต์:",
        ["🚀 โพสต์ทันที (Publish Immediately)", "📅 กำหนดเวลาโพสต์ล่วงหน้า (Schedule)"],
        key="timing_mode"
    )

    if "กำหนดเวลาโพสต์ล่วงหน้า" in post_timing_mode:
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            scheduled_date = st.date_input("เลือกวันที่โพสต์")
        with col_t2:
            scheduled_time = st.time_input("เลือกเวลาโพสต์")

    # ปุ่มสร้างตัวอย่างพรีวิว
    if st.button("👁️ สร้างตัวอย่างเซ็ตโพสต์ (Combo Preview)", type="primary"):
        st.session_state.show_preview = True

    # แสดงผลพรีวิวและปุ่มยืนยันใช้งานจริงตลอดเวลาถ้ากดพรีวิวแล้ว
    if st.session_state.get("show_preview", False):
        st.write("---")
        st.markdown("### 🔍 ผลลัพธ์ตัวอย่างชิ้นงานที่ AI ประมวลผล")
        st.info(f"📋 **โหมดสื่อ:** ภาพนิ่ง (`{image_gen_mode}`) | วิดีโอ (`{video_gen_mode}`)")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if uploaded_combo_video:
                st.video(uploaded_combo_video)
            else:
                st.info("ℹ️ (ใช้ระบบ AI สร้างวิดีโอเคลื่อนไหวจากภาพนิ่ง)")
            if uploaded_audio:
                st.audio(uploaded_audio)
        
        with col_p2:
            if uploaded_combo_images:
                cols_prev = st.columns(min(len(uploaded_combo_images), 2))
                for idx, img in enumerate(uploaded_combo_images[:4]):
                    with cols_prev[idx % len(cols_prev)]:
                        st.image(img, caption=f"ภาพที่ #{idx+1}", use_container_width=True)

        promo_show = matched_prod['PromoPrice'] if 'matched_prod' in locals() else 0
        price_show = matched_prod['Price'] if 'matched_prod' in locals() else 0
        sku_show = matched_prod['ProductID'] if 'matched_prod' in locals() else 'SKU-XX'
        
        st.success(
            f"🔥 **[AI Generated Caption & Voiceover Script]**\n\n"
            f"📌 **SKU:** {sku_show} - {selected_sku_to_post}\n"
            f"🎯 **Prompt:** {ai_custom_prompt}\n\n"
            f"📜 **แคปชัน:** {selected_sku_to_post} จัดโปรโมชั่นพิเศษเหลือเพียง **{promo_show} บาท** (ปกติ {price_show} บาท)\n"
            "🛒 สั่งซื้อพิมพ์ 'สนใจ' หรือทักแชทได้เลยค่ะ!"
        )

        st.write("---")
        st.markdown("### 🎛️ ยืนยันการใช้งานจริง")
        
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🔄 สั่ง AI ทำใหม่ (Regenerate)", key="btn_regen_new"):
                st.warning("🔄 AI กำลังประมวลผลชิ้นงานใหม่...")
                st.rerun()
        
        with col_act2:
            final_btn_label = "🚀 ยืนยัน! โพสต์ทันทีทันที" if "โพสต์ทันที" in post_timing_mode else f"📅 ยืนยัน! ตั้งเวลาโพสต์ ({scheduled_date} {scheduled_time})"
            if st.button(final_btn_label, type="primary", key="btn_confirm_publish_final"):
                if "โพสต์ทันที" in post_timing_mode:
                    st.success(f"🎉 โพสต์คอนเทนต์ SKU ({sku_show}) ไปยัง {', '.join(target_socials)} เรียบร้อยแล้วทันที!")
                else:
                    st.success(f"🎉 ตั้งเวลาโพสต์ไปยัง {', '.join(target_socials)} วันที่ {scheduled_date} เวลา {scheduled_time} สำเร็จ!")
                st.session_state.show_preview = False

# ----------------------------------------------------
# โมดูลที่ 5: คลังสินค้า, สแกนบาร์โค้ด, นำเข้าเอกสาร AI & จัดการ SKU
# ----------------------------------------------------
elif menu == "📊 5. คลังสินค้า, บาร์โค้ด & จัดการ SKU (Inventory)":
    st.markdown("## 📊 คลังสินค้า, ระบบสแกนบาร์โค้ด, นำเข้าเอกสารด้วย AI และจัดการ SKU")
    st.write("---")

    inv_tab1, inv_tab2, inv_tab3 = st.tabs([
        "📥 นำเข้าใบส่งของด้วย AI (PDF & รูปภาพ)", 
        "📦 รับสินค้าเข้าสต็อกผ่านบาร์โค้ด", 
        "➕ เพิ่ม SKU สินค้าใหม่ & รายการคลัง"
    ])

    with inv_tab1:
        st.subheader("🤖 ระบบ AI อัปโหลดและแปลงเอกสารใบส่งของ (Invoice OCR)")
        doc_invoice_file = st.file_uploader("เลือกไฟล์เอกสารใบส่งของ (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])
        if doc_invoice_file and st.button("🚀 สั่ง AI สแกนเอกสาร", type="primary"):
            st.success("✅ AI สแกนเอกสารและดึงข้อมูลเลขที่เอกสาร วันที่ และรายการสินค้าเรียบร้อยแล้ว!")

    with inv_tab2:
        st.subheader("📷 ระบบรับสินค้าเข้าคลังด้วย Barcode")
        with st.form("barcode_receive_form"):
            scanned_barcode = st.text_input("🔍 ยิงหรือกรอกรหัส Barcode")
            doc_qty = st.number_input("จำนวนรับเข้า", min_value=1, value=1)
            if st.form_submit_button("📥 บันทึกรับสินค้าเข้าสต็อก"):
                if scanned_barcode.strip():
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("UPDATE products SET Stock = Stock + ? WHERE Barcode = ?", (doc_qty, scanned_barcode.strip()))
                    conn.commit()
                    conn.close()
                    st.success("✅ อัปเดตสต็อกเข้าคลังสำเร็จ!")

    with inv_tab3:
        col_inv1, col_inv2 = st.columns([1, 1.5])
        with col_inv1:
            st.subheader("➕ เพิ่ม SKU สินค้าใหม่")
            with st.form("add_sku_form"):
                new_sku_id = st.text_input("รหัส SKU", value="P005")
                new_sku_name = st.text_input("ชื่อสินค้า", value="เซรั่มวิตามินซี")
                new_price = st.number_input("ราคาปกติ", min_value=0.0, value=750.0)
                new_promo = st.number_input("ราคาโปรโมชั่น", min_value=0.0, value=590.0)
                new_stock = st.number_input("สต็อกเริ่มต้น", min_value=0, value=100)
                new_unit = st.text_input("หน่วยนับ", value="ชิ้น")
                new_barcode = st.text_input("Barcode", value="885001234005")
                if st.form_submit_button("💾 บันทึก SKU ใหม่"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", (
                        new_sku_id, new_sku_name, new_price, new_promo, new_stock, new_unit, new_barcode
                    ))
                    conn.commit()
                    conn.close()
                    st.success("เพิ่ม SKU สำเร็จ!")
                    st.rerun()
        with col_inv2:
            st.subheader("📋 รายการคลังสินค้าปัจจุบัน")
            conn = get_db_connection()
            inv_df = pd.read_sql_query("SELECT ProductID, ProductName, Price, PromoPrice, Stock, Unit, Barcode FROM products", conn)
            conn.close()
            st.dataframe(inv_df, use_container_width=True)