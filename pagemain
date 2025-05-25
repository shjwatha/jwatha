import streamlit as st
from supabase import create_client, Client

# إعداد الاتصال بـ Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# إعداد واجهة تسجيل الدخول
st.set_page_config(page_title="تسجيل الدخول", page_icon="🔐")
st.title("🔐 تسجيل الدخول")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("دخول")

        if submitted:
            # المحاولة أولاً في جدول المستخدمين
            user_result = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()

            if user_result.data:
                user = user_result.data[0]
                st.session_state.update({
                    "authenticated": True,
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "permissions": "user",
                    "level": user["level"]
                })
                st.success("✅ تم تسجيل الدخول بنجاح")
                st.switch_page("pages/UserDashboard.py")

            else:
                # إذا لم يكن مستخدمًا، فابحث عنه في جدول الأدمن
                admin_result = supabase.table("admins").select("*").eq("username", username).eq("password", password).execute()

                if admin_result.data:
                    admin = admin_result.data[0]
                    st.session_state.update({
                        "authenticated": True,
                        "username": admin["username"],
                        "full_name": admin["full_name"],
                        "permissions": admin["role"],
                        "level": admin["level"]
                    })
                    st.success("✅ تم تسجيل الدخول بنجاح")

                    if admin["role"] == "admin":
                        st.switch_page("pages/AdminDashboard.py")
                    elif admin["role"] in ["supervisor", "sp"]:
                        st.switch_page("pages/Supervisor.py")
                    elif admin["role"] == "super_admin":
                        st.switch_page("pages/SuperAdmin.py")

                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")

else:
    st.switch_page("pages/UserDashboard.py")
