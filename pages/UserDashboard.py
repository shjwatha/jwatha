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
    "🗒️ الإنجازات"
])

elif q_type == "checkbox":
    st.markdown(f"**{t_title}**")
    selected = []
    for opt in option_labels:
        if st.checkbox(opt, key=f"{t_id}_{opt}"):
            selected.append(opt)
    total_score = sum([option_map[opt] for opt in selected])
    responses.append((eval_date_str, username, mentor_name, t_title, total_score, ""))

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
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7))
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date())

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
