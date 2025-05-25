import streamlit as st
import pandas as pd
import pymysql
import pytz
from datetime import datetime, timedelta
from hijri_converter import Gregorian

# تحديد توقيت الرياض
riyadh_tz = pytz.timezone("Asia/Riyadh")


# ===================== إعداد الصفحة والتحقق من الجلسة =====================
st.set_page_config(page_title="تقييم اليوم", page_icon="📋", layout="wide")


# ===== ضبط اتجاه النص من اليمين لليسار =====
st.markdown("""
<style>
body {
    direction: rtl;
    text-align: right;
}
</style>
""", unsafe_allow_html=True)



# التحقق من الجلسة
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("🔐 يجب تسجيل الدخول أولاً")
    st.switch_page("home.py")

if st.session_state.get("permissions") != "user":
    st.warning("🚫 لا تملك صلاحية الوصول لهذه الصفحة.")
    st.switch_page("home.py")


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

# ===================== إشعار عند وجود رسائل غير مقروءة =====================
try:
    cursor.execute("""
        SELECT DISTINCT sender 
        FROM chat_messages 
        WHERE receiver = %s AND read_by_receiver = 0
    """, (username,))
    unread_senders = [row["sender"] for row in cursor.fetchall()]
except Exception as e:
    unread_senders = []

