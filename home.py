import streamlit as st
from supabase import create_client, Client

# إعداد الاتصال بـ Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# إعداد واجهة تسجيل الدخول
st.set_page_config(page_title="تسجيل الدخول", page_icon="🔐")
st.title("🔐 تسجيل الدخول")

# حالة الجلسة
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم أو الاسم الكامل")
        password = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("دخول")

        if submitted:
            username = username.strip().lower()
            password = password.strip()

            # بحث في جدول users
            users_result = supabase.table("users").select("*").eq("password", password).execute()
            user = next((u for u in users_result.data if u["username"].strip().lower() == username or u["full_name"].strip().lower() == username), None)

            if user:
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
                # بحث في جدول admins
                admins_result = supabase.table("admins").select("*").eq("password", password).execute()
                admin = next((a for a in admins_result.data if a["username"].strip().lower() == username or a["full_name"].strip().lower() == username), None)

                if admin:
                    st.session_state.update({
                        "authenticated": True,
                        "username": admin["username"],
                        "full_name": admin["full_name"],
                        "permissions": admin["role"],
                        "level": admin.get("level", 0)  # سوبر آدمن ليس له مستوى محدد
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
    # إذا سجل الدخول سابقًا
    if st.session_state["permissions"] == "user":
        st.switch_page("pages/UserDashboard.py")
    elif st.session_state["permissions"] == "admin":
        st.switch_page("pages/AdminDashboard.py")
    elif st.session_state["permissions"] in ["supervisor", "sp"]:
        st.switch_page("pages/Supervisor.py")
    elif st.session_state["permissions"] == "super_admin":
        st.switch_page("pages/SuperAdmin.py")
