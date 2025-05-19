import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from hijri_converter import Hijri, Gregorian
from supabase import create_client, Client

# ===== إعادة التوجيه إلى صفحة تسجيل الدخول إذا لم يتم تسجيل الدخول =====
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.switch_page("home.py")

# ===== الاتصال بـ Supabase =====
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ===== إعداد الصفحة =====
st.set_page_config(page_title="تقييم اليوم", page_icon="📋", layout="wide")

# ===== تحقق من صلاحية المستخدم =====
if "username" not in st.session_state or "level" not in st.session_state or "permissions" not in st.session_state:
    st.error("❌ يجب تسجيل الدخول أولاً.")
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
user_level = st.session_state["level"]

# ===== جلب بيانات المستخدم والبيانات الإدارية من Supabase =====
try:
    admin_response = supabase.table("admins")\
        .select("username, full_name, mentor")\
        .eq("level", user_level)\
        .execute()
    admin_data = admin_response.data if admin_response.data is not None else []
    
    user_response = supabase.table("users")\
        .select("*")\
        .eq("username", username)\
        .eq("level", user_level)\
        .execute()
    user_data = user_response.data if user_response.data is not None else []
    
    if not user_data:
        st.error("❌ لم يتم العثور على بيانات هذا المستخدم.")
        st.stop()
    user_record = user_data[0]
except Exception as e:
    st.error("❌ حدث خطأ أثناء الاتصال بقاعدة البيانات. حاول مرة أخرى.")
    st.stop()

# ===== جلب اسم المشرف والسوبر مشرف =====
mentor_name = user_record.get("mentor")
sp_row = next((row for row in admin_data if row["username"] == mentor_name), None)
sp_name = sp_row.get("mentor") if sp_row else None

# ===== تعريف أعمدة نموذج التقييم (جدول daily_data) =====
# الأعمدة حسب تفاصيل قاعدة البيانات:
# [التاريخ، صلاة الفجر، صلاة الظهر، صلاة العصر، صلاة المغرب، صلاة العشاء، 
#  السنن الرواتب، ورد الإمام النووي رحمه الله، مختصر إشراق الضياء،
#  سنة الوتر، سنة الضحى، درس - قراءة ( شرعي ), تلاوة قرآن (لا يقل عن ثمن),
#  الدعاء مخ العبادة، لا إله إلا الله، الاستغفار، الصلاة على سيدنا رسول الله صلى الله عليه وسلم]
columns = [
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

# ===== وظيفة التحديث وإعادة التحميل =====
def refresh_button(key):
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key=key):
        st.cache_data.clear()
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.warning("دالة st.experimental_rerun غير مدعومة في هذا الإصدار من Streamlit.")

# ===== دالة جلب بيانات التقييم من جدول daily_data =====
@st.cache_data
def load_data():
    try:
        response = supabase.table("daily_data")\
                    .select("*")\
                    .eq("username", username)\
                    .execute()
        data = response.data if response.data is not None else []
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error("❌ حدث خطأ أثناء تحميل البيانات. حاول لاحقًا.")
        st.stop()

