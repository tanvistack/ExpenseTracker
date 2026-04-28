import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from pymongo import MongoClient
import uuid
from dotenv import load_dotenv
import os

# ================= MongoDB Setup =================
load_dotenv()  # load .env file

mongo_uri = st.secrets["MONGO_URI"] if "MONGO_URI" in st.secrets else os.getenv("MONGO_URI") # get URI from .env

client = MongoClient(mongo_uri)
db = client["expensify_db"]
collection = db["expenses"]

# ================= Category =================
CATEGORY_MAP = {
    " Food": "Food",
    " Transport": "Transport",
    " Housing": "Housing",
    " Utilities": "Utilities",
    " Entertainment": "Entertainment",
    " Shopping": "Shopping",
    " Health": "Health",
    " Education": "Education",
    " Savings": "Savings",
    " Investments": "Investments",
    " Other": "Other"
}
CATEGORY_LIST = list(CATEGORY_MAP.keys())

st.set_page_config(page_title="Expensify", layout="wide")

# ================= Load Data =================
def load_expense_data():
    data = list(collection.find())
    
    if not data:
        return pd.DataFrame(columns=["_id","Date","Category","Description","Amount"])

    df = pd.DataFrame(data)

    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df["Category"] = df["Category"].astype(str).str.strip().str.title()
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    return df

# ================= Insert =================
def insert_expense(entry):
    collection.insert_one(entry)

# ================= Delete =================
def delete_expense(expense_id):
    collection.delete_one({"_id": expense_id})

expense_df = load_expense_data()

# ================= Sidebar =================
with st.sidebar:
    st.title("EXPENSIFY")
    st.divider()

    selected_category = st.selectbox(
        "Filter by Category",
        ["All Categories"] + CATEGORY_LIST
    )

# ================= Filter =================
filtered_df = expense_df.copy()

if selected_category != "All Categories":
    clean_category = CATEGORY_MAP[selected_category]
    filtered_df = filtered_df[filtered_df["Category"] == clean_category]

# ================= Dashboard =================
st.header("Financial Dashboard")

total_expenses = filtered_df["Amount"].sum() if not filtered_df.empty else 0.0
avg_expense = filtered_df["Amount"].mean() if not filtered_df.empty else 0.0
count_expense = len(filtered_df)

c1, c2, c3 = st.columns(3)

c1.metric("Total Outflow", f"₹ {total_expenses:,.0f}")
c2.metric("Average Spend", f"₹ {avg_expense:,.0f}")
c3.metric("Transactions", count_expense)

# ================= Tabs =================
tab1, tab2, tab3 = st.tabs(["Analytics", "Ledger", "Add Expense"])

# ================= Analytics =================
with tab1:
    if not filtered_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            category_summary = filtered_df.groupby("Category")["Amount"].sum().reset_index()

            fig = px.pie(category_summary, values="Amount", names="Category", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            time_summary = filtered_df.groupby("Date")["Amount"].sum().reset_index()

            fig = px.line(time_summary, x="Date", y="Amount", markers=True)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available")

# ================= Ledger =================
with tab2:
    st.subheader("Transaction History")

    if filtered_df.empty:
        st.info("No transactions yet.")
    else:
        df_display = filtered_df.sort_values("Date", ascending=False)

        for index, row in df_display.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 2, 1, 0.5])

                c1.write(row["Date"])
                c2.write(f"{row['Category']} • {row['Description']}")
                c3.write(f"₹ {row['Amount']:.2f}")

                if c4.button("Delete", key=str(row["_id"])):
                    delete_expense(row["_id"])
                    st.success("Deleted successfully")
                    st.rerun()

# ================= Add Expense =================
with tab3:
    st.subheader("Log Transaction")

    with st.form("entry_form", clear_on_submit=True):

        f1, f2 = st.columns(2)

        date_value = f1.date_input("Transaction Date", datetime.today())
        category_value = f2.selectbox("Select Category", CATEGORY_LIST)

        description = st.text_input("What did you spend on?")
        amount_value = st.number_input("Amount (₹)", min_value=0.0, step=50.0)

        submitted = st.form_submit_button("Submit Transaction")

        if submitted:
            if description and amount_value > 0:
                new_entry = {
                    "_id": str(uuid.uuid4()),  # unique id
                    "Date": str(date_value),
                    "Category": CATEGORY_MAP[category_value],
                    "Description": description,
                    "Amount": amount_value
                }

                insert_expense(new_entry)
                st.success("Transaction Added")
                st.rerun()
            else:
                st.error("Enter valid details")
