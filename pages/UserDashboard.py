import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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

# إعداد الصفحة
st.set_page_config(page_title="تقييم اليوم", page_icon="📝", layout="wide")

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

# استرجاع اسم المشرف للمستخدم
cursor.execute("SELECT mentor FROM users WHERE username = %s", (username,))
mentor_result = cursor.fetchone()
mentor_username = mentor_result["mentor"] if mentor_result else None


# التحقق من وجود تقييم سابق اليوم
today = datetime.now().date()
cursor.execute(
    "SELECT * FROM self_assessments WHERE username = %s AND DATE(created_at) = %s",
    (username, today)
)
existing_assessment = cursor.fetchone()

if existing_assessment:
    st.success("✅ لقد قمت بتعبئة تقييم اليوم مسبقًا.")
    st.stop()

st.title("📝 التقييم الذاتي اليومي")
st.markdown("يرجى تعبئة النموذج التالي بناءً على حالتك اليومية:")

# جلب بنود التقييم من قاعدة البيانات
cursor.execute("SELECT * FROM self_assessment_templates")
criteria = cursor.fetchall()

if not criteria:
    st.warning("⚠️ لم يتم إعداد نموذج التقييم الذاتي من قبل الإدارة بعد.")
    st.stop()

answers = {}
with st.form("self_assessment_form"):
    for criterion in criteria:
        qid = criterion["id"]
        question = criterion["question"]
        input_type = criterion["input_type"]

        cursor.execute("SELECT * FROM self_assessment_options WHERE question_id = %s", (qid,))
        options = cursor.fetchall()

        if input_type == "اختيار واحد":
            choice = st.radio(question, [opt["option_text"] for opt in options], key=f"q_{qid}")
            answers[qid] = [choice]

        elif input_type == "اختيار متعدد":
            selected = st.multiselect(question, [opt["option_text"] for opt in options], key=f"q_{qid}")
            answers[qid] = selected

    submitted = st.form_submit_button("✅ إرسال التقييم")

    if submitted:
        total_score = 0
        for qid, selected_options in answers.items():
            for opt_text in selected_options:
                cursor.execute(
                    "SELECT score FROM self_assessment_options WHERE question_id = %s AND option_text = %s",
                    (qid, opt_text)
                )
                opt_score = cursor.fetchone()
                if opt_score:
                    total_score += opt_score["score"]

        cursor.execute(
            "INSERT INTO self_assessments (username, score, created_at) VALUES (%s, %s, NOW())",
            (username, total_score)
        )
        conn.commit()
        st.success(f"✅ تم حفظ تقييمك اليومي. مجموع النقاط: {total_score} من أصل ممكن.")
        st.balloons()
        st.stop()

# عرض التقييمات السابقة
st.subheader("📊 سجل تقييماتك السابقة")

cursor.execute(
    "SELECT score, created_at FROM self_assessments WHERE username = %s ORDER BY created_at DESC LIMIT 30",
    (username,)
)
previous_scores = cursor.fetchall()

if previous_scores:
    df = pd.DataFrame(previous_scores)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["التاريخ الميلادي"] = df["created_at"].dt.strftime("%Y-%m-%d")
    df["التاريخ الهجري"] = df["created_at"].dt.date.apply(lambda x: Gregorian(x.year, x.month, x.day).to_hijri().isoformat())
    df["الدرجة"] = df["score"]
    st.dataframe(df[["التاريخ الهجري", "التاريخ الميلادي", "الدرجة"]], use_container_width=True)
else:
    st.info("🔍 لا توجد تقييمات سابقة.")

# إغلاق الاتصال بقاعدة البيانات
cursor.close()
conn.close()
