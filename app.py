import streamlit as st

# MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="AI Financial Advisor", layout="wide")

import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from storage import load_data, save_data
from advisor import chat_with_advisor

# SAFE PDF IMPORT (prevents crash on Render)
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False


# ---------------- PDF FUNCTION ----------------
def generate_pdf(total_expense, avg_daily, category_sum, savings):
    file_path = "financial_report.pdf"

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph("AI Financial Advisor Report", styles["Title"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Total Expense: ₹{total_expense}", styles["Normal"]))
    content.append(Paragraph(f"Average Daily Spend: ₹{avg_daily}", styles["Normal"]))
    content.append(Paragraph(f"Savings: ₹{savings}", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Category Breakdown:", styles["Heading2"]))

    for category, amount in category_sum.items():
        content.append(Paragraph(f"{category}: ₹{amount}", styles["Normal"]))

    doc.build(content)

    return file_path


# ---------------- CATEGORY FUNCTION ----------------
def categorize_expense(desc):
    desc = str(desc).lower()

    if "swiggy" in desc or "zomato" in desc:
        return "Food"
    elif "uber" in desc or "ola" in desc or "fuel" in desc:
        return "Travel"
    elif "amazon" in desc or "flipkart" in desc:
        return "Shopping"
    elif "bill" in desc or "electricity" in desc:
        return "Bills"
    elif "salary" in desc:
        return "Income"
    else:
        return "Other"


# ---------------- BANK PROCESS FUNCTION ----------------
def process_bank_data(bank_df):

    # Remove empty rows
    bank_df = bank_df.dropna(how="all").reset_index(drop=True)

    # Convert everything to string
    bank_df = bank_df.fillna("").astype(str)

    # -------- STEP 1: Detect Header Row --------
    header_found = False

    for i in range(min(10, len(bank_df))):
        row = bank_df.iloc[i].apply(lambda x: str(x).lower())

        if any("date" in cell for cell in row):
            bank_df.columns = bank_df.iloc[i]
            bank_df = bank_df[i+1:]
            header_found = True
            break

    # -------- STEP 2: If header not found --------
    if not header_found:
        st.warning("⚠️ Header not detected. Using generic parsing")
        bank_df.columns = [f"col_{i}" for i in range(len(bank_df.columns))]

    # Clean column names
    bank_df.columns = [str(col).strip() for col in bank_df.columns]

    # -------- STEP 3: Smart Column Guess --------
    date_col = None
    desc_col = None
    debit_col = None
    credit_col = None
    amount_col = None

    for col in bank_df.columns:
        col_lower = col.lower()

        if "date" in col_lower:
            date_col = col
        elif "narration" in col_lower or "description" in col_lower or "details" in col_lower:
            desc_col = col
        elif "withdraw" in col_lower or "debit" in col_lower:
            debit_col = col
        elif "deposit" in col_lower or "credit" in col_lower:
            credit_col = col
        elif "amount" in col_lower:
            amount_col = col

    # -------- STEP 4: Fallback --------
    cols = bank_df.columns.tolist()

    if not date_col:
        date_col = cols[0]

    if not desc_col:
        desc_col = cols[1] if len(cols) > 1 else cols[0]

    if debit_col:
        amount_series = bank_df[debit_col]
    elif amount_col:
        amount_series = bank_df[amount_col]
    else:
        amount_series = bank_df[cols[-1]]

    # -------- STEP 5: Rename --------
    bank_df.rename(columns={
        date_col: "Date",
        desc_col: "Description"
    }, inplace=True)

    bank_df["Amount"] = pd.to_numeric(amount_series, errors='coerce').fillna(0).abs()

    # -------- STEP 6: Filter --------
    bank_df = bank_df[bank_df["Amount"] > 0]

    # -------- DEBUG --------
    st.info(f"Detected → Date: {date_col}, Desc: {desc_col}")

    return bank_df


# ---------------- APP UI ----------------
st.title("💰 AI Financial Advisor Agent")

df = load_data()

# ---------------- SETTINGS ----------------
st.subheader("⚙️ Personal Settings")

colA, colB = st.columns(2)

with colA:
    salary = st.number_input("Monthly Salary (₹)", min_value=0)

with colB:
    saving_goal = st.number_input("Saving Goal (₹)", min_value=0)

mode = st.selectbox("Advisor Mode", ["Normal", "Strict 😈"])


# ---------------- FILE UPLOAD ----------------
st.subheader("📂 Upload Bank Statement")

uploaded_file = st.file_uploader(
    "Upload CSV or Excel file",
    type=["csv", "xlsx", "xls"]
)

# ---------------- FILE PROCESS ----------------
if uploaded_file is not None:
    try:
        file_name = uploaded_file.name.lower()

        if file_name.endswith(".csv"):
            bank_df = pd.read_csv(uploaded_file)
        else:
            bank_df = pd.read_excel(uploaded_file)

        st.write("Preview:", bank_df.head())

        bank_df = process_bank_data(bank_df)

        bank_df["Category"] = bank_df["Description"].apply(categorize_expense)

        new_data = bank_df[["Date", "Category", "Amount"]]

        df = pd.concat([df, new_data], ignore_index=True)
        save_data(df)

        st.success("Bank data imported successfully ✅")

    except Exception as e:
        st.error(f"Error processing file: {e}")

st.write("Processed Data:", bank_df.head())


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


# ---------------- DISPLAY ----------------
st.subheader("📊 Expense Data")
st.write(df)


# ---------------- ANALYSIS ----------------
if not df.empty:

    df["Date"] = pd.to_datetime(df["Date"])

    total_expense = df["Amount"].sum()
    avg_daily = round(total_expense / len(df["Date"].unique()), 2)

    st.subheader(f"💸 Total Expense: ₹{total_expense}")
    st.write(f"📊 Avg Daily Spend: ₹{avg_daily}")

    category_sum = df.groupby("Category")["Amount"].sum()

    st.subheader("📈 Category Spending")
    plt.figure()
    category_sum.plot(kind="bar")
    st.pyplot(plt)

    st.subheader("📅 Daily Trend")
    daily = df.groupby("Date")["Amount"].sum()

    plt.figure()
    daily.plot(marker='o')
    st.pyplot(plt)

    st.subheader("📆 Monthly Summary")
    df["Month"] = df["Date"].dt.to_period("M")
    monthly = df.groupby("Month")["Amount"].sum()

    plt.figure()
    monthly.plot(marker='o')
    st.pyplot(plt)

    savings = salary - total_expense

    st.subheader("💼 Financial Summary")
    st.write(f"Savings: ₹{savings}")

    if saving_goal > 0:
        if savings >= saving_goal:
            st.success("🎯 Goal Achieved!")
        else:
            st.warning("⚠️ Not meeting saving goal")

    # ---------------- PDF ----------------
    if PDF_AVAILABLE and st.button("📄 Generate Financial Report"):

        pdf_file = generate_pdf(
            total_expense,
            avg_daily,
            category_sum.to_dict(),
            savings
        )

        with open(pdf_file, "rb") as f:
            st.download_button(
                label="⬇️ Download PDF",
                data=f,
                file_name="financial_report.pdf",
                mime="application/pdf"
            )

    elif not PDF_AVAILABLE:
        st.warning("PDF feature not available in this environment")

else:
    category_sum = {}
    total_expense = 0
    avg_daily = 0


# ---------------- CHAT ----------------
st.subheader("💬 AI Financial Chat Advisor")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Ask about your finances...")

if user_input:

    if mode == "Strict 😈":
        user_input = "Be strict. " + user_input

    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    summary = category_sum.to_dict() if not df.empty else {}

    response = chat_with_advisor(
        st.session_state.chat_history,
        summary,
        total_expense,
        avg_daily
    )

    st.session_state.chat_history.append({"role": "assistant", "content": response})

    with st.chat_message("assistant"):
        st.write(response)
