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

    admins, users = [], []

    if choice == "المستوى":
        selected_level = st.selectbox("اختر المستوى", [lvl['level_name'] for lvl in levels], key="view_level")
        cursor.execute("SELECT * FROM admins WHERE level = %s AND is_deleted = FALSE", (selected_level,))
        admins = cursor.fetchall()
        cursor.execute("SELECT * FROM users WHERE level = %s AND is_deleted = FALSE", (selected_level,))
        users = cursor.fetchall()

    elif choice in ["الآدمن", "السوبر مشرف", "المشرف"]:
        role_map = {
            "الآدمن": "admin",
            "السوبر مشرف": "sp",
            "المشرف": "supervisor"
        }
        role = role_map[choice]
        cursor.execute("SELECT * FROM admins WHERE role = %s AND is_deleted = FALSE", (role,))
        admins = cursor.fetchall()

    elif choice == "المستخدم":
        cursor.execute("SELECT * FROM users WHERE is_deleted = FALSE")
        users = cursor.fetchall()

    # عرض الجداول مع أدوات التحكم
    if admins:
        st.subheader("👨‍💼 الإداريون")
        for admin in admins:
            with st.expander(f"👤 {admin['full_name']} - {admin['username']} ({admin['role']})"):
                st.markdown(f"المستوى: {admin['level']}")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(f"📝 تعديل {admin['username']}", key=f"edit_admin_{admin['id']}"):
                        new_full_name = st.text_input("الاسم الكامل", value=admin['full_name'])
                        level_names = [lvl['level_name'] for lvl in levels]
                        new_level = st.selectbox("المستوى", level_names, index=level_names.index(admin['level']) if admin['level'] in level_names else 0)
                        role_names = ["admin", "sp", "supervisor"]
                        new_role = st.selectbox("الدور", role_names, index=role_names.index(admin['role']) if admin['role'] in role_names else 0)
                        if st.button(f"تحديث"):
                            cursor.execute("UPDATE admins SET full_name = %s, level = %s, role = %s WHERE id = %s", (new_full_name, new_level, new_role, admin['id']))
                            conn.commit()
                            st.success("✅ تم التحديث")
                            st.rerun()
                with col2:
                    if st.button(f"🗑️ حذف {admin['username']}", key=f"delete_admin_{admin['id']}"):
                        cursor.execute("UPDATE admins SET is_deleted = TRUE WHERE id = %s", (admin['id'],))
                        conn.commit()
                        st.success("✅ تم حذف الإداري")
                        st.rerun()

    if users:
        st.subheader("👥 المستخدمون")
        for user in users:
            with st.expander(f"👤 {user['full_name']} - {user['username']}"):
                st.markdown(f"المستوى: {user['level']} | المشرف: {user['mentor']}")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(f"📝 تعديل {user['username']}", key=f"edit_user_{user['id']}"):
                        new_full_name = st.text_input("الاسم الكامل", value=user['full_name'])
                        level_names = [lvl['level_name'] for lvl in levels]
                        new_level = st.selectbox("المستوى", level_names, index=level_names.index(user['level']) if user['level'] in level_names else 0)
                        new_mentor = st.selectbox("المشرف", [user['mentor'] for user in users])
                        if st.button(f"تحديث"):
                            cursor.execute("UPDATE users SET full_name = %s, level = %s, mentor = %s WHERE id = %s", (new_full_name, new_level, new_mentor, user['id']))
                            conn.commit()
                            st.success("✅ تم التحديث")
                            st.rerun()
                with col2:
                    if st.button(f"🗑️ حذف {user['username']}", key=f"delete_user_{user['id']}"):
                        cursor.execute("UPDATE users SET is_deleted = TRUE WHERE id = %s", (user['id'],))
                        conn.commit()
                        st.success("✅ تم حذف المستخدم")
                        st.rerun()

    # 🧑‍💼 إضافة آدمن مرتبط بمستوى
    st.subheader("🧑‍💼 إضافة مدير للمستوى")
    with st.form("add_admin"):
        full_name = st.text_input("الاسم الكامل للآدمن")
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
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

    # 👨‍🏫 إضافة سوبر مشرف
    st.subheader("👨‍🏫 إضافة سوبر مشرف")
    with st.form("add_sp"):
        full_name = st.text_input("الاسم الكامل للسوبر مشرف")
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
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

    # 👨‍💼 إضافة مشرف مرتبط بسوبر مشرف
    st.subheader("👨‍💼 إضافة مشرف")
    cursor.execute("SELECT username, full_name, level FROM admins WHERE role = 'sp' AND is_deleted = FALSE")
    supervisors = cursor.fetchall()
    if not supervisors:
        st.info("🔸 لا يوجد سوبر مشرفين حالياً.")
    else:
        with st.form("add_supervisor"):
            full_name = st.text_input("اسم المشرف")
            username = st.text_input("اسم المستخدم للمشرف")
            password = st.text_input("كلمة المرور للمشرف", type="password")
            selected_sp = st.selectbox("اختر سوبر مشرف", [f"{s['full_name']} ({s['username']})" for s in supervisors])
            sp_username = selected_sp.split("(")[-1].replace(")", "").strip()
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



