import streamlit as st

# MUST BE FIRST
st.set_page_config(page_title="AI Financial Advisor", layout="wide")

import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from storage import load_data, save_data
from advisor import chat_with_advisor

# -------- SAFE PDF IMPORT --------
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False


# -------- PDF FUNCTION --------
def generate_pdf(total_expense, avg_daily, category_sum, savings):
    file_path = "financial_report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph("AI Financial Advisor Report", styles["Title"]))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"Total Expense: ₹{total_expense}", styles["Normal"]))
    content.append(Paragraph(f"Avg Daily Spend: ₹{avg_daily}", styles["Normal"]))
    content.append(Paragraph(f"Savings: ₹{savings}", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Category Breakdown:", styles["Heading2"]))
    for cat, amt in category_sum.items():
        content.append(Paragraph(f"{cat}: ₹{amt}", styles["Normal"]))

    doc.build(content)
    return file_path


# -------- CATEGORY --------
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
    else:
        return "Other"


# -------- AMOUNT CLEANER --------
def clean_amount(series):
    series = (
        series.astype(str)
        .str.replace(",", "")
        .str.replace("₹", "")
        .str.replace("CR", "")
        .str.replace("DR", "")
        .str.strip()
    )
    return pd.to_numeric(series, errors='coerce').fillna(0).abs()


# -------- UI --------
st.title("💰 AI Financial Advisor Agent")

df = load_data()

# -------- SETTINGS --------
st.subheader("⚙️ Personal Settings")

colA, colB = st.columns(2)

with colA:
    salary = st.number_input("Monthly Salary (₹)", min_value=0)

with colB:
    saving_goal = st.number_input("Saving Goal (₹)", min_value=0)

mode = st.selectbox("Advisor Mode", ["Normal", "Strict 😈"])


# -------- FILE UPLOAD --------
st.subheader("📂 Upload Bank Statement")

st.info("Upload CSV or Excel file. You can manually map columns if needed.")

uploaded_file = st.file_uploader(
    "Upload file",
    type=["csv", "xlsx", "xls"]
)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)

        st.subheader("📄 Raw Data Preview")
        st.dataframe(raw_df.head())

        # -------- COLUMN SELECTION UI --------
        st.subheader("🛠 Map Your Columns")

        columns = raw_df.columns.tolist()

        date_col = st.selectbox("Select Date Column", columns)
        desc_col = st.selectbox("Select Description Column", columns)
        amount_col = st.selectbox("Select Amount Column", columns)

        processed_df = raw_df.rename(columns={
            date_col: "Date",
            desc_col: "Description",
            amount_col: "Amount"
        })

        processed_df["Amount"] = clean_amount(processed_df["Amount"])

        st.subheader("✅ Processed Data Preview")
        st.dataframe(processed_df.head())

        if st.button("✅ Confirm Import"):

            processed_df["Category"] = processed_df["Description"].apply(categorize_expense)

            new_data = processed_df[["Date", "Category", "Amount"]]

            df = pd.concat([df, new_data], ignore_index=True)
            save_data(df)

            st.success("🎉 Data Imported Successfully")

    except Exception as e:
        st.error(f"Error processing file: {e}")


# -------- ADD EXPENSE --------
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


# -------- DISPLAY --------
st.subheader("📊 Expense Data")
st.write(df)


# -------- ANALYSIS --------
if not df.empty:

    df["Date"] = pd.to_datetime(df["Date"])

    total_expense = df["Amount"].sum()
    avg_daily = round(total_expense / len(df["Date"].unique()), 2)

    st.subheader(f"💸 Total Expense: ₹{total_expense}")
    st.write(f"📊 Avg Daily Spend: ₹{avg_daily}")

    category_sum = df.groupby("Category")["Amount"].sum()

    plt.figure()
    category_sum.plot(kind="bar")
    st.pyplot(plt)

    savings = salary - total_expense

    st.subheader("💼 Financial Summary")
    st.write(f"Savings: ₹{savings}")

    if saving_goal > 0:
        if savings >= saving_goal:
            st.success("🎯 Goal Achieved!")
        else:
            st.warning("⚠️ Not meeting saving goal")

    # PDF
    if PDF_AVAILABLE and st.button("📄 Generate Report"):
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


# -------- CHAT --------
st.subheader("💬 AI Financial Advisor")

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
        total_expense if not df.empty else 0,
        avg_daily if not df.empty else 0
    )

    st.session_state.chat_history.append({"role": "assistant", "content": response})

    with st.chat_message("assistant"):
        st.write(response)
