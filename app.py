import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from storage import load_data, save_data
from advisor import chat_with_advisor

st.subheader("📂 Upload Bank Statement (CSV)")

uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

st.set_page_config(page_title="AI Financial Advisor", layout="centered")

st.title("💰 AI Financial Advisor Agent")

# Load data
df = load_data()

if uploaded_file is not None:
    bank_df = pd.read_csv(uploaded_file)

    st.write("Preview of Uploaded Data:")
    st.dataframe(bank_df)

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



def categorize_expense(description):
    description = str(description).lower()

    if "swiggy" in description or "zomato" in description or "food" in description:
        return "Food"
    elif "uber" in description or "ola" in description or "fuel" in description:
        return "Travel"
    elif "amazon" in description or "flipkart" in description:
        return "Shopping"
    elif "electricity" in description or "bill" in description:
        return "Bills"
    else:
        return "Other"
    

if uploaded_file is not None:

    bank_df["Category"] = bank_df["Description"].apply(categorize_expense)

    new_data = bank_df[["Date", "Category", "Amount"]]

    df = pd.concat([df, new_data], ignore_index=True)
    save_data(df)

    st.success("Bank data imported successfully ✅")

# ---------------- SHOW DATA ----------------
st.subheader("📊 Expense Data")
st.dataframe(df)

# ---------------- ANALYSIS ----------------
if not df.empty:

    total = df["Amount"].sum()
    st.subheader(f"💸 Total Spending: ₹{total}")

    # Category Graph
    category_sum = df.groupby("Category")["Amount"].sum()

    st.subheader("📈 Category Spending")
    plt.figure()
    category_sum.plot(kind="bar")
    st.pyplot(plt)

    # Daily Trend
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

# Show chat
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input
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