import pandas as pd
import streamlit as st
import numpy as np

def validate_dataframe(df):
    """验证DataFrame是否包含R脚本逻辑所需的列和基本数据类型"""
    # Columns needed for SMD calculation based on R script
    required_cols = [
        'Article_ID', 'CTRL_Sample', 'CTRL', 'Ctrl_Error_Bar_Max', # Original Input Name
        'IR_Sample', 'IR', 'IR_Error_Bar_Max'     # Original Input Name
    ]
    errors = []
    warnings = []
    df_validated = df.copy() # Work on a copy

    # Check for required columns
    missing_cols = [col for col in required_cols if col not in df_validated.columns]
    if missing_cols:
        errors.append(f"错误：缺少必需列: {', '.join(missing_cols)}")
        # Return original df if validation fails early, along with potential_subgroup_cols (empty list)
        potential_subgroup_cols = [col for col in df.columns if col not in required_cols] # Basic identification
        return df, False, errors, warnings, potential_subgroup_cols

    # Attempt to convert core numeric columns
    numeric_cols = ['CTRL_Sample', 'CTRL', 'Ctrl_Error_Bar_Max',
                    'IR_Sample', 'IR', 'IR_Error_Bar_Max']
    for col in numeric_cols:
        try:
            # Use pd.to_numeric with errors='coerce' to handle non-numeric gracefully
            df_validated[col] = pd.to_numeric(df_validated[col], errors='coerce')
        except Exception as e: # Catch any unexpected error during conversion attempt
             errors.append(f"错误：转换列 '{col}' 为数值型时出错: {e}")
             potential_subgroup_cols = [c for c in df.columns if c not in required_cols]
             return df, False, errors, warnings, potential_subgroup_cols # Stop validation on error

    # Check for NaNs introduced by coercion or originally present
    cols_to_check_na = ['CTRL_Sample', 'CTRL', 'Ctrl_Error_Bar_Max', 'IR_Sample', 'IR', 'IR_Error_Bar_Max']
    if df_validated[cols_to_check_na].isnull().any().any():
        warnings.append(f"警告：数值列中包含缺失值或无法转换为数值的值。包含这些问题的行将在计算中被忽略。")
        # Keep rows with NA for now, they will be dropped during calculation if needed

    # Check if N (Sample sizes) are valid (> 0, integer ideally)
    for n_col in ['CTRL_Sample', 'IR_Sample']:
         # Check first if column exists and is numeric after coercion attempt
         if n_col in df_validated.columns and pd.api.types.is_numeric_dtype(df_validated[n_col]):
             if (df_validated[n_col].dropna() <= 0).any():
                  warnings.append(f"警告：样本量列 '{n_col}' 包含非正数。这些行可能导致计算错误。")
             # Check if samples sizes are integers after dropping NAs
             if not pd.api.types.is_integer_dtype(df_validated[n_col].dropna()):
                  # Check specifically for non-integers among the numeric values
                  numeric_vals = df_validated[n_col].dropna()
                  non_integers = numeric_vals[numeric_vals % 1 != 0]
                  if not non_integers.empty:
                       warnings.append(f"警告：样本量列 '{n_col}' 包含非整数值。建议使用整数样本量。")
         elif n_col in df_validated.columns: # Column exists but wasn't numeric
              warnings.append(f"警告：样本量列 '{n_col}' 包含非数值，无法检查有效性。")
         # No warning if column was missing, as that's handled by required_cols check


    # Check Error_Bar_Max > Mean (necessary for SD calculation as defined)
    # Use the ORIGINAL column names from the input file here
    if 'Ctrl_Error_Bar_Max' in df_validated.columns and 'CTRL' in df_validated.columns and \
       pd.api.types.is_numeric_dtype(df_validated['Ctrl_Error_Bar_Max']) and \
       pd.api.types.is_numeric_dtype(df_validated['CTRL']):
        # Perform comparison only on rows where both are finite numbers
        valid_comparison = df_validated[['Ctrl_Error_Bar_Max', 'CTRL']].dropna()
        if not valid_comparison.empty and (valid_comparison['Ctrl_Error_Bar_Max'] <= valid_comparison['CTRL']).any():
             warnings.append(f"警告：部分行的 'Ctrl_Error_Bar_Max' 不大于 'CTRL'。SD 计算可能不准确或为负。")

    if 'IR_Error_Bar_Max' in df_validated.columns and 'IR' in df_validated.columns and \
       pd.api.types.is_numeric_dtype(df_validated['IR_Error_Bar_Max']) and \
       pd.api.types.is_numeric_dtype(df_validated['IR']):
        # Perform comparison only on rows where both are finite numbers
        valid_comparison = df_validated[['IR_Error_Bar_Max', 'IR']].dropna()
        if not valid_comparison.empty and (valid_comparison['IR_Error_Bar_Max'] <= valid_comparison['IR']).any():
             warnings.append(f"警告：部分行的 'IR_Error_Bar_Max' 不大于 'IR'。SD 计算可能不准确或为负。")


    # Check if Article_ID is suitable as string identifier
    if 'Article_ID' in df_validated.columns:
        try:
            df_validated['Article_ID'] = df_validated['Article_ID'].astype(str)
            if df_validated['Article_ID'].duplicated().any():
                 warnings.append("警告：'Article_ID' 列包含重复值。建议使用唯一的研究标识符。")
        except Exception as e:
            errors.append(f"错误：无法将 'Article_ID' 转换为字符串: {e}")
            potential_subgroup_cols = [c for c in df.columns if c not in required_cols]
            return df, False, errors, warnings, potential_subgroup_cols
    else:
        # This case should have been caught by required_cols check, but added defensively
         errors.append("错误: 'Article_ID' 列缺失.")
         potential_subgroup_cols = [c for c in df.columns if c not in required_cols]
         return df, False, errors, warnings, potential_subgroup_cols


    # Identify potential subgroup variables (excluding core numeric/ID cols used in calculation)
    # Define core cols based on ORIGINAL input names used for calculation setup
    core_calc_cols = required_cols # These are the direct inputs
    calculated_cols = [ # These are generated later, exclude them if they somehow exist
         'Ctrl_SD', 'RT_SD', 'Sp', 'g', 'SMD', 'SE', 'Variance',
         'CI_lower', 'CI_upper', 'Weight_Fixed', 'Weight_Random'
    ]
    potential_subgroup_cols = [
        col for col in df_validated.columns if col not in core_calc_cols and col not in calculated_cols
    ]

    # Return the validated (type-coerced) dataframe
    return df_validated, not errors, errors, warnings, potential_subgroup_cols