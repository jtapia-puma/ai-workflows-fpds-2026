"""Streamlit interface for the Data Cleaning Agent."""

import streamlit as st
import pandas as pd
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from data_cleaning_agent import LightweightDataCleaningAgent
# NEW: Import helper that builds a tabular data summary for the UI
from data_cleaning_agent.utils import get_dataframe_summary_table

load_dotenv()

ROW_ID_COL = "__row_id__"

# NEW: Styles for HTML table headers (st.dataframe ignores header font CSS)
st.markdown(
    """
    <style>
    table.display-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    table.display-table th {
        font-weight: 700 !important;
        color: #000000 !important;
        text-align: left;
        padding: 0.5rem;
        border-bottom: 1px solid #ddd;
        background-color: #f7f7f7;
        white-space: nowrap;
    }
    table.display-table td {
        padding: 0.45rem 0.5rem;
        border-bottom: 1px solid #eee;
        color: inherit;
    }
    .display-table-wrap {
        width: 100%;
        overflow-x: auto;
        margin-bottom: 0.5rem;
    }
    .imputed-legend {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #333;
    }
    .imputed-legend-swatch {
        width: 1rem;
        height: 1rem;
        background-color: #e0e0e0;
        border: 1px solid #bbb;
        display: inline-block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _format_two_decimals(df: pd.DataFrame) -> pd.DataFrame:
    """NEW: Cap float values at two decimal places."""
    view = df.copy()
    for col in view.select_dtypes(include="number").columns:
        view[col] = view[col].apply(
            lambda x: round(float(x), 2) if pd.notna(x) else x
        )
    return view


def display_table(
    df: pd.DataFrame,
    *,
    show_all_columns: bool = False,
    highlight_mask: Optional[pd.DataFrame] = None,
    show_imputed_legend: bool = False,
    max_decimals: bool = False,
) -> None:
    """Render a dataframe with 1-based row numbers and bold black headers."""
    # NEW: Start row numbering at 1 (not 0)
    view = df.copy().reset_index(drop=True)
    if max_decimals:
        view = _format_two_decimals(view)
    view.index = range(1, len(view) + 1)

    # NEW: Use HTML so header font-weight/color apply (unlike st.dataframe)
    styled = view.style
    if max_decimals:
        # NEW: Format numeric cells to at most two decimal places (Cleaned Data table)
        styled = styled.format(precision=2, na_rep="")

    # NEW: Highlight only specific imputed cells (Cleaned Data table)
    if highlight_mask is not None and not highlight_mask.empty:
        mask = highlight_mask.reset_index(drop=True)
        # Align mask to displayed rows/columns
        mask = mask.reindex(index=range(len(view)), columns=view.columns, fill_value=False)
        mask.index = view.index

        def _highlight_imputed_cells(data):
            styles = pd.DataFrame("", index=data.index, columns=data.columns)
            for col in data.columns:
                if col in mask.columns:
                    styles.loc[mask[col].astype(bool), col] = "background-color: #e0e0e0"
            return styles

        styled = styled.apply(_highlight_imputed_cells, axis=None)

    html = styled.to_html()
    # Ensure our CSS class is present for header/body styling
    html = html.replace('class="dataframe"', 'class="dataframe display-table"', 1)
    st.markdown(f'<div class="display-table-wrap">{html}</div>', unsafe_allow_html=True)

    # NEW: Legend for imputed-value cell highlighting (Cleaned Data only)
    if show_imputed_legend:
        st.markdown(
            """
            <div class="imputed-legend">
                <span class="imputed-legend-swatch"></span>
                <span>Light grey indicates data was imputed</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def get_imputed_cell_mask(df_raw: pd.DataFrame, df_cleaned: pd.DataFrame) -> pd.DataFrame:
    """
    NEW: Boolean mask of cleaned cells that were imputed (missing in raw, filled after).

    Uses __row_id__ when present so row drops (e.g. duplicates) still map correctly.
    """
    mask = pd.DataFrame(False, index=df_cleaned.index, columns=df_cleaned.columns)

    if ROW_ID_COL in df_raw.columns and ROW_ID_COL in df_cleaned.columns:
        raw_by_id = df_raw.set_index(ROW_ID_COL)
        for idx, row_id in df_cleaned[ROW_ID_COL].items():
            if row_id not in raw_by_id.index:
                continue
            raw_row = raw_by_id.loc[row_id]
            for col in df_cleaned.columns:
                if col == ROW_ID_COL or col not in raw_by_id.columns:
                    continue
                # NEW: Only track imputation highlights for numeric columns
                if not pd.api.types.is_numeric_dtype(df_cleaned[col]):
                    continue
                if pd.isna(raw_row[col]) and pd.notna(df_cleaned.at[idx, col]):
                    mask.at[idx, col] = True
        return mask

    # Fallback: positional compare when shapes match
    common_cols = [c for c in df_cleaned.columns if c in df_raw.columns]
    n = min(len(df_raw), len(df_cleaned))
    for col in common_cols:
        # NEW: Only track imputation highlights for numeric columns
        if not pd.api.types.is_numeric_dtype(df_cleaned[col]):
            continue
        was_missing = df_raw[col].iloc[:n].isna().to_numpy()
        now_filled = df_cleaned[col].iloc[:n].notna().to_numpy()
        mask.loc[df_cleaned.index[:n], col] = was_missing & now_filled
    return mask


st.title("🧹 Data Cleaning Agent")

# Upload file
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded_file:
    # Load data
    df_raw = pd.read_csv(uploaded_file)

    # NEW: Show a per-column data summary table after upload
    st.subheader("Data Summary")
    st.write(f"Shape: {df_raw.shape[0]} rows × {df_raw.shape[1]} columns")
    display_table(get_dataframe_summary_table(df_raw), show_all_columns=True)

    # NEW: Show a preview of the raw uploaded data
    st.subheader("Preview")
    display_table(df_raw.head())

    # NEW: Let users select which cleaning operations to run
    st.subheader("Cleaning Operations")
    st.caption("Select the operations to apply:")
    col1, col2 = st.columns(2)
    with col1:
        remove_duplicates = st.checkbox("Remove duplicate rows", value=True)
        drop_high_missing = st.checkbox("Drop high-missing columns (>40%)", value=True)
    with col2:
        remove_outliers = st.checkbox("Remove outliers (IQR capping)", value=True)
        impute_missing = st.checkbox("Impute missing values (numeric only)", value=True)

    # NEW: Build agent instructions from the selected checkboxes
    operations = []
    if remove_duplicates:
        operations.append(
            "Remove duplicate rows."
        )
    if remove_outliers:
        operations.append(
            "Detect numeric outliers with the IQR method and cap (winsorize) "
            "values to [Q1-1.5*IQR, Q3+1.5*IQR]. Do not drop outlier rows."
        )
    if drop_high_missing:
        operations.append(
            "Drop columns with more than 40% missing values."
        )
    if impute_missing:
        operations.append(
            "Impute missing values for numeric columns only (use mean or median). "
            "Do not impute categorical/object/string columns."
        )
    
    # Clean button
    if st.button("Clean Data"):
        # NEW: Require at least one operation before cleaning
        if not operations:
            st.warning("Select at least one cleaning operation.")
        # NEW: Only run cleaning when at least one operation is selected
        if operations:
            # NEW: Track row identity so imputed cells can be highlighted after cleaning
            df_to_clean = df_raw.copy()
            df_to_clean.insert(0, ROW_ID_COL, range(len(df_to_clean)))

            # NEW: Pass only the selected operations to the agent
            user_instructions = (
                "Only perform the following cleaning steps (do not add other steps):\n"
                + "\n".join(f"{i}. {step}" for i, step in enumerate(operations, start=1))
                + f"\nPreserve the '{ROW_ID_COL}' column unchanged (do not drop, impute, or modify it)."
            )
            with st.spinner("Cleaning..."):
                llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
                agent = LightweightDataCleaningAgent(model=llm, log=True)
                # NEW: Invoke agent with selected user_instructions
                agent.invoke_agent(data_raw=df_to_clean, user_instructions=user_instructions)
                # PREVIOUS: agent always ran default cleaning steps with no options selected
                # agent.invoke_agent(data_raw=df_raw)
                df_cleaned = agent.get_data_cleaned()

                # NEW: Cell-level imputed mask for Cleaned Data highlighting
                imputed_mask = (
                    get_imputed_cell_mask(df_to_clean, df_cleaned)
                    if impute_missing
                    else pd.DataFrame(False, index=df_cleaned.index, columns=df_cleaned.columns)
                )

                # NEW: Remove tracking column from user-facing outputs
                if ROW_ID_COL in df_cleaned.columns:
                    display_cleaned = df_cleaned.drop(columns=[ROW_ID_COL])
                    display_mask = imputed_mask.drop(columns=[ROW_ID_COL], errors="ignore")
                else:
                    display_cleaned = df_cleaned
                    display_mask = imputed_mask
                
                st.success("Done!")

                # NEW: Show summary stats for the cleaned dataset (no imputation highlighting)
                st.subheader("Cleaned Data Summary")
                st.write(f"Shape: {display_cleaned.shape[0]} rows × {display_cleaned.shape[1]} columns")
                display_table(get_dataframe_summary_table(display_cleaned), show_all_columns=True)
                
                st.subheader("Cleaned Data")
                st.write(f"Shape: {display_cleaned.shape[0]} rows × {display_cleaned.shape[1]} columns")
                cleaned_preview = display_cleaned.head()
                mask_preview = display_mask.loc[cleaned_preview.index, cleaned_preview.columns]
                has_imputed_cells = bool(mask_preview.to_numpy().any())
                # NEW: Cleaned Data only — 2 decimals + highlight specific imputed cells + legend
                display_table(
                    cleaned_preview,
                    highlight_mask=mask_preview if impute_missing else None,
                    show_imputed_legend=impute_missing and has_imputed_cells,
                    max_decimals=True,
                )
                
                # Download
                csv = display_cleaned.to_csv(index=False)
                st.download_button(
                    "Download Cleaned Data",
                    data=csv,
                    file_name="cleaned_data.csv",
                    mime="text/csv"
                )
