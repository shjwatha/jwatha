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

# ===== إشعار ثابت عند وجود رسائل غير مقروءة =====
try:
    cursor.execute("""
        SELECT DISTINCT sender 
        FROM chat_messages 
        WHERE receiver = %s AND read_by_receiver = 0
    """, (username,))
    unread_senders = [row["sender"] for row in cursor.fetchall()]
except Exception as e:
    unread_senders = []

if unread_senders:
    names_str = " - ".join(unread_senders)
    st.markdown(
        f"""
        <div style="background-color:#FFCCCC; padding:10px; border-radius:5px; border: 1px solid red; margin-bottom: 15px;">
            <b>📨 لديك رسائل جديدة من: {names_str}</b>
        </div>
        """,
        unsafe_allow_html=True
    )

tabs = st.tabs([
    "تقرير إجمالي", 
    "💬 المحادثات", 
    "📋 تجميعي الكل", 
    "📌 تجميعي بند",  
    "تقرير فردي", 
    "📈 رسوم بيانية",
    "📌 رصد الإنجاز",
    "📝 رصد نقاطي"
])

# ===== تبويب 1: تقرير إجمالي =====
with tabs[0]:
    st.subheader("📄 تقرير إجمالي لكل طالب خلال فترة محددة")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7))
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date())

    try:
        cursor.execute("""
            SELECT student, score
            FROM daily_evaluations
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start_date, end_date))
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)

        if df.empty:
            st.info("ℹ️ لا توجد بيانات تقييم خلال هذه الفترة.")
        else:
            df_grouped = df.groupby("student")["score"].sum().reset_index()
            df_grouped.rename(columns={"student": "الطالب", "score": "📊 مجموع الدرجات"}, inplace=True)
            df_grouped = df_grouped.sort_values(by="📊 مجموع الدرجات", ascending=False)
            st.dataframe(df_grouped, use_container_width=True)
    except Exception as e:
        st.error(f"❌ فشل في تحميل البيانات: {e}")

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

    try:
        cursor.execute("""
            SELECT student, question, score
            FROM daily_evaluations
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start_date_all, end_date_all))
        df = pd.DataFrame(cursor.fetchall())

        if df.empty:
            st.info("ℹ️ لا توجد بيانات خلال الفترة المحددة.")
        else:
            pivoted = df.pivot_table(index="student", columns="question", values="score", aggfunc='sum').fillna(0)
            pivoted = pivoted.reindex(my_users, fill_value=0)
            pivoted["📊 المجموع"] = pivoted.sum(axis=1)
            st.dataframe(pivoted.reset_index(), use_container_width=True)
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")

# ===== تبويب 4: تجميعي بند =====
with tabs[3]:
    st.subheader("📌 تجميع حسب بند معين")
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_criteria")
    with col2:
        end = st.date_input("إلى تاريخ", datetime.today().date(), key="end_criteria")

    try:
        cursor.execute("""
            SELECT student, question, score
            FROM daily_evaluations
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start, end))
        df = pd.DataFrame(cursor.fetchall())

        if df.empty:
            st.info("ℹ️ لا توجد بيانات خلال الفترة المحددة.")
        else:
            available_questions = df["question"].unique().tolist()
            selected_q = st.selectbox("اختر البند", available_questions)

            df_q = df[df["question"] == selected_q].groupby("student")["score"].sum()
            df_q = df_q.reindex(my_users, fill_value=0)
            st.dataframe(df_q.reset_index().rename(columns={"student": "الطالب", "score": "📊 المجموع"}))
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")

# ===== تبويب 5: تقرير فردي =====
with tabs[4]:
    st.subheader("🧍‍♂️ تقرير مستخدم محدد")
    col1, col2 = st.columns(2)
    with col1:
        start_ind = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_ind")
    with col2:
        end_ind = st.date_input("إلى تاريخ", datetime.today().date(), key="end_ind")

    try:
        cursor.execute("""
            SELECT student, DATE(timestamp) AS التاريخ, question AS البند, score AS الدرجة, free_text AS "إجابة نصية"
            FROM daily_evaluations
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start_ind, end_ind))
        df = pd.DataFrame(cursor.fetchall())

        if df.empty:
            st.info("ℹ️ لا توجد بيانات خلال الفترة المحددة.")
        else:
            available_students = df["student"].unique().tolist()
            selected_student = st.selectbox("اختر المستخدم", available_students)
            user_data = df[df["student"] == selected_student]
            st.dataframe(user_data.reset_index(drop=True))
    except Exception as e:
        st.error(f"❌ فشل في تحميل البيانات: {e}")