# ===================== تبويب 2: إدارة النماذج والأسئلة =====================
elif selected_tab == "إعداد نموذج التقييم الذاتي":
    st.header("📋 إدارة استمارات التقييم الذاتي")

    # اختيار المستوى
    cursor.execute("SELECT DISTINCT level_name FROM levels")
    levels = [row["level_name"] for row in cursor.fetchall()]
    selected_level = st.selectbox("📚 اختر المستوى", levels)

    # اختيار النموذج
    cursor.execute("SELECT DISTINCT form_name FROM self_assessment_templates WHERE level = %s", (selected_level,))
    forms = [row["form_name"] for row in cursor.fetchall() if row["form_name"]]
    form_display = ["➕ نموذج جديد"] + forms
    selected_form = st.selectbox("🗂️ اختر النموذج", form_display)

    if selected_form == "➕ نموذج جديد":
        new_form = st.text_input("📝 اسم النموذج الجديد")
        if new_form:
            selected_form = new_form

    if selected_form and selected_form != "➕ نموذج جديد":
        st.markdown(f"#### 🧾 النموذج: {selected_form}")

        # عرض الأسئلة الموجودة
        cursor.execute("SELECT id, question, input_type FROM self_assessment_templates WHERE level = %s AND form_name = %s AND is_deleted = 0", (selected_level, selected_form))
        questions = cursor.fetchall()

        for q in questions:
            with st.expander(f"❓ {q['question']}"):
                # تعديل السؤال
                updated_text = st.text_input("🔧 تعديل نص السؤال", value=q['question'], key=f"edit_q_{q['id']}")
                updated_type = st.selectbox("🔄 نوع السؤال", ["radio", "checkbox", "text", "select"], index=["radio", "checkbox", "text", "select"].index(q["input_type"]), key=f"edit_type_{q['id']}")

                options = []
                if updated_type in ["radio", "checkbox", "select"]:
                    cursor.execute("SELECT id, option_text, score FROM self_assessment_options WHERE question_id = %s AND is_deleted = 0", (q["id"],))
                    opts = cursor.fetchall()
                    for i, opt in enumerate(opts):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        opt_text = col1.text_input("الخيار", value=opt["option_text"], key=f"opt_text_{opt['id']}")
                        opt_score = col2.number_input("الدرجة", value=opt["score"], min_value=0, max_value=100, key=f"opt_score_{opt['id']}")
                        delete_opt = col3.checkbox("🗑️ حذف", key=f"delete_opt_{opt['id']}")
                        options.append((opt["id"], opt_text, opt_score, delete_opt))
                elif updated_type == "text":
                    st.info("✏️ هذا السؤال يقبل إجابة نصية من المستخدم (بحد أقصى 200 حرف).")

                if st.button("💾 تحديث السؤال", key=f"save_q_{q['id']}"):
                    cursor.execute("UPDATE self_assessment_templates SET question = %s, input_type = %s WHERE id = %s", (updated_text, updated_type, q["id"]))
                    for oid, otxt, oscore, delete_flag in options:
                        if delete_flag:
                            cursor.execute("UPDATE self_assessment_options SET is_deleted = 1 WHERE id = %s", (oid,))
                        else:
                            cursor.execute("UPDATE self_assessment_options SET option_text = %s, score = %s WHERE id = %s", (otxt, oscore, oid))
                    conn.commit()
                    st.success("✅ تم تحديث السؤال والخيارات.")

                if st.button("🗑️ حذف السؤال نهائيًا", key=f"delete_q_{q['id']}"):
                    cursor.execute("UPDATE self_assessment_templates SET is_deleted = 1 WHERE id = %s", (q["id"],))
                    cursor.execute("UPDATE self_assessment_options SET is_deleted = 1 WHERE question_id = %s", (q["id"],))
                    conn.commit()
                    st.success("❌ تم حذف السؤال.")
                    st.rerun()

        # إضافة سؤال جديد
        st.markdown("---")
        st.markdown("### ➕ إضافة سؤال جديد")
        new_question = st.text_input("🧾 نص السؤال الجديد")
        new_input_type = st.selectbox("🔘 نوع السؤال", ["radio", "checkbox", "text", "select"], key="new_q_type")

        new_options = []
        if new_input_type in ["radio", "checkbox", "select"]:
            num_new_opts = st.number_input("📊 عدد الخيارات", min_value=2, max_value=10, step=1, key="new_num_opts")
            for i in range(int(num_new_opts)):
                col1, col2 = st.columns([3, 1])
                opt_text = col1.text_input(f"الخيار {i+1}", key=f"new_opt_text_{i}")
                opt_score = col2.number_input(f"الدرجة {i+1}", min_value=0, max_value=100, key=f"new_opt_score_{i}")
                new_options.append((opt_text, opt_score))
        elif new_input_type == "text":
            st.info("✏️ هذا السؤال سيُعرض للمستخدم كنص حر (إجابة لا تتجاوز 200 حرف).")

        if st.button("✅ حفظ السؤال الجديد"):
            if new_question.strip():
                cursor.execute(
                    "INSERT INTO self_assessment_templates (question, input_type, level, form_name, is_deleted) VALUES (%s, %s, %s, %s, 0)",
                    (new_question.strip(), new_input_type, selected_level, selected_form)
                )
                qid = cursor.lastrowid
                if new_input_type in ["radio", "checkbox", "select"]:
                    for txt, score in new_options:
                        if txt.strip():
                            cursor.execute(
                                "INSERT INTO self_assessment_options (question_id, option_text, score, is_deleted) VALUES (%s, %s, %s, 0)",
                                (qid, txt.strip(), score)
                            )
                conn.commit()
                st.success("✅ تم حفظ السؤال الجديد.")

                for key in list(st.session_state.keys()):
                    if key.startswith("new_"):
                        del st.session_state[key]

                st.rerun()
            else:
                st.warning("⚠️ يرجى إدخال نص السؤال.")
        
