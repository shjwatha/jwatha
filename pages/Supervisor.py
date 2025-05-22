import streamlit as st
import pymysql
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go

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

# ===== إعداد الصفحة =====
st.set_page_config(page_title="📊 تقارير المشرف", page_icon="📊", layout="wide")

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

st.title(f"👋 أهلاً {st.session_state['username']}")

# ===== تحديد المستخدمين المتاحين للمحادثة =====
all_user_options = []

# التحقق من صلاحيات المستخدم وتحديد المستخدمين المسموح لهم بالمحادثة
if st.session_state["permissions"] == "sp":
    my_supervisors = []
    cursor.execute("SELECT username FROM users WHERE role = 'supervisor' AND mentor = %s", (st.session_state["username"],))
    my_supervisors = [row['username'] for row in cursor.fetchall()]
    all_user_options += [(s, "مشرف") for s in my_supervisors]

if st.session_state["permissions"] in ["supervisor", "sp"]:
    assigned_users = []
    cursor.execute("SELECT username FROM users WHERE role = 'user' AND mentor = %s", (st.session_state["username"],))
    assigned_users = [row['username'] for row in cursor.fetchall()]
    all_user_options += [(u, "مستخدم") for u in assigned_users]

# إضافة سوبر مشرفين (إن وُجدوا) إلى القائمة للدردشة معهم
# تحميل بيانات الطلاب لعرض التقارير
if st.session_state["permissions"] == "supervisor":
    cursor.execute("SELECT * FROM users WHERE role = 'user' AND mentor = %s", (st.session_state["username"],))
    filtered_users = cursor.fetchall()
