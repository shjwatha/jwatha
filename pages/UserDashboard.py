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
    mentor_name = mentor_row["mentor"] if mentor_row else None

    if not mentor_name:
        st.error("⚠️ لا يوجد مشرف مرتبط بهذا الحساب. يرجى مراجعة الإدارة.")
        st.stop()

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



# ===================== تبويب 1: إدخال البيانات (نموذج ديناميكي من قاعدة البيانات) =====================
# جلب المستوى الحالي للمستخدم
try:
# جلب المستوى والتحقق من مطابقته مع المستويات المعتمدة
    cursor.execute("SELECT level FROM users WHERE username = %s AND is_deleted = FALSE", (username,))
    level_row = cursor.fetchone()
    user_level = level_row["level"] if level_row else "غير معروف"

# جلب المستويات من جدول levels
    cursor.execute("SELECT level_name FROM levels")
    valid_levels = [row["level_name"] for row in cursor.fetchall() if row["level_name"]]

    if user_level not in valid_levels:
        st.error("⚠️ مستوى المستخدم غير موجود ضمن المستويات المعتمدة.")
        st.stop()

except Exception as e:
    st.error(f"❗️ فشل في جلب مستوى المستخدم: {e}")
    user_level = "غير معروف"


with tabs[0]:
    st.markdown(f"<h3 style='color:#0000FF; font-weight:bold;'>👋 أهلاً {username} | مجموعتك: {mentor_name} | مستواك: {user_level}</h3>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#0000FF; font-weight:bold;'>📝 المحاسبة الذاتية اليومية (نموذج مخصص)</h4>", unsafe_allow_html=True)

    with st.form("dynamic_evaluation_form"):
        today = datetime.today().date()
        hijri_dates = []
        for i in range(7):
            g_date = today - timedelta(days=i)
            h_date = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
            weekday = g_date.strftime("%A")
            arabic_weekday = {
                "Saturday": "السبت", "Sunday": "الأحد", "Monday": "الاثنين",
                "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
                "Thursday": "الخميس", "Friday": "الجمعة"
            }[weekday]
            label = f"{arabic_weekday} - {g_date.day}/{g_date.month}/{g_date.year}"
            hijri_dates.append((label, g_date))
        hijri_labels = [label for label, _ in hijri_dates]
        selected_label = st.selectbox("📅 اختر التاريخ", hijri_labels)
        selected_date = dict(hijri_dates)[selected_label]
        eval_date_str = selected_date.strftime("%Y-%m-%d")

        # جلب البنود من قاعدة البيانات حسب مستوى المستخدم
        try:
            cursor.execute(
                "SELECT id, question FROM self_assessment_templates WHERE is_deleted = 0 AND level = %s ORDER BY id ASC",
                (user_level,)
            )
            templates = cursor.fetchall()
        except Exception as e:
            st.error(f"❗️ فشل في تحميل البنود: {e}")
            templates = []

        responses = []
        if templates:
            for t in templates:
                t_id = t["id"]
                t_title = t["question"]
                try:
                    cursor.execute(
                        "SELECT option_text, score FROM self_assessment_options WHERE question_id = %s AND is_deleted = 0 ORDER BY id ASC",
                        (t_id,)
                    )
                    options = cursor.fetchall()
                    if options:
                        option_labels = [f"{o['option_text']} ({o['score']} نقاط)" for o in options]
                        option_map = dict(zip(option_labels, [o['score'] for o in options]))
                        selected = st.radio(t_title, option_labels, key=t_title)
                        responses.append((eval_date_str, username, mentor_name, t_title, option_map[selected]))
                    else:
                        st.warning(f"⚠️ لا توجد خيارات للبند: {t_title}")
                except Exception as e:
                    st.error(f"❗️ خطأ أثناء تحميل خيارات البند '{t_title}': {e}")
        else:
            st.info("ℹ️ لا توجد بنود نشطة لهذا المستوى. تأكد أن المشرف العام أعدّ النموذج.")

        if st.form_submit_button("📏 حفظ"):
            if responses:
                try:
                    cursor.execute(
                        "DELETE FROM daily_evaluations WHERE student = %s AND DATE(timestamp) = %s",
                        (username, eval_date_str)
                    )
                    for row in responses:
                        cursor.execute(
                            "INSERT INTO daily_evaluations (timestamp, student, supervisor, question, score) VALUES (%s, %s, %s, %s, %s)",
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *row)
                        )
                    conn.commit()
                    st.success("✅ تم حفظ التقييم بنجاح.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❗️ خطأ أثناء حفظ البيانات: {e}")
            else:
                st.warning("⚠️ لا توجد إجابات لحفظها.")
# ===================== تبويب 2: المحادثات =====================
with tabs[1]:
    st.subheader("💬 المحادثة مع المشرف")

    options = []

    try:
        # الخطوة 1: جلب المشرف المباشر للمستخدم
        cursor.execute("SELECT mentor FROM users WHERE username = %s AND is_deleted = FALSE", (username,))
        user_row = cursor.fetchone()
        if user_row and user_row["mentor"]:
            mentor_1 = user_row["mentor"]
            options.append(mentor_1)

            # الخطوة 2: جلب مشرف المشرف (السوبر مشرف)
            cursor.execute("SELECT mentor FROM users WHERE username = %s AND is_deleted = FALSE", (mentor_1,))
            super_row = cursor.fetchone()
            if super_row and super_row["mentor"]:
                mentor_2 = super_row["mentor"]
                if mentor_2 not in options:
                    options.append(mentor_2)

    except Exception as e:
        st.error(f"❌ فشل تحميل قائمة المشرفين: {e}")

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
