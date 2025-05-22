-- ✅ التبويبات الرئيسية
import streamlit as st
import pymysql
import pandas as pd

st.set_page_config(layout="wide", page_title="لوحة التحكم - SuperAdmin")

# الاتصال بقاعدة البيانات
conn = pymysql.connect(
    host=st.secrets["DB_HOST"],
    port=int(st.secrets["DB_PORT"]),
    user=st.secrets["DB_USER"],
    password=st.secrets["DB_PASSWORD"],
    database=st.secrets["DB_NAME"],
    charset='utf8mb4'
)
cursor = conn.cursor(pymysql.cursors.DictCursor)

# التحقق من تسجيل الدخول
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("🔐 يجب تسجيل الدخول أولاً")
    st.stop()

if st.session_state["permissions"] != "super_admin":
    st.error("🚫 لا تملك صلاحية الوصول إلى هذه الصفحة.")
    st.stop()

st.title("🎛️ لوحة تحكم المدير العام")

# تحميل المستويات من قاعدة البيانات
cursor.execute("SELECT * FROM levels")
levels = cursor.fetchall()

# 🧭 التبويبات
selected_tab = st.radio("📂 اختر القسم", [
    "إدارة الأعضاء",
    "إعداد نموذج التقييم الذاتي",
    "نقاطي (تقييم من المشرف)",
    "نقل المستويات"
], horizontal=True)

# ========== التبويب الأول: إدارة الأعضاء ==========
if selected_tab == "إدارة الأعضاء":
    st.header("👥 إدارة الأعضاء")

    st.markdown("""
    ### 📌 إختر نوع العضو لعرض القائمة:
    """)

    choice = st.selectbox("نوع الأعضاء", ["المستوى", "الآدمن", "السوبر مشرف", "المشرف", "المستخدم"], key="user_filter")

    if choice == "المستوى":
        selected_level = st.selectbox("اختر المستوى", [lvl['level_name'] for lvl in levels], key="view_level")
        cursor.execute("SELECT * FROM admins WHERE level = %s", (selected_level,))
        admins = cursor.fetchall()
        cursor.execute("SELECT * FROM users WHERE level = %s", (selected_level,))
        users = cursor.fetchall()
        st.subheader("🔍 جميع الأعضاء المرتبطين بالمستوى")
        st.dataframe(pd.DataFrame(admins + users))

    elif choice in ["الآدمن", "السوبر مشرف", "المشرف"]:
        role_map = {
            "الآدمن": "admin",
            "السوبر مشرف": "sp",
            "المشرف": "supervisor"
        }
        role = role_map[choice]
        cursor.execute("SELECT * FROM admins WHERE role = %s", (role,))
        admins = cursor.fetchall()
        if admins:
            df = pd.DataFrame(admins)
            st.dataframe(df)
        else:
            st.info("لا يوجد أعضاء في هذا النوع.")

    elif choice == "المستخدم":
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        if users:
            df = pd.DataFrame(users)
            st.dataframe(df)
        else:
            st.info("لا يوجد مستخدمين.")

    # تضمين إضافات الأعضاء هنا (تمّت إضافتها سابقًا في الملف)

    # 🧑‍💼 إضافة آدمن مرتبط بمستوى
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
        username = st.text_input("اسم المستخدم للسوبر مشرف")
        password = st.text_input("كلمة المرور للسوبر مشرف")
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

    # 👨‍💼 إضافة مشرف مباشر مرتبط بسوبر مشرف
    st.subheader("👨‍💼 إضافة مشرف")

    cursor.execute("SELECT username, full_name, level FROM admins WHERE role = 'sp'")
    supervisors = cursor.fetchall()

    if not supervisors:
        st.info("🔸 لا يوجد سوبر مشرفين حالياً.")
    else:
        with st.form("add_supervisor"):
            full_name = st.text_input("اسم المشرف")
            username = st.text_input("اسم المستخدم للمشرف")
            password = st.text_input("كلمة المرور للمشرف")
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

