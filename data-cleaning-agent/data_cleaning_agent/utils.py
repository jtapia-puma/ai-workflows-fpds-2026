# Utility functions for lightweight data cleaning agent

import re
import logging
import pandas as pd
from langchain_core.output_parsers import BaseOutputParser

logger = logging.getLogger(__name__)


class PythonOutputParser(BaseOutputParser):
    """Extract Python code from LLM responses."""
    
    def parse(self, text: str):
        """Extract code from ```python``` blocks or return text as-is."""
        python_code_match = re.search(r'```python(.*?)```', text, re.DOTALL)
        if python_code_match:
            return python_code_match.group(1).strip()
        return text


# NEW: Tabular summary for Streamlit (dtypes, missingness, uniqueness, numeric stats)
def get_dataframe_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a tabular dataset summary (one row per column).

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to summarize.

    Returns
    -------
    pd.DataFrame
        Summary with dtype, missingness, uniqueness, and numeric stats
        (min, max, median, mean, std, quartiles, IQR) where applicable.
    """
    n_rows = max(len(df), 1)
    rows = []
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        # NEW: Base columns for every feature in the summary table
        row = {
            "Column": col,
            "Data Type": str(df[col].dtype),
            "Missing Count": missing_count,
            "Missing %": round(missing_count / n_rows * 100, 2),
            "Unique Values": int(df[col].nunique(dropna=True)),
            # NEW: Numeric stats placeholders (filled only for numeric columns)
            "Min": None,
            "Max": None,
            "Median": None,
            "Mean": None,
            "Std Dev": None,
            "25th %": None,
            "50th %": None,
            "75th %": None,
            "IQR": None,
        }

        # NEW: Compute descriptive stats for numeric columns only (2 decimal places)
        if pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            if not series.empty:
                q25 = float(series.quantile(0.25))
                q50 = float(series.quantile(0.50))
                q75 = float(series.quantile(0.75))
                row.update(
                    {
                        "Min": round(float(series.min()), 2),
                        "Max": round(float(series.max()), 2),
                        "Median": round(float(series.median()), 2),
                        "Mean": round(float(series.mean()), 2),
                        "Std Dev": round(float(series.std()), 2) if len(series) > 1 else 0.0,
                        "25th %": round(q25, 2),
                        "50th %": round(q50, 2),
                        "75th %": round(q75, 2),
                        "IQR": round(q75 - q25, 2),
                    }
                )

        rows.append(row)
    return pd.DataFrame(rows)


def get_dataframe_summary(df: pd.DataFrame) -> str:
    """
    Generate a simple summary of a DataFrame for the LLM.
    
    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to summarize.
    
    Returns
    -------
    str
        A text summary of the DataFrame.
    """
    missing_stats = (df.isna().sum() / len(df) * 100).sort_values(ascending=False)
    missing_summary = "\n".join([f"{col}: {val:.2f}%" for col, val in missing_stats.items()])
    
    column_types = "\n".join([f"{col}: {dtype}" for col, dtype in df.dtypes.items()])
    
    summary = f"""
        Dataset Summary:
        ----------------
        Column Data Types:
        {column_types}

        Missing Value Percentage:
        {missing_summary}"""

    return summary.strip()


def execute_agent_code(state, data_key, code_snippet_key, result_key, error_key, agent_function_name):
    """
    Execute the generated agent code on the data.
    
    Parameters
    ----------
    state : dict
        The current state containing data and code.
    data_key : str
        Key in state where the input data is stored.
    code_snippet_key : str
        Key in state where the generated code is stored.
    result_key : str
        Key to store the result in.
    error_key : str
        Key to store any error message in.
    agent_function_name : str
        Name of the function to execute from the generated code.
    
    Returns
    -------
    dict
        Dictionary with result and error keys.
    """
    logger.info("Executing agent code")
    
    data = state.get(data_key)
    agent_code = state.get(code_snippet_key)
    df = pd.DataFrame.from_dict(data)
    
    # Execute the LLM-generated code in isolated namespace
    # Note: exec() can be risky - only use with trusted LLM-generated code
    local_vars = {}
    global_vars = {}
    exec(agent_code, global_vars, local_vars)
    
    # Get the function from executed code
    agent_function = local_vars.get(agent_function_name)
    if not agent_function or not callable(agent_function):
        raise ValueError(f"Function '{agent_function_name}' not found in generated code.")
    
    # Run the function and handle errors
    agent_error = None
    result = None
    try:
        result = agent_function(df)
        if isinstance(result, pd.DataFrame):
            result = result.to_dict()
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        agent_error = f"An error occurred during data cleaning: {str(e)}"
    
    return {result_key: result, error_key: agent_error}


def fix_agent_code(state, code_snippet_key, error_key, llm, prompt_template, function_name, retry_count_key="retry_count"):
    """
    Fix errors in the generated agent code using the LLM.
    
    Parameters
    ----------
    state : dict
        The current state containing code and error information.
    code_snippet_key : str
        Key in state where the broken code is stored.
    error_key : str
        Key in state where the error message is stored.
    llm : LLM
        The language model to use for fixing the code.
    prompt_template : str
        Template for the fix prompt (should have {code_snippet}, {error}, {function_name} placeholders).
    function_name : str
        Name of the function being fixed.
    retry_count_key : str, optional
        Key in state for tracking retry count. Defaults to "retry_count".
    
    Returns
    -------
    dict
        Dictionary with updated code, cleared error, and incremented retry count.
    """
    logger.info("Fixing agent code")
    logger.debug(f"Retry count: {state.get(retry_count_key)}")
    
    code_snippet = state.get(code_snippet_key)
    error_message = state.get(error_key)
    
    # Create the fix prompt
    prompt = prompt_template.format(
        code_snippet=code_snippet,
        error=error_message,
        function_name=function_name,
    )
    
    # Get fixed code from LLM
    response = (llm | PythonOutputParser()).invoke(prompt)
    
    return {
        code_snippet_key: response,
        error_key: None,
        retry_count_key: state.get(retry_count_key) + 1
    }
