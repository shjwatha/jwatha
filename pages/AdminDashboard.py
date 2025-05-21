# ✅ AdminDashboard.py — إدارة المستخدمين (MySQL فقط)
import streamlit as st
import pandas as pd
import pymysql

# إعداد الصفحة
st.set_page_config(page_title="لوحة الإدارة", page_icon="🛠️")
st.title("🛠️ لوحة إدارة المستخدمين")

# التأكد من تسجيل الدخول
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



# 📦 إنشاء 20 مستخدم دفعة واحدة
st.subheader("📦 إنشاء 20 مستخدم دفعة واحدة")

st.markdown("""
    <style>
    .rtl input, .rtl select, .rtl textarea {
        direction: rtl;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)

with st.form("bulk_user_form"):
    full_names, usernames, passwords, mentors = [], [], [], []
    for i in range(1, 21):
        st.markdown(f"#### 👤 المستخدم رقم {i}", unsafe_allow_html=True)
        cols = st.columns(4)
        with cols[0]: full_names.append(st.text_input(f"الاسم الكامل {i}", key=f"full_name_{i}"))
        with cols[1]: usernames.append(st.text_input(f"اسم المستخدم {i}", key=f"username_{i}"))
        with cols[2]: passwords.append(st.text_input(f"كلمة المرور {i}", key=f"password_{i}"))
        with cols[3]: mentors.append(st.text_input(f"اسم المشرف {i}", key=f"mentor_{i}"))

    submit_bulk = st.form_submit_button("💾 حفظ جميع المستخدمين")

    if submit_bulk:
        created_count = 0
        skipped_count = 0
        for i in range(20):
            fn, un, pw, mn = full_names[i].strip(), usernames[i].strip(), passwords[i].strip(), mentors[i].strip()
            if not fn or not un or not pw or not mn:
                continue
            cursor.execute("SELECT * FROM users WHERE username = %s OR full_name = %s", (un, fn))
            if cursor.fetchone():
                st.warning(f"🚫 تم تجاوز '{un}' لأن الاسم أو اسم المستخدم مستخدم من قبل.")
                skipped_count += 1
                continue
            cursor.execute("""
                INSERT INTO users (full_name, username, password, mentor, level)
                VALUES (%s, %s, %s, %s, %s)
            """, (fn, un, pw, mn, admin_level))
            created_count += 1
        conn.commit()
        st.success(f"✅ تم إنشاء {created_count} مستخدم. تم تجاوز {skipped_count} مستخدم (بيانات ناقصة أو مكررة).")
        st.rerun()
