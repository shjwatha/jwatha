import streamlit as st
import pymysql

# إعداد صفحة تسجيل الدخول
st.set_page_config(page_title="تسجيل الدخول", page_icon="🔐")
st.title("🔐 تسجيل الدخول")


# ===== ضبط اتجاه النص من اليمين لليسار =====
st.markdown("""
<style>
body {
    direction: rtl;
    text-align: right;
}
</style>
""", unsafe_allow_html=True)



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

    # تحميل المستويات المعتمدة من جدول levels
    cursor.execute("SELECT level_name FROM levels")
    valid_levels = [row["level_name"] for row in cursor.fetchall() if row["level_name"]]
except Exception as e:
    st.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
    st.stop()

# إعداد الجلسة
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# نموذج تسجيل الدخول
if not st.session_state["authenticated"]:
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("دخول")

        if submitted:
            # تحقق من جدول المستخدمين
            cursor.execute("""
                SELECT * FROM users 
                WHERE (username = %s OR full_name = %s) AND password = %s AND is_deleted = 0
            """, (username, username, password))
            
            user = cursor.fetchone()

            if user:
                if user["level"] not in valid_levels:
                    st.error("⚠️ مستوى المستخدم غير موجود في قاعدة البيانات. يرجى مراجعة الإدارة.")
                elif not user["mentor"]:
                    st.error("⚠️ لا يوجد مشرف مرتبط بهذا الحساب. يرجى مراجعة الإدارة.")
                else:
                    st.session_state.update({
                        "authenticated": True,
                        "username": user["username"],
                        "full_name": user["full_name"],
                        "permissions": "user",
                        "level": user["level"]
                    })
                    st.success("✅ تم تسجيل الدخول بنجاح")
                    st.switch_page("pages/UserDashboard.py")
                    st.stop()

            # تحقق من جدول الأدمن (admin / supervisor / sp)
            cursor.execute("""
                SELECT * FROM admins 
                WHERE (username = %s OR full_name = %s) AND password = %s AND is_deleted = 0
            """, (username, username, password))

            admin = cursor.fetchone()

            if admin:
                if admin["level"] not in valid_levels:
                    st.error("⚠️ المستوى المرتبط بحساب الأدمن غير صالح.")
                elif admin["role"] == "supervisor" and not admin.get("mentor"):
                    st.error("⚠️ لا يوجد سوبر مشرف مرتبط بهذا المشرف.")
                else:
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

            # تحقق من جدول السوبر آدمن
            cursor.execute("""
                SELECT * FROM super_admins 
                WHERE (username = %s OR full_name = %s) AND password = %s
            """, (username, username, password))

            super_admin = cursor.fetchone()

            if super_admin:
                st.session_state.update({
                    "authenticated": True,
                    "username": super_admin["username"],
                    "full_name": super_admin["full_name"],
                    "permissions": super_admin["role"]
                })
                st.success("✅ تم تسجيل الدخول بنجاح")
                st.switch_page("pages/SuperAdmin.py")
                st.stop()

            # إذا لم يتم التحقق في أي جدول
            st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")

# إعادة توجيه المستخدم إذا كان مسجل دخوله مسبقًا
else:
    if st.session_state["permissions"] == "admin":
        st.switch_page("pages/AdminDashboard.py")
    elif st.session_state["permissions"] in ["supervisor", "sp"]:
        st.switch_page("pages/Supervisor.py")
    elif st.session_state["permissions"] == "super_admin":
        st.switch_page("pages/SuperAdmin.py")
    else:
        st.switch_page("pages/UserDashboard.py")
