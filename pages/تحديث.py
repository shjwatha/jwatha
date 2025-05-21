import streamlit as st
import pymysql
import pandas as pd

# ===== إعداد صفحة Streamlit =====
st.set_page_config(layout="wide", page_title="📊 جلب المعلومات")
st.title("📊 جلب المعلومات من قاعدة البيانات")

# ===== شعار قابل للنقر =====
st.markdown("""
<style>
@media (max-width: 768px) {
    .responsive-logo {
        height: 100px !important;
    }
}
@media (min-width: 769px) {
    .responsive-logo {
        height: 200px !important;
    }
}
</style>
<div style="text-align: center; margin-top: 20px;">
    <a href="https://self-discipline-emwsdnb4myfqwcr6cqrmic.streamlit.app/" target="_blank">
        <img class="responsive-logo" src="https://self-discipline-emwsdnb4myfqwcr6cqrmic.streamlit.app/" alt="الصفحة الرئيسية">
    </a>
</div>
""", unsafe_allow_html=True)

# ===== تحميل البيانات من MySQL =====
@st.cache_data
def load_data():
    try:
        conn = pymysql.connect(
            host=st.secrets["DB_HOST"],
            port=int(st.secrets["DB_PORT"]),
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            charset='utf8mb4'
        )
        df = pd.read_sql("SELECT * FROM users", conn)
        return df
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء جلب البيانات: {e}")
        return pd.DataFrame()

# ===== زر التحديث فقط =====
if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_top"):
    st.cache_data.clear()
    df = load_data()
    if not df.empty:
        st.success("✅ تم جلب البيانات بنجاح")
        st.dataframe(df.drop(columns=['username', 'password'], errors='ignore'))  # إخفاء الحقول الحساسة
    else:
        st.info("ℹ️ لا توجد بيانات لعرضها.")
