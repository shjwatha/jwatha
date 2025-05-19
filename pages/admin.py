import streamlit as st
import gspread
import pandas as pd
import json
from google.oauth2.service_account import Credentials

# ===== إعداد الاتصال بـ Google Sheets =====
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
client = gspread.authorize(creds)

# ===== التحقق من الجلسة =====
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("🔐 يجب تسجيل الدخول أولاً")
    st.switch_page("home.py")

if st.session_state.get("permissions") != "admin":
    role = st.session_state.get("permissions")
    if role == "user":
        st.switch_page("pages/UserDashboard.py")
    elif role in ["supervisor", "sp"]:
        st.switch_page("pages/Supervisor.py")
    else:
        st.switch_page("home.py")

# ===== تحميل الملف الخاص بالأدمن =====
try:
    spreadsheet = client.open_by_key(st.session_state["sheet_id"])
    admin_sheet = spreadsheet.worksheet("admin")
    users_df = pd.DataFrame(admin_sheet.get_all_records())
except Exception as e:
    if "Quota exceeded" in str(e) or "429" in str(e):
        st.error("❌ لقد تجاوزت عدد المرات المسموح لك بها الاتصال بقاعدة البيانات في الدقيقة.\n\nيرجى المحاولة مجددًا بعد دقيقة.")
    else:
        st.error("❌ حدث خطأ أثناء تحميل الملف الخاص بك. يرجى المحاولة لاحقًا.")
    st.stop()

# ===== إعداد الصفحة =====
st.set_page_config(page_title="لوحة الأدمن", page_icon="🛠️")
st.title("🛠️ لوحة إدارة المستخدمين")

if st.button("🔄 جلب المعلومات من قاعدة البيانات"):
    st.cache_data.clear()
    st.rerun()

# ===== الأعمدة الافتراضية لكل مستخدم جديد =====
def get_default_columns():
    return [
        "التاريخ",
        "صلاة الفجر",
        "صلاة الظهر",
        "صلاة العصر",
        "صلاة المغرب",
        "صلاة العشاء",
        "السنن الرواتب",
        "ورد الإمام النووي رحمه الله",
        "مختصر إشراق الضياء",
        "سنة الوتر",
        "سنة الضحى",
        "درس - قراءة ( شرعي )",
        "تلاوة قرآن (لا يقل عن ثمن)",
        "الدعاء مخ العبادة",
        "لا إله إلا الله",
        "الاستغفار",
        "الصلاة على سيدنا رسول الله صلى الله عليه وسلم"
    ]

# ===== قراءة المشرفين =====
supervisors_df = users_df[users_df["role"] == "supervisor"]

# ===== إنشاء عدة مستخدمين دفعة واحدة =====
st.subheader("➕ إنشاء عدة حسابات دفعة واحدة")

with st.form("bulk_create_form"):
    mentor_options = supervisors_df["username"].tolist()
    user_entries = []

    for i in range(20):
        st.markdown(f"### 👤 المستخدم رقم {i+1}")
        cols = st.columns([3, 3, 3, 3])
        full_name = cols[0].text_input("الاسم الكامل", key=f"full_name_{i}")
        username = cols[1].text_input("اسم المستخدم", key=f"username_{i}")
        password = cols[2].text_input("كلمة المرور", key=f"password_{i}")
        mentor = cols[3].selectbox("المشرف", mentor_options, key=f"mentor_{i}")
        user_entries.append({
            "full_name": full_name.strip(),
            "username": username.strip(),
            "password": password.strip(),
            "mentor": mentor.strip()
        })

    submit_bulk = st.form_submit_button("💾 حفظ جميع المستخدمين")

