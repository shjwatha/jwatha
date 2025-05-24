import streamlit as st
import pymysql
import pandas as pd

st.set_page_config(page_title="لوحة آدمن المستوى", page_icon="🛠️")

# التحقق من الجلسة
if "authenticated" not in st.session_state or st.session_state["permissions"] != "admin":
    st.error("❌ لا تملك صلاحية الوصول إلى هذه الصفحة.")
    st.stop()

st.title(f"🛠️ لوحة آدمن المستوى ({st.session_state['level']})")

# الاتصال بقاعدة البيانات
conn = pymysql.connect(
    host=st.secrets["DB_HOST"],
    port=int(st.secrets["DB_PORT"]),
    user=st.secrets["DB_USER"],
    password=st.secrets["DB_PASSWORD"],
    database=st.secrets["DB_NAME"],
    charset="utf8mb4"
)
cursor = conn.cursor(pymysql.cursors.DictCursor)

# عرض المستخدمين
cursor.execute("SELECT * FROM users WHERE level = %s AND is_deleted = 0", (st.session_state["level"],))
users = cursor.fetchall()

st.subheader("📋 قائمة المستخدمين")
if not users:
    st.info("لا يوجد مستخدمون في هذا المستوى.")
else:
    df = pd.DataFrame(users)[["full_name", "username", "mentor"]]
    df.columns = ["الاسم الكامل", "اسم المستخدم", "المشرف"]
    st.dataframe(df, use_container_width=True)

# إضافة مستخدم جديد
st.subheader("➕ إضافة مستخدم جديد")
with st.form("add_user_form"):
    full_name = st.text_input("الاسم الكامل")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور")
    mentor = st.text_input("المشرف")
    submit = st.form_submit_button("إضافة")

    if submit:
        if not all([full_name, username, password, mentor]):
            st.warning("⚠️ جميع الحقول مطلوبة.")
        else:
            # تحقق من التعارض
            cursor.execute("SELECT 1 FROM users WHERE username = %s OR full_name = %s", (username, full_name))
            if cursor.fetchone():
                st.error("❌ الاسم الكامل أو اسم المستخدم مستخدم بالفعل.")
            else:
                cursor.execute("""
                    INSERT INTO users (full_name, username, password, mentor, level)
                    VALUES (%s, %s, %s, %s, %s)
                """, (full_name.strip(), username.strip(), password.strip(), mentor.strip(), st.session_state["level"]))
                conn.commit()
                st.success("✅ تم إضافة المستخدم بنجاح.")
                st.rerun()

