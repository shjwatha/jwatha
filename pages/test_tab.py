import streamlit as st
import pymysql

# الاتصال
conn = pymysql.connect(
    host="localhost",
    user="your_user",
    password="your_pass",
    database="zad_DB",
    charset="utf8mb4"
)
cursor = conn.cursor(pymysql.cursors.DictCursor)

st.title("🚧 اختبار: اختيار المستوى والنموذج فقط")

# اختيار المستوى
cursor.execute("SELECT DISTINCT level_name FROM levels")
levels = [row["level_name"] for row in cursor.fetchall()]
selected_level = st.selectbox("📚 اختر المستوى", levels)

# اختيار نموذج
cursor.execute("SELECT DISTINCT form_name FROM self_assessment_templates WHERE level = %s", (selected_level,))
forms = [row["form_name"] for row in cursor.fetchall() if row["form_name"]]
form_display = ["➕ نموذج جديد"] + forms
selected_form = st.selectbox("🗂️ اختر النموذج", form_display)