# ========== التبويب الثاني: إعداد نموذج التقييم الذاتي ==========
elif selected_tab == "إعداد نموذج التقييم الذاتي":
    st.header("📝 إعداد نموذج التقييم الذاتي")

    # اختيار أو إنشاء بند جديد
    st.subheader("➕ إضافة بند تقييم")

    with st.form("add_criterion"):
        question = st.text_input("عنوان البند (السؤال)")
        input_type = st.selectbox("نوع الإجابة", ["اختيار واحد", "اختيار متعدد"])
        submitted_q = st.form_submit_button("➕ أضف البند")

        if submitted_q and question:
            cursor.execute(
                "INSERT INTO self_assessment_templates (question, input_type) VALUES (%s, %s)",
                (question, input_type)
            )
            conn.commit()
            st.success("✅ تم إضافة البند")
            st.rerun()

    # جلب البنود الحالية
    cursor.execute("SELECT * FROM self_assessment_templates")
    questions = cursor.fetchall()

    if questions:
        st.subheader("🧩 البنود الحالية")
        for q in questions:
            with st.expander(f"{q['question']} ({q['input_type']})"):
                # عرض الخيارات المرتبطة
                cursor.execute("SELECT * FROM self_assessment_options WHERE question_id = %s", (q["id"],))
                options = cursor.fetchall()
                for opt in options:
                    st.markdown(f"🔘 {opt['option_text']} - {opt['score']} نقطة")

                with st.form(f"add_option_{q['id']}"):
                    option_text = st.text_input("النص", key=f"opt_text_{q['id']}")
                    score = st.number_input("الدرجة", min_value=0, max_value=100, step=1, key=f"opt_score_{q['id']}")
                    submitted_opt = st.form_submit_button("➕ أضف خيار")

                    if submitted_opt and option_text:
                        cursor.execute(
                            "INSERT INTO self_assessment_options (question_id, option_text, score) VALUES (%s, %s, %s)",
                            (q["id"], option_text, score)
                        )
                        conn.commit()
                        st.success("✅ تم إضافة الخيار")
                        st.rerun()
    else:
        st.info("لا توجد بنود تقييم بعد.")


# ========== التبويب الثالث: نقاطي (تقييم من المشرف) ==========
elif selected_tab == "نقاطي (تقييم من المشرف)":
    st.header("🏅 التقييم اليدوي للمستخدمين")

    # جلب المشرفين
    cursor.execute("SELECT username, full_name FROM admins WHERE role = 'supervisor'")
    supervisors = cursor.fetchall()
    if not supervisors:
        st.info("🚫 لا يوجد مشرفين.")
    else:
        selected_supervisor = st.selectbox("اختر المشرف", [f"{s['full_name']} ({s['username']})" for s in supervisors])
        mentor_username = selected_supervisor.split("(")[-1].replace(")", "").strip()

        # جلب المستخدمين المرتبطين به
        cursor.execute("SELECT username, full_name FROM users WHERE mentor = %s", (mentor_username,))
        mentees = cursor.fetchall()
        if not mentees:
            st.info("📭 لا يوجد مستخدمين تحت هذا المشرف.")
        else:
            selected_user = st.selectbox("👤 اختر المستخدم", [f"{m['full_name']} ({m['username']})" for m in mentees])
            user_username = selected_user.split("(")[-1].replace(")", "").strip()

            with st.form("add_score"):
                title = st.text_input("اسم التقييم", placeholder="مثال: سلوك، انضباط، أداء عام")
                score = st.number_input("الدرجة", 0, 100, step=1)
                submit_score = st.form_submit_button("📥 حفظ التقييم")

                if submit_score and title:
                    cursor.execute(
                        "INSERT INTO user_scores (user, score_title, score_value, evaluator, created_at) VALUES (%s, %s, %s, %s, NOW())",
                        (user_username, title, score, mentor_username)
                    )
                    conn.commit()
                    st.success("✅ تم تسجيل التقييم")

    # عرض جميع التقييمات
    st.subheader("📊 جميع التقييمات المسجلة")
    cursor.execute("SELECT * FROM user_scores ORDER BY created_at DESC")
    scores = cursor.fetchall()
    if scores:
        df = pd.DataFrame(scores)
        df.columns = ["المعرف", "المستخدم", "عنوان التقييم", "الدرجة", "المُقيّم", "تاريخ التقييم"]
        st.dataframe(df)
    else:
        st.info("لا توجد تقييمات بعد.")


