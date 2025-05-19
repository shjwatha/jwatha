import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from hijri_converter import Gregorian
from supabase import create_client, Client

# ===== التحقق من تسجيل الدخول =====
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.switch_page("home.py")

# ===== الاتصال بـ Supabase =====
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ===== إعداد الصفحة =====
st.set_page_config(page_title="تقييم اليوم", page_icon="📋", layout="wide")

# ===== التحقق من الصلاحيات =====
if "username" not in st.session_state or "level" not in st.session_state:
    st.error("❌ يجب تسجيل الدخول أولاً.")
    st.stop()

if st.session_state["permissions"] != "user":
    if st.session_state["permissions"] == "admin":
        st.warning("تم تسجيل الدخول كأدمن، سيتم تحويلك للوحة التحكم...")
        st.switch_page("pages/AdminDashboard.py")
    elif st.session_state["permissions"] in ["supervisor", "sp"]:
        st.warning("تم تسجيل الدخول كمشرف، سيتم تحويلك للتقارير...")
        st.switch_page("pages/Supervisor.py")
    else:
        st.error("⚠️ صلاحية غير معروفة.")
        st.stop()

username = st.session_state["username"]
user_level = st.session_state["level"]

# ===== تحميل بيانات المستخدم والمشرفين من Supabase =====
try:
    admin_data = supabase.table("admins").select("username, full_name, mentor").eq("level", user_level).execute().data
    user_data = supabase.table("users").select("*").eq("username", username).eq("level", user_level).execute().data
    if not user_data:
        st.error("❌ لم يتم العثور على بيانات هذا المستخدم.")
        st.stop()
    worksheet_data = user_data[0]
except Exception as e:
    st.error("❌ حدث خطأ أثناء الاتصال بقاعدة البيانات. حاول مرة أخرى.")
    st.stop()

# ===== جلب أسماء المشرف والسوبر مشرف =====
mentor_name = worksheet_data.get("mentor")
sp_row = next((row for row in admin_data if row["username"] == mentor_name), None)
sp_name = sp_row["mentor"] if sp_row else None


# ===== جلب أسماء البنود من Supabase =====
@st.cache_data
def get_daily_data_columns():
    result = supabase.table("daily_data").select("*").eq("username", username).limit(1).execute()
    if not result.data:
        return []
    df = pd.DataFrame(result.data)
    return [col for col in df.columns if col not in ["id", "username", "level", "التاريخ"]]

columns = ["التاريخ"] + get_daily_data_columns()

# ===== تبويب إدخال البيانات =====
st.title(f"👋 أهلاً {username} | مجموعتك / {mentor_name}")
st.markdown("### 📝 المحاسبة الذاتية")

with st.form("daily_form"):
    today = datetime.today().date()

    hijri_dates = []
    for i in range(7):
        g_date = today - timedelta(days=i)
        h_date = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
        weekday = g_date.strftime("%A")
        arabic_weekday = {
            "Saturday": "السبت",
            "Sunday": "الأحد",
            "Monday": "الاثنين",
            "Tuesday": "الثلاثاء",
            "Wednesday": "الأربعاء",
            "Thursday": "الخميس",
            "Friday": "الجمعة"
        }[weekday]
        g_date_str = f"{g_date.day}/{g_date.month}/{g_date.year}"
        hijri_label = f"{arabic_weekday} - {g_date_str}"
        hijri_dates.append((hijri_label, g_date))

    hijri_labels = [label for label, _ in hijri_dates]
    selected_label = st.selectbox("📅 اختر التاريخ (هجري)", hijri_labels)
    selected_date = dict(hijri_dates)[selected_label]
    date_str = selected_date.strftime("%Y-%m-%d")

    inputs = {"username": username, "level": user_level, "التاريخ": date_str}

    for col_name in columns[1:]:
        value = st.text_input(f"{col_name}", key=col_name)
        inputs[col_name] = value

    submitted = st.form_submit_button("💾 حفظ")

    if submitted:
        try:
            # حذف الإدخال السابق إن وجد
            existing = supabase.table("daily_data").select("id").eq("username", username).eq("level", user_level).eq("التاريخ", date_str).execute()
            if existing.data:
                entry_id = existing.data[0]["id"]
                supabase.table("daily_data").update(inputs).eq("id", entry_id).execute()
            else:
                supabase.table("daily_data").insert(inputs).execute()
            st.success("✅ تم الحفظ بنجاح.")
        except Exception as e:
            st.error("❌ حدث خطأ أثناء حفظ البيانات. حاول لاحقًا.")