if unread_senders:
    names_str = " - ".join(unread_senders)
    st.markdown(
        f"""
        <div style='background-color:#FFF4CC; padding:12px; border-radius:6px; border:1px solid #FFD700; margin-bottom: 20px;'>
            <span style='color:red; font-weight:bold; font-size:16px;'>📨 لديك رسائل جديدة من: {names_str}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# ===================== التبويبات =====================
tabs = st.tabs([
    "📝 إدخال البيانات", 
    "💬 المحادثات", 
    "📊 تقارير المجموع", 
    "🗒️ الإنجازات",
    "🏅 نقاط تقييم المشرف"
])

# ===================== تبويب 1: إدخال البيانات =====================
try:
    cursor.execute("SELECT level FROM users WHERE username = %s AND is_deleted = FALSE", (username,))
    level_row = cursor.fetchone()
    user_level = level_row["level"] if level_row else "غير معروف"

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

    today = datetime.now(riyadh_tz).date()
    hijri_dates = []
    for i in range(7):
        g_date = today - timedelta(days=i)
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

    # اختيار النموذج المتاح
    try:
        cursor.execute("SELECT DISTINCT form_name FROM self_assessment_templates WHERE is_deleted = 0 AND level = %s", (user_level,))
        form_rows = cursor.fetchall()
        available_forms = [row["form_name"] for row in form_rows if row["form_name"]]
    except Exception as e:
        st.error(f"❗️ فشل في تحميل النماذج: {e}")
        available_forms = []

    if not available_forms:
        st.info("ℹ️ لا توجد نماذج تقييم متاحة لهذا المستوى.")
        st.stop()

    if len(available_forms) == 1:
        selected_form = available_forms[0]
        st.info(f"📄 النموذج المختار تلقائيًا: {selected_form}")
    else:
        selected_form = st.selectbox("📄 اختر النموذج", available_forms, key="selected_form")

    with st.form("dynamic_evaluation_form"):
        try:
            cursor.execute("""
                SELECT id, question, input_type 
                FROM self_assessment_templates 
                WHERE is_deleted = 0 AND level = %s AND form_name = %s 
                ORDER BY id ASC
            """, (user_level, selected_form))
            templates = cursor.fetchall()
        except Exception as e:
            st.error(f"❗️ فشل في تحميل البنود: {e}")
            templates = []

        responses = []
        if templates:
            for t in templates:
                t_id = t["id"]
                t_title = t["question"]
                q_type = t["input_type"]

                try:
                    if q_type == "text":
                        user_input = st.text_area(t_title, key=f"text_{t_id}", max_chars=200)
                        responses.append((eval_date_str, username, mentor_name, t_title, 0, user_input.strip()))

                    else:
                        cursor.execute("SELECT option_text, score FROM self_assessment_options WHERE question_id = %s AND is_deleted = 0 ORDER BY id ASC", (t_id,))
                        options = cursor.fetchall()
                        option_labels = [f"{o['option_text']} ({o['score']} نقاط)" for o in options]
                        option_map = dict(zip(option_labels, [o['score'] for o in options]))

                        if q_type == "radio":
                            selected = st.radio(t_title, option_labels, key=f"radio_{t_id}")
                            responses.append((eval_date_str, username, mentor_name, t_title, option_map[selected], ""))

                        elif q_type == "select":
                            selected = st.selectbox(t_title, option_labels, key=f"select_{t_id}")
                            responses.append((eval_date_str, username, mentor_name, t_title, option_map[selected], ""))

                        elif q_type == "checkbox":
                            st.markdown(f"**{t_title}**")
                            selected = []
                            for opt in option_labels:
                                checkbox_key = f"{t_id}_{opt}"
                                if st.checkbox(opt, key=checkbox_key):
                                    selected.append(opt)
                            total_score = sum([option_map[opt] for opt in selected])
                            responses.append((eval_date_str, username, mentor_name, t_title, total_score, ""))






                        else:
                            st.warning(f"⚠️ نوع السؤال غير مدعوم: {q_type}")
                except Exception as e:
                    st.error(f"❗️ خطأ أثناء تحميل خيارات البند '{t_title}': {e}")
        else:
            st.info("ℹ️ لا توجد بنود نشطة لهذا النموذج.")

        if st.form_submit_button("📏 حفظ"):
            if responses:
                try:
                    cursor.execute("DELETE FROM daily_evaluations WHERE student = %s AND DATE(timestamp) = %s", (username, eval_date_str))
                    for eval_row in responses:
                        academic_year = f"{selected_date.year}-{selected_date.year + 1}"
                        cursor.execute("""
                            INSERT INTO daily_evaluations (timestamp, student, supervisor, question, score, free_text, academic_year)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            datetime.now(riyadh_tz).strftime("%Y-%m-%d %H:%M:%S"),
                            eval_row[1], eval_row[2], eval_row[3], eval_row[4], eval_row[5], academic_year
                        ))

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
        cursor.execute("SELECT mentor FROM users WHERE username = %s AND is_deleted = FALSE", (username,))
        user_row = cursor.fetchone()
        if user_row and user_row["mentor"]:
            mentor_1 = user_row["mentor"]
            options.append(mentor_1)

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
                if msg["sender"] == username:
                    check_icon = "✅" if msg["read_by_receiver"] == 1 else "☑️"
                else:
                    check_icon = ""
                ts = msg["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                time_str = ts.strftime("%I:%M %p - %Y/%m/%d").replace("AM", "صباحًا").replace("PM", "مساءً")
                st.markdown(
                    f"""
                    <div style='color:{color}; margin-bottom:2px;'>
                        <b>{sender_label}:</b> {msg['message']} <span style='float:left;'>{check_icon}</span>
                        <br><span style='font-size:11px; color:gray;'>{time_str}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("💬 لا توجد رسائل بعد.")

        # ✅ حقل الإدخال
        if "new_msg" not in st.session_state:
            st.session_state["new_msg"] = ""

        new_msg = st.text_area("✏️ اكتب رسالتك", height=100, key="new_msg")

        if st.button("📨 إرسال الرسالة"):
            if new_msg.strip():
                ts = datetime.now(riyadh_tz).strftime("%Y-%m-%d %H:%M:%S")
                try:
                    cursor.execute(
                        "INSERT INTO chat_messages (timestamp, sender, receiver, message, read_by_receiver) VALUES (%s, %s, %s, %s, %s)",
                        (ts, username, selected_mentor, new_msg.strip(), 0)
                    )
                    conn.commit()
                    st.success("✅ تم إرسال الرسالة")
                    # نحذف الرسالة ونعيد تحميل الصفحة
                    del st.session_state["new_msg"]
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ فشل الإرسال: {e}")
            else:
                st.warning("⚠️ لا يمكن إرسال رسالة فارغة.")

# ===================== تبويب 3: تقارير المجموع =====================

with tabs[2]:
    st.subheader("📊 تقارير الأداء خلال فترة")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.now(riyadh_tz).date() - timedelta(days=7))
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.now(riyadh_tz).date())

    # اختيار النموذج
    try:
        cursor.execute("""
            SELECT DISTINCT form_name 
            FROM self_assessment_templates 
            WHERE is_deleted = 0 AND level = %s
        """, (user_level,))
        form_rows = cursor.fetchall()
        available_forms = [row["form_name"] for row in form_rows if row["form_name"]]
    except Exception as e:
        st.error(f"❗️ فشل في تحميل النماذج: {e}")
        available_forms = []

    if not available_forms:
        st.warning("⚠️ لا توجد نماذج متاحة.")
        st.stop()

    if len(available_forms) == 1:
        selected_form = available_forms[0]
        st.info(f"📄 النموذج المختار تلقائيًا: {selected_form}")
    else:
        selected_form = st.selectbox("📄 اختر النموذج", available_forms, key="selected_form_report")

    # تحميل التقييمات من daily_evaluations
    try:
        df = pd.read_sql("""
            SELECT DATE(timestamp) AS التاريخ, question AS البند, score AS الدرجة, free_text
            FROM daily_evaluations
            WHERE student = %s AND DATE(timestamp) BETWEEN %s AND %s
            ORDER BY timestamp DESC
        """, conn, params=(username, start_date, end_date))
    except Exception as e:
        st.error(f"❌ فشل في تحميل التقارير: {e}")
        df = pd.DataFrame()

    # جلب بنود النموذج لتصفية الأسئلة المطلوبة
    try:
        cursor.execute("""
            SELECT question, input_type 
            FROM self_assessment_templates 
            WHERE level = %s AND form_name = %s AND is_deleted = 0
        """, (user_level, selected_form))
        qrows = cursor.fetchall()
        form_questions = [row["question"] for row in qrows]
        text_questions = [row["question"] for row in qrows if row["input_type"] == "text"]
    except Exception as e:
        st.error(f"❗️ فشل في جلب بنود النموذج: {e}")
        form_questions = []
        text_questions = []

    if not df.empty and form_questions:
        df = df[df["البند"].isin(form_questions)]

        # تقسيم الإجابات النصية عن الإجابات بالدرجات
        df_text = df[df["البند"].isin(text_questions)]
        df_scored = df[~df["البند"].isin(text_questions)]

        # عرض الدرجات
        if not df_scored.empty:
            summary = df_scored.groupby(["التاريخ", "البند"]).sum().reset_index()
            pivoted = summary.pivot(index="التاريخ", columns="البند", values="الدرجة").fillna(0)
            pivoted.insert(0, "📊 المجموع", pivoted.sum(axis=1))

            st.markdown("### 📈 تقييم البنود القابلة للتقدير")
            st.dataframe(pivoted, use_container_width=True)

        # عرض النصوص
        if not df_text.empty:
            df_text = df_text[df_text["free_text"].notnull() & (df_text["free_text"].str.strip() != "")]
            if not df_text.empty:
                st.markdown("### 📝 إجابات المستخدم للأسئلة النصية")
                st.dataframe(
                    df_text[["التاريخ", "البند", "free_text"]].rename(columns={"free_text": "الإجابة النصية"}),
                    use_container_width=True
                )
            else:
                st.info("ℹ️ لا توجد إجابات نصية محفوظة.")
    else:
        st.info("ℹ️ لا توجد بيانات في الفترة المحددة أو لهذا النموذج.")


# ===================== تبويب 4: الإنجازات =====================
with tabs[3]:
    st.subheader("🏆 إنجازاتي")

    try:
        df_ach = pd.read_sql("""
            SELECT sa.timestamp, al.achievement, sa.supervisor
            FROM student_achievements sa
            JOIN achievements_list al ON sa.achievement_id = al.id
            WHERE sa.student = %s
            ORDER BY sa.timestamp DESC
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


# ===================== تبويب 5: نقاط المشرف =====================
with tabs[4]:
    st.subheader("🏅 نقاط تقييم المشرف")

    try:
        # جلب البنود التي يسمح بعرضها للمستخدم
        cursor.execute("""
            SELECT question FROM supervisor_criteria
            WHERE is_visible_to_user = TRUE
        """)
        visible_criteria = [row["question"] for row in cursor.fetchall()]

        # جلب تقييم المشرف فقط للبنود المسموح عرضها
        cursor.execute("""
            SELECT DATE(timestamp) AS التاريخ, question AS البند, score AS الدرجة
            FROM supervisor_evaluations
            WHERE student = %s
            ORDER BY timestamp DESC
        """, (username,))
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)

        if df.empty or not visible_criteria:
            st.info("ℹ️ لا توجد نقاط متاحة للعرض من المشرف.")
        else:
            df = df[df["البند"].isin(visible_criteria)]
            pivoted = df.pivot_table(index="التاريخ", columns="البند", values="الدرجة", aggfunc='sum').fillna(0)
            pivoted.insert(0, "📊 المجموع", pivoted.sum(axis=1))

            st.markdown("### 🧾 النقاط التي رصدها المشرف والمسموح لك برؤيتها")
            st.dataframe(pivoted, use_container_width=True)
    except Exception as e:
        st.error(f"❌ فشل في تحميل نقاط المشرف: {e}")


# ===================== إغلاق الاتصال =====================
cursor.close()
conn.close()
