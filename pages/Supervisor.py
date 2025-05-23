import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime, timedelta
import plotly.graph_objects as go

# ===== إعداد الصفحة والتحقق من الجلسة =====
st.set_page_config(page_title="📊 تقارير المشرف", page_icon="📊", layout="wide")

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.error("🚫 الرجاء تسجيل الدخول.")
    st.stop()

username = st.session_state.get("username", "")
permissions = st.session_state.get("permissions", "")

if permissions not in ["supervisor", "sp"]:
    st.error("🚫 لا تملك صلاحية الوصول لهذه الصفحة.")
    st.stop()

st.title(f"👋 أهلاً {username}")

# ===== الاتصال بقاعدة البيانات =====
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

# ===== التحقق من المستوى والربط الهرمي للمشرفين =====
try:
    cursor.execute("SELECT level, mentor FROM admins WHERE username = %s AND is_deleted = FALSE", (username,))
    row = cursor.fetchone()
    my_level = row["level"] if row else None
    my_mentor = row["mentor"] if row else None

    cursor.execute("SELECT level_name FROM levels")
    valid_levels = [lvl["level_name"] for lvl in cursor.fetchall()]

    if not my_level or my_level not in valid_levels:
        st.error("⚠️ المستوى المرتبط بهذا الحساب غير معتمد. يرجى مراجعة الإدارة.")
        st.stop()

    if permissions == "supervisor" and not my_mentor:
        st.error("⚠️ لا يوجد سوبر مشرف مرتبط بهذا المشرف.")
        st.stop()

except Exception as e:
    st.error(f"❌ فشل في التحقق من مستوى المشرف أو السوبر مشرف: {e}")
    st.stop()

# ===== تحميل المستخدمين والمشرفين =====
all_user_options = []

if permissions == "sp":
    cursor.execute("SELECT username FROM admins WHERE role = 'supervisor' AND mentor = %s AND is_deleted = FALSE", (username,))
    my_supervisors = [row["username"] for row in cursor.fetchall()]
    all_user_options += [(s, "مشرف") for s in my_supervisors]
else:
    my_supervisors = []

# تحميل الطلاب المرتبطين بالمشرف أو السوبر مشرف (حسب المستوى أيضاً)
my_users = []
for supervisor in ([username] + my_supervisors):
    cursor.execute("""
        SELECT username FROM users 
        WHERE role = 'user' AND mentor = %s AND is_deleted = FALSE AND level = %s
    """, (supervisor, my_level))
    my_users += [row["username"] for row in cursor.fetchall()]
all_user_options += [(u, "مستخدم") for u in my_users]

# تحميل تقارير الأداء
try:
    merged_df = pd.read_sql("SELECT * FROM reports", conn)
except Exception as e:
    st.error(f"❌ حدث خطأ أثناء تحميل تقارير الأداء: {e}")
    merged_df = pd.DataFrame()

# ===== إشعار بالرسائل غير المقروءة قبل عرض التبويبات =====
try:
    cursor.execute("""
        SELECT COUNT(*) as unread_count 
        FROM chat_messages 
        WHERE receiver = %s AND read_by_receiver = 0
    """, (username,))
    unread_row = cursor.fetchone()
    unread_count = unread_row["unread_count"] if unread_row else 0
except Exception as e:
    unread_count = 0

# تهيئة التبويب الحالي في session_state
if "selected_tab_index" not in st.session_state:
    st.session_state["selected_tab_index"] = 0  # التبويب الأول (تقرير إجمالي)

# إشعار إذا كان هناك رسائل جديدة
if unread_count > 0 and st.session_state["selected_tab_index"] != 1:
    st.warning(f"📬 لديك {unread_count} رسالة جديدة غير مقروءة في تبويب المحادثات.")
    if st.button("🔁 الانتقال إلى تبويب المحادثات"):
        st.session_state["selected_tab_index"] = 1
        st.rerun()

# ===== التبويبات =====
tabs = st.tabs([
    "تقرير إجمالي", 
    "💬 المحادثات", 
    "📋 تجميعي الكل", 
    "📌 تجميعي بند",  
    "تقرير فردي", 
    "📈 رسوم بيانية",
    "📌 رصد الإنجاز"
])

# ===== تبويب 1: تقرير إجمالي =====
with tabs[0]:
    st.subheader("📄 تقرير إجمالي")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7))
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date())

    if not merged_df.empty and "التاريخ" in merged_df.columns:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], format="%Y-%m-%d", errors="coerce")
        filtered_df = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start_date)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end_date))
        ]
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("ℹ️ لا توجد بيانات متاحة.")

