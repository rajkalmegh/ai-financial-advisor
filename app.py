import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from storage import load_data, save_data
from advisor import chat_with_advisor

# PDF imports
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# MUST BE FIRST
st.set_page_config(page_title="AI Financial Advisor", layout="wide")

st.title("💰 AI Financial Advisor Agent")

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


# ---------------- LOAD DATA ----------------
df = load_data()

# ---------------- SETTINGS ----------------
st.subheader("⚙️ Personal Settings")

colA, colB = st.columns(2)

with colA:
    salary = st.number_input("Monthly Salary (₹)", min_value=0)

with colB:
    saving_goal = st.number_input("Saving Goal (₹)", min_value=0)

mode = st.selectbox("Advisor Mode", ["Normal", "Strict 😈"])



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

    # Clean column names
    bank_df.columns = [col.strip() for col in bank_df.columns]

    desc_col, withdraw_col, deposit_col = None, None, None

    for col in bank_df.columns:
        if "narration" in col.lower() or "description" in col.lower():
            desc_col = col
        if "withdraw" in col.lower() or "debit" in col.lower():
            withdraw_col = col
        if "deposit" in col.lower() or "credit" in col.lower():
            deposit_col = col

    if not desc_col:
        st.error("❌ Description column not found")
        st.stop()

    bank_df.rename(columns={desc_col: "Description"}, inplace=True)

    # Create Amount column
    bank_df["Amount"] = bank_df[withdraw_col].fillna(0) if withdraw_col else 0
    bank_df["Amount"] = bank_df["Amount"].abs()

    # Remove zero rows
    bank_df = bank_df[bank_df["Amount"] > 0]

    # Ensure Date column
    if "Date" not in bank_df.columns:
        st.error("❌ Date column missing")
        st.stop()

    return bank_df




# ---------------- FILE UPLOAD ----------------
st.subheader("📂 Upload Bank Statement")

uploaded_file = st.file_uploader(
    "Upload CSV, Excel or PDF",
    type=["csv", "xlsx", "xls", "pdf"]
)

# ---------------- PROCESS FILE ----------------
if uploaded_file is not None:
    try:

        file_name = uploaded_file.name.lower()

        # ---------- HANDLE PDF ----------
        if file_name.endswith(".pdf"):
            st.warning("⚠️ PDF parsing not supported yet.")
            st.info("👉 Please download bank statement as Excel (.xls) from your bank.")
            st.stop()

        # ---------- HANDLE CSV ----------
        elif file_name.endswith(".csv"):
            bank_df = pd.read_csv(uploaded_file)

        # ---------- HANDLE EXCEL ----------
        elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            bank_df = pd.read_excel(uploaded_file)

        else:
            st.error("Unsupported file format")
            st.stop()

        st.write("Preview:", bank_df.head())

        # Process bank data
        bank_df = process_bank_data(bank_df)

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

    total_income = salary
    savings = total_income - total_expense

    st.subheader("💼 Financial Summary")
    st.write(f"Income: ₹{total_income}")
    st.write(f"Savings: ₹{savings}")

    if saving_goal > 0:
        if savings >= saving_goal:
            st.success("🎯 Goal Achieved!")
        else:
            st.warning("⚠️ Not meeting saving goal")

    # ---------------- PDF DOWNLOAD ----------------
    if st.button("📄 Generate Financial Report"):

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
