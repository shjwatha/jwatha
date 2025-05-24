
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