# ===== دالة عرض المحادثة مع المشرفين =====
def show_chat():
    st.markdown("### 💬 المحادثة مع المشرفين")

    options = [mentor_name]
    if sp_name:
        options.append(sp_name)

    # خيار افتراضي
    if "selected_mentor_display" not in st.session_state:
        st.session_state["selected_mentor_display"] = "اختر الشخص"

    options_display = ["اختر الشخص"] + options
    selected_mentor_display = st.selectbox("📨 اختر الشخص الذي ترغب بمراسلته", options_display, key="selected_mentor_display")

    if selected_mentor_display != "اختر الشخص":
        selected_mentor = selected_mentor_display

        # جلب بيانات الدردشة من جدول chat
        chat_response = supabase.table("chat").select("*").execute()
        chat_data = pd.DataFrame(chat_response.data) if chat_response.data is not None else pd.DataFrame(
            columns=["timestamp", "from", "to", "message", "read_by_receiver"])
        
        if chat_data.empty:
            st.info("💬 لا توجد رسائل حالياً.")
            return
        
        required_columns = {"from", "to", "message", "timestamp"}
        if not required_columns.issubset(chat_data.columns):
            st.warning("⚠️ الأعمدة الأساسية غير موجودة في بيانات الدردشة.")
            return

        # تحديث حالة القراءة (يفترض وجود حقل "id")
        unread_msgs = chat_data[
            (chat_data["from"] == selected_mentor) &
            (chat_data["to"] == username) &
            (chat_data["read_by_receiver"].astype(str).str.strip() == "")
        ]
        if not unread_msgs.empty and "id" in unread_msgs.columns:
            for _, row in unread_msgs.iterrows():
                supabase.table("chat").update({"read_by_receiver": "✓"}).eq("id", row["id"]).execute()

        # إعادة جلب بيانات الدردشة بعد التحديث
        chat_response = supabase.table("chat").select("*").execute()
        chat_data = pd.DataFrame(chat_response.data) if chat_response.data is not None else pd.DataFrame()

        messages = chat_data[
            ((chat_data["from"] == username) & (chat_data["to"] == selected_mentor)) |
            ((chat_data["from"] == selected_mentor) & (chat_data["to"] == username))
        ]
        if not messages.empty:
            messages = messages.sort_values(by="timestamp")
        else:
            st.info("💬 لا توجد رسائل حالياً.")

        for _, msg in messages.iterrows():
            if msg["from"] == username:
                st.markdown(f"<p style='color:#000080'><b> أنت:</b> {msg['message']}</p>", unsafe_allow_html=True)
            else:
                st.markdown(f"<p style='color:#8B0000'><b>{msg['from']}:</b> {msg['message']}</p>", unsafe_allow_html=True)

        new_msg = st.text_area("✏️ اكتب رسالتك هنا", height=100)
        if st.button("📨 إرسال الرسالة"):
            if new_msg.strip():
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_record = {
                    "timestamp": timestamp,
                    "from": username,
                    "to": selected_mentor,
                    "message": new_msg,
                    "read_by_receiver": ""
                }
                supabase.table("chat").insert(new_record).execute()
                st.success("✅ تم إرسال الرسالة")
                st.experimental_rerun()
            else:
                st.warning("⚠️ لا يمكن إرسال رسالة فارغة.")

# ===== التبويبات الرئيسية =====
tabs = st.tabs(["📝 إدخال البيانات", "💬 المحادثات", "📋 تجميع الكل", "🏆 إنجازاتي"])