# ===== تبويب 3: تجميعي الكل =====
with tabs[2]:
    st.subheader("📋 تجميع درجات الكل")
    col1, col2 = st.columns(2)
    with col1:
        start_date_all = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_all")
    with col2:
        end_date_all = st.date_input("إلى تاريخ", datetime.today().date(), key="end_all")

    try:
        cursor.execute("""
            SELECT student, question, score
            FROM daily_evaluations
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start_date_all, end_date_all))
        df = pd.DataFrame(cursor.fetchall())

        if df.empty:
            st.info("ℹ️ لا توجد بيانات خلال الفترة المحددة.")
        else:
            # تحميل البنود لمعرفة هل كل بند قابل للعرض أم لا
            cursor.execute("SELECT question, is_visible_to_user FROM supervisor_criteria")
            visibility_map = {row['question']: row['is_visible_to_user'] for row in cursor.fetchall()}

            # حذف البنود غير القابلة للعرض إن وجدت
            df = df[df['question'].isin(visibility_map)]

            pivoted = df.pivot_table(index="student", columns="question", values="score", aggfunc='sum').fillna(0)
            pivoted = pivoted.reindex(my_users, fill_value=0)

            # إضافة عمود يوضّح هل هذا البند مرئي للمستخدم أم لا
            renamed_cols = {q: f"{q} (عرض للمستخدم: {'نعم' if visibility_map[q] else 'لا'})" for q in pivoted.columns}
            pivoted.rename(columns=renamed_cols, inplace=True)

            pivoted["📊 المجموع"] = pivoted.sum(axis=1)
            st.dataframe(pivoted.reset_index(), use_container_width=True)
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")

# ===== تبويب 4: تجميعي بند =====
with tabs[3]:
    st.subheader("📌 تجميع حسب بند معين")
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_criteria")
    with col2:
        end = st.date_input("إلى تاريخ", datetime.today().date(), key="end_criteria")

    try:
        cursor.execute("""
            SELECT student, question, score
            FROM daily_evaluations
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start, end))
        df = pd.DataFrame(cursor.fetchall())

        if df.empty:
            st.info("ℹ️ لا توجد بيانات خلال الفترة المحددة.")
        else:
            available_questions = df["question"].unique().tolist()
            selected_q = st.selectbox("اختر البند", available_questions)

            df_q = df[df["question"] == selected_q].groupby("student")["score"].sum()
            df_q = df_q.reindex(my_users, fill_value=0)
            st.dataframe(df_q.reset_index().rename(columns={"student": "الطالب", "score": "📊 المجموع"}))
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")

