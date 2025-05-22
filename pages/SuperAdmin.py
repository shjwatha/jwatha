# ✅ SuperAdmin.py — مدير النظام (MySQL فقط)
import streamlit as st
import pandas as pd
import pymysql

# إعداد الصفحة
st.set_page_config(page_title="لوحة المدير العام", page_icon="👑")
st.title("👑 لوحة المدير العام")

# التأكد من الجلسة
if "authenticated" not in st.session_state or st.session_state.get("permissions") != "super_admin":
    st.error("🚫 لا تملك صلاحية الوصول.")
    st.stop()

# الاتصال بقاعدة البيانات
try:
    conn = pymysql.connect(
        host=st.secrets["DB_HOST"],
        port=int(st.secrets["DB_PORT"]),
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_NAME"],
        charset='utf8mb4'
    )
    cursor = conn.cursor(pymysql.cursors.DictCursor)
except Exception as e:
    st.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
    st.stop()

# 🔄 زر التحديث
if st.button("🔄 تحديث الصفحة"):
    st.rerun()

# 🎯 إدارة المستويات
st.subheader("🎯 إدارة المستويات")
cursor.execute("SELECT * FROM levels")
levels = cursor.fetchall()
level_df = pd.DataFrame(levels)
if not level_df.empty:
    st.dataframe(level_df)

with st.form("add_level"):
    level_name = st.text_input("اسم المستوى")
    submit_level = st.form_submit_button("➕ إضافة مستوى")
    if submit_level and level_name:
        cursor.execute("INSERT INTO levels (level_name) VALUES (%s)", (level_name,))
        conn.commit()
        st.success("✅ تم إضافة المستوى")
        st.rerun()

# 🧑‍💼 إضافة مدير (آدمن) مرتبط بمستوى
st.subheader("🧑‍💼 إضافة مدير للمستوى")

with st.form("add_admin"):
    full_name = st.text_input("الاسم الكامل للآدمن")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور")
    level_options = [lvl['level_name'] for lvl in levels]
    level = st.selectbox("اختر المستوى", level_options)
    submit_admin = st.form_submit_button("➕ إضافة")

    if submit_admin:
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        if cursor.fetchone():
            st.warning("⚠️ اسم المستخدم مستخدم مسبقًا.")
        else:
            cursor.execute(
                "INSERT INTO admins (full_name, username, password, role, level) VALUES (%s, %s, %s, %s, %s)",
                (full_name, username, password, 'admin', level)
            )
            conn.commit()
            st.success("✅ تم إضافة الآدمن")
            st.rerun()

# 👨‍🏫 إضافة سوبر مشرف مرتبط بمستوى
st.subheader("👨‍🏫 إضافة سوبر مشرف")

with st.form("add_sp"):
    full_name = st.text_input("الاسم الكامل للسوبر مشرف")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور")
    level = st.selectbox("اختر المستوى للسوبر مشرف", level_options, key="sp_level")
    submit_sp = st.form_submit_button("➕ إضافة سوبر مشرف")

    if submit_sp:
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        if cursor.fetchone():
            st.warning("⚠️ اسم المستخدم موجود مسبقًا.")
        else:
            cursor.execute(
                "INSERT INTO admins (full_name, username, password, role, level) VALUES (%s, %s, %s, %s, %s)",
                (full_name, username, password, 'sp', level)
            )
            conn.commit()
            st.success("✅ تم إضافة السوبر مشرف")
            st.rerun()

# 👨‍💼 إضافة مشرف مباشر مرتبط بسوبر مشرف (نفس المستوى)
st.subheader("👨‍💼 إضافة مشرف مباشر")

# جلب قائمة السوبر مشرفين
cursor.execute("SELECT username, full_name, level FROM admins WHERE role = 'sp'")
supervisors = cursor.fetchall()

if not supervisors:
    st.info("🔸 لا يوجد سوبر مشرفين حالياً.")
else:
    with st.form("add_supervisor"):
        full_name = st.text_input("اسم المشرف")
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور")
        selected_sp = st.selectbox("اختر سوبر مشرف", [f"{s['full_name']} ({s['username']})" for s in supervisors])
        sp_username = selected_sp.split('(')[-1].replace(')', '').strip()
        sp_level = next((s['level'] for s in supervisors if s['username'] == sp_username), None)
        submit_sup = st.form_submit_button("➕ إضافة مشرف")

        if submit_sup:
            cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
            if cursor.fetchone():
                st.warning("⚠️ اسم المستخدم مستخدم مسبقًا.")
            else:
                cursor.execute(
                    "INSERT INTO admins (full_name, username, password, role, level, mentor) VALUES (%s, %s, %s, %s, %s, %s)",
                    (full_name, username, password, 'supervisor', sp_level, sp_username)
                )
                conn.commit()
                st.success("✅ تم إضافة المشرف")
                st.rerun()

# 👤 إضافة مستخدم جديد مرتبط بمشرف
st.subheader("👤 إضافة مستخدم جديد")

# جلب المشرفين
cursor.execute("SELECT username, full_name, level FROM admins WHERE role = 'supervisor'")
mentors = cursor.fetchall()

if not mentors:
    st.info("🔸 لا يوجد مشرفون حالياً.")
else:
    with st.form("add_user"):
        full_name = st.text_input("اسم المستخدم الكامل")
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور")
        selected_mentor = st.selectbox("اختر مشرف", [f"{m['full_name']} ({m['username']})" for m in mentors])
        mentor_username = selected_mentor.split('(')[-1].replace(')', '').strip()
        mentor_level = next((m['level'] for m in mentors if m['username'] == mentor_username), None)

        submit_user = st.form_submit_button("➕ إضافة المستخدم")

        if submit_user:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                st.warning("⚠️ اسم المستخدم موجود مسبقًا.")
            else:
                cursor.execute(
                    "INSERT INTO users (full_name, username, password, role, level, mentor) VALUES (%s, %s, %s, %s, %s, %s)",
                    (full_name, username, password, 'user', mentor_level, mentor_username)
                )
                conn.commit()
                st.success("✅ تم إضافة المستخدم")
                st.rerun()

# 🧾 عرض المستخدمين
st.subheader("📋 قائمة المستخدمين")
cursor.execute("SELECT full_name, username, level, mentor FROM users ORDER BY created_at DESC")
users = cursor.fetchall()
if users:
    st.dataframe(pd.DataFrame(users))

# 🧾 عرض الإداريين
st.subheader("📋 قائمة الإداريين")
cursor.execute("SELECT full_name, username, role, level, mentor FROM admins ORDER BY role, level")
admins = cursor.fetchall()
if admins:
    st.dataframe(pd.DataFrame(admins))