elif st.session_state["permissions"] == "sp":
    cursor.execute("SELECT * FROM users WHERE role = 'supervisor' AND mentor = %s", (st.session_state["username"],))
    supervisors = [row['username'] for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM users WHERE role = 'user' AND mentor IN (%s)", (",".join(supervisors),))
    filtered_users = cursor.fetchall()
else:
    filtered_users = []

all_data = []
users_with_data = []
all_usernames = [user['username'] for user in filtered_users]

for user in filtered_users:
    user_name = user['username']
    try:
        # هنا يمكن تعديل طريقة جلب البيانات لتكون من قاعدة البيانات
        cursor.execute("SELECT * FROM user_data WHERE username = %s", (user_name,))
        user_records = cursor.fetchall()
        df = pd.DataFrame(user_records)
        if "التاريخ" in df.columns:
            df["التاريخ"] = pd.to_datetime(df["التاريخ"], errors="coerce")
            df.insert(0, "username", user_name)
            all_data.append(df)
            users_with_data.append(user_name)
    except Exception as e:
        st.warning(f"⚠️ خطأ في تحميل بيانات {user_name}: {e}")

if not all_data:
    st.info("ℹ️ لا توجد بيانات.")
    st.stop()

merged_df = pd.concat(all_data, ignore_index=True)

# ====== تبويبات الصفحة ======
tabs = st.tabs([ "تقرير إجمالي", "💬 المحادثات", "📋 تجميعي الكل", "📌 تجميعي بند", "تقرير فردي", "📈 رسوم بيانية", "📌 رصد الإنجاز"])

# ===== دالة عرض المحادثة =====

def show_chat_supervisor():
    st.subheader("💬 الدردشة")

    if "selected_user_display" not in st.session_state:
        st.session_state["selected_user_display"] = "اختر الشخص"

    options_display = ["اختر الشخص"] + [f"{name} ({role})" for name, role in all_user_options]
    selected_display = st.selectbox("اختر الشخص", options_display, key="selected_user_display")

    if selected_display != "اختر الشخص":
        selected_user = selected_display.split("(")[0]

        # هنا يمكنك تحديث دالة استرجاع المحادثات
        cursor.execute("SELECT * FROM chat WHERE (from_user = %s AND to_user = %s) OR (from_user = %s AND to_user = %s)", (st.session_state['username'], selected_user, selected_user, st.session_state['username']))
        chat_data = pd.DataFrame(cursor.fetchall())

        # تحقق من أن البيانات ليست فارغة
        if chat_data.empty:
            st.info("💬 لا توجد رسائل بعد.")
        else:
            # تحقق من وجود الأعمدة المطلوبة
            required_columns = ['timestamp', 'from', 'to', 'message', 'read_by_receiver']
            if not required_columns.issubset(chat_data.columns):
                st.warning(f"⚠️ الأعمدة المطلوبة غير موجودة في قاعدة البيانات. الأعمدة الموجودة: {chat_data.columns}")
                return

            # حذف أي بيانات فارغة في الحقول المطلوبة
            chat_data = chat_data.dropna(subset=['timestamp', 'from', 'to', 'message', 'read_by_receiver'])

            # تحديث حالة القراءة
            unread_indexes = chat_data[
                (chat_data['from'] == selected_user) &
                (chat_data['to'] == st.session_state['username']) &
                (chat_data['read_by_receiver'].astype(str).str.strip() == "")
            ].index.tolist()

            for i in unread_indexes:
                cursor.execute("UPDATE chat SET read_by_receiver = %s WHERE id = %s", ("✓", chat_data.iloc[i]['id']))
                conn.commit()

            # عرض الرسائل
            messages = chat_data[
                ((chat_data['from'] == st.session_state['username']) & (chat_data['to'] == selected_user)) |
                ((chat_data['from'] == selected_user) & (chat_data['to'] == st.session_state['username']))
            ]
            messages = messages.sort_values(by='timestamp')

            if messages.empty:
                st.info("💬 لا توجد رسائل بعد.")
            else:
                for _, msg in messages.iterrows():
                    if msg['from'] == st.session_state['username']:
                        st.markdown(f"<p style='color:#8B0000;'>ب‍ أنت: {msg['message']}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='color:#000080;'>ب‍ {msg['from']}: {msg['message']}</p>", unsafe_allow_html=True)

        # حقل النص لإدخال الرسالة
        new_msg = st.text_area("✏️ اكتب رسالتك", height=100, key="chat_message")
        if st.button("📨 إرسال الرسالة"):
            if new_msg.strip():  # تأكد من أن الرسالة ليست فارغة
                timestamp = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d %H%M%S")
                cursor.execute("INSERT INTO chat (timestamp, from_user, to_user, message) VALUES (%s, %s, %s, %s)", (timestamp, st.session_state['username'], selected_user, new_msg))
                conn.commit()
                st.success("✅ تم إرسال الرسالة")

                # إعادة تحميل الصفحة بعد الإرسال
                st.rerun()

                # مسح النص في حقل النص
                del st.session_state['chat_message']
            else:
                st.warning("⚠️ لا يمكن إرسال رسالة فارغة.")


# ===== تبويب 1 تقرير إجمالي =====
with tabs[0]:
    # === تنبيه بالرسائل غير المقروءة ===
    cursor.execute("SELECT * FROM chat WHERE to_user = %s AND read_by_receiver = ''", (st.session_state['username'],))
    chat_data = pd.DataFrame(cursor.fetchall())
    
    # === التقويم لتصفية البيانات حسب التاريخ ===
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_0")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_0")

    filtered_df = merged_df[
        (merged_df['التاريخ'] >= pd.to_datetime(start_date)) & 
        (merged_df['التاريخ'] <= pd.to_datetime(end_date))
    ]

    # تحقق من وجود الأعمدة المطلوبة
    required_columns = ['to', 'message', 'read_by_receiver', 'from']
    if all(col in chat_data.columns for col in required_columns):
        unread_msgs = chat_data[
            (chat_data['to'] == st.session_state['username']) &
            (chat_data['message'].notna()) &
            (chat_data['read_by_receiver'].astype(str).str.strip() == "")
        ]
        senders = unread_msgs['from'].unique().tolist()
        if senders:
            sender_list = ", ".join(senders)
            st.markdown(
                f"<p style='color:red; font-weight:bold;'>يوجد لديك عدد دردشات لم تطلع عليها من ({sender_list})</p>",
                unsafe_allow_html=True
            )
    else:
        st.warning("⚠️ لا يوجد لديك دردشات، تأكد من الضغط على أيقونة جلب المعلومات من قاعدة البيانات دائمًا.")

    st.subheader("مجموع درجات كل مستخدم")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_2"):
        st.cache_data.clear()
        st.rerun()

    scores = filtered_df.drop(columns=['التاريخ', 'username'], errors='ignore')
    grouped = filtered_df.groupby('username')[scores.columns].sum()
    grouped = grouped.reindex(all_usernames, fill_value=0)  # ✅ ضمان ظهور كل المستخدمين
    grouped['المجموع'] = grouped.sum(axis=1)
    grouped = grouped.sort_values(by='المجموع', ascending=True)

    for user, row in grouped.iterrows():
        st.markdown(f"<span style='color:#006400;'>{user}  {row['المجموع']} درجة</span>", unsafe_allow_html=True)

