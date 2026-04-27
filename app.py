import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from storage import load_data, save_data
from advisor import chat_with_advisor

# MUST BE FIRST
st.set_page_config(page_title="AI Financial Advisor", layout="wide")

st.title("💰 AI Financial Advisor Agent")

# ---------------- LOAD DATA ----------------
df = load_data()

# ---------------- FILE UPLOAD ----------------
st.subheader("📂 Upload Bank Statement")

uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])


# ---------------- CATEGORY LOGIC ----------------
def categorize_expense(description):
    description = str(description).lower()

    if "swiggy" in description or "zomato" in description:
        return "Food"
    elif "uber" in description or "ola" in description or "fuel" in description:
        return "Travel"
    elif "amazon" in description or "flipkart" in description:
        return "Shopping"
    elif "electricity" in description or "bill" in description:
        return "Bills"
    else:
        return "Other"


# ---------------- FILE PROCESSING ----------------
if uploaded_file is not None:
    try:
        # Detect file type
        if uploaded_file.name.endswith(".csv"):
            bank_df = pd.read_csv(uploaded_file)
        else:
            bank_df = pd.read_excel(uploaded_file)

        st.write("Preview of Uploaded Data:")
        st.write(bank_df.head())

        # -------- HANDLE HDFC FORMAT --------
        if "Narration" in bank_df.columns:
            bank_df.rename(columns={"Narration": "Description"}, inplace=True)

        if "Withdrawal Amt" in bank_df.columns:
            bank_df["Amount"] = bank_df["Withdrawal Amt"].fillna(0)

        elif "Amount" not in bank_df.columns:
            st.error("❌ Unable to detect amount column")
            st.stop()

        # Clean data
        bank_df["Amount"] = bank_df["Amount"].abs()
        bank_df = bank_df[bank_df["Amount"] > 0]

        # Ensure required columns exist
        if "Description" not in bank_df.columns:
            st.error("❌ Description column missing")
            st.stop()

        if "Date" not in bank_df.columns:
            st.error("❌ Date column missing")
            st.stop()

        # Categorize
        bank_df["Category"] = bank_df["Description"].apply(categorize_expense)

        new_data = bank_df[["Date", "Category", "Amount"]]

        df = pd.concat([df, new_data], ignore_index=True)
        save_data(df)

        st.success("Bank data imported successfully ✅")

    except Exception as e:
        st.error(f"Error processing file: {e}")


# ---------------- ADD EXPENSE ----------------
st.subheader("➕ Add Expense")

col1, col2 = st.columns(2)

with col1:
    category = st.selectbox("Category", ["Food", "Travel", "Shopping", "Bills", "Other"])
with col2:
    amount = st.number_input("Amount (₹)", min_value=1)

expense_date = st.date_input("Date", value=date.today())

if st.button("Add Expense"):
    new_entry = pd.DataFrame([[expense_date, category, amount]],
                             columns=["Date", "Category", "Amount"])
    df = pd.concat([df, new_entry], ignore_index=True)
    save_data(df)
    st.success("Expense Added ✅")


# ---------------- SHOW DATA ----------------
st.subheader("📊 Expense Data")
st.write(df)


# ---------------- ANALYSIS ----------------
if not df.empty:

    total = df["Amount"].sum()
    st.subheader(f"💸 Total Spending: ₹{total}")

    category_sum = df.groupby("Category")["Amount"].sum()

    st.subheader("📈 Category Spending")
    plt.figure()
    category_sum.plot(kind="bar")
    st.pyplot(plt)

    st.subheader("📅 Daily Trend")
    df["Date"] = pd.to_datetime(df["Date"])
    daily = df.groupby("Date")["Amount"].sum()

    plt.figure()
    daily.plot(marker='o')
    st.pyplot(plt)

    avg_daily = round(total / len(daily), 2)

else:
    total = 0
    avg_daily = 0
    category_sum = {}


# ---------------- CHAT ----------------
st.subheader("💬 AI Financial Chat Advisor")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Ask about your finances...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    summary = category_sum.to_dict() if not df.empty else {}

    response = chat_with_advisor(
        st.session_state.chat_history,
        summary,
        total,
        avg_daily
    )

    st.session_state.chat_history.append({"role": "assistant", "content": response})

    with st.chat_message("assistant"):
        st.write(response)
