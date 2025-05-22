import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pymysql

# ===== إعداد الصفحة وفحص تسجيل الدخول =====
st.set_page_config(page_title="📊 تقارير المشرف", page_icon="📊", layout="wide")

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("🚫 الرجاء تسجيل الدخول.")
    st.stop()

# التأكد من وجود معلومات المستخدم في الجلسة
username = st.session_state.get("username", "المستخدم")
permissions = st.session_state.get("permissions", "")

st.title(f"👋 أهلاً {username}")

# ===== ضبط اتجاه النص إلى اليمين =====
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

# ===== الاتصال بقاعدة بيانات MySQL =====
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

# ===== تحميل بيانات المستخدمين (الطلاب) =====
cursor.execute("SELECT * FROM users WHERE is_deleted = FALSE")
users_data = cursor.fetchall()
if users_data:
    users_df = pd.DataFrame(users_data)
else:
    users_df = pd.DataFrame()

# إعداد قائمة المستخدمين للمحادثة بناءً على الصلاحيات
all_user_options = []
if permissions == "sp":
    # السوبر مشرف: يجلب قائمة المشرفين التابعين له
    my_supervisors = users_df[(users_df["role"] == "supervisor") & (users_df["mentor"] == username)]["username"].tolist()
    all_user_options += [(s, "مشرف") for s in my_supervisors]

if permissions in ["supervisor", "sp"]:
    # المشرف: يجلب قائمة الطلاب المرتبطين به
    assigned_users = users_df[(users_df["role"] == "user") & (users_df["mentor"].isin([username] + [s for s, _ in all_user_options]))]
    all_user_options += [(u, "مستخدم") for u in assigned_users["username"].tolist()]

# تحميل بيانات التقارير من جدول reports (يُفترض وجود جدول تقارير يحتوي على عمود "التاريخ" و"username" وباقي البنود)
try:
    merged_df = pd.read_sql("SELECT * FROM reports", conn)
except Exception as e:
    st.error(f"❌ حدث خطأ أثناء جلب بيانات التقارير: {e}")
    merged_df = pd.DataFrame()

# إنشاء التبويبات الرئيسية
tabs = st.tabs([
    "تقرير إجمالي", 
    "💬 المحادثات", 
    "📋 تجميعي الكل", 
    "📌 تجميعي بند",  
    "تقرير فردي", 
    "📈 رسوم بيانية", 
    "📌 رصد الإنجاز"
])

##########################################
# تبويب 1: تقرير إجمالي
##########################################
with tabs[0]:
    st.subheader("تقرير إجمالي")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_0")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_0")
    
    if not merged_df.empty and "التاريخ" in merged_df.columns:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], errors="coerce")
        filtered_df = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start_date)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end_date))
        ]
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("ℹ️ لا توجد بيانات للتقرير.")

