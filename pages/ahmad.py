import streamlit as st
import pymysql

# الاتصال بقاعدة بيانات MySQL
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


st.set_page_config(page_title="تحديث البنود المشوهة", layout="centered")
st.title("🛠️ تصحيح البنود المشوهة - self_assessment_options")

st.markdown("أدخل معرف البند (ID) والنص الجديد لإصلاح التشويه:")

with st.form("update_form"):
    col1, col2 = st.columns([1, 3])
    with col1:
        option_id = st.number_input("رقم البند (ID)", min_value=1, step=1)
    with col2:
        new_text = st.text_input("النص الصحيح للبند")

    submitted = st.form_submit_button("💾 تحديث البند")

if submitted:
    if not new_text.strip():
        st.error("⚠️ الرجاء إدخال نص جديد.")
    else:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE self_assessment_options SET option_text = %s WHERE id = %s", (new_text, option_id))
            conn.commit()
            cursor.close()
            conn.close()
            st.success(f"✅ تم تحديث البند رقم {option_id} بنجاح.")
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء التحديث: {e}")