if submit_bulk:
    SHEET_IDS = {
        "المستوى 1":  "1Jx6MsOy4x5u7XsWFx1G3HpdQS1Ic5_HOEogbnWCXA3c",
        "المستوى 2":  "1kyNn69CTM661nNMhiestw3VVrH6rWrDQl7-dN5eW0kQ",
        "المستوى 3":  "1rZT2Hnc0f4pc4qKctIRt_eH6Zt2O8yF-SIpS66IzhNU",
        "المستوى 4":  "19L878i-iQtZgHgqFThSFgWJBFpTsQFiD5QS7lno8rsI",
        "المستوى 5":  "1YimetyT4xpKGheuN-TFm5J8w6k6cf3yIwQXRmvIqTW0",
        "المستوى 6":  "1Fxo3XgJHCJgcuXseNjmRePRH4L0t6gpkDv0Sz0Tm_u8",
        "المستوى 7":  "1t5u5qE8tXSChK4ezshF5FZ_eYMpjR_00xsp4CUrPp5c",
        "المستوى 8":  "1crt5ERYxrt8Cg1YkcK40CkO3Bribr3vOMmOkttDpR1A",
        "المستوى 9":  "1v4asV17nPg2u62eYsy1dciQX5WnVqNRmXrWfTY2jvD0",
        "المستوى 10": "15waTwimthOdMTeqGS903d8ELR8CtCP3ZivIYSsgLmP4",
        "المستوى 11": "1BSqbsfjw0a4TM-C0W0pIh7IhqzZ8jU3ZhFy8gu4CMWo",
        "المستوى 12": "1AtsVnicX_6Ew7Oci3xP77r6W3yA-AhntlT3TNGcbPbM",
        "المستوى 13": "1jcCGm1rfW_6bNg8tyaK6aOyKvXuC4Jc2w-wrjiDX20s",
        "المستوى 14": "1qkhZjgftc7Ro9pGJGdydICHQb0yUtV8P9yWzSCD3ewo",
        "المستوى 15": "1gOmeFwHnRZGotaUHqVvlbMtVVt1A2L7XeIuolIyJjAY"
    }

    created_count = 0
    skipped_count = 0

    for entry in user_entries:
        full_name = entry["full_name"]
        username = entry["username"]
        password = entry["password"]
        mentor = entry["mentor"]
        role = "user"

        if not full_name or not username or not password or not mentor:
            continue

        username_check = username.lower()
        full_name_check = full_name.lower()
        is_duplicate = False
        had_error = False

        for sid in SHEET_IDS.values():
            try:
                sheet = client.open_by_key(sid).worksheet("admin")
                df = pd.DataFrame(sheet.get_all_records())
                for _, row in df.iterrows():
                    u = str(row["username"]).strip().lower()
                    f = str(row["full_name"]).strip().lower()
                    if username_check == u or username_check == f or full_name_check == u or full_name_check == f:
                        is_duplicate = True
                        break
                if is_duplicate:
                    break
            except Exception as e:
                had_error = True
                if "Quota exceeded" in str(e) or "429" in str(e):
                    st.error("❌ لقد تجاوزت عدد المرات المسموح لك بها الاتصال بقاعدة البيانات في الدقيقة.\n\nيرجى المحاولة مجددًا بعد دقيقة.")
                else:
                    st.error("⚠️ حدث خطأ غير متوقع أثناء التحقق من الحسابات. يرجى المحاولة لاحقًا.")
                break

        if had_error:
            st.warning(f"⚠️ تعذر إنشاء الحساب: {username} (خطأ في التحقق)")
            continue
        elif is_duplicate:
            st.warning(f"🚫 تم تجاوز '{username}' لأن الاسم أو اسم المستخدم مستخدم من قبل شخص آخر.")
            continue

        try:
            worksheet_name = f"بيانات - {username}"
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols="30")
            worksheet.insert_row(get_default_columns(), 1)
            admin_sheet.append_row([full_name, username, password, worksheet_name, role, mentor])
            created_count += 1
        except Exception as e:
            if "already exists" in str(e):
                st.error(f"❌ اسم الورقة موجود مسبقًا: {worksheet_name}")
            else:
                st.error(f"❌ فشل في إنشاء المستخدم '{username}': {e}")
            continue

    st.success(f"✅ تم إنشاء {created_count} مستخدم. تم تجاوز {skipped_count} مستخدم (بيانات ناقصة أو مكررة).")
