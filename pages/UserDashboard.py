import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime, timedelta
from hijri_converter import Gregorian

# ===================== إعداد الصفحة والتحقق من الجلسة =====================
st.set_page_config(page_title="تقييم اليوم", page_icon="📋", layout="wide")

# التحقق من تسجيل الدخول وصلاحية المستخدم
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("❌ يجب تسجيل الدخول أولاً.")
    st.stop()

if "username" not in st.session_state:
    st.error("❌ بيانات المستخدم غير متاحة.")
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

# ===================== الاتصال بقاعدة البيانات =====================
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

# ===================== جلب بيانات المستخدم والمشرف =====================
try:
    cursor.execute("SELECT mentor FROM users WHERE username = %s AND is_deleted = FALSE", (username,))
    mentor_row = cursor.fetchone()
    mentor_name = mentor_row["mentor"] if mentor_row else "غير معروف"

    # جلب السوبر مشرف (إن وجد)
    cursor.execute("SELECT mentor FROM users WHERE username = %s AND is_deleted = FALSE", (mentor_name,))
    sp_row = cursor.fetchone()
    sp_name = sp_row["mentor"] if sp_row else None
except Exception as e:
    st.error(f"❌ خطأ في جلب بيانات المستخدم: {e}")
    mentor_name = "غير معروف"
    sp_name = None

# ===================== إعداد التبويبات الرئيسية =====================
tabs = st.tabs(["📝 إدخال البيانات", "💬 المحادثات", "📊 تقارير المجموع", "🗒️ الإنجازات"])

