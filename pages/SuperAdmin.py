import streamlit as st
from supabase import create_client, Client
# التحقق من الجلسة
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("⚠️ يجب تسجيل الدخول أولاً.")
    st.stop()

if st.session_state.get("permissions") != "super_admin":
    st.error("🚫 ليس لديك صلاحية للوصول إلى هذه الصفحة.")
    st.stop()

# الاتصال بـ Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

st.set_page_config(page_title="⚙️ لوحة السوبر آدمن", page_icon="🛠️")
st.title("🛠️ لوحة السوبر آدمن")

st.subheader("📁 إنشاء مستوى جديد")

with st.form("create_level_form"):
    level_number = st.number_input("رقم المستوى", min_value=1, max_value=100, step=1)
    create_level_btn = st.form_submit_button("➕ إنشاء")

    if create_level_btn:
        # التحقق هل المستوى موجود مسبقًا
        existing = supabase.table("levels").select("level").eq("level", level_number).execute()

        if existing.data:
            st.warning("⚠️ هذا المستوى موجود مسبقًا.")
        else:
            try:
                supabase.table("levels").insert({"level": level_number}).execute()
                st.success("✅ تم إنشاء المستوى بنجاح.")
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء إنشاء المستوى: {e}")


st.markdown("---")
st.subheader("👤 إنشاء آدمن لمستوى")

with st.form("create_admin_form"):
    admin_full_name = st.text_input("الاسم الكامل للآدمن")
    admin_username = st.text_input("اسم المستخدم")
    admin_password = st.text_input("كلمة المرور")
    
    level_options = supabase.table("levels").select("*").execute().data
    level_choices = [lvl["level"] for lvl in level_options] if level_options else []
    selected_level = st.selectbox("اختر المستوى", level_choices)

    create_admin_btn = st.form_submit_button("➕ إنشاء الآدمن")

    if create_admin_btn:
        # تحقق من الحقول
        if not admin_full_name or not admin_username or not admin_password:
            st.warning("⚠️ يرجى تعبئة جميع الحقول.")
        else:
            # التحقق من التكرار في جميع الجداول
            duplicate_found = False

            for table_name in ["users", "admins", "super_admins"]:
                result = supabase.table(table_name).select("username, full_name").execute().data
                for record in result:
                    if admin_username.lower() == record["username"].lower() or \
                       admin_username.lower() == record["full_name"].lower() or \
                       admin_full_name.lower() == record["username"].lower() or \
                       admin_full_name.lower() == record["full_name"].lower():
                        duplicate_found = True
                        break
                if duplicate_found:
                    break

            if duplicate_found:
                st.error("❌ الاسم الكامل أو اسم المستخدم مستخدم مسبقًا في النظام.")
            else:
                try:
                    supabase.table("admins").insert({
                        "full_name": admin_full_name,
                        "username": admin_username,
                        "password": admin_password,
                        "level": selected_level,
                        "role": "admin"
                    }).execute()
                    st.success("✅ تم إنشاء الآدمن بنجاح.")
                except Exception as e:
                    st.error(f"❌ فشل في إنشاء الآدمن: {e}")

st.markdown("---")
st.subheader("🧑‍🏫 إنشاء سوبر مشرف لمستوى")

with st.form("create_sp_form"):
    sp_full_name = st.text_input("الاسم الكامل للسوبر مشرف")
    sp_username = st.text_input("اسم المستخدم")
    sp_password = st.text_input("كلمة المرور")
    
    level_options = supabase.table("levels").select("*").execute().data
    level_choices = [lvl["level"] for lvl in level_options] if level_options else []
    selected_level = st.selectbox("اختر المستوى", level_choices, key="sp_level")

    create_sp_btn = st.form_submit_button("➕ إنشاء سوبر مشرف")

    if create_sp_btn:
        if not sp_full_name or not sp_username or not sp_password:
            st.warning("⚠️ يرجى تعبئة جميع الحقول.")
        else:
            # التحقق من التكرار
            duplicate = False
            for table_name in ["users", "admins", "super_admins"]:
                result = supabase.table(table_name).select("username, full_name").execute().data
                for record in result:
                    if sp_username.lower() == record["username"].lower() or \
                       sp_username.lower() == record["full_name"].lower() or \
                       sp_full_name.lower() == record["username"].lower() or \
                       sp_full_name.lower() == record["full_name"].lower():
                        duplicate = True
                        break
                if duplicate:
                    break

            if duplicate:
                st.error("❌ الاسم الكامل أو اسم المستخدم مستخدم مسبقًا.")
            else:
                try:
                    supabase.table("admins").insert({
                        "full_name": sp_full_name,
                        "username": sp_username,
                        "password": sp_password,
                        "role": "sp",  # رمز سوبر مشرف
                        "level": selected_level
                    }).execute()
                    st.success("✅ تم إنشاء سوبر المشرف بنجاح.")
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء الإنشاء: {e}")

