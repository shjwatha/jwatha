# ✅ AdminDashboard.py — إدارة المستخدمين (MySQL فقط)
import streamlit as st
import pandas as pd
import pymysql

# إعداد الصفحة
st.set_page_config(page_title="لوحة الإدارة", page_icon="🛠️", layout="wide")
st.title("🛠️ لوحة إدارة المستخدمين")

# التحقق من الجلسة
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("⚠️ يجب تسجيل الدخول أولًا.")
    st.stop()

if st.session_state["permissions"] != "admin":
    st.error("🚫 لا تملك الصلاحية للوصول إلى هذه الصفحة.")
    st.stop()

admin_username = st.session_state["username"]
admin_level = st.session_state["level"]

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
    st.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
    st.stop()

# 🔄 زر تحديث البيانات
if st.button("🔄 تحديث البيانات"):
    st.rerun()


# جلب جميع المستخدمين من نفس المستوى
cursor.execute("SELECT * FROM users WHERE level = %s", (admin_level,))
users_data = cursor.fetchall()
users_df = pd.DataFrame(users_data)

st.subheader(f"📋 قائمة المستخدمين في المستوى {admin_level}")
if users_df.empty:
    st.info("لا يوجد مستخدمون بعد.")
else:
    display_df = users_df[["full_name", "username", "mentor"]]
    display_df.columns = ["الاسم الكامل", "اسم المستخدم", "المشرف"]
    st.dataframe(display_df, use_container_width=True)

st.subheader("➕ إنشاء حساب جديد")

with st.form("create_user_form"):
    full_name = st.text_input("الاسم الكامل")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور")
    mentor = st.text_input("اسم المشرف")
    submitted = st.form_submit_button("إنشاء")

    if submitted:
        if not full_name or not username or not password or not mentor:
            st.warning("⚠️ يرجى تعبئة جميع الحقول.")
        else:
            cursor.execute("SELECT * FROM users WHERE username = %s OR full_name = %s", (username, full_name))
            exists_user = cursor.fetchone()

            if exists_user:
                st.error("❌ الاسم الكامل أو اسم المستخدم مستخدم من قبل.")
            else:
                try:
                    cursor.execute("""
                        INSERT INTO users (full_name, username, password, mentor, level)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (full_name.strip(), username.strip(), password.strip(), mentor.strip(), admin_level))
                    conn.commit()
                    st.success("✅ تم إنشاء المستخدم بنجاح.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء إنشاء المستخدم: {e}")

# 🗑️ حذف مستخدم موجود
st.subheader("🗑️ حذف مستخدم")
if not users_df.empty:
    selected_user = st.selectbox("اختر مستخدمًا للحذف:", users_df["username"])
    if st.button("❌ حذف المستخدم"):
        try:
            cursor.execute("DELETE FROM users WHERE username = %s AND level = %s", (selected_user, admin_level))
            conn.commit()
            st.success("✅ تم حذف المستخدم.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ لم يتم الحذف: {e}")

# ➕ إنشاء 20 مستخدم دفعة واحدة
st.subheader("📦 إنشاء 20 مستخدم دفعة واحدة")
with st.form("bulk_create_form"):
    base_name = st.text_input("اسم الأساس (سيتم توليد الأسماء تلقائيًا مثل user1, user2,...)")
    base_password = st.text_input("كلمة المرور الموحدة")
    base_mentor = st.text_input("المشرف")
    submitted_bulk = st.form_submit_button("إنشاء الدفعة")

    if submitted_bulk:
        if not base_name or not base_password or not base_mentor:
            st.warning("⚠️ يرجى تعبئة جميع الحقول.")
        else:
            try:
                for i in range(1, 21):
                    uname = f"{base_name}{i}"
                    fname = f"{base_name} رقم {i}"
                    cursor.execute("SELECT * FROM users WHERE username = %s", (uname,))
                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO users (full_name, username, password, mentor, level)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (fname, uname, base_password, base_mentor, admin_level))
                conn.commit()
                st.success("✅ تم إنشاء 20 مستخدم بنجاح.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ فشل إنشاء المستخدمين: {e}")
