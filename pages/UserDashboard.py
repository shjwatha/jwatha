import streamlit as st
import pandas as pd
from datetime import datetime
from hijri_converter import Gregorian
import pymysql

# التحقق من تسجيل الدخول
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.switch_page("home.py")

if st.session_state["permissions"] != "user":
    if st.session_state["permissions"] == "admin":
        st.switch_page("pages/AdminDashboard.py")
    elif st.session_state["permissions"] in ["supervisor", "sp"]:
        st.switch_page("pages/Supervisor.py")
    else:
        st.error("❌ صلاحية غير معروفة")
        st.stop()

username = st.session_state["username"]
user_level = st.session_state["level"]

st.set_page_config(page_title="لوحة المستخدم", page_icon="🧑", layout="wide")
st.title("🧑 لوحة التحكم الخاصة بك")

# الاتصال بقاعدة البيانات
conn = pymysql.connect(
    host=st.secrets["DB_HOST"],
    port=int(st.secrets["DB_PORT"]),
    user=st.secrets["DB_USER"],
    password=st.secrets["DB_PASSWORD"],
    database=st.secrets["DB_NAME"],
    charset='utf8mb4'
)
cursor = conn.cursor(pymysql.cursors.DictCursor)

# جلب اسم المشرف
cursor.execute("SELECT mentor FROM users WHERE username = %s", (username,))
mentor_result = cursor.fetchone()
mentor_username = mentor_result["mentor"] if mentor_result else None

# التبويبات
tabs = st.tabs(["📝 التقييم الذاتي", "📊 سجل التقييمات", "💬 ملاحظات المشرف"])

with tabs[0]:
    st.subheader("📝 التقييم الذاتي اليومي")

    # تحقق من التقييم السابق
    today = datetime.now().date()
    cursor.execute("SELECT * FROM self_assessments WHERE username = %s AND DATE(created_at) = %s", (username, today))
    if cursor.fetchone():
        st.success("✅ لقد قمت بتعبئة تقييم اليوم مسبقًا.")
        st.stop()

    # تحميل البنود من القاعدة
    cursor.execute("SELECT * FROM self_assessment_templates")
    criteria = cursor.fetchall()

    if not criteria:
        st.warning("⚠️ لم يتم إعداد نموذج التقييم بعد.")
        st.stop()

    answers = {}
    with st.form("daily_form"):
        for criterion in criteria:
            qid = criterion["id"]
            question = criterion["question"]
            input_type = criterion["input_type"]

            cursor.execute("SELECT * FROM self_assessment_options WHERE question_id = %s", (qid,))
            options = cursor.fetchall()

            if input_type == "اختيار واحد":
                selected = st.radio(question, [opt["option_text"] for opt in options], key=f"radio_{qid}")
                answers[qid] = [selected]
            elif input_type == "اختيار متعدد":
                selected = st.multiselect(question, [opt["option_text"] for opt in options], key=f"multi_{qid}")
                answers[qid] = selected

        submitted = st.form_submit_button("📥 إرسال التقييم")
        if submitted:
            total_score = 0
            for qid, selected_options in answers.items():
                for opt_text in selected_options:
                    cursor.execute("SELECT score FROM self_assessment_options WHERE question_id = %s AND option_text = %s", (qid, opt_text))
                    result = cursor.fetchone()
                    if result:
                        total_score += result["score"]

            cursor.execute("INSERT INTO self_assessments (username, score, created_at) VALUES (%s, %s, NOW())", (username, total_score))
            conn.commit()
            st.success(f"✅ تم حفظ التقييم بنجاح. مجموع النقاط: {total_score}")
            st.balloons()
            st.stop()


with tabs[1]:
    st.subheader("📊 سجل التقييمات السابقة")

    cursor.execute(
        "SELECT score, created_at FROM self_assessments WHERE username = %s ORDER BY created_at DESC LIMIT 30",
        (username,)
    )
    assessments = cursor.fetchall()

    if assessments:
        df = pd.DataFrame(assessments)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["التاريخ الميلادي"] = df["created_at"].dt.strftime("%Y-%m-%d")
        df["التاريخ الهجري"] = df["created_at"].dt.date.apply(
            lambda x: Gregorian(x.year, x.month, x.day).to_hijri().isoformat()
        )
        df["الدرجة"] = df["score"]
        st.dataframe(df[["التاريخ الهجري", "التاريخ الميلادي", "الدرجة"]], use_container_width=True)
    else:
        st.info("🔍 لا توجد تقييمات مسجلة بعد.")

with tabs[2]:
    st.subheader("💬 ملاحظات المشرف")

    cursor.execute(
        "SELECT note, created_at, sender FROM supervisor_notes WHERE recipient = %s ORDER BY created_at DESC",
        (username,)
    )
    notes = cursor.fetchall()

    if notes:
        notes_df = pd.DataFrame(notes)
        notes_df["created_at"] = pd.to_datetime(notes_df["created_at"])
        notes_df["التاريخ"] = notes_df["created_at"].dt.strftime("%Y-%m-%d %H:%M")
        notes_df.rename(columns={
            "note": "الملاحظة",
            "sender": "المُرسل"
        }, inplace=True)
        st.dataframe(notes_df[["الملاحظة", "المُرسل", "التاريخ"]], use_container_width=True)
    else:
        st.info("📭 لا توجد ملاحظات بعد.")


# ✅ إغلاق الاتصال بقاعدة البيانات بعد انتهاء التبويبات
cursor.close()
conn.close()