# ===================== تبويب 1: إدخال البيانات (التقييم اليومي) =====================
with tabs[0]:
    st.markdown(f"<h3 style='color:#0000FF; font-weight:bold;'>👋 أهلاً {username} | مجموعتك: {mentor_name}</h3>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#0000FF; font-weight:bold;'>📝 المحاسبة الذاتية اليومية</h4>", unsafe_allow_html=True)
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_tab1"):
        st.experimental_rerun()

    with st.form("daily_evaluation_form"):
        # تحديد التاريخ: عرض آخر 7 أيام بصيغة هجري
        today = datetime.today().date()
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
            label = f"{arabic_weekday} - {g_date.day}/{g_date.month}/{g_date.year}"
            hijri_dates.append((label, g_date))
        hijri_labels = [label for label, _ in hijri_dates]
        selected_label = st.selectbox("📅 اختر التاريخ (هجري)", hijri_labels)
        selected_date = dict(hijri_dates)[selected_label]

        # التقييم الرئيسي: 5 بنود
        st.markdown("<h4 style='font-weight:bold;'>التقييم الرئيسي (5 بنود)</h4>", unsafe_allow_html=True)
        options_main = ["في المسجد جماعة = 5 نقاط", "في المنزل جماعة = 4 نقاط", "في المسجد منفرد = 4 نقاط", "في المنزل منفرد = 3 نقاط", "خارج الوقت = 0 نقاط"]
        mapping_main = {
            "في المسجد جماعة = 5 نقاط": 5,
            "في المنزل جماعة = 4 نقاط": 4,
            "في المسجد منفرد = 4 نقاط": 4,
            "في المنزل منفرد = 3 نقاط": 3,
            "خارج الوقت = 0 نقاط": 0
        }
        main_scores = []
        for i in range(1, 6):
            score = st.radio(f"البند {i}", options_main, index=0, key=f"main_{i}")
            main_scores.append(mapping_main[score])

        # السنن الرواتب: جمع عدد الاختيارات (كل خيار = 1 نقطة)
        st.markdown("<h4 style='font-weight:bold;'>السنن الرواتب</h4>", unsafe_allow_html=True)
        checkbox_options = ["الفجر = 1", "الظهر = 1", "العصر = 1", "المغرب = 1", "العشاء = 1"]
        sunnah_count = 0
        for opt in checkbox_options:
            if st.checkbox(opt, key=f"sunnah_{opt}"):
                sunnah_count += 1

        # تقييم ورد الإمام: اختيار من الخيارات
        st.markdown("<h4 style='font-weight:bold;'>ورد الإمام</h4>", unsafe_allow_html=True)
        options_read = ["قرأته لفترتين = 4 نقاط", "قرأته مرة واحدة = 2 نقطة", "لم أقرأ = 0 نقطة"]
        mapping_read = {"قرأته لفترتين = 4 نقاط": 4, "قرأته مرة واحدة = 2 نقطة": 2, "لم أقرأ = 0 نقطة": 0}
        reading_score = st.radio("اختيار", options_read, key="reading")

        # أسئلة نعم/لا (2 نقطة): 4 بنود
        st.markdown("<h4 style='font-weight:bold;'>أسئلة نعم/لا (2 نقطة)</h4>", unsafe_allow_html=True)
        options_yes2 = ["نعم = 2", "لا = 0"]
        mapping_yes2 = {"نعم = 2": 2, "لا = 0": 0}
        yes2_scores = []
        for i in range(1, 5):
            score = st.radio(f"سؤال {i}", options_yes2, key=f"yes2_{i}")
            yes2_scores.append(mapping_yes2[score])

        # أسئلة نعم/لا (1 نقطة): 2 بنود
        st.markdown("<h4 style='font-weight:bold;'>أسئلة نعم/لا (1 نقطة)</h4>", unsafe_allow_html=True)
        options_yes1 = ["نعم = 1", "لا = 0"]
        mapping_yes1 = {"نعم = 1": 1, "لا = 0": 0}
        yes1_scores = []
        for i in range(1, 3):
            score = st.radio(f"سؤال إضافي {i}", options_yes1, key=f"yes1_{i}")
            yes1_scores.append(mapping_yes1[score])

        submit_form = st.form_submit_button("💾 حفظ")
        if submit_form:
            # تحضير القيم: evaluation_date، username، ثم ترتيب توقيعات البنود
            eval_date_str = selected_date.strftime("%Y-%m-%d")
            vals = [eval_date_str, username] + main_scores + [sunnah_count, reading_score] + yes2_scores + yes1_scores
            try:
                # التحقق مما إذا كان سجل التقييم موجود مسبقًا لهذا المستخدم وتاريخ معين
                cursor.execute("SELECT id FROM daily_evaluations WHERE username = %s AND evaluation_date = %s", (username, eval_date_str))
                res = cursor.fetchone()
                if res:
                    update_query = """
                        UPDATE daily_evaluations
                        SET main1=%s, main2=%s, main3=%s, main4=%s, main5=%s,
                            sunnah=%s, reading=%s, yes2_1=%s, yes2_2=%s, yes2_3=%s, yes2_4=%s, yes1_1=%s, yes1_2=%s
                        WHERE id = %s
                    """
                    update_vals = main_scores + [sunnah_count, reading_score] + yes2_scores + yes1_scores + [res["id"]]
                    cursor.execute(update_query, update_vals)
                else:
                    insert_query = """
                        INSERT INTO daily_evaluations
                        (evaluation_date, username, main1, main2, main3, main4, main5, sunnah, reading, yes2_1, yes2_2, yes2_3, yes2_4, yes1_1, yes1_2)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, vals)
                conn.commit()
                st.success("✅ تم حفظ التقييم بنجاح")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء حفظ التقييم: {e}")

# ===================== تبويب 2: المحادثات =====================
with tabs[1]:
    st.markdown("### 💬 المحادثة مع المشرفين")
    # إعداد قائمة خيارات المحادثة (المشرف الأساسي والسوبر مشرف إن وجد)
    options = [mentor_name]
    if sp_name:
        options.append(sp_name)
    if "selected_mentor_display" not in st.session_state:
        st.session_state["selected_mentor_display"] = "اختر الشخص"
    options_display = ["اختر الشخص"] + options
    selected_mentor_display = st.selectbox("📨 اختر الشخص الذي ترغب بمراسلته", options_display, key="selected_mentor_display")
    if selected_mentor_display != "اختر الشخص":
        selected_mentor = selected_mentor_display
        try:
            query_chat = """
                SELECT * FROM chat_messages 
                WHERE ((`from`=%s AND `to`=%s) OR (`from`=%s AND `to`=%s))
                ORDER BY timestamp ASC
            """
            cursor.execute(query_chat, (selected_mentor, username, username, selected_mentor))
            chat_msgs = cursor.fetchall()
            chat_df = pd.DataFrame(chat_msgs)
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء جلب بيانات الدردشة: {e}")
            chat_df = pd.DataFrame(columns=["id", "timestamp", "from", "to", "message", "read_by_receiver"])
        # تحديث حالة الرسائل غير المقروءة
        if not chat_df.empty and "read_by_receiver" in chat_df.columns:
            unread_msgs = chat_df[(chat_df["from"]==selected_mentor) & (chat_df["to"]==username) & (chat_df["read_by_receiver"]=="")]
            for msg in unread_msgs:
                try:
                    cursor.execute("UPDATE chat_messages SET read_by_receiver=%s WHERE id=%s", ("✓", msg["id"]))
                    conn.commit()
                except Exception as e:
                    st.error(f"❌ خطأ أثناء تحديث حالة الرسالة: {e}")
        if chat_df.empty:
            st.info("💬 لا توجد رسائل حالياً.")
        else:
            for _, msg in chat_df.iterrows():
                if msg["from"] == username:
                    st.markdown(f"<p style='color:#000080'><b>أنت:</b> {msg['message']}</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p style='color:#8B0000'><b>{msg['from']}:</b> {msg['message']}</p>", unsafe_allow_html=True)
        new_chat = st.text_area("✏️ اكتب رسالتك هنا", height=100, key="chat_message")
        if st.button("📨 إرسال الرسالة", key="send_chat"):
            if new_chat.strip():
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    cursor.execute(
                        "INSERT INTO chat_messages (timestamp, `from`, `to`, message, read_by_receiver) VALUES (%s, %s, %s, %s, %s)",
                        (ts, username, selected_mentor, new_chat, "")
                    )
                    conn.commit()
                    st.success("✅ تم إرسال الرسالة")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء إرسال الرسالة: {e}")
            else:
                st.warning("⚠️ لا يمكن إرسال رسالة فارغة.")


# ===================== تبويب 3: تقارير المجموع =====================
with tabs[2]:
    st.title("📊 تقارير المجموع للفترة")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_tab3"):
        st.experimental_rerun()
    col1, col2 = st.columns(2)
    with col1:
        report_start = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="report_start")
    with col2:
        report_end = st.date_input("إلى تاريخ", datetime.today().date(), key="report_end")
    try:
        # استعلام لجلب سجلات التقييم اليومي للمستخدم في الفترة المحددة
        query_report = """
            SELECT * FROM daily_evaluations 
            WHERE evaluation_date BETWEEN %s AND %s AND username = %s
        """
        cursor.execute(query_report, (report_start.strftime("%Y-%m-%d"), report_end.strftime("%Y-%m-%d"), username))
        eval_rows = cursor.fetchall()
        report_df = pd.DataFrame(eval_rows)
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء جلب بيانات التقارير: {e}")
        report_df = pd.DataFrame()
    if report_df.empty:
        st.info("⚠️ لا توجد بيانات في الفترة المحددة.")
    else:
        # يتم تجميع كافة الأعمدة العددية (باستثناء id، username، evaluation_date)
        numeric_cols = report_df.select_dtypes(include=["number"]).columns.tolist()
        for col in ["id", "username", "evaluation_date"]:
            if col in numeric_cols:
                numeric_cols.remove(col)
        aggregated = report_df[numeric_cols].sum()
        total_score = aggregated.sum()
        st.metric(label="📌 مجموعك الكلي لجميع البنود", value=int(total_score))
        result_df = pd.DataFrame(aggregated).reset_index()
        result_df.columns = ["البند", "المجموع"]
        result_df = result_df.sort_values(by="المجموع", ascending=True)
        # تنسيق الأعمدة باستخدام HTML
        result_df["البند"] = result_df["البند"].apply(lambda x: f"<p style='color:#8B0000; text-align:center'>{x}</p>")
        result_df["المجموع"] = result_df["المجموع"].apply(lambda x: f"<p style='color:#000080; text-align:center'>{x}</p>")
        st.markdown(result_df.to_html(escape=False, index=False), unsafe_allow_html=True)

# ===================== تبويب 4: الإنجازات =====================
with tabs[3]:
    st.title("🗒️ الإنجازات")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_notes"):
        st.experimental_rerun()
    try:
        query_ach = "SELECT * FROM student_achievements WHERE student = %s ORDER BY timestamp DESC"
        cursor.execute(query_ach, (username,))
        ach_rows = cursor.fetchall()
        ach_df = pd.DataFrame(ach_rows)
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء جلب بيانات الإنجازات: {e}")
        ach_df = pd.DataFrame()
    if ach_df.empty:
        st.info("📭 لا توجد إنجازات حتى الآن.")
    else:
        # إعادة تسمية الأعمدة للتنسيق
        ach_df.rename(columns={
            "timestamp": "📅 التاريخ",
            "supervisor": "👤 المشرف",
            "achievement": "📝 الإنجاز"
        }, inplace=True)
        st.dataframe(ach_df, use_container_width=True)

# ===================== إغلاق الاتصال =====================
cursor.close()
conn.close()
