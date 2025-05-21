import streamlit as st
import pymysql
import pandas as pd

# إعداد واجهة الصفحة
st.set_page_config(page_title="تسجيل الدخول", page_icon="🔐")
st.title("🔐 تسجيل الدخول")

# الاتصال بقاعدة بيانات MySQL
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
    st.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
    st.stop()

# حالة تسجيل الدخول
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("دخول")

        if submitted:
            # المحاولة أولاً في جدول users
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()

            if user:
                st.session_state.update({
                    "authenticated": True,
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "permissions": "user",
                    "level": user.get("level", "")
                })
                st.success("✅ تم تسجيل الدخول بنجاح")
                st.switch_page("pages/UserDashboard.py")
                st.stop()

            # المحاولة في جدول admins
            cursor.execute("SELECT * FROM admins WHERE username = %s AND password = %s", (username, password))
            admin = cursor.fetchone()

            if admin:
                st.session_state.update({
                    "authenticated": True,
                    "username": admin["username"],
                    "full_name": admin["full_name"],
                    "permissions": admin["role"],
                    "level": admin.get("level", "")
                })
                st.success("✅ تم تسجيل الدخول بنجاح")

                if admin["role"] == "admin":
                    st.switch_page("pages/AdminDashboard.py")
                elif admin["role"] in ["supervisor", "sp"]:
                    st.switch_page("pages/Supervisor.py")
                else:
                    st.error("❌ نوع صلاحية غير معروف")
                st.stop()

            # المحاولة في جدول super_admins
            cursor.execute("SELECT * FROM super_admins")
            super_admins = cursor.fetchall()
            admin_match = next(
                (
                    a for a in super_admins
                    if (
                        a["username"].strip().lower() == username.lower() or
                        a["full_name"].strip().lower() == username.lower()
                    ) and a["password"] == password
                ),
                None
            )

            if admin_match:
                st.session_state.update({
                    "authenticated": True,
                    "username": admin_match["username"],
                    "full_name": admin_match["full_name"],
                    "permissions": admin_match["role"]
                })
                st.success("✅ تم تسجيل الدخول بنجاح")
                st.switch_page("pages/SuperAdmin.py")
                st.stop()

            else:
                st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")

else:
    st.switch_page("pages/UserDashboard.py")
