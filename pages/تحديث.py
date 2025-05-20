import streamlit as st
from supabase import create_client, Client
import pandas as pd

# الاتصال بـ Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# إعداد الصفحة
st.set_page_config(page_title="📊 جلب المعلومات من Supabase", page_icon="📊")

st.title("📊 جلب البيانات من Supabase")

# جلب البيانات من Supabase
@st.cache_data
def load_data():
    try:
        # استعلام لجلب بيانات من جدول "users"
        data = supabase.table("users").select("*").execute().data
        if not data:
            st.warning("⚠️ لا توجد بيانات في جدول المستخدمين.")
            return None
        return data
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء جلب البيانات: {e}")
        return None

# جلب البيانات
data = load_data()

# تحقق من البيانات قبل عرضها
if data:
    df = pd.DataFrame(data)
    st.dataframe(df)  # عرض البيانات في جدول Streamlit
else:
    st.error("❌ لم يتم العثور على أي بيانات لعرضها.")