# ===== تبويب 5: تقرير فردي =====
with tabs[4]:
    st.subheader("🧍‍♂️ تقرير مستخدم محدد")
    col1, col2 = st.columns(2)
    with col1:
        start_ind = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_ind")
    with col2:
        end_ind = st.date_input("إلى تاريخ", datetime.today().date(), key="end_ind")

    try:
        cursor.execute("""
            SELECT student, DATE(timestamp) AS التاريخ, question AS البند, score AS الدرجة, free_text AS "إجابة نصية"
            FROM daily_evaluations
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start_ind, end_ind))
        df = pd.DataFrame(cursor.fetchall())

        if df.empty:
            st.info("ℹ️ لا توجد بيانات خلال الفترة المحددة.")
        else:
            available_students = df["student"].unique().tolist()
            selected_student = st.selectbox("اختر المستخدم", available_students)
            user_data = df[df["student"] == selected_student]
            st.dataframe(user_data.reset_index(drop=True))
    except Exception as e:
        st.error(f"❌ فشل في تحميل البيانات: {e}")

# ===== تبويب 6: رسوم بيانية =====
with tabs[5]:
    st.subheader("📈 توزيع المجموع")
    col1, col2 = st.columns(2)
    with col1:
        start_chart = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_chart")
    with col2:
        end_chart = st.date_input("إلى تاريخ", datetime.today().date(), key="end_chart")

    try:
        cursor.execute("""
            SELECT student, score
            FROM daily_evaluations
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start_chart, end_chart))
        df = pd.DataFrame(cursor.fetchall())

        if df.empty:
            st.info("ℹ️ لا توجد بيانات خلال هذه الفترة.")
        else:
            grouped = df.groupby("student")["score"].sum()
            grouped = grouped.reindex(my_users, fill_value=0)
            fig = go.Figure(go.Pie(
                labels=grouped.index,
                values=grouped.values,
                hole=0.4,
                title="توزيع النقاط"
            ))
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"❌ فشل في تحميل أو عرض البيانات: {e}")

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
                cursor.execute("UPDATE admins SET level = %s WHERE mentor = %s", (level, sp_username))
                cursor.execute("UPDATE users SET level = %s WHERE mentor IN (SELECT username FROM admins WHERE mentor = %s)", (level, sp_username))
                conn.commit()
                st.success("✅ تم نقل السوبر مشرف والمشرفين والمستخدمين")

    elif action == "نقل مشرف إلى سوبر مشرف":
        cursor.execute("SELECT username, full_name FROM admins WHERE role = 'supervisor'")
        supervisors = cursor.fetchall()
        cursor.execute("SELECT username, full_name, level FROM admins WHERE role = 'sp'")
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

# ========== إغلاق الاتصال ==========
cursor.close()
conn.close()