##########################################
# تبويب 2: المحادثات
##########################################
with tabs[1]:
    st.subheader("💬 المحادثات")
    
    def show_chat_supervisor():
        st.subheader("الدردشة")
        if "selected_user_display" not in st.session_state:
            st.session_state["selected_user_display"] = "اختر الشخص"
        options_display = ["اختر الشخص"] + [f"{name} ({role})" for name, role in all_user_options]
        selected_display = st.selectbox("اختر الشخص", options_display, key="selected_user_display")
        
        if selected_display != "اختر الشخص":
            # استخراج اسم المستخدم من النص (مثلاً: "محمد (مشرف)")
            selected_user = selected_display.split("(")[0].strip()
            try:
                # جلب بيانات الدردشة من جدول chat_messages
                chat_df = pd.read_sql("SELECT * FROM chat_messages", conn)
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء جلب بيانات الدردشة: {e}")
                chat_df = pd.DataFrame()
            
            if chat_df.empty:
                st.info("💬 لا توجد رسائل بعد.")
            else:
                required_columns = {"timestamp", "from", "to", "message", "read_by_receiver"}
                if not required_columns.issubset(chat_df.columns):
                    st.warning(f"⚠️ الأعمدة المطلوبة غير موجودة في بيانات الدردشة. الأعمدة الموجودة: {list(chat_df.columns)}")
                else:
                    # تحديث حالة الرسائل غير المقروءة
                    unread_indexes = chat_df[
                        (chat_df["from"] == selected_user) &
                        (chat_df["to"] == username) &
                        (chat_df["read_by_receiver"].astype(str).str.strip() == "")
                    ].index.tolist()
                    for i in unread_indexes:
                        cursor.execute("UPDATE chat_messages SET read_by_receiver = %s WHERE id = %s", ("✓", chat_df.loc[i, "id"]))
                        conn.commit()
                    
                    # عرض الرسائل (من المستخدم الحالي أو من الشخص المحدد)
                    messages = chat_df[
                        ((chat_df["from"] == username) & (chat_df["to"] == selected_user)) |
                        ((chat_df["from"] == selected_user) & (chat_df["to"] == username))
                    ].sort_values(by="timestamp")
                    
                    if messages.empty:
                        st.info("💬 لا توجد رسائل بعد.")
                    else:
                        for _, msg in messages.iterrows():
                            if msg["from"] == username:
                                st.markdown(f"<p style='color:#8B0000;'>أنت: {msg['message']}</p>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<p style='color:#000080;'>{msg['from']}: {msg['message']}</p>", unsafe_allow_html=True)
            
            new_msg = st.text_area("✏️ اكتب رسالتك", height=100, key="chat_message")
            if st.button("📨 إرسال الرسالة"):
                if new_msg.strip():
                    msg_timestamp = (datetime.utcnow() + pd.Timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        cursor.execute(
                            "INSERT INTO chat_messages (timestamp, `from`, `to`, message, read_by_receiver) VALUES (%s, %s, %s, %s, %s)",
                            (msg_timestamp, username, selected_user, new_msg, "")
                        )
                        conn.commit()
                        st.success("✅ تم إرسال الرسالة")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ حدث خطأ أثناء إرسال الرسالة: {e}")
                else:
                    st.warning("⚠️ لا يمكن إرسال رسالة فارغة.")
    
    show_chat_supervisor()

##########################################
# تبويب 3: تجميعي الكل
##########################################
with tabs[2]:
    st.subheader("📋 تفاصيل الدرجات للجميع")
    col1, col2 = st.columns(2)
    with col1:
        start_date_all = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_all")
    with col2:
        end_date_all = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_all")
    
    if not merged_df.empty and "التاريخ" in merged_df.columns:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], errors="coerce")
        filtered_df_all = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start_date_all)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end_date_all))
        ]
        # إزالة الأعمدة "التاريخ" واسترجاع باقي الدرجات
        try:
            scores_df = filtered_df_all.drop(columns=["التاريخ", "username"], errors="ignore")
            # تجميع النقاط حسب اسم المستخدم
            grouped = filtered_df_all.groupby("username")[scores_df.columns].sum()
            # ضمان ظهور جميع المستخدمين (حسب قائمة المستخدمين المسجلة)
            all_usernames = users_df["username"].tolist() if not users_df.empty else []
            grouped = grouped.reindex(all_usernames, fill_value=0)
            grouped = grouped.reset_index()
            st.dataframe(grouped, use_container_width=True)
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء تجميع البيانات: {e}")
    else:
        st.info("ℹ️ لا توجد بيانات للتقرير.")

##########################################
# تبويب 4: تجميعي بند
##########################################
with tabs[3]:
    st.subheader("📌 تجميعي بند لمستخدم")
    col1, col2 = st.columns(2)
    with col1:
        start_date_criteria = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_criteria")
    with col2:
        end_date_criteria = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_criteria")
    
    if not merged_df.empty and "التاريخ" in merged_df.columns:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], errors="coerce")
        filtered_df_criteria = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start_date_criteria)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end_date_criteria))
        ]
        all_columns = [col for col in filtered_df_criteria.columns if col not in ["التاريخ", "username"]]
        if all_columns:
            selected_activity = st.selectbox("اختر البند", all_columns, key="selected_activity")
            try:
                activity_sum = filtered_df_criteria.groupby("username")[selected_activity].sum().sort_values(ascending=True)
                all_usernames = users_df["username"].tolist() if not users_df.empty else []
                activity_sum = activity_sum.reindex(all_usernames, fill_value=0)
                st.dataframe(activity_sum, use_container_width=True)
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء تجميع البند: {e}")
        else:
            st.info("ℹ️ لا توجد بنود أخرى للتجميع.")
    else:
        st.info("ℹ️ لا توجد بيانات للتقرير.")

##########################################
# تبويب 5: تقرير فردي
##########################################
with tabs[4]:
    st.subheader("تقرير تفصيلي لمستخدم")
    col1, col2 = st.columns(2)
    with col1:
        start_date_indiv = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_indiv")
    with col2:
        end_date_indiv = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_indiv")
    
    if not merged_df.empty and "التاريخ" in merged_df.columns:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], errors="coerce")
        filtered_df_indiv = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start_date_indiv)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end_date_indiv))
        ]
        available_users = filtered_df_indiv["username"].unique().tolist()
        if available_users:
            selected_user_indiv = st.selectbox("اختر المستخدم", available_users, key="selected_user_indiv")
            user_df = filtered_df_indiv[filtered_df_indiv["username"] == selected_user_indiv].sort_values("التاريخ")
            if user_df.empty:
                st.info("ℹ️ لا توجد بيانات لهذا المستخدم في الفترة المحددة.")
            else:
                st.dataframe(user_df.reset_index(drop=True), use_container_width=True)
        else:
            st.info("ℹ️ لا توجد بيانات للتقرير.")
    else:
        st.info("ℹ️ لا توجد بيانات للتقرير.")

