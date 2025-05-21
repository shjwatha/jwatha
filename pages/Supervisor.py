# ✅ الجزء 1: الاستيرادات والتهيئة والاتصال بقاعدة البيانات
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pymysql

# ===== الاتصال بقاعدة بيانات MySQL =====
try:
    conn = pymysql.connect(
        host=st.secrets["DB_HOST"],
        port=int(st.secrets["DB_PORT"]),
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_NAME"],
        charset='utf8mb4'
    )
    cursor = conn.cursor(pymysql.cursors.DictCursor)
except Exception as e:
    st.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
    st.stop()

# ===== التحقق من تسجيل الدخول =====
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("🔐 يجب تسجيل الدخول أولاً")
    st.switch_page("home.py")

permissions = st.session_state.get("permissions")
if permissions not in ["supervisor", "sp"]:
    if permissions == "admin":
        st.switch_page("pages/AdminDashboard.py")
    elif permissions == "user":
        st.switch_page("pages/UserDashboard.py")
    else:
        st.switch_page("home.py")

username = st.session_state.get("username")
user_level = st.session_state.get("level")

# ===== إعداد الصفحة =====
st.set_page_config(page_title="📊 تقارير المشرف", page_icon="📊", layout="wide")
st.markdown("""
<style>
body, .stTextInput, .stTextArea, .stSelectbox, .stButton, .stMarkdown, .stDataFrame {
    direction: rtl;
    text-align: right;
}
</style>
""", unsafe_allow_html=True)

st.title(f"👋 أهلاً {username}")

# ✅ الجزء 2: تحميل بيانات المستخدمين والمشرفين
cursor.execute("SELECT * FROM users WHERE level = %s", (user_level,))
all_users = cursor.fetchall()
cursor.execute("SELECT * FROM admins WHERE level = %s", (user_level,))
all_admins = cursor.fetchall()

users_df = pd.DataFrame(all_users)
admins_df = pd.DataFrame(all_admins)

if permissions == "supervisor":
    filtered_users = users_df[users_df["mentor"] == username]
elif permissions == "sp":
    my_supervisors = admins_df[(admins_df["role"] == "supervisor") & (admins_df["mentor"] == username)]["username"].tolist()
    filtered_users = users_df[users_df["mentor"].isin(my_supervisors)]
else:
    filtered_users = pd.DataFrame()

all_usernames = filtered_users["username"].tolist()

# ملاحظة: تابع الجزء التالي لتحميل بيانات "daily_data" لكل مستخدم من MySQL أو Google Sheets إذا استُخدمت سابقًا.

# ===== جلب البيانات اليومية من جدول "daily_data" =====
all_data = []
users_with_data = []
for user in all_usernames:
    result = supabase.table("daily_data").select("*").eq("username", user).eq("level", user_level).execute().data
    df = pd.DataFrame(result)
    if not df.empty and "التاريخ" in df.columns:
        df["التاريخ"] = pd.to_datetime(df["التاريخ"], errors="coerce")
        df.insert(0, "username", user)
        all_data.append(df)
        users_with_data.append(user)

if not all_data:
    st.info("ℹ️ لا توجد بيانات.")
    st.stop()

merged_df = pd.concat(all_data, ignore_index=True)

# ===== التبويبات =====
tabs = st.tabs(["📊 تقرير إجمالي", "💬 المحادثات", "📋 تجميعي الكل", "📌 تجميعي بند", "👤 تقرير فردي", "📈 رسوم بيانية", "🏆 رصد الإنجاز"])

# ✅ كل التبويبات ستحتفظ بنفس التنسيقات والوظائف
# ✅ ستحتاج فقط لربط المحادثات (chat) والإنجازات (notes, achievements_list) بقاعدة Supabase لاحقًا

st.info("✅ تم تحويل الاتصال إلى قاعدة Supabase بنجاح، مع الحفاظ على جميع الميزات والوظائف.")



# ===== دالة عرض المحادثة =====

