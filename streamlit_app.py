import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Construction Project Dashboard",
    layout="wide"
)

st.title("Construction Project Invoice Dashboard")
st.caption("Demo dashboard using simulated construction-project data.")

# Load data from the CSV stored in this GitHub repository
df = pd.read_csv("data/construction_project_invoices.csv")

# Prepare fields
df["Invoice_Date"] = pd.to_datetime(df["Invoice_Date"])
df["Invoice_Amount"] = pd.to_numeric(df["Invoice_Amount"], errors="coerce")

# Optional interactive vendor filter
vendors = sorted(df["Vendor"].dropna().unique())

selected_vendors = st.multiselect(
    "Vendor",
    options=vendors,
    default=vendors
)

filtered_df = df[df["Vendor"].isin(selected_vendors)]

# Aggregate invoices by month and vendor
monthly = (
    filtered_df
    .groupby(
        [
            pd.Grouper(key="Invoice_Date", freq="MS"),
            "Vendor"
        ],
        as_index=False
    )["Invoice_Amount"]
    .sum()
)

# Create one BI-style visualization
fig = px.line(
    monthly,
    x="Invoice_Date",
    y="Invoice_Amount",
    color="Vendor",
    markers=True,
    title="Monthly Invoice Amount by Vendor",
    labels={
        "Invoice_Date": "Month",
        "Invoice_Amount": "Invoice Amount",
        "Vendor": "Vendor"
    }
)

fig.update_layout(
    hovermode="x unified",
    yaxis_tickprefix="$",
    yaxis_tickformat=",",
    legend_title_text="Vendor"
)

st.plotly_chart(fig, use_container_width=True)