st.markdown("---")
st.subheader("👨‍🏫 إنشاء مشرف وربطه بسوبر مشرف")

with st.form("create_mentor_form"):
    mentor_full_name = st.text_input("الاسم الكامل للمشرف")
    mentor_username = st.text_input("اسم المستخدم")
    mentor_password = st.text_input("كلمة المرور")

    # جلب جميع السوبر مشرفين لربط المشرف بهم
    sp_data = supabase.table("admins").select("*").eq("role", "sp").execute().data
    if sp_data:
        sp_map = {f"{sp['full_name']} (المستوى {sp['level']})": (sp['username'], sp['level']) for sp in sp_data}
        selected_sp = st.selectbox("اختر السوبر مشرف", list(sp_map.keys()))
        sp_username, selected_level = sp_map[selected_sp]
    else:
        st.warning("⚠️ لا يوجد سوبر مشرفين متاحين.")
        selected_level = None
        sp_username = None

    create_mentor_btn = st.form_submit_button("➕ إنشاء مشرف")

    if create_mentor_btn:
        if not mentor_full_name or not mentor_username or not mentor_password or not selected_level:
            st.warning("⚠️ يرجى تعبئة جميع الحقول.")
        else:
            # التحقق من التكرار
            duplicate = False
            for table in ["users", "admins", "super_admins"]:
                results = supabase.table(table).select("username, full_name").execute().data
                for rec in results:
                    if mentor_username.lower() == rec["username"].lower() or \
                       mentor_username.lower() == rec["full_name"].lower() or \
                       mentor_full_name.lower() == rec["username"].lower() or \
                       mentor_full_name.lower() == rec["full_name"].lower():
                        duplicate = True
                        break
                if duplicate:
                    break

            if duplicate:
                st.error("❌ الاسم الكامل أو اسم المستخدم مستخدم مسبقًا.")
            else:
                try:
                    supabase.table("admins").insert({
                        "full_name": mentor_full_name,
                        "username": mentor_username,
                        "password": mentor_password,
                        "role": "supervisor",  # مشرف عادي
                        "level": selected_level,
                        "mentor": sp_username  # يُسجل المشرف التابع لهذا السوبر مشرف
                    }).execute()
                    st.success("✅ تم إنشاء المشرف وربطه بالسوبر مشرف.")
                except Exception as e:
                    st.error(f"❌ فشل الإنشاء: {e}")


st.markdown("---")
st.subheader("👤 إنشاء مستخدم وربطه بمشرف")

with st.form("create_user_form"):
    user_full_name = st.text_input("الاسم الكامل للمستخدم")
    user_username = st.text_input("اسم المستخدم")
    user_password = st.text_input("كلمة المرور")

    # جلب جميع المشرفين المتاحين
    mentors_data = supabase.table("admins").select("*").eq("role", "supervisor").execute().data
    if mentors_data:
        mentor_map = {
            f"{m['full_name']} (المستوى {m['level']})": (m['username'], m['level']) for m in mentors_data
        }
        selected_mentor = st.selectbox("اختر المشرف المرتبط به", list(mentor_map.keys()))
        mentor_username, user_level = mentor_map[selected_mentor]
    else:
        st.warning("⚠️ لا يوجد مشرفين متاحين.")
        user_level = None
        mentor_username = None

    create_user_btn = st.form_submit_button("➕ إنشاء المستخدم")

    if create_user_btn:
        if not user_full_name or not user_username or not user_password or not user_level:
            st.warning("⚠️ يرجى تعبئة جميع الحقول.")
        else:
            # التحقق من التكرار في الجداول الثلاثة
            duplicate = False
            for table in ["users", "admins", "super_admins"]:
                records = supabase.table(table).select("username, full_name").execute().data
                for rec in records:
                    if user_username.lower() == rec["username"].lower() or \
                       user_username.lower() == rec["full_name"].lower() or \
                       user_full_name.lower() == rec["username"].lower() or \
                       user_full_name.lower() == rec["full_name"].lower():
                        duplicate = True
                        break
                if duplicate:
                    break

            if duplicate:
                st.error("❌ الاسم الكامل أو اسم المستخدم مستخدم مسبقًا.")
            else:
                try:
                    supabase.table("users").insert({
                        "full_name": user_full_name,
                        "username": user_username,
                        "password": user_password,
                        "mentor": mentor_username,
                        "level": user_level
                    }).execute()
                    st.success("✅ تم إنشاء المستخدم بنجاح.")
                except Exception as e:
                    st.error(f"❌ فشل الإنشاء: {e}")