# ========== التبويب الرابع: نقل المستويات ==========
elif selected_tab == "نقل المستويات":
    st.header("🔄 إدارة وربط المستويات")

    action = st.selectbox("اختر العملية", ["نقل سوبر مشرف إلى مستوى", "نقل مشرف إلى سوبر مشرف", "نقل مستخدم إلى مشرف"])

    if action == "نقل سوبر مشرف إلى مستوى":
        cursor.execute("SELECT username, full_name FROM admins WHERE role = 'sp'")
        sps = cursor.fetchall()
        if not sps:
            st.warning("لا يوجد سوبر مشرفين.")
        else:
            selected_sp = st.selectbox("اختر السوبر مشرف", [f"{s['full_name']} ({s['username']})" for s in sps])
            sp_username = selected_sp.split("(")[-1].replace(")", "").strip()
            level = st.selectbox("اختر المستوى الجديد", [lvl['level_name'] for lvl in levels])
            if st.button("🔁 نقل"):
                cursor.execute("UPDATE admins SET level = %s WHERE username = %s", (level, sp_username))
                cursor.execute("UPDATE admins SET level = %s WHERE mentor = %s", (level, sp_username))  # تحديث المشرفين
                cursor.execute("UPDATE users SET level = %s WHERE mentor IN (SELECT username FROM admins WHERE mentor = %s)", (level, sp_username))  # تحديث المستخدمين
                conn.commit()
                st.success("✅ تم نقل السوبر مشرف والمشرفين والمستخدمين")

    elif action == "نقل مشرف إلى سوبر مشرف":
        cursor.execute("SELECT username, full_name FROM admins WHERE role = 'supervisor'")
        supervisors = cursor.fetchall()
        cursor.execute("SELECT username, full_name FROM admins WHERE role = 'sp'")
        sps = cursor.fetchall()

        if not supervisors or not sps:
            st.warning("تأكد من وجود مشرفين وسوبر مشرفين.")
        else:
            selected_sup = st.selectbox("اختر المشرف", [f"{s['full_name']} ({s['username']})" for s in supervisors])
            sup_username = selected_sup.split("(")[-1].replace(")", "").strip()
            selected_sp = st.selectbox("اختر السوبر مشرف الجديد", [f"{s['full_name']} ({s['username']})" for s in sps])
            sp_username = selected_sp.split("(")[-1].replace(")", "").strip()
            sp_level = next((s['level'] for s in sps if s['username'] == sp_username), None)

            if st.button("🔁 نقل المشرف"):
                cursor.execute("UPDATE admins SET mentor = %s, level = %s WHERE username = %s", (sp_username, sp_level, sup_username))
                cursor.execute("UPDATE users SET level = %s WHERE mentor = %s", (sp_level, sup_username))
                conn.commit()
                st.success("✅ تم نقل المشرف والمستخدمين التابعين له")

    elif action == "نقل مستخدم إلى مشرف":
        cursor.execute("SELECT username, full_name FROM users")
        users = cursor.fetchall()
        cursor.execute("SELECT username, full_name, level FROM admins WHERE role = 'supervisor'")
        supervisors = cursor.fetchall()

        if not users or not supervisors:
            st.warning("تأكد من وجود مستخدمين ومشرفين.")
        else:
            selected_user = st.selectbox("اختر المستخدم", [f"{u['full_name']} ({u['username']})" for u in users])
            user_username = selected_user.split("(")[-1].replace(")", "").strip()
            selected_sup = st.selectbox("اختر المشرف الجديد", [f"{s['full_name']} ({s['username']})" for s in supervisors])
            sup_username = selected_sup.split("(")[-1].replace(")", "").strip()
            sup_level = next((s['level'] for s in supervisors if s['username'] == sup_username), None)

            if st.button("🔁 نقل المستخدم"):
                cursor.execute("UPDATE users SET mentor = %s, level = %s WHERE username = %s", (sup_username, sup_level, user_username))
                conn.commit()
                st.success("✅ تم نقل المستخدم")
# ========== ختامي ==========
# إغلاق الاتصال بقاعدة البيانات
cursor.close()
conn.close()

st.caption("تم تطوير هذه اللوحة لإدارة هيكلية البرنامج بشكل كامل بواسطة المدير العام.")
