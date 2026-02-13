import streamlit as st
import pandas as pd
import math
import io

# Estimated annual returns for different portfolio types
PORTFOLIO_RATES = {
    "Conservative (60/40)": 0.06,
    "Diversified Global": 0.08,
    "International Diversified": 0.07,
    "Real Estate": 0.09,
    "Aggressive Growth": 0.10,
}


def calculate_years_to_target(current_value, target_value, annual_rate, monthly_contribution=0):
    """
    Calculate years to reach a target portfolio value using compound growth
    with optional monthly contributions.

    Uses the future value formula:
        FV = PV * (1+r)^n + PMT * ((1+r)^n - 1) / r
    Solved numerically for n.
    """
    if current_value >= target_value:
        return 0.0

    if annual_rate <= 0:
        if monthly_contribution <= 0:
            return float("inf")
        # No growth, just contributions
        remaining = target_value - current_value
        months = remaining / monthly_contribution
        return round(months / 12, 2)

    r = annual_rate / 12  # monthly rate
    pmt = monthly_contribution

    if pmt == 0:
        # Simple compound growth: FV = PV * (1+r)^n  =>  n = ln(FV/PV) / ln(1+r)
        if current_value <= 0:
            return float("inf")
        months = math.log(target_value / current_value) / math.log(1 + r)
        return round(months / 12, 2)

    # With contributions: FV = PV*(1+r)^n + PMT*((1+r)^n - 1)/r
    # Let x = (1+r)^n
    # target = current_value * x + pmt * (x - 1) / r
    # target = x * (current_value + pmt/r) - pmt/r
    # x = (target + pmt/r) / (current_value + pmt/r)
    numerator = target_value + pmt / r
    denominator = current_value + pmt / r

    if denominator <= 0:
        return float("inf")

    ratio = numerator / denominator
    if ratio <= 0:
        return float("inf")

    months = math.log(ratio) / math.log(1 + r)
    return round(months / 12, 2)


def build_projection_table(current_value, annual_rate, monthly_contribution, years):
    """Build a year-by-year projection table."""
    rows = []
    balance = current_value
    monthly_rate = annual_rate / 12

    total_years = int(math.ceil(years)) if years != float("inf") else 30

    for year in range(1, total_years + 1):
        contributions_this_year = 0
        growth_this_year = 0
        for _ in range(12):
            interest = balance * monthly_rate
            growth_this_year += interest
            balance += interest + monthly_contribution
            contributions_this_year += monthly_contribution
        rows.append({
            "Year": year,
            "Starting Balance": round(balance - growth_this_year - contributions_this_year, 2),
            "Contributions": round(contributions_this_year, 2),
            "Growth": round(growth_this_year, 2),
            "Ending Balance": round(balance, 2),
        })
    return pd.DataFrame(rows)


def main():
    st.set_page_config(page_title="Portfolio Growth Calculator", layout="wide")
    st.title("Portfolio Growth Calculator")
    st.write("Calculate how long it takes to reach your financial goal based on your portfolio type.")

    # ---- Sidebar: Import from Excel ----
    st.sidebar.header("Import from Excel")
    uploaded_file = st.sidebar.file_uploader("Upload a previous projection (.xlsx)", type=["xlsx"])

    imported_defaults = {}
    if uploaded_file is not None:
        try:
            df_import = pd.read_excel(uploaded_file)
            st.sidebar.success("File loaded successfully.")
            st.sidebar.dataframe(df_import)
            # Try to extract defaults from the first row
            if not df_import.empty:
                row = df_import.iloc[0]
                if "Current Value" in row:
                    imported_defaults["current"] = float(row["Current Value"])
                if "Target Value" in row:
                    imported_defaults["target"] = float(row["Target Value"])
                if "Monthly Contribution" in row:
                    imported_defaults["monthly"] = float(row["Monthly Contribution"])
                if "Portfolio Type" in row:
                    imported_defaults["portfolio_type"] = str(row["Portfolio Type"])
        except Exception as e:
            st.sidebar.error(f"Error reading file: {e}")

    # ---- Main inputs ----
    col1, col2 = st.columns(2)

    with col1:
        current_value = st.number_input(
            "Current Portfolio Value ($)",
            min_value=0.0,
            value=imported_defaults.get("current", 10000.0),
            step=1000.0,
            format="%.2f",
        )
        target_value = st.number_input(
            "Target Portfolio Value ($)",
            min_value=0.0,
            value=imported_defaults.get("target", 1000000.0),
            step=10000.0,
            format="%.2f",
        )

    with col2:
        monthly_contribution = st.number_input(
            "Monthly Contribution ($)",
            min_value=0.0,
            value=imported_defaults.get("monthly", 500.0),
            step=100.0,
            format="%.2f",
        )
        portfolio_types = list(PORTFOLIO_RATES.keys())
        default_index = 0
        if "portfolio_type" in imported_defaults:
            try:
                default_index = portfolio_types.index(imported_defaults["portfolio_type"])
            except ValueError:
                default_index = 0

        selected_portfolio = st.selectbox(
            "Portfolio Type",
            portfolio_types,
            index=default_index,
            format_func=lambda x: f"{x} — Est. {PORTFOLIO_RATES[x]*100:.0f}% annual return",
        )

    annual_rate = PORTFOLIO_RATES[selected_portfolio]

    # ---- Calculate ----
    if st.button("Calculate", type="primary"):
        if current_value >= target_value:
            st.success("You have already reached your target!")
            return

        years = calculate_years_to_target(current_value, target_value, annual_rate, monthly_contribution)

        if years == float("inf"):
            st.error("Target is unreachable with the current inputs. Increase contributions or choose a higher-return portfolio.")
            return

        # Results summary
        st.divider()
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("Years to Goal", f"{years:.1f}")
        res_col2.metric("Strategy", selected_portfolio)
        res_col3.metric("Est. Annual Return", f"{annual_rate*100:.0f}%")

        # Projection table
        st.subheader("Year-by-Year Projection")
        df_projection = build_projection_table(current_value, annual_rate, monthly_contribution, years)
        st.dataframe(
            df_projection,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Year": st.column_config.NumberColumn("Year", format="%d"),
                "Starting Balance": st.column_config.NumberColumn("Starting Balance", format="$%,.2f"),
                "Contributions": st.column_config.NumberColumn("Contributions", format="$%,.2f"),
                "Growth": st.column_config.NumberColumn("Growth", format="$%,.2f"),
                "Ending Balance": st.column_config.NumberColumn("Ending Balance", format="$%,.2f"),
            },
        )

        # Chart
        st.subheader("Growth Over Time")
        st.line_chart(df_projection.set_index("Year")["Ending Balance"])

        # ---- Export to Excel ----
        st.subheader("Export Results")

        summary_df = pd.DataFrame([{
            "Portfolio Type": selected_portfolio,
            "Current Value": current_value,
            "Target Value": target_value,
            "Monthly Contribution": monthly_contribution,
            "Estimated Annual Return": annual_rate,
            "Years to Goal": years,
        }])

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            df_projection.to_excel(writer, sheet_name="Projection", index=False)

        st.download_button(
            label="Download as Excel",
            data=buffer.getvalue(),
            file_name="portfolio_projection.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.spreadsheet",
        )


if __name__ == "__main__":
    main()
