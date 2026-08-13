import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Construction Project Dashboard",
    page_icon="🏗️",
    layout="wide"
)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

@st.cache_data
def load_data():
    df = pd.read_csv("data/construction_project_invoices.csv")

    # Dates
    date_columns = [
        "Invoice_Month",
        "Invoice_Date",
        "Due_Date",
        "Payment_Date"
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Numeric fields
    numeric_columns = [
        "Invoice_Amount",
        "Outstanding_Amount",
        "Paid_Amount",
        "Days_to_Pay"
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Re-create Year and Quarter from Invoice_Date
    # so filtering is consistent.
    df["Year"] = df["Invoice_Date"].dt.year
    df["Quarter"] = "Q" + df["Invoice_Date"].dt.quarter.astype(str)

    # Simple analytical payment classification.
    # Any invoice with money still outstanding is treated
    # as Outstanding, including partially paid invoices.
    df["Payment_State"] = df["Outstanding_Amount"].apply(
        lambda x: "Outstanding" if x > 0 else "Paid"
    )

    return df


df = load_data()


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.title("🏗️ Construction Project Invoice Dashboard")

st.caption(
    "Interactive demonstration dashboard using simulated construction-project data."
)


# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------

st.sidebar.header("Filters")


# Vendor
all_vendors = sorted(df["Vendor"].dropna().unique())

selected_vendors = st.sidebar.multiselect(
    "Vendor",
    options=all_vendors,
    default=all_vendors
)


# Year
all_years = sorted(df["Year"].dropna().astype(int).unique())

selected_years = st.sidebar.multiselect(
    "Year",
    options=all_years,
    default=all_years
)


# Quarter
quarter_order = ["Q1", "Q2", "Q3", "Q4"]

available_quarters = [
    q for q in quarter_order
    if q in df["Quarter"].dropna().unique()
]

selected_quarters = st.sidebar.multiselect(
    "Quarter",
    options=available_quarters,
    default=available_quarters
)


# Payment status
payment_filter = st.sidebar.selectbox(
    "Paid vs. Outstanding",
    options=["All", "Paid", "Outstanding"]
)


# Date range
min_date = df["Invoice_Date"].min().date()
max_date = df["Invoice_Date"].max().date()

selected_date_range = st.sidebar.date_input(
    "Invoice date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)


# ---------------------------------------------------------
# APPLY FILTERS
# ---------------------------------------------------------

filtered_df = df.copy()

filtered_df = filtered_df[
    filtered_df["Vendor"].isin(selected_vendors)
]

filtered_df = filtered_df[
    filtered_df["Year"].isin(selected_years)
]

filtered_df = filtered_df[
    filtered_df["Quarter"].isin(selected_quarters)
]


if payment_filter != "All":
    filtered_df = filtered_df[
        filtered_df["Payment_State"] == payment_filter
    ]


if len(selected_date_range) == 2:

    start_date = pd.Timestamp(selected_date_range[0])
    end_date = pd.Timestamp(selected_date_range[1])

    filtered_df = filtered_df[
        (filtered_df["Invoice_Date"] >= start_date)
        &
        (filtered_df["Invoice_Date"] <= end_date)
    ]


# ---------------------------------------------------------
# HANDLE EMPTY RESULT
# ---------------------------------------------------------

if filtered_df.empty:
    st.warning(
        "No invoices match the selected filters. "
        "Try expanding the filters in the sidebar."
    )
    st.stop()


# ---------------------------------------------------------
# KPI CARDS
# ---------------------------------------------------------

total_invoiced = filtered_df["Invoice_Amount"].sum()
total_paid = filtered_df["Paid_Amount"].sum()
total_outstanding = filtered_df["Outstanding_Amount"].sum()
invoice_count = len(filtered_df)


kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="Total Invoiced",
        value=f"${total_invoiced:,.0f}"
    )

with kpi2:
    st.metric(
        label="Total Paid",
        value=f"${total_paid:,.0f}"
    )

with kpi3:
    st.metric(
        label="Outstanding Balance",
        value=f"${total_outstanding:,.0f}"
    )

with kpi4:
    st.metric(
        label="Number of Invoices",
        value=f"{invoice_count:,}"
    )


st.divider()


# ---------------------------------------------------------
# CHART 1
# MONTHLY INVOICE VOLUME
# ---------------------------------------------------------

monthly_volume = (
    filtered_df
    .set_index("Invoice_Date")
    .resample("MS")
    .size()
    .reset_index(name="Invoice_Count")
)


fig_volume = px.area(
    monthly_volume,
    x="Invoice_Date",
    y="Invoice_Count",
    markers=True,
    title="Monthly Invoice Volume",
    labels={
        "Invoice_Date": "Month",
        "Invoice_Count": "Number of Invoices"
    }
)

fig_volume.update_layout(
    hovermode="x unified"
)

st.plotly_chart(
    fig_volume,
    use_container_width=True
)


# ---------------------------------------------------------
# CHART 2
# INVOICED VS PAID BY MONTH
# ---------------------------------------------------------

monthly_invoiced = (
    filtered_df
    .set_index("Invoice_Date")
    ["Invoice_Amount"]
    .resample("MS")
    .sum()
    .reset_index()
)

monthly_invoiced.columns = [
    "Month",
    "Invoiced"
]


# Payments are grouped by actual payment date.
payments_df = filtered_df.dropna(
    subset=["Payment_Date"]
)

monthly_paid = (
    payments_df
    .set_index("Payment_Date")
    ["Paid_Amount"]
    .resample("MS")
    .sum()
    .reset_index()
)

monthly_paid.columns = [
    "Month",
    "Paid"
]


monthly_comparison = pd.merge(
    monthly_invoiced,
    monthly_paid,
    on="Month",
    how="outer"
).fillna(0)

monthly_comparison = monthly_comparison.sort_values(
    "Month"
)


monthly_long = monthly_comparison.melt(
    id_vars="Month",
    value_vars=["Invoiced", "Paid"],
    var_name="Type",
    value_name="Amount"
)


fig_monthly = px.line(
    monthly_long,
    x="Month",
    y="Amount",
    color="Type",
    markers=True,
    title="Invoiced vs. Paid by Month",
    labels={
        "Month": "Month",
        "Amount": "Amount",
        "Type": ""
    }
)

fig_monthly.update_layout(
    hovermode="x unified",
    yaxis_tickprefix="$",
    yaxis_tickformat=","
)

st.plotly_chart(
    fig_monthly,
    use_container_width=True
)


# ---------------------------------------------------------
# CHARTS 3 + 4
# TWO-COLUMN LAYOUT
# ---------------------------------------------------------

left_chart, right_chart = st.columns(2)


# Total invoiced by subcontractor
vendor_invoiced = (
    filtered_df
    .groupby("Vendor", as_index=False)["Invoice_Amount"]
    .sum()
    .sort_values(
        "Invoice_Amount",
        ascending=False
    )
)


fig_vendor_invoiced = px.bar(
    vendor_invoiced,
    x="Vendor",
    y="Invoice_Amount",
    title="Total Invoiced by Subcontractor",
    labels={
        "Vendor": "Subcontractor",
        "Invoice_Amount": "Total Invoiced"
    }
)

fig_vendor_invoiced.update_layout(
    yaxis_tickprefix="$",
    yaxis_tickformat=","
)


with left_chart:
    st.plotly_chart(
        fig_vendor_invoiced,
        use_container_width=True
    )


# Outstanding by subcontractor
vendor_outstanding = (
    filtered_df
    .groupby("Vendor", as_index=False)["Outstanding_Amount"]
    .sum()
    .sort_values(
        "Outstanding_Amount",
        ascending=False
    )
)


fig_vendor_outstanding = px.bar(
    vendor_outstanding,
    x="Vendor",
    y="Outstanding_Amount",
    title="Outstanding Balance by Subcontractor",
    labels={
        "Vendor": "Subcontractor",
        "Outstanding_Amount": "Outstanding Balance"
    }
)

fig_vendor_outstanding.update_layout(
    yaxis_tickprefix="$",
    yaxis_tickformat=","
)


with right_chart:
    st.plotly_chart(
        fig_vendor_outstanding,
        use_container_width=True
    )


# ---------------------------------------------------------
# CHARTS 5 + 6
# TWO-COLUMN LAYOUT
# ---------------------------------------------------------

left_chart2, right_chart2 = st.columns(2)


# Paid vs outstanding
payment_summary = pd.DataFrame({
    "Category": [
        "Paid",
        "Outstanding"
    ],
    "Amount": [
        total_paid,
        total_outstanding
    ]
})


fig_payment = px.pie(
    payment_summary,
    names="Category",
    values="Amount",
    hole=0.55,
    title="Paid vs. Outstanding"
)

fig_payment.update_traces(
    textposition="inside",
    textinfo="percent+label",
    hovertemplate=(
        "%{label}<br>"
        "$%{value:,.0f}<br>"
        "%{percent}"
        "<extra></extra>"
    )
)


with left_chart2:
    st.plotly_chart(
        fig_payment,
        use_container_width=True
    )


# Average days to pay
paid_invoices = filtered_df[
    filtered_df["Days_to_Pay"].notna()
]

avg_days = (
    paid_invoices
    .groupby("Vendor", as_index=False)["Days_to_Pay"]
    .mean()
    .sort_values(
        "Days_to_Pay",
        ascending=False
    )
)


fig_days = px.bar(
    avg_days,
    x="Vendor",
    y="Days_to_Pay",
    title="Average Days to Pay by Subcontractor",
    labels={
        "Vendor": "Subcontractor",
        "Days_to_Pay": "Average Days to Pay"
    }
)

fig_days.update_traces(
    hovertemplate=(
        "%{x}<br>"
        "Average days: %{y:.1f}"
        "<extra></extra>"
    )
)


with right_chart2:
    st.plotly_chart(
        fig_days,
        use_container_width=True
    )


# ---------------------------------------------------------
# INVOICE DETAIL TABLE
# ---------------------------------------------------------

st.divider()

st.subheader("Invoice Detail")


search_text = st.text_input(
    "Search invoices",
    placeholder="Search invoice ID, vendor, status..."
)


detail_df = filtered_df.copy()


if search_text:

    search_text_lower = search_text.lower()

    searchable_columns = [
        "Invoice_ID",
        "Vendor",
        "Status"
    ]

    search_mask = pd.Series(
        False,
        index=detail_df.index
    )

    for column in searchable_columns:

        if column in detail_df.columns:

            search_mask = (
                search_mask
                |
                detail_df[column]
                .astype(str)
                .str.lower()
                .str.contains(
                    search_text_lower,
                    na=False
                )
            )

    detail_df = detail_df[
        search_mask
    ]


display_columns = [
    "Invoice_ID",
    "Invoice_Date",
    "Due_Date",
    "Vendor",
    "Invoice_Amount",
    "Status",
    "Payment_Date",
    "Days_to_Pay",
    "Paid_Amount",
    "Outstanding_Amount"
]


detail_df = detail_df[
    display_columns
].sort_values(
    "Invoice_Date",
    ascending=False
)


st.dataframe(
    detail_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Invoice_ID": "Invoice",
        "Invoice_Date": st.column_config.DateColumn(
            "Invoice Date",
            format="MM/DD/YYYY"
        ),
        "Due_Date": st.column_config.DateColumn(
            "Due Date",
            format="MM/DD/YYYY"
        ),
        "Vendor": "Subcontractor",
        "Invoice_Amount": st.column_config.NumberColumn(
            "Invoice Amount",
            format="$%.2f"
        ),
        "Status": "Status",
        "Payment_Date": st.column_config.DateColumn(
            "Payment Date",
            format="MM/DD/YYYY"
        ),
        "Days_to_Pay": st.column_config.NumberColumn(
            "Days to Pay",
            format="%.0f"
        ),
        "Paid_Amount": st.column_config.NumberColumn(
            "Paid Amount",
            format="$%.2f"
        ),
        "Outstanding_Amount": st.column_config.NumberColumn(
            "Outstanding",
            format="$%.2f"
        )
    }
)


st.caption(
    f"Showing {len(detail_df):,} of "
    f"{len(filtered_df):,} invoices matching the current filters."
)
