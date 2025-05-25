import streamlit as st
import pymysql
import pandas as pd

# ===== التحقق من تسجيل الدخول =====
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("🔐 يجب تسجيل الدخول أولاً")
    st.switch_page("home.py")

# ===== إعداد صفحة Streamlit =====
st.set_page_config(layout="wide", page_title="⚙️ إعدادات المستخدم")

# ===== الاتصال بقاعدة بيانات MySQL =====
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

# ===== جلب بيانات المستخدم =====
username = st.session_state.get("username")
full_name = st.session_state.get("full_name")
permissions = st.session_state.get("permissions")

if permissions not in ["user", "admin", "supervisor", "sp"]:
    st.error("🚫 لا تملك صلاحية الوصول لهذه الصفحة.")
    st.stop()

# ===== تحديد الجدول حسب الصلاحية =====
table_name = "users" if permissions == "user" else "admins"

cursor.execute(f"SELECT * FROM {table_name} WHERE username = %s AND is_deleted = 0", (username,))
user_row = cursor.fetchone()

if not user_row:
    st.error("⚠️ لم يتم العثور على المستخدم.")
    st.stop()

# ===== عرض العنوان =====
st.title(f"👋 أهلاً {full_name}")

# ===== تغيير كلمة المرور =====
st.subheader("🔒 تغيير كلمة المرور")
with st.form("change_password_form"):
    current_pass = st.text_input("كلمة المرور الحالية", type="password")
    new_pass = st.text_input("كلمة المرور الجديدة", type="password")
    confirm_pass = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
    submit_pass = st.form_submit_button("تحديث كلمة المرور")

    if submit_pass:
        actual_pass = user_row["password"]

        if current_pass != actual_pass:
            st.error("❌ كلمة المرور الحالية غير صحيحة.")
        elif new_pass != confirm_pass:
            st.error("❌ كلمة المرور الجديدة وتأكيدها غير متطابقتين.")
        elif len(new_pass) < 6:
            st.error("❌ يجب أن تكون كلمة المرور الجديدة مكونة من 6 أحرف على الأقل.")
        elif new_pass == "":
            st.error("❌ لا يمكن أن تكون كلمة المرور فارغة.")
        else:
            try:
                cursor.execute(f"UPDATE {table_name} SET password = %s WHERE username = %s", (new_pass, username))
                conn.commit()
                st.success("✅ تم تحديث كلمة المرور بنجاح.")
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء التحديث: {e}")
