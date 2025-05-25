import streamlit as st
import pymysql
import pandas as pd

st.set_page_config(page_title="لوحة آدمن المستوى", page_icon="🛠️")

# تحقق من الجلسة
if "authenticated" not in st.session_state or st.session_state["permissions"] != "admin":
    st.error("❌ لا تملك صلاحية الوصول إلى هذه الصفحة.")
    st.stop()

admin_level = st.session_state["level"]




# الاتصال بقاعدة بيانات MySQL
conn = pymysql.connect(
    host=st.secrets["DB_HOST"],
    port=int(st.secrets["DB_PORT"]),
    user=st.secrets["DB_USER"],
    password=st.secrets["DB_PASSWORD"],
    database=st.secrets["DB_NAME"],
    charset="utf8mb4"
)
cursor = conn.cursor(pymysql.cursors.DictCursor)

# تحميل المستخدمين في نفس المستوى
cursor.execute("SELECT * FROM users WHERE level = %s AND is_deleted = 0", (admin_level,))
users = cursor.fetchall()
users_df = pd.DataFrame(users)

# تحميل المشرفين (الذين لديهم role = 'supervisor') في نفس المستوى
cursor.execute("SELECT username FROM admins WHERE role = 'supervisor' AND level = %s AND is_deleted = 0", (admin_level,))
mentor_options = [row["username"] for row in cursor.fetchall()]

# تحميل كل المستخدمين والأدمن للتحقق من التكرار
cursor.execute("SELECT username, full_name FROM users WHERE is_deleted = 0")
all_users = cursor.fetchall()
cursor.execute("SELECT username, full_name FROM admins WHERE is_deleted = 0")
all_admins = cursor.fetchall()
all_existing_names = set()
for entry in all_users + all_admins:
    all_existing_names.add(entry["username"])
    all_existing_names.add(entry["full_name"])

# العنوان الرئيسي
st.title(f"🛠️ لوحة آدمن - مستوى {admin_level}")

# إنشاء التبويبات
tabs = st.tabs(["➕ إضافة مستخدم", "✏️ تعديل مستخدم", "📥 إضافة 20 مستخدم دفعة واحدة"])

# ===================== التبويب الأول: إضافة مستخدم =====================
with tabs[0]:
    st.subheader("➕ إضافة مستخدم جديد")

    with st.form("add_user_form"):
        username = st.text_input("اسم المستخدم")
        full_name = st.text_input("الاسم الكامل")
        password = st.text_input("كلمة المرور", type="password")
        mentor = st.selectbox("المشرف", mentor_options)
        submit = st.form_submit_button("إضافة")

        if submit:
            if not all([full_name.strip(), username.strip(), password.strip(), mentor.strip()]):
                st.warning("⚠️ جميع الحقول مطلوبة.")
            elif full_name in all_existing_names or username in all_existing_names:
                st.error("❌ لا يمكن أن يتطابق الاسم الكامل مع اسم مستخدم أو العكس.")
            else:
                cursor.execute("""
                    INSERT INTO users (full_name, username, password, mentor, level)
                    VALUES (%s, %s, %s, %s, %s)
                """, (full_name.strip(), username.strip(), password.strip(), mentor.strip(), admin_level))
                conn.commit()
                st.success("✅ تم إضافة المستخدم بنجاح.")
                st.rerun()

# ===================== التبويب الثاني: تعديل المستخدمين =====================
with tabs[1]:
    st.subheader("✏️ تعديل بيانات المستخدمين")

    if users_df.empty:
        st.info("لا يوجد مستخدمون في هذا المستوى.")
    else:
        selected_user = st.selectbox("اختر مستخدمًا", users_df["username"])
        selected_user_data = users_df[users_df["username"] == selected_user].iloc[0]

        new_username = st.text_input("اسم المستخدم", value=selected_user_data["username"])
        new_full_name = st.text_input("الاسم الكامل", value=selected_user_data["full_name"])
        new_password = st.text_input("كلمة المرور الجديدة (اختياري)", type="password")

        if st.button("💾 حفظ التعديلات"):
            conflict = False
            if new_full_name != selected_user_data["full_name"] and new_full_name in all_existing_names:
                conflict = True
            if new_username != selected_user_data["username"] and new_username in all_existing_names:
                conflict = True

            if conflict:
                st.error("❌ لا يمكن أن يتطابق الاسم الكامل مع اسم مستخدم أو العكس.")
            else:
                cursor.execute("""
                    UPDATE users
                    SET full_name = %s, username = %s
                    WHERE id = %s
                """, (new_full_name, new_username, selected_user_data["id"]))

                if new_password:
                    cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_password, selected_user_data["id"]))

                conn.commit()
                st.success("✅ تم تحديث بيانات المستخدم.")
                st.rerun()
# ===================== التبويب الثالث: إضافة 20 مستخدم دفعة واحدة =====================
with tabs[2]:
    st.subheader("📥 إضافة 20 مستخدم دفعة واحدة")

    st.markdown("أدخل بيانات كل مستخدم في صف خاص به.")

    if "bulk_reset" not in st.session_state:
        for i in range(20):
            st.session_state[f"username_{i}"] = ""
            st.session_state[f"fullname_{i}"] = ""
            st.session_state[f"password_{i}"] = ""

    bulk_data = []
    for i in range(20):
        st.markdown(f"#### 👤 المستخدم رقم {i+1}")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            username = st.text_input(f"اسم المستخدم {i+1}", key=f"username_{i}")
        with col2:
            full_name = st.text_input(f"الاسم الكامل {i+1}", key=f"fullname_{i}")
        with col3:
            password = st.text_input(f"كلمة المرور {i+1}", type="password", key=f"password_{i}")
        with col4:
            mentor = st.selectbox(f"المشرف {i+1}", mentor_options, key=f"mentor_{i}")

        bulk_data.append({
            "username": username.strip(),
            "full_name": full_name.strip(),
            "password": password.strip(),
            "mentor": mentor.strip()
        })

    if st.button("🚀 إضافة المستخدمين دفعة واحدة"):
        success_count = 0
        errors = []

        for i, user in enumerate(bulk_data, start=1):
            username = user["username"]
            full_name = user["full_name"]
            password = user["password"]
            mentor = user["mentor"]

            if not all([username, full_name, password, mentor]):
                errors.append(f"المستخدم {i}: جميع الحقول مطلوبة")
                continue

            if username in all_existing_names or full_name in all_existing_names:
                errors.append(f"المستخدم {i}: الاسم الكامل أو اسم المستخدم مستخدم مسبقًا")
                continue

            try:
                cursor.execute("""
                    INSERT INTO users (full_name, username, password, mentor, level)
                    VALUES (%s, %s, %s, %s, %s)
                """, (full_name, username, password, mentor, admin_level))
                conn.commit()
                all_existing_names.update([username, full_name])
                success_count += 1
            except Exception as e:
                errors.append(f"المستخدم {i}: خطأ أثناء الإدخال - {str(e)}")

        st.success(f"✅ تم إضافة {success_count} مستخدم بنجاح.")
        if errors:
            st.error("\n".join(errors))

        # تفريغ الحقول بعد الإضافة
        for i in range(20):
            st.session_state[f"username_{i}"] = ""
            st.session_state[f"fullname_{i}"] = ""
            st.session_state[f"password_{i}"] = ""
