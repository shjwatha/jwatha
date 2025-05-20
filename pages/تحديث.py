import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ===== إعداد صفحة Streamlit =====
st.set_page_config(layout="wide", page_title="📊 جلب المعلومات")
st.title("📊 معلومات المستخدمين")

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

# ===== الاتصال بـ Supabase =====
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ===== تحميل البيانات من Supabase =====
@st.cache_data
def load_data():
    try:
# ===== زر التحديث فقط =====
if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_top"):
    st.cache_data.clear()
    data = load_data()
    st.success("✅ تم جلب البيانات بنجاح")

