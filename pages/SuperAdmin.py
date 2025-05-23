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
# ===================== تبويب 2: إنشاء استمارة التقييم الذاتي ===================elif selected_tab == "إعداد نموذج التقييم الذاتي":
    st.header("📝 إدارة نماذج التقييم الذاتي")

    # ========================================
    # 1. اختيار المستوى
    # ========================================
    level_options = [lvl['level_name'] for lvl in levels]
    selected_level = st.selectbox("اختر المستوى", level_options, key="dashboard_level")
    
    st.markdown("---")
    
    # ========================================
    # 2. إدارة النماذج (التقييمات) لهذا المستوى
    # ========================================
    # استعلام للحصول على النماذج المميزة (حقل form) لهذا المستوى
    query_forms = "SELECT DISTINCT form FROM self_assessment_templates WHERE level = %s"
    cursor.execute(query_forms, (selected_level,))
    forms_data = cursor.fetchall()
    # استخراج أسماء النماذج الموجودة
    form_names = [row["form"] for row in forms_data if row["form"] is not None]
    if not form_names:
        form_names = ["-----"]
    
    col_form1, col_form2 = st.columns([3, 1])
    with col_form1:
        # نعرض قائمة منسدلة للنماذج الموجوده
        selected_form = st.selectbox("اختر النموذج", options=form_names, key="selected_form")
    with col_form2:
        if st.button("إضافة نموذج جديد", key="new_form_btn"):
            st.session_state["adding_new_form"] = True

    # نموذج إضافة نموذج جديد (في نفس الصفحة)
    if st.session_state.get("adding_new_form", False):
        with st.form("new_form_form"):
            new_form_name = st.text_input("اسم النموذج الجديد", key="new_form_name")
            if st.form_submit_button("حفظ النموذج"):
                if new_form_name.strip() == "":
                    st.error("يجب إدخال اسم النموذج")
                else:
                    # يتم حفظ اسم النموذج في حالة الجلسة ليصبح المُختار
                    st.session_state["selected_form"] = new_form_name
                    st.success("تم إضافة النموذج الجديد")
                    st.session_state["adding_new_form"] = False
    # اعتماد النموذج الحالي من حالة الجلسة إذا وُجد، وإلا من اختيار القائمة    
    current_form = st.session_state.get("selected_form", selected_form)
    
    st.markdown("---")
    st.subheader(f"النموذج الحالي: {current_form}")
    
    # ========================================
    # 3. إدارة الأسئلة ضمن النموذج الحالي
    # ========================================
    # استعلام للحصول على جميع الأسئلة المرتبطة بالمستوى والنموذج الحالي
    query_questions = """
        SELECT id, question, input_type 
        FROM self_assessment_templates 
        WHERE level = %s AND form = %s
    """
    cursor.execute(query_questions, (selected_level, current_form))
    questions_data = cursor.fetchall()
    question_options = [f"{q['id']}: {q['question']}" for q in questions_data] if questions_data else ["-----"]
    
    col_q1, col_q2 = st.columns([3, 1])
    with col_q1:
        selected_question_str = st.selectbox("اختر سؤال للتعديل", options=question_options, key="selected_question")
    with col_q2:
        if st.button("إضافة سؤال جديد", key="new_question_btn"):
            st.session_state["adding_new_question"] = True

    st.markdown("---")
    
    # ========================================
    # 4. إضافة سؤال جديد للنموذج الحالي
    # ========================================
    if st.session_state.get("adding_new_question", False):
        st.markdown("### إضافة سؤال جديد")
        with st.form("new_question_form"):
            new_question_text = st.text_input("نص السؤال", key="new_question_text")
            new_question_type = st.selectbox(
                "نوع الإدخال", 
                ["خيار واحد (radio)", "خيارات متعددة (checkbox)", "نص مفتوح (text)", "قائمة منسدلة (select)"], 
                key="new_question_type"
            )
            # في حالة أن نوع السؤال يحتاج خيارات (كل ما عدا النص المفتوح)
            if new_question_type != "نص مفتوح (text)":
                st.markdown("#### إضافة خيارات للسؤال (مع الدرجة)")
                if "new_question_answers" not in st.session_state:
                    st.session_state["new_question_answers"] = []
                new_ans_text = st.text_input("نص الإجابة", key="new_ans_text")
                new_ans_score = st.number_input("الدرجة", min_value=0, max_value=100, step=1, key="new_ans_score")
                if st.button("➕ إضافة إجابة", key="add_ans_btn"):
                    if new_ans_text.strip() == "":
                        st.error("يجب إدخال نص الإجابة")
                    else:
                        st.session_state["new_question_answers"].append({
                            "answer_text": new_ans_text,
                            "score": new_ans_score
                        })
                        st.success("تم إضافة الإجابة")
                if st.session_state.get("new_question_answers"):
                    st.markdown("**الإجابات المضافة:**")
                    for idx, ans in enumerate(st.session_state["new_question_answers"]):
                        st.write(f"{idx+1}. {ans['answer_text']} - {ans['score']} نقطة")
            submitted_new_question = st.form_submit_button("حفظ السؤال")
            if submitted_new_question:
                if new_question_text.strip() == "":
                    st.error("يجب إدخال نص السؤال")
                elif new_question_type != "نص مفتوح (text)" and (not st.session_state.get("new_question_answers")):
                    st.error("يجب إضافة إجابة واحدة على الأقل")
                else:
                    # تحويل نوع الإدخال إلى صيغة قاعدة البيانات
                    mapping = {
                        "خيار واحد (radio)": "radio",
                        "خيارات متعددة (checkbox)": "checkbox",
                        "نص مفتوح (text)": "text",
                        "قائمة منسدلة (select)": "select"
                    }
                    db_question_type = mapping[new_question_type]
                    try:
                        insert_question_query = """
                            INSERT INTO self_assessment_templates (level, form, question, input_type)
                            VALUES (%s, %s, %s, %s)
                        """
                        cursor.execute(insert_question_query, (selected_level, current_form, new_question_text, db_question_type))
                        conn.commit()
                        new_question_id = cursor.lastrowid
                        
                        # في حالة أن نوع السؤال يحتاج خيارات، ندرجها في جدول الخيارات
                        if db_question_type != "text" and st.session_state.get("new_question_answers"):
                            insert_option_query = """
                                INSERT INTO self_assessment_options (question_id, option_text, score)
                                VALUES (%s, %s, %s)
                            """
                            for ans in st.session_state["new_question_answers"]:
                                cursor.execute(insert_option_query, (new_question_id, ans["answer_text"], ans["score"]))
                            conn.commit()
                        st.success("تم حفظ السؤال بنجاح")
                        # إعادة تعيين متغيرات إضافة السؤال
                        st.session_state.pop("adding_new_question")
                        st.session_state.pop("new_question_answers", None)
                    except Exception as e:
                        st.error(f"❌ حدث خطأ أثناء حفظ السؤال: {e}")

    # ========================================
    # 5. تعديل سؤال موجود
    # ========================================
    # إذا كان في القائمة المختارة سؤال محدد (غير placeholder)
    if selected_question_str != "-----":
         try:
             selected_question_id = int(selected_question_str.split(":")[0])
         except Exception:
             selected_question_id = None
         if selected_question_id:
             query_edit = "SELECT id, question, input_type FROM self_assessment_templates WHERE id = %s"
             cursor.execute(query_edit, (selected_question_id,))
             q_detail = cursor.fetchone()
             if q_detail:
                 st.markdown("### تعديل السؤال")
                 with st.form("edit_question_form"):
                     edited_question_text = st.text_input("تعديل نص السؤال", value=q_detail["question"], key="edited_question_text")
                     submitted_edit = st.form_submit_button("حفظ التعديلات")
                     if submitted_edit:
                         try:
                             update_query = "UPDATE self_assessment_templates SET question = %s WHERE id = %s"
                             cursor.execute(update_query, (edited_question_text, selected_question_id))
                             conn.commit()
                             st.success("تم تعديل السؤال بنجاح")
                         except Exception as e:
                             st.error(f"❌ خطأ أثناء حفظ التعديلات: {e}")