##########################################
# تبويب 6: رسوم بيانية
##########################################
with tabs[5]:
    st.subheader("📈 رسوم بيانية")
    col1, col2 = st.columns(2)
    with col1:
        start_date_chart = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_chart")
    with col2:
        end_date_chart = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_chart")
    
    if not merged_df.empty and "التاريخ" in merged_df.columns:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], errors="coerce")
        filtered_df_chart = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start_date_chart)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end_date_chart))
        ]
        try:
            scores_chart = filtered_df_chart.drop(columns=["التاريخ", "username"], errors="ignore")
            grouped_chart = filtered_df_chart.groupby("username")[scores_chart.columns].sum()
            all_usernames = users_df["username"].tolist() if not users_df.empty else []
            grouped_chart = grouped_chart.reindex(all_usernames, fill_value=0)
            # إضافة عمود المجموع
            grouped_chart["المجموع"] = grouped_chart.sum(axis=1)
            # رسم دائرة بيانية
            fig = go.Figure(go.Pie(
                labels=grouped_chart.index,
                values=grouped_chart["المجموع"],
                hole=0.4,
                title="مجموع الدرجات"
            ))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء رسم الرسوم البيانية: {e}")
    else:
        st.info("ℹ️ لا توجد بيانات للتقرير.")

##########################################
# تبويب 7: رصد الإنجاز
##########################################
with tabs[6]:
    st.subheader("📌 رصد الإنجاز")
    
    # الجزء الأول: رصد إنجاز جديد
    st.markdown("### ➕ رصد إنجاز جديد")
    # نفترض أن جدول achievements_list يحتوي على الإنجازات المتاحة
    try:
        achievements_df = pd.read_sql("SELECT achievement FROM achievements_list", conn)
        achievements = achievements_df["achievement"].dropna().tolist() if not achievements_df.empty else []
    except Exception as e:
        st.error(f"❌ تعذر تحميل قائمة الإنجازات: {e}")
        achievements = []
    
    if not users_df.empty and "username" in users_df.columns:
        student_list = users_df[users_df["role"] == "user"]["username"].tolist()
    else:
        student_list = []
    
    if student_list and achievements:
        selected_student = st.selectbox("اختر الطالب", student_list, key="student_select_achievement")
        selected_achievement = st.selectbox("🏆 اختر الإنجاز", achievements, key="achievement_select")
        if st.button("✅ رصد الإنجاز"):
            # التحقق من التكرار
            try:
                query_dup = "SELECT * FROM student_achievements WHERE student=%s AND achievement=%s"
                cursor.execute(query_dup, (selected_student, selected_achievement))
                exists = cursor.fetchone()
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء التحقق: {e}")
                exists = None
            if exists:
                st.warning("⚠️ هذا الإنجاز تم رصده مسبقًا لهذا الطالب. لا يمكن تكراره.")
            else:
                timestamp_ach = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    cursor.execute(
                        "INSERT INTO student_achievements (timestamp, student, supervisor, achievement) VALUES (%s, %s, %s, %s)",
                        (timestamp_ach, selected_student, username, selected_achievement)
                    )
                    conn.commit()
                    st.success("✅ تم رصد الإنجاز للطالب بنجاح.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء تسجيل الإنجاز: {e}")
    else:
        st.info("ℹ️ تأكد من وجود بيانات الطلاب وقائمة الإنجازات.")

    st.markdown("---")
    st.markdown("### 📖 عرض إنجازات طالب")
    if student_list:
        selected_view_student = st.selectbox("📚 اختر الطالب لعرض إنجازاته", student_list, key="student_view_achievement")
        if st.button("📄 عرض الإنجازات"):
            try:
                query_view = "SELECT timestamp, student, supervisor, achievement FROM student_achievements WHERE student=%s ORDER BY timestamp DESC"
                df_achievements = pd.read_sql(query_view, conn, params=(selected_view_student,))
                if df_achievements.empty:
                    st.warning("⚠️ لا توجد إنجازات مسجلة لهذا الطالب بعد.")
                else:
                    # إعادة تسمية الأعمدة للتنسيق
                    df_achievements = df_achievements.rename(columns={
                        "timestamp": "🕒 التاريخ",
                        "student": "الطالب",
                        "supervisor": "‍🏫 المشرف",
                        "achievement": "🏆 الإنجاز"
                    })
                    st.dataframe(df_achievements, use_container_width=True)
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء جلب بيانات الإنجازات: {e}")
    else:
        st.info("ℹ️ لا توجد بيانات للطلاب.")

# ===== إغلاق الاتصال ==========
cursor.close()
conn.close()
