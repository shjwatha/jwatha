import streamlit as st
from supabase import create_client, Client
import pandas as pd

# إعداد الصفحة
st.set_page_config(page_title="لوحة الإدارة", page_icon="🛠️")
st.title("🛠️ لوحة إدارة المستخدمين")

# التأكد من تسجيل الدخول
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("⚠️ يجب تسجيل الدخول أولًا.")
    st.stop()

if st.session_state["permissions"] != "admin":
    st.error("🚫 لا تملك الصلاحية للوصول إلى هذه الصفحة.")
    st.stop()

admin_username = st.session_state["username"]
admin_level = st.session_state["level"]

# 🔄 زر تحديث البيانات
if st.button("🔄 تحديث البيانات"):
    st.rerun()

# جلب جميع المستخدمين من نفس المستوى
users_response = supabase.table("users").select("*").eq("level", admin_level).execute()
users_df = pd.DataFrame(users_response.data) if users_response.data else pd.DataFrame(columns=["full_name", "username", "mentor"])

st.subheader(f"📋 قائمة المستخدمين في المستوى {admin_level}")
if users_df.empty:
    st.info("لا يوجد مستخدمون بعد.")
else:
    display_df = users_df[["full_name", "username", "mentor"]]
    display_df.columns = ["الاسم الكامل", "اسم المستخدم", "المشرف"]
    st.dataframe(display_df, use_container_width=True)

st.subheader("➕ إنشاء حساب جديد")

with st.form("create_user_form"):
    full_name = st.text_input("الاسم الكامل")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور")
    mentor = st.text_input("اسم المشرف")  # المشرف يتم إدخاله يدويًا هنا
    submitted = st.form_submit_button("إنشاء")

    if submitted:
        if not full_name or not username or not password or not mentor:
            st.warning("⚠️ يرجى تعبئة جميع الحقول.")
        else:
            # التحقق من التكرار في قاعدة البيانات
            exists_user = supabase.table("users").select("*").or_(
                f"username.eq.{username},full_name.eq.{full_name}"
            ).execute()

            if exists_user.data:
                st.error("❌ الاسم الكامل أو اسم المستخدم مستخدم من قبل.")
            else:
                # إنشاء المستخدم الجديد
                insert_response = supabase.table("users").insert({
                    "full_name": full_name.strip(),
                    "username": username.strip(),
                    "password": password.strip(),
                    "mentor": mentor.strip(),
                    "level": admin_level
                }).execute()

                if insert_response.status_code == 201:
                    st.success("✅ تم إنشاء المستخدم بنجاح.")
                    st.rerun()
                else:
                    st.error("❌ حدث خطأ أثناء إنشاء المستخدم.")

st.subheader("📦 إنشاء 20 مستخدم دفعة واحدة")

st.markdown(
    """
    <style>
    .rtl input, .rtl select, .rtl textarea {
        direction: rtl;
        text-align: right;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.form("bulk_user_form"):
    full_names = []
    usernames = []
    passwords = []
    mentors = []

    for i in range(1, 21):
        st.markdown(f"#### 👤 المستخدم رقم {i}", unsafe_allow_html=True)
        cols = st.columns(4)
        with cols[0]:
            full_names.append(st.text_input(f"الاسم الكامل {i}", key=f"full_name_{i}"))
        with cols[1]:
            usernames.append(st.text_input(f"اسم المستخدم {i}", key=f"username_{i}"))
        with cols[2]:
            passwords.append(st.text_input(f"كلمة المرور {i}", key=f"password_{i}"))
        with cols[3]:
            mentors.append(st.text_input(f"اسم المشرف {i}", key=f"mentor_{i}"))

    submit_bulk = st.form_submit_button("💾 حفظ جميع المستخدمين")

    if submit_bulk:
        created_count = 0
        skipped_count = 0

        for i in range(20):
            fn = full_names[i].strip()
            un = usernames[i].strip()
            pw = passwords[i].strip()
            mn = mentors[i].strip()

            if not fn or not un or not pw or not mn:
                continue

            check = supabase.table("users").select("*").or_(
                f"username.eq.{un},full_name.eq.{fn}"
            ).execute()

            if check.data:
                st.warning(f"🚫 تم تجاوز '{un}' لأن الاسم أو اسم المستخدم مستخدم من قبل.")
                skipped_count += 1
                continue

            supabase.table("users").insert({
                "full_name": fn,
                "username": un,
                "password": pw,
                "mentor": mn,
                "level": admin_level
            }).execute()
            created_count += 1

        st.success(f"✅ تم إنشاء {created_count} مستخدم. تم تجاوز {skipped_count} مستخدم (بيانات ناقصة أو مكررة).")
        st.rerun()

st.subheader("👥 إدارة المستخدمين التابعين لك")

# تحميل المستخدمين حسب المستوى
try:
    users_data = supabase.table("users").select("*").eq("level", admin_level).execute()
    users_df = pd.DataFrame(users_data.data)
except Exception as e:
    st.error("❌ حدث خطأ أثناء تحميل المستخدمين.")
    users_df = pd.DataFrame()

if users_df.empty:
    st.info("ℹ️ لا يوجد مستخدمون في هذا المستوى حتى الآن.")
else:
    selected_user = st.selectbox("🧑 اختر مستخدم لحذفه", users_df["username"])
    if st.button("🗑️ حذف المستخدم"):
        user_to_delete = users_df[users_df["username"] == selected_user]
        if not user_to_delete.empty:
            user_id = user_to_delete.iloc[0]["id"]
            supabase.table("users").delete().eq("id", user_id).execute()
            st.success(f"✅ تم حذف المستخدم: {selected_user}")
            st.rerun()

    st.markdown("### 📋 قائمة المستخدمين")
    st.dataframe(users_df[["full_name", "username", "mentor", "created_at"]], use_container_width=True)

if admin_role in ["supervisor", "sp", "super_admin"]:
    st.subheader("📊 لوحة المشرف")

    view_mode = st.radio("📌 اختر طريقة العرض", ["حسب المشرف", "حسب المستوى"], horizontal=True)

    if view_mode == "حسب المشرف":
        mentors = users_df["mentor"].dropna().unique().tolist()
        selected_mentor = st.selectbox("👨‍🏫 اختر المشرف", mentors)

        filtered_df = users_df[users_df["mentor"] == selected_mentor]
        st.markdown(f"### 👥 المستخدمون تحت إشراف: {selected_mentor}")
        st.dataframe(filtered_df[["full_name", "username", "created_at"]], use_container_width=True)

    else:  # حسب المستوى
        levels = sorted(users_df["level"].dropna().unique().astype(int))
        selected_level = st.selectbox("🎯 اختر المستوى", levels)

        filtered_df = users_df[users_df["level"] == selected_level]
        st.markdown(f"### 👥 المستخدمون في المستوى: {selected_level}")
        st.dataframe(filtered_df[["full_name", "username", "mentor", "created_at"]], use_container_width=True)