# ========== التبويب الثالث: نقاطي ==========
elif selected_tab == "نقاطي (تقييم من المشرف)":
    st.header("🏅 إعداد بنود تقييم من المشرف")

    st.subheader("➕ إضافة بند جديد")
    with st.form("add_supervisor_criterion"):
        level = st.selectbox("اختر المستوى", [lvl['level_name'] for lvl in levels], key="supervised_level")
        question = st.text_input("عنوان البند")
        max_score = st.number_input("الدرجة الكاملة", min_value=1, max_value=100, value=10)
        submitted = st.form_submit_button("➕ أضف البند")

        if submitted and question:
            try:
                insert_query = "INSERT INTO supervisor_criteria (question, max_score, level) VALUES (%s, %s, %s)"
                print(f"الاستعلام: {insert_query} | القيم: {(question, max_score, level)}")
                cursor.execute(insert_query, (question, max_score, level))
                conn.commit()
                st.success("✅ تم حفظ البند")
                st.rerun()  # إعادة تحميل الصفحة بعد التحديث
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء إضافة البند: {e}")

    st.subheader("📋 البنود الحالية حسب المستوى")
    selected_supervised_level = st.selectbox("اختر المستوى", [lvl['level_name'] for lvl in levels], key="supervised_view")

    try:
        cursor.execute("SELECT * FROM supervisor_criteria WHERE level = %s", (selected_supervised_level,))
        results = cursor.fetchall()

        if results:
            for row in results:
                with st.expander(f"{row['question']} (درجة كاملة: {row['max_score']})"):
                    col1, col2 = st.columns([1, 1])
                    
                    # نموذج منفصل لتحديث البند
                    with col1:
                        with st.form(key=f"edit_form_{row['id']}"):
                            new_question = st.text_input("عنوان البند", value=row['question'], key=f"edit_q_{row['id']}")
                            new_score = st.number_input("الدرجة الكاملة", min_value=1, max_value=100, value=row['max_score'], key=f"edit_s_{row['id']}")
                            if st.form_submit_button("📝 تحديث"):
                                try:
                                    update_query = "UPDATE supervisor_criteria SET question = %s, max_score = %s WHERE id = %s"
                                    print(f"الاستعلام: {update_query} | القيم: {(new_question, new_score, row['id'])}")
                                    cursor.execute(update_query, (new_question, new_score, row['id']))
                                    conn.commit()
                                    st.success("✅ تم التحديث")
                                    st.rerun()  # إعادة تحميل الصفحة بعد التحديث
                                except Exception as e:
                                    st.error(f"❌ حدث خطأ أثناء التحديث: {e}")
                    
                    # زر حذف منفصل
                    with col2:
                        if st.button("🗑️ حذف", key=f"delete_btn_{row['id']}"):
                            try:
                                delete_query = "DELETE FROM supervisor_criteria WHERE id = %s"
                                print(f"الاستعلام: {delete_query} | القيم: {(row['id'],)}")
                                cursor.execute(delete_query, (row['id'],))
                                conn.commit()
                                st.success("✅ تم الحذف")
                                st.rerun()  # إعادة تحميل الصفحة بعد الحذف
                            except Exception as e:
                                st.error(f"❌ حدث خطأ أثناء الحذف: {e}")
        else:
            st.info("لا توجد بنود تقييم لهذا المستوى بعد.")
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء جلب البنود الخاصة بالمستوى: {e}")

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