st.markdown("---")
st.subheader("🔄 دمج أو نقل المستخدمين بين المستويات")

# جلب جميع المستخدمين
users_data = supabase.table("users").select("id, full_name, username, mentor, level").execute().data
if not users_data:
    st.info("ℹ️ لا يوجد مستخدمون.")
else:
    user_map = {f"{u['full_name']} - {u['username']} (المستوى {u['level']})": u for u in users_data}
    selected_users = st.multiselect("اختر المستخدمين لنقلهم", options=list(user_map.keys()))

    # جلب جميع المشرفين
    mentors_data = supabase.table("admins").select("username, full_name, level").eq("role", "supervisor").execute().data
    if mentors_data:
        mentor_map = {
            f"{m['full_name']} (المستوى {m['level']})": (m["username"], m["level"]) for m in mentors_data
        }
        selected_mentor_label = st.selectbox("اختر المشرف الجديد", list(mentor_map.keys()))
        new_mentor_username, new_level = mentor_map[selected_mentor_label]

        if st.button("🚀 تنفيذ النقل"):
            updated_count = 0
            for user_label in selected_users:
                user_info = user_map[user_label]
                supabase.table("users").update({
                    "mentor": new_mentor_username,
                    "level": new_level
                }).eq("id", user_info["id"]).execute()
                updated_count += 1

            st.success(f"✅ تم نقل {updated_count} مستخدم إلى المشرف الجديد.")
    else:
        st.warning("⚠️ لا يوجد مشرفين متاحين.")


st.markdown("---")
st.subheader("🏆 إدارة قائمة الإنجازات")

# جلب القائمة الحالية
achievements_data = supabase.table("achievements_list").select("*").execute().data
achievements_data = sorted(achievements_data, key=lambda x: x["id"])

# عرض القائمة الحالية
if achievements_data:
    for achievement in achievements_data:
        col1, col2, col3 = st.columns([5, 1, 1])
        with col1:
            new_val = st.text_input(f"✏️ تعديل الإنجاز ID {achievement['id']}", value=achievement["الإنجاز"], key=f"edit_{achievement['id']}")
        with col2:
            if st.button("💾 حفظ", key=f"save_{achievement['id']}"):
                supabase.table("achievements_list").update({"الإنجاز": new_val}).eq("id", achievement["id"]).execute()
                st.success("✅ تم تحديث الإنجاز")
                st.rerun()
        with col3:
            if st.button("🗑️ حذف", key=f"delete_{achievement['id']}"):
                supabase.table("achievements_list").delete().eq("id", achievement["id"]).execute()
                st.success("🗑️ تم الحذف")
                st.rerun()
else:
    st.info("📭 لا توجد عناصر حالياً في القائمة.")

st.markdown("---")
st.subheader("➕ إضافة إنجاز جديد")
new_achievement = st.text_input("أدخل الإنجاز الجديد")
if st.button("➕ إضافة"):
    if new_achievement.strip():
        supabase.table("achievements_list").insert({"الإنجاز": new_achievement.strip()}).execute()
        st.success("✅ تم إضافة الإنجاز")
        st.rerun()
    else:
        st.warning("⚠️ يرجى كتابة نص الإنجاز قبل الإضافة.")