# ===== تبويب المحادثات =====
st.markdown("### 💬 المحادثة مع المشرف / السوبر مشرف")

selected_mentor = mentor_name
if st.checkbox("🧭 التواصل مع السوبر مشرف"):
    selected_mentor = sp_name

# جلب الرسائل بين المستخدم والمشرف
chat_data_raw = supabase.table("chat").select("*").or_(
    f"(from.eq.{username},to.eq.{selected_mentor})",
    f"(from.eq.{selected_mentor},to.eq.{username})"
).order("timestamp", desc=False).execute().data

chat_data = pd.DataFrame(chat_data_raw)

# عرض المحادثة
if not chat_data.empty:
    for i, row in chat_data.iterrows():
        sender = "🟢 أنت" if row["from"] == username else f"🔵 {row['from']}"
        st.markdown(f"**{sender}:** {row['message']}")
else:
    st.info("لا توجد رسائل حالياً.")

# إدخال رسالة جديدة
with st.form("chat_form"):
    new_msg = st.text_input("✉️ أكتب رسالتك هنا")
    send = st.form_submit_button("📨 إرسال")

    if send and new_msg.strip():
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        supabase.table("chat").insert({
            "timestamp": timestamp,
            "from": username,
            "to": selected_mentor,
            "message": new_msg,
            "read_by_receiver": ""
        }).execute()
        st.experimental_rerun()

# تحديث حالة القراءة
unread_indexes = chat_data[
    (chat_data["to"] == username) &
    (chat_data["read_by_receiver"] != "✓")
].index.tolist()

for i in unread_indexes:
    msg_id = chat_data.iloc[i]["id"]
    supabase.table("chat").update({"read_by_receiver": "✓"}).eq("id", msg_id).execute()



# ===== تبويب 3: تقرير يوم محدد =====
with tabs[2]:
    st.markdown("### 👤 تقرير يوم محدد")

    # جلب قائمة التواريخ التي فيها بيانات
    dates_data = supabase.table("daily_data") \
        .select("التاريخ") \
        .eq("username", username) \
        .eq("level", user_level) \
        .order("التاريخ", desc=True) \
        .execute().data

    date_options = [row["التاريخ"] for row in dates_data]

    if not date_options:
        st.info("لا توجد بيانات متاحة.")
    else:
        selected_date = st.selectbox("📅 اختر التاريخ", date_options)
        record = supabase.table("daily_data") \
            .select("*") \
            .eq("username", username) \
            .eq("level", user_level) \
            .eq("التاريخ", selected_date) \
            .execute().data

        if not record:
            st.warning("لا توجد بيانات لهذا التاريخ.")
        else:
            df_record = pd.DataFrame([record[0]])
            df_display = df_record.drop(columns=["id", "username", "level"], errors="ignore").set_index("التاريخ")
            st.dataframe(df_display.T, use_container_width=True)


# ===== تبويب الإنجازات =====
st.markdown("### 🏆 إنجازاتي")

# جلب إنجازات المستخدم من جدول notes
notes_data = supabase.table("notes") \
    .select("*") \
    .eq("الطالب", username) \
    .order("timestamp", desc=True) \
    .execute().data

df_notes = pd.DataFrame(notes_data)

if not df_notes.empty:
    df_notes_display = df_notes.drop(columns=["id"], errors="ignore")
    st.dataframe(df_notes_display, use_container_width=True)
else:
    st.info("لم يتم تسجيل أي إنجازات حتى الآن.")

# جلب قائمة الإنجازات من جدول achievements_list
achievements = supabase.table("achievements_list").select("*").execute().data
achievements_list = [row["الإنجاز"] for row in achievements]

# إدخال إنجاز جديد
with st.form("add_achievement_form"):
    st.markdown("### ➕ إضافة إنجاز جديد")
    selected_achievement = st.selectbox("اختر الإنجاز", achievements_list)
    submit_achievement = st.form_submit_button("✅ إضافة")

    if submit_achievement and selected_achievement:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        supabase.table("notes").insert({
            "timestamp": timestamp,
            "الطالب": username,
            "المشرف": mentor_name,
            "الملاحظة": selected_achievement
        }).execute()
        st.success("✅ تم تسجيل الإنجاز بنجاح.")
        st.experimental_rerun()