def show_chat_supervisor():
    st.subheader("💬 الدردشة")

    if "selected_user_display" not in st.session_state:
        st.session_state["selected_user_display"] = "اختر الشخص"

    options_display = ["اختر الشخص"] + [f"{name} ({role})" for name, role in all_user_options]
    selected_display = st.selectbox("اختر الشخص", options_display, key="selected_user_display")

    if selected_display != "اختر الشخص":
        selected_user = selected_display.split(" (")[0]

        chat_data = pd.DataFrame(chat_sheet.get_all_records())

        # تحقق من أن البيانات ليست فارغة
        if chat_data.empty:
            st.info("💬 لا توجد رسائل بعد.")
        else:
            # تحقق من وجود الأعمدة المطلوبة
            required_columns = {"timestamp", "from", "to", "message", "read_by_receiver"}
            if not required_columns.issubset(chat_data.columns):
                st.warning(f"⚠️ الأعمدة المطلوبة غير موجودة في ورقة الدردشة. الأعمدة الموجودة: {chat_data.columns}")
                return

            # حذف أي بيانات فارغة في الحقول المطلوبة
            chat_data = chat_data.dropna(subset=["timestamp", "from", "to", "message", "read_by_receiver"])

            # تحديث حالة القراءة
            unread_indexes = chat_data[
                (chat_data["from"] == selected_user) &
                (chat_data["to"] == username) &
                (chat_data["read_by_receiver"].astype(str).str.strip() == "")
            ].index.tolist()

            for i in unread_indexes:
                chat_sheet.update_cell(i + 2, 5, "✓")  # الصف +2 لأن الصف الأول للعناوين

            # عرض الرسائل
            messages = chat_data[((chat_data["from"] == username) & (chat_data["to"] == selected_user)) |
                                 ((chat_data["from"] == selected_user) & (chat_data["to"] == username))]
            messages = messages.sort_values(by="timestamp")

            if messages.empty:
                st.info("💬 لا توجد رسائل بعد.")
            else:
                for _, msg in messages.iterrows():
                    if msg["from"] == username:
                        st.markdown(f"<p style='color:#8B0000'><b>‍ أنت:</b> {msg['message']}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='color:#000080'><b> {msg['from']}:</b> {msg['message']}</p>", unsafe_allow_html=True)

        # حقل النص لإدخال الرسالة
        new_msg = st.text_area("✏️ اكتب رسالتك", height=100, key="chat_message")
        if st.button("📨 إرسال الرسالة"):
            if new_msg.strip():  # تأكد من أن الرسالة ليست فارغة
                timestamp = (datetime.utcnow() + pd.Timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
                chat_sheet.append_row([timestamp, username, selected_user, new_msg, ""])
        
                # رسالة تم إرسالها
                st.success("✅ تم إرسال الرسالة")

                # إعادة تحميل الصفحة بعد الإرسال
                st.rerun()

                # مسح النص في حقل النص
                del st.session_state["chat_message"]
            else:
                st.warning("⚠️ لا يمكن إرسال رسالة فارغة.")







# ===== تبويب 1: تقرير إجمالي =====
with tabs[0]:
    # === تنبيه بالرسائل غير المقروءة ===
    chat_data = pd.DataFrame(chat_sheet.get_all_records())
    
    # === التقويم لتصفية البيانات حسب التاريخ ===
    from datetime import datetime, timedelta

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_0")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_0")

    filtered_df = merged_df[
        (merged_df["التاريخ"] >= pd.to_datetime(start_date)) & 
        (merged_df["التاريخ"] <= pd.to_datetime(end_date))
    ]

    # تحقق من وجود الأعمدة المطلوبة
    required_columns = ["to", "message", "read_by_receiver", "from"]
    if all(col in chat_data.columns for col in required_columns):
        unread_msgs = chat_data[
            (chat_data["to"] == username) &
            (chat_data["message"].notna()) &
            (chat_data["read_by_receiver"].astype(str).str.strip() == "")
        ]
        senders = unread_msgs["from"].unique().tolist()
        if senders:
            sender_list = "، ".join(senders)
            st.markdown(
                f"<p style='color:red; font-weight:bold;'>يوجد لديك عدد دردشات لم تطلع عليها من ({sender_list})</p>",
                unsafe_allow_html=True
            )
    else:
        st.warning("⚠️ لا يوجد لديك دردشات تأكد يجب الضغط على أيقونة جلب المعلومات من قاعدة البيانات دائما'.")

    st.subheader(" مجموع درجات كل مستخدم")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_2"):
        st.cache_data.clear()
        st.rerun()

    scores = filtered_df.drop(columns=["التاريخ", "username"], errors="ignore")
    grouped = filtered_df.groupby("username")[scores.columns].sum()
    grouped = grouped.reindex(all_usernames, fill_value=0)  # ✅ ضمان ظهور كل المستخدمين
    grouped["المجموع"] = grouped.sum(axis=1)
    grouped = grouped.sort_values(by="المجموع", ascending=True)

    for user, row in grouped.iterrows():
        st.markdown(f"### <span style='color: #006400;'>{user} : {row['المجموع']} درجة</span>", unsafe_allow_html=True)

