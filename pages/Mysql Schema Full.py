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

# 🎯 المستويات
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

# 🧑‍💼 إدارة المشرفين
st.subheader("🧑‍💼 إضافة مشرف جديد")

with st.form("add_supervisor"):
    full_name = st.text_input("الاسم الكامل")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور")
    role = st.selectbox("الدور", ["admin", "supervisor", "sp"])
    level = st.text_input("المستوى")
    mentor = st.text_input("المشرف (اختياري)", value="")
    submit_admin = st.form_submit_button("➕ إضافة")

    if submit_admin:
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        if cursor.fetchone():
            st.warning("⚠️ اسم المستخدم مستخدم مسبقًا.")
        else:
            cursor.execute(
                "INSERT INTO admins (full_name, username, password, role, level, mentor) VALUES (%s, %s, %s, %s, %s, %s)",
                (full_name, username, password, role, level, mentor or None)
            )
            conn.commit()
            st.success("✅ تم إنشاء الحساب")
            st.rerun()

# 👤 إنشاء حساب مستخدم عادي
st.subheader("👤 إضافة مستخدم جديد")

with st.form("add_user"):
    u_full_name = st.text_input("اسم المستخدم الكامل")
    u_username = st.text_input("اسم المستخدم")
    u_password = st.text_input("كلمة المرور")
    u_level = st.text_input("المستوى")
    u_mentor = st.text_input("المشرف")
    submit_user = st.form_submit_button("➕ إضافة")

    if submit_user:
        cursor.execute("SELECT * FROM users WHERE username = %s", (u_username,))
        if cursor.fetchone():
            st.warning("⚠️ اسم المستخدم مستخدم مسبقًا.")
        else:
            cursor.execute(
                "INSERT INTO users (full_name, username, password, level, mentor, role) VALUES (%s, %s, %s, %s, %s, %s)",
                (u_full_name, u_username, u_password, u_level, u_mentor, 'user')
            )
            conn.commit()
            st.success("✅ تم إضافة المستخدم")
            st.rerun()

# 👑 حساب مدير عام جديد
st.subheader("👑 إضافة مدير عام جديد")

with st.form("add_super_admin"):
    sa_name = st.text_input("اسم المدير")
    sa_username = st.text_input("اسم المستخدم")
    sa_password = st.text_input("كلمة المرور")
    submit_sa = st.form_submit_button("➕ إضافة")

    if submit_sa:
        cursor.execute("SELECT * FROM super_admins WHERE username = %s", (sa_username,))
        if cursor.fetchone():
            st.warning("⚠️ اسم المستخدم موجود مسبقًا.")
        else:
            cursor.execute(
                "INSERT INTO super_admins (full_name, username, password, role) VALUES (%s, %s, %s, %s)",
                (sa_name, sa_username, sa_password, 'super_admin')
            )
            conn.commit()
            st.success("✅ تم إنشاء المدير العام")
            st.rerun()

# 🏆 عرض الإنجازات
st.subheader("🏆 الإنجازات")
cursor.execute("SELECT * FROM achievements ORDER BY timestamp DESC")
achievements = cursor.fetchall()
if achievements:
    df = pd.DataFrame(achievements)
    st.dataframe(df[["username", "achievement", "timestamp"]], use_container_width=True)
else:
    st.info("لا توجد إنجازات حاليًا.")

# 💬 المحادثات
st.subheader("💬 المحادثات")
cursor.execute("SELECT * FROM chat ORDER BY timestamp DESC")
messages = cursor.fetchall()
if messages:
    for msg in messages:
        st.markdown(f"📨 من `{msg['sender']}` إلى `{msg['receiver']}`:")
        st.code(msg['message'])
else:
    st.info("لا توجد رسائل حالياً.")
