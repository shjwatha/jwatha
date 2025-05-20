import streamlit as st
import pandas as pd
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
        # التحقق هل المستوى موجود مسبقًا في Supabase
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

# نفس الأسلوب يمكن تطبيقه على جميع الأجزاء الأخرى من الكود مثل إنشاء سوبر مشرف، مشرف، ومستخدم.

# تأكد من أنك تستخدم Supabase للتحقق من البيانات عند إنشائها أو تعديلها بدلاً من Google Sheets.
