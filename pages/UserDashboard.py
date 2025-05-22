import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime, timedelta
from hijri_converter import Gregorian

# ===================== إعداد الصفحة والتحقق من الجلسة =====================
st.set_page_config(page_title="تقييم اليوم", page_icon="📋", layout="wide")

# التحقق من الجلسة
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("❌ يجب تسجيل الدخول أولاً.")
    st.stop()

if "username" not in st.session_state:
    st.error("❌ بيانات المستخدم غير متاحة.")
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

# ===================== الاتصال بقاعدة البيانات =====================
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

# ===================== جلب اسم المشرف =====================
try:
    cursor.execute("SELECT mentor FROM users WHERE username = %s AND is_deleted = FALSE", (username,))
    mentor_row = cursor.fetchone()
    mentor_name = mentor_row["mentor"] if mentor_row else "غير معروف"
except Exception as e:
    st.error(f"❌ فشل في جلب اسم المشرف: {e}")
    mentor_name = "غير معروف"

# ===================== التبويبات =====================
tabs = st.tabs([
    "📝 إدخال البيانات", 
    "💬 المحادثات", 
    "📊 تقارير المجموع", 
    "🗒️ الإنجازات"
])


# ===================== تبويب 2: المحادثات =====================
with tabs[1]:
    st.subheader("💬 المحادثة مع المشرف")

    options = [mentor_name]
    cursor.execute("SELECT mentor FROM users WHERE username = %s", (mentor_name,))
    sp = cursor.fetchone()
    if sp and sp["mentor"]:
        options.append(sp["mentor"])

    selected_mentor = st.selectbox("اختر الشخص للمراسلة", ["اختر الشخص"] + options)
    if selected_mentor != "اختر الشخص":
        try:
            chat_df = pd.read_sql("SELECT * FROM chat_messages", conn)
        except Exception as e:
            st.error(f"❌ فشل تحميل المحادثات: {e}")
            chat_df = pd.DataFrame()

        if not chat_df.empty:
            unread = chat_df[
                (chat_df["sender"] == selected_mentor) &
                (chat_df["receiver"] == username) &
                (chat_df["read_by_receiver"] == 0)
            ]
            for _, msg in unread.iterrows():
                cursor.execute("UPDATE chat_messages SET read_by_receiver = 1 WHERE id = %s", (msg["id"],))
                conn.commit()

            msgs = chat_df[
                ((chat_df["sender"] == username) & (chat_df["receiver"] == selected_mentor)) |
                ((chat_df["sender"] == selected_mentor) & (chat_df["receiver"] == username))
            ].sort_values("timestamp")

            for _, msg in msgs.iterrows():
                sender_label = "أنت" if msg["sender"] == username else msg["sender"]
                color = "#8B0000" if msg["sender"] == username else "#000080"
                st.markdown(f"<p style='color:{color};'><b>{sender_label}:</b> {msg['message']}</p>", unsafe_allow_html=True)
        else:
            st.info("💬 لا توجد رسائل بعد.")

        new_msg = st.text_area("✏️ اكتب رسالتك", height=100)
        if st.button("📨 إرسال الرسالة"):
            if new_msg.strip():
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    cursor.execute(
                        "INSERT INTO chat_messages (timestamp, sender, receiver, message, read_by_receiver) VALUES (%s, %s, %s, %s, %s)",
                        (ts, username, selected_mentor, new_msg, 0)
                    )
                    conn.commit()
                    st.success("✅ تم إرسال الرسالة")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ فشل الإرسال: {e}")
            else:
                st.warning("⚠️ لا يمكن إرسال رسالة فارغة.")

# ===================== تبويب 3: تقارير المجموع =====================
with tabs[2]:
    st.subheader("📊 تقارير الأداء خلال فترة")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7))
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date())

    try:
        df = pd.read_sql("""
            SELECT DATE(timestamp) AS التاريخ, question AS البند, score AS الدرجة
            FROM daily_evaluations
            WHERE student = %s AND DATE(timestamp) BETWEEN %s AND %s
            ORDER BY timestamp DESC
        """, conn, params=(username, start_date, end_date))
    except Exception as e:
        st.error(f"❌ فشل في تحميل التقارير: {e}")
        df = pd.DataFrame()

    if not df.empty:
        summary = df.groupby(["التاريخ", "البند"]).sum().reset_index()
        pivoted = summary.pivot(index="التاريخ", columns="البند", values="الدرجة").fillna(0)
        st.dataframe(pivoted, use_container_width=True)
    else:
        st.info("ℹ️ لا توجد بيانات في الفترة المحددة.")

# ===================== تبويب 4: الإنجازات =====================
with tabs[3]:
    st.subheader("🏆 إنجازاتي")

    try:
        df_ach = pd.read_sql("""
            SELECT timestamp, achievement, supervisor 
            FROM student_achievements 
            WHERE student = %s ORDER BY timestamp DESC
        """, conn, params=(username,))
    except Exception as e:
        st.error(f"❌ فشل في تحميل الإنجازات: {e}")
        df_ach = pd.DataFrame()

    if not df_ach.empty:
        df_ach.rename(columns={
            "timestamp": "🕒 التاريخ",
            "achievement": "🏆 الإنجاز",
            "supervisor": "📌 بواسطة"
        }, inplace=True)
        st.dataframe(df_ach, use_container_width=True)
    else:
        st.info("ℹ️ لم يتم تسجيل أي إنجازات بعد.")

# ===================== إغلاق الاتصال =====================
cursor.close()
conn.close()