# ===== تبويب 2: المحادثات =====
with tabs[1]:
    st.subheader("💬 المحادثة")
    display_options = ["اختر الشخص"] + [f"{name} ({role})" for name, role in all_user_options]
    selected_display = st.selectbox("اختر الشخص", display_options)
    
    if selected_display != "اختر الشخص":
        selected_user = selected_display.split("(")[0].strip()

        try:
            chat_df = pd.read_sql("SELECT * FROM chat_messages", conn)
        except Exception as e:
            st.error(f"❌ فشل تحميل المحادثات: {e}")
            chat_df = pd.DataFrame()

        if not chat_df.empty:
            # تحديث حالة القراءة
            unread = chat_df[
                (chat_df["sender"] == selected_user) &
                (chat_df["receiver"] == username) &
                (chat_df["read_by_receiver"] == 0)
            ]
            for _, msg in unread.iterrows():
                cursor.execute("UPDATE chat_messages SET read_by_receiver = 1 WHERE id = %s", (msg["id"],))
            conn.commit()

            # عرض الرسائل
            msgs = chat_df[
                ((chat_df["sender"] == username) & (chat_df["receiver"] == selected_user)) |
                ((chat_df["sender"] == selected_user) & (chat_df["receiver"] == username))
            ].sort_values("timestamp")

            for _, msg in msgs.iterrows():
                sender_name = "أنت" if msg["sender"] == username else msg["sender"]
                color = "#8B0000" if msg["sender"] == username else "#000080"
                if msg["sender"] == username:
                    check_icon = "✅" if msg["read_by_receiver"] == 1 else "☑️"
                else:
                    check_icon = ""

                ts = msg["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                time_str = ts.strftime("%I:%M %p - %Y/%m/%d").replace("AM", "صباحًا").replace("PM", "مساءً")

                st.markdown(
                    f"""
                    <div style='color:{color}; margin-bottom:2px;'>
                        <b>{sender_name}:</b> {msg['message']} <span style='float:left;'>{check_icon}</span>
                        <br><span style='font-size:11px; color:gray;'>{time_str}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("💬 لا توجد رسائل حالياً.")

        # تفريغ الحقل بعد الإرسال
        if "new_msg" not in st.session_state:
            st.session_state["new_msg"] = ""

        new_msg = st.text_area("✏️ اكتب رسالتك", height=100, key="new_msg")
        if st.button("📨 إرسال الرسالة"):
            if new_msg.strip():
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    cursor.execute(
                        "INSERT INTO chat_messages (timestamp, sender, receiver, message, read_by_receiver) VALUES (%s, %s, %s, %s, %s)",
                        (ts, username, selected_user, new_msg.strip(), 0)
                    )
                    conn.commit()
                    st.success("✅ تم الإرسال")
                    del st.session_state["new_msg"]  # ✅ تفريغ الحقل
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ فشل الإرسال: {e}")
            else:
                st.warning("⚠️ لا يمكن إرسال رسالة فارغة.")
# ===== تبويب 3: تجميعي الكل =====
with tabs[2]:
    st.subheader("📋 تجميع درجات الكل")
    col1, col2 = st.columns(2)
    with col1:
        start_date_all = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_all")
    with col2:
        end_date_all = st.date_input("إلى تاريخ", datetime.today().date(), key="end_all")

    if not merged_df.empty:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], format="%Y-%m-%d", errors="coerce")
        df_filtered = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start_date_all)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end_date_all))
        ]
        try:
            data = df_filtered.drop(columns=["التاريخ", "username"], errors="ignore")
            grouped = df_filtered.groupby("username")[data.columns].sum()
            grouped = grouped.reindex(my_users, fill_value=0).reset_index()
            st.dataframe(grouped, use_container_width=True)
        except Exception as e:
            st.error(f"❌ خطأ في تجميع البيانات: {e}")
    else:
        st.info("ℹ️ لا توجد بيانات متاحة.")

# ===== تبويب 4: تجميعي بند =====
with tabs[3]:
    st.subheader("📌 تجميع حسب بند معين")
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_criteria")
    with col2:
        end = st.date_input("إلى تاريخ", datetime.today().date(), key="end_criteria")

    if not merged_df.empty:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], errors="coerce")
        df_filtered = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end))
        ]
        all_cols = [c for c in df_filtered.columns if c not in ["التاريخ", "username"]]
        if all_cols:
            selected_col = st.selectbox("اختر البند", all_cols)
            try:
                summary = df_filtered.groupby("username")[selected_col].sum()
                summary = summary.reindex(my_users, fill_value=0)
                st.dataframe(summary)
            except Exception as e:
                st.error(f"❌ خطأ في تجميع البند: {e}")
        else:
            st.warning("⚠️ لا توجد بنود متاحة.")
    else:
        st.info("ℹ️ لا توجد بيانات.")

# ===== تبويب 5: تقرير فردي =====
with tabs[4]:
    st.subheader("🧍‍♂️ تقرير مستخدم محدد")
    col1, col2 = st.columns(2)
    with col1:
        start_ind = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_ind")
    with col2:
        end_ind = st.date_input("إلى تاريخ", datetime.today().date(), key="end_ind")

    if not merged_df.empty:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], errors="coerce")
        df_filtered = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start_ind)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end_ind))
        ]
        available_users = df_filtered["username"].unique().tolist()
        if available_users:
            selected_user = st.selectbox("اختر المستخدم", available_users)
            user_data = df_filtered[df_filtered["username"] == selected_user]
            st.dataframe(user_data.reset_index(drop=True))
        else:
            st.warning("⚠️ لا توجد بيانات.")

# ===== تبويب 6: رسوم بيانية =====
with tabs[5]:
    st.subheader("📈 توزيع المجموع")
    col1, col2 = st.columns(2)
    with col1:
        start_chart = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_chart")
    with col2:
        end_chart = st.date_input("إلى تاريخ", datetime.today().date(), key="end_chart")

    if not merged_df.empty:
        merged_df["التاريخ"] = pd.to_datetime(merged_df["التاريخ"], errors="coerce")
        df_chart = merged_df[
            (merged_df["التاريخ"] >= pd.to_datetime(start_chart)) &
            (merged_df["التاريخ"] <= pd.to_datetime(end_chart))
        ]
        try:
            chart_data = df_chart.drop(columns=["التاريخ", "username"], errors="ignore")
            grouped = df_chart.groupby("username")[chart_data.columns].sum()
            grouped["المجموع"] = grouped.sum(axis=1)
            fig = go.Figure(go.Pie(
                labels=grouped.index,
                values=grouped["المجموع"],
                hole=0.4,
                title="توزيع النقاط"
            ))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"❌ خطأ في عرض الرسم البياني: {e}")
    else:
        st.info("ℹ️ لا توجد بيانات.")

# ===== تبويب 7: 📌 رصد الإنجاز =====
with tabs[6]:
    st.subheader("📌 رصد الإنجاز")
    
    # --- القسم الأول: رصد إنجاز جديد ---
    st.markdown("### ➕ رصد إنجاز جديد")
    
    try:
        achievements_df = pd.read_sql("SELECT achievement FROM achievements_list", conn)
        achievements = achievements_df["achievement"].dropna().tolist() if not achievements_df.empty else []
    except Exception as e:
        st.error(f"❌ تعذر تحميل قائمة الإنجازات: {e}")
        achievements = []

    try:
        student_df = pd.read_sql("SELECT username FROM users WHERE role = 'user' AND is_deleted = FALSE", conn)
        student_list = student_df["username"].tolist() if not student_df.empty else []
    except Exception as e:
        st.error(f"❌ تعذر تحميل قائمة الطلاب: {e}")
        student_list = []

    if student_list and achievements:
        selected_student = st.selectbox("👤 اختر الطالب", student_list, key="student_select_achievement")
        selected_achievement = st.selectbox("🏆 اختر الإنجاز", achievements, key="achievement_select")
        if st.button("✅ رصد الإنجاز"):
            try:
                cursor.execute("SELECT * FROM student_achievements WHERE student = %s AND achievement = %s", (selected_student, selected_achievement))
                exists = cursor.fetchone()
                if exists:
                    st.warning("⚠️ هذا الإنجاز تم رصده مسبقًا لهذا الطالب.")
                else:
                    timestamp_now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        "INSERT INTO student_achievements (timestamp, student, supervisor, achievement) VALUES (%s, %s, %s, %s)",
                        (timestamp_now, selected_student, username, selected_achievement)
                    )
                    conn.commit()
                    st.success("✅ تم رصد الإنجاز بنجاح.")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء رصد الإنجاز: {e}")
    else:
        st.info("ℹ️ تأكد من وجود بيانات طلاب وقائمة إنجازات.")

    st.markdown("---")

    # --- القسم الثاني: عرض إنجازات طالب معين ---
    st.markdown("### 📖 عرض إنجازات طالب")

    if student_list:
        selected_view_student = st.selectbox("📚 اختر الطالب", student_list, key="student_view_achievement")
        if st.button("📄 عرض الإنجازات"):
            try:
                ach_query = """
                    SELECT timestamp, student, supervisor, achievement 
                    FROM student_achievements 
                    WHERE student = %s 
                    ORDER BY timestamp DESC
                """
                df_ach = pd.read_sql(ach_query, conn, params=(selected_view_student,))
                if df_ach.empty:
                    st.warning("⚠️ لا توجد إنجازات لهذا الطالب.")
                else:
                    df_ach.rename(columns={
                        "timestamp": "🕒 التاريخ",
                        "student": "الطالب",
                        "supervisor": "المشرف",
                        "achievement": "🏆 الإنجاز"
                    }, inplace=True)
                    st.dataframe(df_ach, use_container_width=True)
            except Exception as e:
                st.error(f"❌ فشل في عرض الإنجازات: {e}")
    else:
        st.info("ℹ️ لا توجد بيانات لعرضها.")