# ===== تبويب 2 المحادثات =====
with tabs[1]:
    show_chat_supervisor()

# ===== تبويب 3 تجميعي الكل =====
with tabs[2]:
    # === التقويم لتصفية البيانات حسب التاريخ ===
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_2")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_2")

    filtered_df = merged_df[
        (merged_df['التاريخ'] >= pd.to_datetime(start_date)) & 
        (merged_df['التاريخ'] <= pd.to_datetime(end_date))
    ]

    scores = filtered_df.drop(columns=['التاريخ', 'username'], errors='ignore')
    grouped = filtered_df.groupby('username')[scores.columns].sum()
    grouped = grouped.reindex(all_usernames, fill_value=0)  # ✅ لإظهار كل المستخدمين

    # إعادة تعيين 'username' كعمود
    grouped = grouped.reset_index()

    # عكس ترتيب الأعمدة مع الحفاظ على عمود 'username' في البداية
    grouped = grouped[['username'] + [col for col in grouped.columns if col != 'username']]

    st.subheader("📋 تفاصيل الدرجات للجميع")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_3"):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        """
        <style>
        .stDataFrame {
            direction: rtl;
            text-align: right;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.dataframe(grouped, use_container_width=True)

# ===== تبويب 4 تجميعي بند =====
with tabs[3]:
    # === التقويم لتصفية البيانات حسب التاريخ ===
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_3")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_3")

    filtered_df = merged_df[
        (merged_df['التاريخ'] >= pd.to_datetime(start_date)) & 
        (merged_df['التاريخ'] <= pd.to_datetime(end_date))
    ]

    st.subheader("📌 مجموع بند لمستخدم")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_4"):
        st.cache_data.clear()
        st.rerun()
    
    all_columns = [col for col in filtered_df.columns if col not in ['التاريخ', 'username']]
    selected_activity = st.selectbox("اختر البند", all_columns)

    activity_sum = filtered_df.groupby('username')[selected_activity].sum().sort_values(ascending=True)
    activity_sum = activity_sum.reindex(all_usernames, fill_value=0)  # ✅ ضمان ظهور كل المستخدمين

    st.dataframe(activity_sum, use_container_width=True)

# ===== تبويب 5 تقرير فردي =====
with tabs[4]:
    # === التقويم لتصفية البيانات حسب التاريخ ===
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_4")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_4")

    filtered_df = merged_df[
        (merged_df['التاريخ'] >= pd.to_datetime(start_date)) & 
        (merged_df['التاريخ'] <= pd.to_datetime(end_date))
    ]

    st.subheader("تقرير تفصيلي لمستخدم")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_5"):
        st.cache_data.clear()
        st.rerun()
    
    selected_user = st.selectbox("اختر المستخدم", filtered_df['username'].unique())
    user_df = filtered_df[filtered_df['username'] == selected_user].sort_values('التاريخ')

    if user_df.empty:
        st.info("لا توجد بيانات لهذا المستخدم في الفترة المحددة.")
    else:
        st.dataframe(user_df.reset_index(drop=True), use_container_width=True)

