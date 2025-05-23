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
# ===================== تبويب 2: إنشاء استمارة التقييم الذاتي =====================
elif selected_tab == "إعداد نموذج التقييم الذاتي":
    st.header("📝 إعداد نموذج التقييم الذاتي - تسلسل الخطوات")

    # إعداد متغير خطوة الإدخال إذا لم يكن موجوداً مسبقاً
    if "current_step" not in st.session_state:
        st.session_state["current_step"] = 0

    # الخطوة 0: اختيار المستوى
    if st.session_state["current_step"] == 0:
        with st.form("step0_form"):
            level_options = [lvl['level_name'] for lvl in levels]
            selected_level = st.selectbox("الخطوة 0: اختر المستوى", level_options, key="selected_level")
            if st.form_submit_button("التالي"):
                st.session_state["current_step"] = 1
                st.experimental_rerun()

    # الخطوة 1: اختيار نوع السؤال
    elif st.session_state["current_step"] == 1:
        with st.form("step1_form"):
            question_types = [
                "خيار واحد (radio)",
                "خيارات متعددة (checkbox)",
                "نص مفتوح (text)",
                "قائمة منسدلة (select)"
            ]
            selected_question_type = st.selectbox("الخطوة 1: اختر نوع السؤال", question_types, key="selected_question_type")
            if st.form_submit_button("التالي"):
                st.session_state["selected_question_type"] = selected_question_type
                st.session_state["current_step"] = 2
                st.experimental_rerun()

    # الخطوة 2: إدخال نص السؤال
    elif st.session_state["current_step"] == 2:
        with st.form("step2_form"):
            question_text = st.text_input("الخطوة 2: أدخل نص السؤال", key="question_text")
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("السابق"):
                    st.session_state["current_step"] = 1
                    st.experimental_rerun()
            with col2:
                if st.form_submit_button("التالي"):
                    if question_text.strip() == "":
                        st.error("❌ يجب إدخال نص السؤال")
                    else:
                        st.session_state["question_text"] = question_text
                        st.session_state["current_step"] = 3
                        st.experimental_rerun()

    # الخطوة 3: إدخال الإجابات (في حالة نوع السؤال لا يعتمد على نص مفتوح)
    elif st.session_state["current_step"] == 3:
        selected_type = st.session_state.get("selected_question_type", "نص مفتوح (text)")
        question_text = st.session_state.get("question_text", "")
        st.markdown(f"**السؤال:** {question_text}")
        
        # لو كان نوع السؤال نص مفتوح فلا حاجة لإضافة إجابات
        if selected_type == "نص مفتوح (text)":
            st.info("السؤال من نوع نص مفتوح، لا يتطلب إدخال إجابات.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("السابق"):
                    st.session_state["current_step"] = 2
                    st.experimental_rerun()
            with col2:
                if st.button("حفظ السؤال"):
                    try:
                        mapping = {
                            "خيار واحد (radio)": "radio",
                            "خيارات متعددة (checkbox)": "checkbox",
                            "نص مفتوح (text)": "text",
                            "قائمة منسدلة (select)": "select"
                        }
                        db_input_type = mapping[selected_type]
                        insert_template_query = """
                            INSERT INTO self_assessment_templates (level, question, input_type)
                            VALUES (%s, %s, %s)
                        """
                        cursor.execute(insert_template_query, (st.session_state["selected_level"], question_text, db_input_type))
                        conn.commit()
                        st.success("✅ تم حفظ السؤال بنجاح")
                        # إعادة ضبط الخطوات بعد الحفظ
                        st.session_state["current_step"] = 0
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ أثناء حفظ السؤال: {e}")
        else:
            st.markdown("### الخطوة 3: أضف إجابات السؤال (مع الدرجة)")
            
            if "answers" not in st.session_state:
                st.session_state["answers"] = []
            
            with st.form("answer_form"):
                answer_text = st.text_input("أدخل نص الإجابة", key="answer_text")
                answer_score = st.number_input("أدخل الدرجة", min_value=0, max_value=100, step=1, key="answer_score")
                if st.form_submit_button("➕ إضافة إجابة"):
                    if answer_text.strip() == "":
                        st.warning("⚠️ يرجى إدخال نص الإجابة")
                    else:
                        st.session_state["answers"].append({
                            "answer_text": answer_text,
                            "score": answer_score
                        })
                        st.success("✅ تم إضافة الإجابة")
                        st.experimental_rerun()
            
            if st.session_state["answers"]:
                st.markdown("**الإجابات المضافة:**")
                for idx, ans in enumerate(st.session_state["answers"]):
                    col_ans1, col_ans2 = st.columns([4, 1])
                    with col_ans1:
                        st.write(f"{idx+1}. {ans['answer_text']} - {ans['score']} نقطة")
                    with col_ans2:
                        if st.button("حذف", key=f"delete_ans_{idx}"):
                            st.session_state["answers"].pop(idx)
                            st.experimental_rerun()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("السابق"):
                    st.session_state["current_step"] = 2
                    st.experimental_rerun()
            with col3:
                if st.button("حفظ السؤال"):
                    if not st.session_state["answers"]:
                        st.error("❌ يجب إضافة إجابة واحدة على الأقل")
                    else:
                        try:
                            mapping = {
                                "خيار واحد (radio)": "radio",
                                "خيارات متعددة (checkbox)": "checkbox",
                                "نص مفتوح (text)": "text",
                                "قائمة منسدلة (select)": "select"
                            }
                            db_input_type = mapping[selected_type]
                            insert_template_query = """
                                INSERT INTO self_assessment_templates (level, question, input_type)
                                VALUES (%s, %s, %s)
                            """
                            cursor.execute(insert_template_query, (st.session_state["selected_level"], question_text, db_input_type))
                            conn.commit()
                            template_id = cursor.lastrowid
                            
                            insert_option_query = """
                                INSERT INTO self_assessment_options (question_id, option_text, score)
                                VALUES (%s, %s, %s)
                            """
                            for ans in st.session_state["answers"]:
                                cursor.execute(insert_option_query, (template_id, ans["answer_text"], ans["score"]))
                            conn.commit()
                            st.success("✅ تم حفظ السؤال والإجابات بنجاح")
                            st.session_state["current_step"] = 0
                            st.session_state["answers"] = []
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"❌ حدث خطأ أثناء حفظ البيانات: {e}")
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