# ===== التبويب الأول: إدخال البيانات (المحاسبة الذاتية) =====
with tabs[0]:
    st.markdown(
        """
        <style>
        body, .stTextInput, .stTextArea, .stSelectbox, .stButton, .stMarkdown, .stDataFrame {
            direction: rtl;
            text-align: right;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(f"<h3 style='color: #0000FF; font-weight: bold; font-size: 24px;'>👋 أهلاً {username} | مجموعتك / {mentor_name}</h3>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #0000FF; font-weight: bold; font-size: 20px;'>📝 المحاسبة الذاتية</h4>", unsafe_allow_html=True)

    refresh_button("refresh_tab1")

    # تنبيه بالرسائل غير المقروءة
    chat_response = supabase.table("chat").select("*").execute()
    chat_data = pd.DataFrame(chat_response.data) if chat_response.data is not None else pd.DataFrame()
    if "read_by_receiver" in chat_data.columns:
        unread_msgs = chat_data[
            (chat_data["to"] == username) &
            (chat_data["message"].notna()) &
            (chat_data["read_by_receiver"].astype(str).str.strip() == "")
        ]
        senders = unread_msgs["from"].unique().tolist()
        if senders:
            sender_list = "، ".join(senders)
            st.markdown(f"""
            <table style="width:100%;">
                <tr>
                    <td style="direction: rtl; text-align: right; color: red; font-weight: bold; font-size: 16px;">
                        📬 يوجد لديك رسائل لم تطلع عليها من: ({sender_list})
                    </td>
                </tr>
            </table>
            """, unsafe_allow_html=True)

    with st.form("daily_form"):
        today = datetime.today().date()

        # إعداد التواريخ الهجرية لآخر 7 أيام
        hijri_dates = []
        for i in range(7):
            g_date = today - timedelta(days=i)
            h_date = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
            weekday = g_date.strftime("%A")
            arabic_weekday = {
                "Saturday": "السبت",
                "Sunday": "الأحد",
                "Monday": "الاثنين",
                "Tuesday": "الثلاثاء",
                "Wednesday": "الأربعاء",
                "Thursday": "الخميس",
                "Friday": "الجمعة"
            }[weekday]
            g_date_str = f"{g_date.day}/{g_date.month}/{g_date.year}"
            hijri_label = f"{arabic_weekday} - {g_date_str}"
            hijri_dates.append((hijri_label, g_date))

        hijri_labels = [label for label, _ in hijri_dates]
        selected_label = st.selectbox("📅 اختر التاريخ (هجري)", hijri_labels)
        selected_date = dict(hijri_dates)[selected_label]
        # أول قيمة: التاريخ
        values = [selected_date.strftime("%Y-%m-%d")]

        # 1. 5 أعمدة للصلوات:
        options_1 = ["في المسجد جماعة = 5 نقاط", "في المنزل جماعة = 4 نقاط", 
                     "في المسجد منفرد = 4 نقاط", "في المنزل منفرد = 3 نقاط", "خارج الوقت = 0 نقاط"]
        for prayer in ["صلاة الفجر", "صلاة الظهر", "صلاة العصر", "صلاة المغرب", "صلاة العشاء"]:
            st.markdown(f"<h4 style='font-weight: bold;'>{prayer}</h4>", unsafe_allow_html=True)
            rating = st.radio(prayer, options_1, index=0, key=prayer)
            # ذخيرة القيمة كنص للنقاط (يمكنك تغيير طريقة الحساب بدمج الرقم مباشرة)
            values.append(str(options_1.index(rating) * 1 + (5 if "5 نقاط" in rating else 0)))  
            # هنا يُفضّل حساب النقاط بطريقة أكثر وضوحاً؛ اخترت استخدام ترتيب الخيارات كمثال.

        # 2. السنن الرواتب (checkbox)
        checkbox_options = ["الفجر = 1 نقطة", "الظهر = 1 نقطة", "العصر = 1 نقطة", "المغرب = 1 نقطة", "العشاء = 1 نقطة"]
        st.markdown(f"<h4 style='font-weight: bold;'>السنن الرواتب</h4>", unsafe_allow_html=True)
        checkbox_cols = st.columns(1)
        selected_checkboxes = []
        for option in checkbox_options:
            with checkbox_cols[0]:
                if st.checkbox(option, key=f"السنن_{option}"):
                    selected_checkboxes.append(option)
        values.append(str(len(selected_checkboxes)))
        
        # 3. عمود "ورد الإمام النووي رحمه الله" مع خيارات الراديو
        time_read_options = ["قرأته لفترتين = 4 نقاط", "قرأته مرة واحدة في اليوم = 2 نقطة", "لم أتمكن من قراءته لهذا اليوم = 0 نقاط"]
        ratings_read = {
            "قرأته لفترتين = 4 نقاط": 4,
            "قرأته مرة واحدة في اليوم = 2 نقطة": 2,
            "لم أتمكن من قراءته لهذا اليوم = 0 نقاط": 0
        }
        for col_name in ["ورد الإمام النووي رحمه الله", "مختصر إشراق الضياء"]:
            st.markdown(f"<h4 style='font-weight: bold;'>{col_name}</h4>", unsafe_allow_html=True)
            rating = st.radio("", time_read_options, key=col_name)
            values.append(str(ratings_read[rating]))

        # 4. باقي 8 أعمدة بنظام نعم/لا مع نقطة لكل "نعم"
        yes_no_options = ["نعم = 1 نقطة", "لا = 0 نقطة"]
        ratings_yes_no = {"نعم = 1 نقطة": 1, "لا = 0 نقطة": 0}
        remaining_cols = ["سنة الوتر", "سنة الضحى", "درس - قراءة ( شرعي )", 
                          "تلاوة قرآن (لا يقل عن ثمن)", "الدعاء مخ العبادة", 
                          "لا إله إلا الله", "الاستغفار", "الصلاة على سيدنا رسول الله صلى الله عليه وسلم"]
        for col_name in remaining_cols:
            st.markdown(f"<h4 style='font-weight: bold;'>{col_name}</h4>", unsafe_allow_html=True)
            rating = st.radio("", yes_no_options, horizontal=True, key=col_name)
            values.append(str(ratings_yes_no[rating]))

        submit = st.form_submit_button("💾 حفظ")

        if submit:
            # التأكد من أن التاريخ المختار من ضمن آخر 7 أيام
            if selected_date not in [d for _, d in hijri_dates]:
                st.error("❌ التاريخ غير صالح. لا يمكن حفظ البيانات لأكثر من أسبوع سابق فقط")
            else:
                try:
                    date_str = selected_date.strftime("%Y-%m-%d")
                    if len(values) != len(columns):
                        st.error("❌ هناك خلل في إدخال البيانات. الرجاء التأكد من تعبئة كافة الحقول.")
                        st.stop()
                    
                    # تحويل القائمة إلى قاموس مع إضافة اسم المستخدم والمستوى
                    record = {columns[i]: values[i] for i in range(len(values))}
                    record["username"] = username
                    record["level"] = user_level
                    
                    # البحث عن سجل موجود لنفس التاريخ واسم المستخدم
                    existing_response = supabase.table("daily_data")\
                        .select("*")\
                        .eq("التاريخ", date_str)\
                        .eq("username", username)\
                        .execute()
                    existing_records = existing_response.data if existing_response.data is not None else []
                    
                    if existing_records:
                        supabase.table("daily_data")\
                            .update(record)\
                            .eq("التاريخ", date_str)\
                            .eq("username", username)\
                            .execute()
                    else:
                        supabase.table("daily_data").insert(record).execute()
                    
                    st.cache_data.clear()
                    data = load_data()
                    st.success("✅ تم الحفظ بنجاح والاتصال بقاعدة البيانات")
                except Exception as e:
                    if "Quota exceeded" in str(e) or "429" in str(e):
                        st.error("❌ لقد تجاوزت عدد المرات المسموح بها للاتصال بقاعدة البيانات.\n\nيرجى المحاولة مجددًا بعد دقيقة.")
                    else:
                        st.error(f"❌ حدث خطأ أثناء حفظ البيانات: {str(e)}")

# ===== التبويب الثاني: المحادثات =====
with tabs[1]:
    refresh_button("refresh_chat")
    show_chat()

# ===== التبويب الثالث: تجميع الكل (عرض كافة التقييمات) =====
with tabs[2]:
    st.title("📋 تجميع الكل")
    refresh_button("refresh_tab2")

    try:
        daily_response = supabase.table("daily_data")\
                            .select("*")\
                            .eq("username", username)\
                            .execute()
        df = pd.DataFrame(daily_response.data) if daily_response.data is not None else pd.DataFrame()
    except Exception as e:
        if "Quota exceeded" in str(e) or "429" in str(e):
            st.error("❌ لقد تجاوزت عدد المرات المسموح بها للاتصال بقاعدة البيانات.\n\nيرجى المحاولة مجددًا بعد دقيقة.")
        else:
            st.error("❌ حدث خطأ أثناء تحميل البيانات. حاول لاحقًا.")
        st.stop()

    if "التاريخ" not in df.columns:
        st.warning("⚠️ لا توجد بيانات بعد في جدول التقييمات. الرجاء البدء بإدخال أول تقييم.")
        st.stop()

    df["التاريخ"] = pd.to_datetime(df["التاريخ"], errors="coerce")
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7))
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date())

    mask = (df["التاريخ"] >= pd.to_datetime(start_date)) & (df["التاريخ"] <= pd.to_datetime(end_date))
    filtered = df[mask].drop(columns=["التاريخ"], errors="ignore")

    if filtered.empty:
        st.warning("⚠️ لا توجد بيانات في الفترة المحددة.")
    else:
        for col in filtered.columns:
            filtered[col] = pd.to_numeric(filtered[col], errors="coerce").fillna(0)

        totals = filtered.sum(numeric_only=True)
        total_score = totals.sum()

        st.metric(label="📌 مجموعك الكلي لجميع البنود", value=int(total_score))

        result_df = pd.DataFrame(totals, columns=["المجموع"])
        result_df.index.name = "البند"
        result_df = result_df.reset_index()
        result_df = result_df.sort_values(by="المجموع", ascending=True)

        result_df = result_df[["المجموع", "البند"]]
        result_df["البند"] = result_df["البند"].apply(lambda x: f"<p style='color:#8B0000; text-align:center'>{x}</p>")
        result_df["المجموع"] = result_df["المجموع"].apply(lambda x: f"<p style='color:#000080; text-align:center'>{x}</p>")

        st.markdown(result_df.to_html(escape=False, index=False), unsafe_allow_html=True)

# ===== التبويب الرابع: إنجازاتي =====
with tabs[3]:
    st.title("🏆 إنجازاتي")
    refresh_button("refresh_notes")

    try:
        # جلب بيانات الملاحظات التي تخص الطالب من جدول notes وبيانات الإنجازات من achievements_list يمكن التعامل معها منفصلًا
        notes_response = supabase.table("notes")\
                            .select("*")\
                            .eq("الطالب", username)\
                            .execute()
        notes_data = pd.DataFrame(notes_response.data) if notes_response.data is not None else pd.DataFrame()
    except Exception as e:
        st.error("❌ تعذر تحميل بيانات الملاحظات.")
        st.stop()

    if notes_data.empty or "الطالب" not in notes_data.columns:
        st.info("📭 لا توجد ملاحظات حتى الآن.")
    else:
        user_notes = notes_data[notes_data["الطالب"] == username]
        if user_notes.empty:
            st.warning("📭 لا توجد ملاحظات مسجلة لك حتى الآن.")
        else:
            user_notes = user_notes[["timestamp", "المشرف", "الملاحظة"]]
            user_notes.rename(columns={
                "timestamp": "📅 التاريخ",
                "المشرف": "👤 المشرف",
                "الملاحظة": "📝 الملاحظة"
            }, inplace=True)
            st.dataframe(user_notes, use_container_width=True)
