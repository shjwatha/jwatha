import streamlit as st
import gspread
import pandas as pd
import json
import re
import time
from google.oauth2.service_account import Credentials

# دالة استخراج مفتاح الملف من الرابط باستخدام تعبير نمطي
def extract_spreadsheet_id(url):
    pattern = r"/d/([a-zA-Z0-9-_]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# ===== إعداد الاتصال بـ Google Sheets =====
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
client = gspread.authorize(creds)

# ===== قائمة روابط Google Sheets =====
sheet_links = [
    "https://docs.google.com/spreadsheets/d/1gOmeFwHnRZGotaUHqVvlbMtVVt1A2L7XeIuolIyJjAY",
    "https://docs.google.com/spreadsheets/d/1Jx6MsOy4x5u7XsWFx1G3HpdQS1Ic5_HOEogbnWCXA3c",
    "https://docs.google.com/spreadsheets/d/1kyNn69CTM661nNMhiestw3VVrH6rWrDQl7-dN5eW0kQ",
    "https://docs.google.com/spreadsheets/d/1rZT2Hnc0f4pc4qKctIRt_eH6Zt2O8yF-SIpS66IzhNU",
    "https://docs.google.com/spreadsheets/d/19L878i-iQtZgHgqFThSFgWJBFpTsQFiD5QS7lno8rsI",
    "https://docs.google.com/spreadsheets/d/1YimetyT4xpKGheuN-TFm5J8w6k6cf3yIwQXRmvIqTW0",
    "https://docs.google.com/spreadsheets/d/1Fxo3XgJHCJgcuXseNjmRePRH4L0t6gpkDv0Sz0Tm_u8",
    "https://docs.google.com/spreadsheets/d/1t5u5qE8tXSChK4ezshF5FZ_eYMpjR_00xsp4CUrPp5c",
    "https://docs.google.com/spreadsheets/d/1crt5ERYxrt8Cg1YkcK40CkO3Bribr3vOMmOkttDpR1A",
    "https://docs.google.com/spreadsheets/d/1v4asV17nPg2u62eYsy1dciQX5WnVqNRmXrWfTY2jvD0",
    "https://docs.google.com/spreadsheets/d/15waTwimthOdMTeqGS903d8ELR8CtCP3ZivIYSsgLmP4",
    "https://docs.google.com/spreadsheets/d/1BSqbsfjw0a4TM-C0W0pIh7IhqzZ8jU3ZhFy8gu4CMWo",
    "https://docs.google.com/spreadsheets/d/1AtsVnicX_6Ew7Oci3xP77r6W3yA-AhntlT3TNGcbPbM",
    "https://docs.google.com/spreadsheets/d/1jcCGm1rfW_6bNg8tyaK6aOyKvXuC4Jc2w-wrjiDX20s",
    "https://docs.google.com/spreadsheets/d/1qkhZjgftc7Ro9pGJGdydICHQb0yUtV8P9yWzSCD3ewo"
]

# ===== إعداد صفحة تسجيل الدخول =====
st.set_page_config(page_title="تسجيل الدخول", page_icon="🔐")
st.title("🔐 تسجيل الدخول")

# زر لتحديث البيانات يدويًا
if st.button("🔄 جلب المعلومات من قاعدة البيانات"):
    st.cache_data.clear()
    st.success("✅ تم تحديث البيانات")

# إضافة حقول وهمية مخفية لمنع تعبئة iCloud Keychain على iOS
st.markdown(
    """
    <input type="text" name="fake_username" style="opacity:0; position:absolute; top:-1000px;">
    <input type="password" name="fake_password" style="opacity:0; position:absolute; top:-1000px;">
    """,
    unsafe_allow_html=True
)

# التأكد من وجود حالة للجلسة
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# ===== نموذج تسجيل الدخول =====
if not st.session_state["authenticated"]:
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("دخول")

        if submitted:
            match_found = False
            with st.spinner("جاري تحويلك لملف البيانات الخاص بك قد يستغرق الأمر دقيقة أو دقيقتين"):
                for link in sheet_links:
                    sheet_id = extract_spreadsheet_id(link)
                    try:
                        admin_sheet = client.open_by_key(sheet_id).worksheet("admin")
                        users_df = pd.DataFrame(admin_sheet.get_all_records())
                        
                        # التحقق من البيانات بناءً على "username" أو "full_name" وكلمة المرور
                        matched = users_df[
                            (((users_df["username"] == username) | (users_df["full_name"] == username)) &
                             (users_df["password"] == password))
                        ]
                        
                        if not matched.empty:
                            user_row = matched.iloc[0]
                            st.session_state["authenticated"] = True
                            st.session_state["username"] = user_row["username"]
                            st.session_state["sheet_url"] = link
                            st.session_state["sheet_id"] = sheet_id
                            st.session_state["permissions"] = user_row["role"]
                            st.session_state["full_name"] = user_row["full_name"] 
                            match_found = True
                            break  # خروج من الحلقة عند إيجاد تطابق
                    except Exception:
                        # تجاهل أي أخطاء مثل تجاوز الحصة دون عرضها للمستخدم
                        continue

            if match_found:
                st.success("✅ تم تسجيل الدخول بنجاح")
                # تأخير بسيط لإتاحة عرض رسالة النجاح ثم التوجيه
                time.sleep(1.5)
                if st.session_state["permissions"] in ["supervisor", "sp"]:
                    st.switch_page("pages/Supervisor.py")
                elif st.session_state["permissions"] == "admin":
                    st.switch_page("pages/AdminDashboard.py")
                elif st.session_state["permissions"] == "user":
                    st.switch_page("pages/UserDashboard.py")
            else:
                st.error("❌ البيانات المدخلة غير صحيحة")
else:
    # إذا كانت بيانات الجلسة تشير إلى تسجيل دخول صحيح يتم إعادة التوجيه مباشرة
    permission = st.session_state.get("permissions")
    if permission in ["supervisor", "sp"]:
        st.switch_page("pages/Supervisor.py")
    elif permission == "admin":
        st.switch_page("pages/AdminDashboard.py")
    elif permission == "user":
        st.switch_page("pages/UserDashboard.py")
    else:
        st.error("⚠️ صلاحية غير معروفة.")