# ===== تبويب 6: رسوم بيانية =====
with tabs[5]:
    st.subheader("📈 توزيع المجموع")
    col1, col2 = st.columns(2)
    with col1:
        start_chart = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_chart")
    with col2:
        end_chart = st.date_input("إلى تاريخ", datetime.today().date(), key="end_chart")

    try:
        cursor.execute("""
            SELECT student, score
            FROM daily_evaluations
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (start_chart, end_chart))
        df = pd.DataFrame(cursor.fetchall())

        if df.empty:
            st.info("ℹ️ لا توجد بيانات خلال هذه الفترة.")
        else:
            grouped = df.groupby("student")["score"].sum()
            grouped = grouped.reindex(my_users, fill_value=0)
            fig = go.Figure(go.Pie(
                labels=grouped.index,
                values=grouped.values,
                hole=0.4,
                title="توزيع النقاط"
            ))
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"❌ فشل في تحميل أو عرض البيانات: {e}")

# ===== تبويب 7: 📌 رصد الإنجاز =====
with tabs[6]:
    st.subheader("📌 رصد الإنجاز")
    
    # --- القسم الأول: رصد إنجاز جديد ---
    st.markdown("### ➕ رصد إنجاز جديد")
    
    # 1. جلب قائمة الإنجازات (managed by SuperAdmin)
    try:
        ach_df = pd.read_sql("SELECT id, achievement FROM achievements_list", conn)

        achievements = ach_df.to_dict('records')
    except Exception as e:
        st.error(f"❌ تعذر تحميل قائمة الإنجازات: {e}")
        achievements = []

    # 2. جلب قائمة الطلاب المرتبطين بالمشرف (بما في ذلك تدرّجه)
    all_students = []
    for sup in [username] + my_supervisors:
        cursor.execute("""
            SELECT username 
            FROM users 
            WHERE role='user' AND mentor=%s AND is_deleted=FALSE AND level=%s
        """, (sup, my_level))
        all_students += [r["username"] for r in cursor.fetchall()]
    student_list = sorted(set(all_students))

    if achievements and student_list:
        # اختيار الطالب
        selected_student = st.selectbox("👤 اختر الطالب", student_list, key="student_select_ach")
        # بناء القائمة لعرضها بصيغة "🏆 إنجاز"
        achievement_labels = [f"{a['achievement']}" for a in achievements]
        sel_idx = st.selectbox("🏆 اختر الإنجاز", list(range(len(achievement_labels))),
                               format_func=lambda i: achievement_labels[i],
                               key="ach_select_idx")
        
        if st.button("✅ رصد الإنجاز"):
            ach_id = achievements[sel_idx]["id"]
            ach_name = achievements[sel_idx]["achievement"]
            try:
                # تأكد من عدم وجود تسجيل مسبق
                cursor.execute(
                    "SELECT 1 FROM student_achievements WHERE student=%s AND achievement_id=%s",
                    (selected_student, ach_id)
                )
                if cursor.fetchone():
                    st.warning("⚠️ هذا الإنجاز تم رصده مسبقًا لهذا الطالب.")
                else:
                    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        """
                        INSERT INTO student_achievements 
                            (timestamp, student, supervisor, achievement_id) 
                        VALUES (%s, %s, %s, %s)
                        """,
                        (ts, selected_student, username, ach_id)
                    )
                    conn.commit()
                    st.success(f"✅ تم رصد الإنجاز «{ach_name}» للطالب {selected_student}.")
                    st.rerun()

            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء رصد الإنجاز: {e}")
    else:
        st.info("ℹ️ تأكد من وجود بيانات طلاب وقائمة إنجازات.")

    st.markdown("---")

    # --- القسم الثاني: عرض إنجازات طالب معين ---
    st.markdown("### 📖 عرض إنجازات طالب")

    if student_list:
        selected_view = st.selectbox("📚 اختر الطالب للعرض", student_list, key="student_view_ach")
        if st.button("📄 عرض الإنجازات"):
            try:
                query = """
                    SELECT sa.timestamp AS التاريخ,
                           al.achievement AS "🏆 الإنجاز",
                           sa.supervisor AS "المشرف"
                    FROM student_achievements sa
                    JOIN achievements_list al
                      ON sa.achievement_id = al.id
                    WHERE sa.student = %s
                    ORDER BY sa.timestamp DESC
                """
                df_view = pd.read_sql(query, conn, params=(selected_view,))
                if df_view.empty:
                    st.warning("⚠️ لا توجد إنجازات مسجّلة لهذا الطالب.")
                else:
                    st.dataframe(df_view, use_container_width=True)
            except Exception as e:
                st.error(f"❌ فشل في عرض الإنجازات: {e}")
    else:
        st.info("ℹ️ لا توجد بيانات لعرضها.")


# ===== تبويب 8: 📝 رصد نقاطي لكل طالب =====
with tabs[7]:
    st.subheader("📝 رصد النقاط من المشرف")

    # اختيار الطالب
    if not my_users:
        st.info("ℹ️ لا يوجد طلاب مرتبطين بك.")
    else:
        selected_student = st.selectbox("👤 اختر الطالب", my_users)

        # تحميل البنود الخاصة بمستوى المشرف
        try:
            cursor.execute("SELECT question, max_score, is_visible_to_user FROM supervisor_criteria WHERE level = %s", (my_level,))
            criteria = cursor.fetchall()

            if not criteria:
                st.info("ℹ️ لا توجد بنود تقييم لهذا المستوى.")
            else:
                with st.form("evaluation_form"):
                    scores = {}
                    for item in criteria:
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            scores[item['question']] = st.number_input(
                                f"🔹 {item['question']} (من {item['max_score']})",
                                min_value=0, max_value=item['max_score'], step=1,
                                key=f"score_{item['question']}"
                            )
                        with col2:
                            st.markdown(f"<br>📢 <b>يظهر للمستخدم؟</b> {'نعم' if item['is_visible_to_user'] else 'لا'}", unsafe_allow_html=True)

                    submitted = st.form_submit_button("💾 حفظ التقييم")

                    if submitted:
                        timestamp_now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                        try:
                            for q, s in scores.items():
                                academic_year = f"{datetime.utcnow().year}-{datetime.utcnow().year + 1}"
                                cursor.execute("""
                                    INSERT INTO supervisor_evaluations (timestamp, student, supervisor, question, score, academic_year)

                                    VALUES (%s, %s, %s, %s, %s)
                                """, (timestamp_now, selected_student, username, q, s, academic_year))

                            conn.commit()
                            st.success("✅ تم حفظ التقييم.")
                        except Exception as e:
                            st.error(f"❌ حدث خطأ أثناء الحفظ: {e}")

        except Exception as e:
            st.error(f"❌ فشل في تحميل البنود: {e}")