# ===== تبويب 6 رسوم بيانية =====
with tabs[5]:
    # === التقويم لتصفية البيانات حسب التاريخ ===
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ", datetime.today().date() - timedelta(days=7), key="start_date_5")
    with col2:
        end_date = st.date_input("إلى تاريخ", datetime.today().date(), key="end_date_5")

    filtered_df = merged_df[
        (merged_df['التاريخ'] >= pd.to_datetime(start_date)) & 
        (merged_df['التاريخ'] <= pd.to_datetime(end_date))
    ]

    st.subheader("📈 رسوم بيانية")
    if st.button("🔄 جلب المعلومات من قاعدة البيانات", key="refresh_6"):
        st.cache_data.clear()
        st.rerun()

    scores = filtered_df.drop(columns=['التاريخ', 'username'], errors='ignore')
    grouped = filtered_df.groupby('username')[scores.columns].sum()
    grouped = grouped.reindex(all_usernames, fill_value=0)  # ✅ ضمان ظهور كل المستخدمين
    grouped['المجموع'] = grouped.sum(axis=1)

    fig = go.Figure(go.Pie(
        labels=grouped.index,
        values=grouped['المجموع'],
        hole=0.4,
        title="مجموع الدرجات"
    ))
    st.plotly_chart(fig, use_container_width=True)


# ================= تبويب رصد الإنجازات ==================

with tabs[6]:
    st.subheader("📌 رصد الإنجاز")

    # 🟢 استيراد قائمة الإنجازات من قاعدة البيانات
    try:
        cursor.execute("SELECT * FROM achievements")
        achievements_data = cursor.fetchall()
        achievements = [a['achievement_name'] for a in achievements_data]
    except Exception as e:
        st.error(f"❌ تعذر تحميل قائمة الإنجازات: {e}")
        st.stop()

    # 🟢 استيراد ورقة الملاحظات أو إنشاءها إذا لم تكن موجودة
    try:
        cursor.execute("SELECT * FROM notes WHERE supervisor = %s", (st.session_state['username'],))
        notes_data = pd.DataFrame(cursor.fetchall())
    except Exception as e:
        st.error(f"❌ تعذر تحميل الملاحظات: {e}")
        st.stop()

    # 🟢 القسم الأول رصد إنجاز جديد
    st.markdown("### ➕ رصد إنجاز جديد")

    student_list = [user['username'] for user in filtered_users]
    selected_student = st.selectbox("اختر الطالب", student_list, key="student_select_achievement")

    selected_achievement = st.selectbox("🏆 اختر الإنجاز", achievements, key="achievement_select")

    if st.button("✅ رصد الإنجاز"):
        # التحقق من التكرار
        already_exists = False
        if not notes_data.empty:
            exists_df = notes_data[
                (notes_data['student'] == selected_student) &
                (notes_data['achievement'] == selected_achievement)
            ]
            if not exists_df.empty:
                already_exists = True

        if already_exists:
            st.warning("⚠️ هذا الإنجاز تم رصده مسبقًا لهذا الطالب. لا يمكن تكراره.")
        else:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H%M%S")
            cursor.execute("INSERT INTO notes (timestamp, student, supervisor, achievement) VALUES (%s, %s, %s, %s)",
                           (timestamp, selected_student, st.session_state['username'], selected_achievement))
            conn.commit()
            st.success("✅ تم رصد الإنجاز للطالب بنجاح.")
            st.cache_data.clear()
            st.rerun()

    # 🔵 القسم الثاني استعراض إنجازات طالب معين
    st.markdown("---")
    st.markdown("### 📖 عرض إنجازات طالب")

    selected_view_student = st.selectbox("📚 اختر الطالب لعرض إنجازاته", student_list, key="student_view_achievement")

    if st.button("📄 عرض الإنجازات"):
        if notes_data.empty:
            st.info("ℹ️ لا توجد بيانات إنجازات حتى الآن.")
        else:
            filtered = notes_data[notes_data['student'] == selected_view_student]
            if filtered.empty:
                st.warning("⚠️ لا توجد إنجازات مسجلة لهذا الطالب بعد.")
            else:
                filtered = filtered.rename(columns={
                    'timestamp': '🕒 التاريخ',
                    'student': 'الطالب',
                    'supervisor': 'المشرف',
                    'achievement': '🏆 الإنجاز'
                })
                st.dataframe(filtered[['🕒 التاريخ', 'الطالب', 'المشرف', '🏆 الإنجاز']], use_container_width=True)

