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

# 🧾 عرض قائمة الأعضاء حسب النوع مع خيار الحذف
st.subheader("👥 قائمة الأعضاء")
عرض_حسب = st.selectbox("📌 اختر نوع العرض", ["المستوى", "الآدمن", "السوبر مشرف", "المشرف", "المستخدم"])

if عرض_حسب == "المستوى":
    المستويات = [lvl['level_name'] for lvl in levels]
    مستوى_مختار = st.selectbox("🎯 اختر المستوى", المستويات)
    cursor.execute("SELECT full_name, username, role FROM admins WHERE level = %s UNION SELECT full_name, username, role FROM users WHERE level = %s", (مستوى_مختار, مستوى_مختار))
    members = cursor.fetchall()
    if members:
        df = pd.DataFrame(members)
        df.columns = ["الاسم الكامل", "اسم المستخدم", "الدور"]
        selected_user = st.selectbox("اختر مستخدم لحذفه", df["اسم المستخدم"]) if not df.empty else None
        if st.button("🗑️ حذف المستخدم") and selected_user:
            table = "admins" if any(m['username'] == selected_user and m['role'] != 'user' for m in members) else "users"
            cursor.execute(f"DELETE FROM {table} WHERE username = %s", (selected_user,))
            conn.commit()
            st.success(f"✅ تم حذف المستخدم: {selected_user}")
            st.rerun()
        st.dataframe(df)
    else:
        st.info("لا يوجد أعضاء في هذا المستوى.")

elif عرض_حسب == "الآدمن":
    cursor.execute("SELECT full_name, username, level FROM admins WHERE role = 'admin'")
    admins = cursor.fetchall()
    if admins:
        df = pd.DataFrame(admins)
        df.columns = ["الاسم الكامل", "اسم المستخدم", "المستوى"]
        selected_user = st.selectbox("اختر آدمن لحذفه", df["اسم المستخدم"]) if not df.empty else None
        if st.button("🗑️ حذف الآدمن") and selected_user:
            cursor.execute("DELETE FROM admins WHERE username = %s", (selected_user,))
            conn.commit()
            st.success(f"✅ تم حذف الآدمن: {selected_user}")
            st.rerun()
        st.dataframe(df)
    else:
        st.info("لا يوجد آدمن حالياً.")

elif عرض_حسب == "السوبر مشرف":
    cursor.execute("SELECT full_name, username, level FROM admins WHERE role = 'sp'")
    sps = cursor.fetchall()
    if sps:
        df = pd.DataFrame(sps)
        df.columns = ["الاسم الكامل", "اسم المستخدم", "المستوى"]
        selected_user = st.selectbox("اختر سوبر مشرف لحذفه", df["اسم المستخدم"]) if not df.empty else None
        if st.button("🗑️ حذف السوبر مشرف") and selected_user:
            cursor.execute("DELETE FROM admins WHERE username = %s", (selected_user,))
            conn.commit()
            st.success(f"✅ تم حذف السوبر مشرف: {selected_user}")
            st.rerun()
        st.dataframe(df)
    else:
        st.info("لا يوجد سوبر مشرفين.")

elif عرض_حسب == "المشرف":
    cursor.execute("SELECT full_name, username, mentor, level FROM admins WHERE role = 'supervisor'")
    supervisors = cursor.fetchall()
    if supervisors:
        df = pd.DataFrame(supervisors)
        df.columns = ["الاسم الكامل", "اسم المستخدم", "السوبر مشرف", "المستوى"]
        selected_user = st.selectbox("اختر مشرف لحذفه", df["اسم المستخدم"]) if not df.empty else None
        if st.button("🗑️ حذف المشرف") and selected_user:
            cursor.execute("DELETE FROM admins WHERE username = %s", (selected_user,))
            conn.commit()
            st.success(f"✅ تم حذف المشرف: {selected_user}")
            st.rerun()
        st.dataframe(df)
    else:
        st.info("لا يوجد مشرفين.")

elif عرض_حسب == "المستخدم":
    cursor.execute("SELECT full_name, username, mentor, level FROM users")
    users = cursor.fetchall()
    if users:
        df = pd.DataFrame(users)
        df.columns = ["الاسم الكامل", "اسم المستخدم", "المشرف", "المستوى"]
        selected_user = st.selectbox("اختر مستخدم لحذفه", df["اسم المستخدم"]) if not df.empty else None
        if st.button("🗑️ حذف المستخدم") and selected_user:
            cursor.execute("DELETE FROM users WHERE username = %s", (selected_user,))
            conn.commit()
            st.success(f"✅ تم حذف المستخدم: {selected_user}")
            st.rerun()
        st.dataframe(df)
    else:
        st.info("لا يوجد مستخدمين.")