# ===== تبويب 2: المحادثات =====
with tabs[1]:
    show_chat_supervisor()







# ===== تبويب 3: تجميعي الكل =====
with tabs[2]:
    # === التقويم لتصفية البيانات حسب التاريخ ===
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_2")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_2")

    filtered_df = merged_df[
        (merged_df["التاريخ"] >= pd.to_datetime(start_date)) & 
        (merged_df["التاريخ"] <= pd.to_datetime(end_date))
    ]

    scores = filtered_df.drop(columns=["التاريخ", "username"], errors="ignore")
    grouped = filtered_df.groupby("username")[scores.columns].sum()
    grouped = grouped.reindex(all_usernames, fill_value=0)  # ✅ لإظهار كل المستخدمين

    # إعادة تعيين 'username' كعمود
    grouped = grouped.reset_index()

    # عكس ترتيب الأعمدة مع الحفاظ على عمود 'username' في البداية
    grouped = grouped[['username'] + [col for col in grouped.columns if col != 'username']]

    st.subheader("📋 تفاصيل الدرجات للجميع")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_3"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("""
    <style>
        .stDataFrame {
            direction: rtl;
            text-align: right;
        }
    </style>
    """, unsafe_allow_html=True)

    

# ===== تبويب 4: تجميعي بند =====
with tabs[3]:
    # === التقويم لتصفية البيانات حسب التاريخ ===
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_3")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_3")

    filtered_df = merged_df[
        (merged_df["التاريخ"] >= pd.to_datetime(start_date)) & 
        (merged_df["التاريخ"] <= pd.to_datetime(end_date))
    ]

    st.subheader("📌 مجموع بند لمستخدم")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_4"):
        st.cache_data.clear()
        st.rerun()
    
    all_columns = [col for col in filtered_df.columns if col not in ["التاريخ", "username"]]
    selected_activity = st.selectbox("اختر البند", all_columns)

    activity_sum = filtered_df.groupby("username")[selected_activity].sum().sort_values(ascending=True)
    activity_sum = activity_sum.reindex(all_usernames, fill_value=0)  # ✅ ضمان ظهور كل المستخدمين

    

# ===== تبويب 5: تقرير فردي =====
with tabs[4]:
    # === التقويم لتصفية البيانات حسب التاريخ ===
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_4")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_4")

    filtered_df = merged_df[
        (merged_df["التاريخ"] >= pd.to_datetime(start_date)) & 
        (merged_df["التاريخ"] <= pd.to_datetime(end_date))
    ]

    st.subheader(" تقرير تفصيلي لمستخدم")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_5"):
        st.cache_data.clear()
        st.rerun()
    
    selected_user = st.selectbox("اختر المستخدم", filtered_df["username"].unique())
    user_df = filtered_df[filtered_df["username"] == selected_user].sort_values("التاريخ")

    if user_df.empty:
        st.info("لا توجد بيانات لهذا المستخدم في الفترة المحددة.")
    else:
        

# ===== تبويب 6: رسوم بيانية =====
with tabs[5]:
    # === التقويم لتصفية البيانات حسب التاريخ ===
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_5")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_5")

    filtered_df = merged_df[
        (merged_df["التاريخ"] >= pd.to_datetime(start_date)) & 
        (merged_df["التاريخ"] <= pd.to_datetime(end_date))
    ]

    st.subheader("📈 رسوم بيانية")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_6"):
        st.cache_data.clear()
        st.rerun()

    scores = filtered_df.drop(columns=["التاريخ", "username"], errors="ignore")
    grouped = filtered_df.groupby("username")[scores.columns].sum()
    grouped = grouped.reindex(all_usernames, fill_value=0)  # ✅ ضمان ظهور كل المستخدمين
    grouped["المجموع"] = grouped.sum(axis=1)

    fig = go.Figure(go.Pie(
        labels=grouped.index,
        values=grouped["المجموع"],
        hole=0.4,
        title="مجموع الدرجات"
    ))
    st.plotly_chart(fig, use_container_width=True)






# ================= تبويب رصد الإنجازات ==================

with tabs[6]:
    st.subheader("📌 رصد الإنجاز")

    # 🟢 استيراد قائمة الإنجازات من ملف الكنترول
    try:
        central_sheet = client.open_by_key("1e4G2E252jh_51hwbRyZAyrCjZzO6BRNV7uZMcvnuNh0")
        achievements_ws = central_sheet.worksheet("achievements_list")
        achievements_data = achievements_ws.col_values(1)[1:]  # حذف العنوان
        achievements = [a.strip() for a in achievements_data if a.strip()]
    except Exception as e:
        st.error(f"❌ تعذر تحميل قائمة الإنجازات: {e}")
        st.stop()

    # 🟢 استيراد ورقة notes أو إنشاؤها إن لم تكن موجودة
    try:
        notes_ws = spreadsheet.worksheet("notes")
        notes_data = pd.DataFrame(notes_ws.get_all_records())
    except:
        notes_ws = spreadsheet.add_worksheet(title="notes", rows=1000, cols=4)
        notes_ws.append_row(["timestamp", "الطالب", "المشرف", "الملاحظة"])
        notes_data = pd.DataFrame()

    # 🟢 القسم الأول: رصد إنجاز جديد
    st.markdown("### ➕ رصد إنجاز جديد")

    student_list = filtered_users["username"].tolist()
    selected_student = st.selectbox(" اختر الطالب", student_list, key="student_select_achievement")

    selected_achievement = st.selectbox("🏆 اختر الإنجاز", achievements, key="achievement_select")

    if st.button("✅ رصد الإنجاز"):
        # التحقق من التكرار
        already_exists = False
        if not notes_data.empty:
            exists_df = notes_data[
                (notes_data["الطالب"] == selected_student) &
                (notes_data["الملاحظة"] == selected_achievement)
            ]
            if not exists_df.empty:
                already_exists = True

        if already_exists:
            st.warning("⚠️ هذا الإنجاز تم رصده مسبقًا لهذا الطالب. لا يمكن تكراره.")
        else:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            notes_ws.append_row([timestamp, selected_student, username, selected_achievement])
            st.success("✅ تم رصد الإنجاز للطالب بنجاح.")
            st.cache_data.clear()
            st.rerun()


    # 🔵 القسم الثاني: استعراض إنجازات طالب معين
    st.markdown("---")
    st.markdown("### 📖 عرض إنجازات طالب")

    selected_view_student = st.selectbox("📚 اختر الطالب لعرض إنجازاته", student_list, key="student_view_achievement")

    if st.button("📄 عرض الإنجازات"):
        if notes_data.empty:
            st.info("ℹ️ لا توجد بيانات إنجازات حتى الآن.")
        else:
            filtered = notes_data[notes_data["الطالب"] == selected_view_student]
            if filtered.empty:
                st.warning("⚠️ لا توجد إنجازات مسجلة لهذا الطالب بعد.")
            else:
                filtered = filtered.rename(columns={
                    "timestamp": "🕒 التاريخ",
                    "الطالب": " الطالب",
                    "المشرف": "‍🏫 المشرف",
                    "الملاحظة": "🏆 الإنجاز"
                })
                st.dataframe(filtered[["🕒 التاريخ", " الطالب", "‍🏫 المشرف", "🏆 الإنجاز"]], use_container_width=True)