# ================= تبويب محادثات المشرف ==================
# ================= تبويب 7 محادثات المشرف ==================

with tabs[7]:
    st.subheader("📬 محادثات المشرف")

    if "selected_user_display" not in st.session_state:
        st.session_state["selected_user_display"] = "اختر الشخص"

    options_display = ["اختر الشخص"] + [f"{name} ({role})" for name, role in all_user_options]
    selected_display = st.selectbox("اختر الشخص", options_display, key="selected_user_display")

    if selected_display != "اختر الشخص":
        selected_user = selected_display.split("(")[0]

        # هنا يمكنك تحديث دالة استرجاع المحادثات
        cursor.execute("SELECT * FROM chat WHERE (from_user = %s AND to_user = %s) OR (from_user = %s AND to_user = %s)", 
                       (st.session_state['username'], selected_user, selected_user, st.session_state['username']))
        chat_data = pd.DataFrame(cursor.fetchall())

        # تحقق من أن البيانات ليست فارغة
        if chat_data.empty:
            st.info("💬 لا توجد رسائل بعد.")
        else:
            # تحقق من وجود الأعمدة المطلوبة
            required_columns = ['timestamp', 'from', 'to', 'message', 'read_by_receiver']
            if not required_columns.issubset(chat_data.columns):
                st.warning(f"⚠️ الأعمدة المطلوبة غير موجودة في قاعدة البيانات. الأعمدة الموجودة: {chat_data.columns}")
                return

            # حذف أي بيانات فارغة في الحقول المطلوبة
            chat_data = chat_data.dropna(subset=['timestamp', 'from', 'to', 'message', 'read_by_receiver'])

            # تحديث حالة القراءة
            unread_indexes = chat_data[
                (chat_data['from'] == selected_user) &
                (chat_data['to'] == st.session_state['username']) &
                (chat_data['read_by_receiver'].astype(str).str.strip() == "")
            ].index.tolist()

            for i in unread_indexes:
                cursor.execute("UPDATE chat SET read_by_receiver = %s WHERE id = %s", ("✓", chat_data.iloc[i]['id']))
                conn.commit()

            # عرض الرسائل
            messages = chat_data[
                ((chat_data['from'] == st.session_state['username']) & (chat_data['to'] == selected_user)) |
                ((chat_data['from'] == selected_user) & (chat_data['to'] == st.session_state['username']))
            ]
            messages = messages.sort_values(by='timestamp')

            if messages.empty:
                st.info("💬 لا توجد رسائل بعد.")
            else:
                for _, msg in messages.iterrows():
                    if msg['from'] == st.session_state['username']:
                        st.markdown(f"<p style='color:#8B0000;'>ب‍ أنت: {msg['message']}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='color:#000080;'>ب‍ {msg['from']}: {msg['message']}</p>", unsafe_allow_html=True)

        # حقل النص لإدخال الرسالة
        new_msg = st.text_area("✏️ اكتب رسالتك", height=100, key="chat_message")
        if st.button("📨 إرسال الرسالة"):
            if new_msg.strip():  # تأكد من أن الرسالة ليست فارغة
                timestamp = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d %H%M%S")
                cursor.execute("INSERT INTO chat (timestamp, from_user, to_user, message) VALUES (%s, %s, %s, %s)", 
                               (timestamp, st.session_state['username'], selected_user, new_msg))
                conn.commit()
                st.success("✅ تم إرسال الرسالة")

                # إعادة تحميل الصفحة بعد الإرسال
                st.rerun()

                # مسح النص في حقل النص
                del st.session_state['chat_message']
            else:
                st.warning("⚠️ لا يمكن إرسال رسالة فارغة.")
