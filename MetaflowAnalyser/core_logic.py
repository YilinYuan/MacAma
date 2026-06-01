import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm # 用于 Egger's Test

def preprocess_data_r_logic(df):
    """
    Preprocesses data according to the R script logic:
    Calculates SD, Pooled SD, Hedges' g, SMD, SE, and CIs.
    """
    print("开始数据预处理...")
    print(f"原始数据行数: {len(df)}")
    
    df_processed = df.copy()

    # Rename columns for clarity
    df_processed = df_processed.rename(columns={
        'Article_ID': 'study',
        'CTRL_Sample': 'Sample_ctrl',
        'CTRL': 'Ctrl',
        'Ctrl_Error_Bar_Max': 'Ctrl_Error_Bar_M',
        'IR_Sample': 'Sample_rt',
        'IR': 'RT',
        'IR_Error_Bar_Max': 'RT_Error_Bar_M'
    })

    # Convert necessary columns to numeric
    numeric_cols = ['Sample_ctrl', 'Ctrl', 'Ctrl_Error_Bar_M', 'Sample_rt', 'RT', 'RT_Error_Bar_M']
    for col in numeric_cols:
        df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')

    df_processed['study'] = df_processed['study'].astype(str)

    essential_cols = ['Sample_ctrl', 'Ctrl', 'Ctrl_Error_Bar_M', 'Sample_rt', 'RT', 'RT_Error_Bar_M']
    df_processed = df_processed.dropna(subset=essential_cols)
    print(f"基本数据清理后行数: {len(df_processed)}")

    # Calculate SD
    df_processed['Ctrl_SD'] = round((df_processed['Ctrl_Error_Bar_M'] - df_processed['Ctrl']) * np.sqrt(df_processed['Sample_ctrl']), 4)
    df_processed['RT_SD'] = round((df_processed['RT_Error_Bar_M'] - df_processed['RT']) * np.sqrt(df_processed['Sample_rt']), 4)

    df_processed.loc[df_processed['Ctrl_SD'] <= 0, 'Ctrl_SD'] = np.nan
    df_processed.loc[df_processed['RT_SD'] <= 0, 'RT_SD'] = np.nan

    df_processed = df_processed.dropna(subset=['Ctrl_SD', 'RT_SD'])
    print(f"SD计算后有效行数: {len(df_processed)}")

    n_ctrl = df_processed['Sample_ctrl']
    n_rt = df_processed['Sample_rt']
    sd_ctrl = df_processed['Ctrl_SD']
    sd_rt = df_processed['RT_SD']
    df_pooled_sd = n_ctrl + n_rt - 2
    df_pooled_sd[df_pooled_sd <= 0] = np.nan # Avoid division by zero or sqrt of negative

    df_processed['Sp'] = round(np.sqrt(((n_ctrl - 1) * sd_ctrl**2 + (n_rt - 1) * sd_rt**2) / df_pooled_sd.replace(0, np.nan)), 4)


    df_hedges_g = 4 * (n_ctrl + n_rt) - 9
    df_hedges_g[df_hedges_g <= 0] = np.nan # Avoid division by zero

    df_processed['g'] = round(1 - 3 / df_hedges_g.replace(0, np.nan), 4)


    sp_safe = df_processed['Sp'].replace(0, np.nan)
    df_processed['SMD'] = round(df_processed['g'] * (df_processed['RT'] - df_processed['Ctrl']) / sp_safe, 4)

    term1 = (n_ctrl + n_rt) / (n_ctrl * n_rt)
    term2_denom = 2 * (n_ctrl + n_rt - 2)
    term2_denom[term2_denom <= 0] = np.nan # Avoid division by zero
    
    # Ensure SMD is numeric for squaring, handle potential NaNs from previous steps
    smd_for_term2 = pd.to_numeric(df_processed['SMD'], errors='coerce')
    term2 = smd_for_term2**2 / term2_denom.replace(0, np.nan)

    df_processed['SE'] = round(np.sqrt(term1 + term2), 4)
    
    # Drop rows if any critical calculation resulted in NaN, before final Variance calculation
    df_processed = df_processed.dropna(subset=['Sp', 'g', 'SMD', 'SE'])
    print(f"最终有效数据行数: {len(df_processed)}")

    df_processed['Variance'] = round(df_processed['SE']**2, 4)

    return df_processed

def eggers_test(effect_sizes, standard_errors, variances):
    """
    Performs Egger's regression test for funnel plot asymmetry.
    Regresses standardized effect (ES/SE) against precision (1/SE).
    Weights are 1 / Var(ES) = 1 / SE^2.
    """
    # Egger's test typically requires a minimum number of studies (e.g., >3 or >5, sometimes cited as 10 for reliability)
    # For calculation purposes, at least 2 are needed for df_resid > 0 if using k-2.
    # A regression with intercept and one predictor needs at least 2 points for parameters, 3 for a p-value on slope/intercept.
    if len(effect_sizes) < 3: 
        return {"intercept": np.nan, "se_intercept": np.nan, "p_value": np.nan, "df_resid": len(effect_sizes) - 2, "t_value": np.nan, "error": "Egger's test requires at least 3 studies for meaningful results."}

    # Ensure no division by zero for standard_errors
    # Use a small epsilon to avoid issues with very small SEs that are effectively zero
    valid_se_indices = standard_errors > 1e-9 
    if np.sum(valid_se_indices) < 3:
        return {"intercept": np.nan, "se_intercept": np.nan, "p_value": np.nan, "df_resid": np.sum(valid_se_indices) - 2, "t_value": np.nan, "error": "Not enough studies with valid non-zero SE for Egger's test."}

    es_filt = effect_sizes[valid_se_indices]
    se_filt = standard_errors[valid_se_indices]
    var_filt = variances[valid_se_indices] # These are Var(ES) = SE^2

    # y = ES / SE (Standardized Effect Size)
    y = es_filt / se_filt
    # x = 1 / SE (Precision)
    x = 1.0 / se_filt

    # Add constant for intercept term
    X = sm.add_constant(x, prepend=True) # X will be [const, precision]

    # Weights for WLS: inverse of the variance of the effect size (ES) itself.
    # This is a common weighting scheme for Egger's test.
    weights = 1.0 / var_filt # weights = 1 / SE^2

    try:
        wls_model = sm.WLS(y, X, weights=weights)
        results = wls_model.fit()

        intercept = results.params[0]       # Intercept (beta_0)
        se_intercept = results.bse[0]       # Standard error of intercept
        p_value_intercept = results.pvalues[0] # P-value for the intercept
        t_value_intercept = results.tvalues[0] # t-statistic for the intercept
        df_resid = int(results.df_resid)    # Degrees of freedom for residuals

        return {"intercept": round(intercept, 4),
                "se_intercept": round(se_intercept, 4),
                "p_value": round(p_value_intercept, 4),
                "df_resid": df_resid, 
                "t_value": round(t_value_intercept, 4),
                "bias_coeff": round(results.params[1], 4) if len(results.params) > 1 else np.nan, # Slope, sometimes reported
                "p_value_bias_coeff": round(results.pvalues[1], 4) if len(results.pvalues) > 1 else np.nan
                }
    except Exception as e:
        return {"intercept": np.nan, "se_intercept": np.nan, "p_value": np.nan, "df_resid": len(es_filt) - 2, "t_value": np.nan, "error": f"Error in Egger's regression: {e}"}


def meta_analysis(effect_sizes, variances):
    """
    执行固定效应和随机效应Meta分析, 并加入Egger's检验
    """
    k = len(effect_sizes)
    if k < 2:
        return {"error": "需要至少2个研究才能进行Meta分析", 
                "eggers_test": {"error": "Egger's test requires more studies than available for meta-analysis."}}

    variances_arr = np.array(variances, dtype=float)
    effect_sizes_arr = np.array(effect_sizes, dtype=float)
    # Calculate SE, ensuring variances are non-negative before sqrt
    standard_errors_arr = np.sqrt(np.maximum(variances_arr, 0)) 

    valid_indices = np.isfinite(effect_sizes_arr) & \
                    np.isfinite(variances_arr) & (variances_arr > 1e-12) & \
                    np.isfinite(standard_errors_arr) & (standard_errors_arr > 1e-9)
    
    effect_sizes_valid = effect_sizes_arr[valid_indices]
    variances_valid = variances_arr[valid_indices]
    standard_errors_valid = standard_errors_arr[valid_indices]
    k_valid = len(effect_sizes_valid)

    if k_valid < 2:
         return {"error": "有效研究数量不足（少于2个）",
                 "eggers_test": {"error": "Not enough valid studies for Egger's test."}}

    weights_fe = 1.0 / variances_valid
    sum_weights_fe = np.sum(weights_fe)
    
    if sum_weights_fe == 0: # Avoid division by zero if all variances are huge/infinite
        return {"error": "无法计算固定效应模型 (权重总和为零)", 
                "eggers_test": {"error": "Cannot perform Egger's test due to weight calculation issues."}}

    pooled_es_fe = round(np.sum(weights_fe * effect_sizes_valid) / sum_weights_fe, 4)
    se_pooled_fe = round(np.sqrt(1.0 / sum_weights_fe), 4)
    z_fe = pooled_es_fe / se_pooled_fe if se_pooled_fe > 0 else 0
    p_value_fe = round(2 * (1 - stats.norm.cdf(np.abs(z_fe))), 4)

    q_stat = round(np.sum(weights_fe * (effect_sizes_valid - pooled_es_fe)**2), 4)
    df_q = k_valid - 1
    p_value_q = round(1 - stats.chi2.cdf(q_stat, df_q) if df_q > 0 else 1.0, 4)
    
    if q_stat <= 0: # Avoid division by zero or issues if Q is not positive
        i_squared = 0.0
    else:
        i_squared = round(max(0.0, (q_stat - df_q) / q_stat) * 100 if q_stat > df_q else 0.0, 4)


    sum_weights_fe_sq = np.sum(weights_fe**2)
    c_dl = sum_weights_fe - sum_weights_fe_sq / sum_weights_fe if sum_weights_fe > 0 else 1.0
    if c_dl <= 0: # c_dl must be positive for tau_squared calculation
        tau_squared = 0.0
        # print("Warning: C_DL was zero or negative, tau_squared set to 0.")
    else:
        tau_squared = round(max(0.0, (q_stat - df_q) / c_dl) if q_stat > df_q else 0.0, 4)


    weights_re_denom = variances_valid + tau_squared
    # Prevent division by zero if all variances_valid + tau_squared are zero
    weights_re_denom[weights_re_denom <= 1e-12] = np.nan # Replace with NaN to avoid division by zero and propagate issue
    
    weights_re = 1.0 / weights_re_denom
    
    # Check if any weights_re became NaN due to denom issues
    if np.isnan(weights_re).any():
        # Handle error or set RE results to NaN
        sum_weights_re = np.nan
        pooled_es_re = np.nan
        se_pooled_re = np.nan
        # print("Warning: Could not calculate random effects weights due to zero denominators after tau_squared addition.")
    else:
        sum_weights_re = np.sum(weights_re)

    if sum_weights_re == 0 or np.isnan(sum_weights_re):
        pooled_es_re = np.nan
        se_pooled_re = np.nan
    else:
        pooled_es_re = round(np.sum(weights_re * effect_sizes_valid) / sum_weights_re, 4)
        se_pooled_re = round(np.sqrt(1.0 / sum_weights_re), 4)

    z_re = pooled_es_re / se_pooled_re if se_pooled_re > 0 and np.isfinite(se_pooled_re) and np.isfinite(pooled_es_re) else 0
    p_value_re = round(2 * (1 - stats.norm.cdf(np.abs(z_re))) if np.isfinite(z_re) else np.nan, 4)

    pred_se = np.sqrt(tau_squared + se_pooled_re**2) if np.isfinite(se_pooled_re) and np.isfinite(tau_squared) else np.nan
    pred_interval = calculate_ci(pooled_es_re, pred_se) if np.isfinite(pred_se) and np.isfinite(pooled_es_re) else (np.nan, np.nan)

    weights_fe_full = np.full(k, np.nan)
    weights_re_full = np.full(k, np.nan)
    if k_valid > 0: # Ensure there are valid indices to put weights
        np.put(weights_fe_full, np.where(valid_indices)[0], weights_fe if not np.isscalar(weights_fe) or k_valid ==1 else [weights_fe])
        np.put(weights_re_full, np.where(valid_indices)[0], weights_re if not np.isscalar(weights_re) or k_valid ==1 else [weights_re])
    
    # Perform Egger's test
    eggers_results = eggers_test(effect_sizes_valid, standard_errors_valid, variances_valid)

    return {
        "k": k_valid,
        "fixed": {"pooled_es": pooled_es_fe, "se": se_pooled_fe, "p_value": p_value_fe},
        "random": {"pooled_es": pooled_es_re, "se": se_pooled_re, "p_value": p_value_re},
        "heterogeneity": {"Q": q_stat, "df": df_q, "p_value_Q": p_value_q, "I_squared": i_squared, "tau_squared": tau_squared},
        "prediction": {"lower": pred_interval[0], "upper": pred_interval[1]},
        "weights_fixed": np.round(weights_fe_full, 4),
        "weights_random": np.round(weights_re_full, 4),
        "valid_indices": valid_indices,
        "eggers_test": eggers_results 
    }

def calculate_ci(es, se, conf_level=0.95):
    """计算置信区间"""
    if not np.isfinite(es) or not np.isfinite(se) or se <= 0:
         return (np.nan, np.nan)
    z_score = stats.norm.ppf(1 - (1 - conf_level) / 2)
    ci_lower = round(es - z_score * se, 4)
    ci_upper = round(es + z_score * se, 4)
    return ci_lower, ci_upper

def subgroup_analysis(df, subgroup_var, conf_level=0.95):
    """
    对指定变量进行亚组分析
    """
    df_analysis = df.copy()
    
    if df_analysis.empty or 'SMD' not in df_analysis.columns or 'Variance' not in df_analysis.columns:
        return {"error": "无效的数据集或缺少SMD/Variance列"}

    if subgroup_var not in df_analysis.columns:
        return {"error": f"亚组变量 '{subgroup_var}' 不在数据中。"}

    # Ensure 'Sample_ctrl' and 'Sample_rt' exist for subgroup summary if they are used from original df_processed
    # These are used for total sample sizes in subgroups in create_forest_plot.
    # If not present in df_analysis passed to subgroup_analysis (e.g. if it's only SMD & Var),
    # then k is the primary measure of subgroup size.
    
    # Filter out rows where subgroup variable is NaN, as groupby would create a separate group for NaNs
    df_filtered_for_subgroup = df_analysis.dropna(subset=[subgroup_var, 'SMD', 'Variance'])
    if df_filtered_for_subgroup.empty:
         return {"error": f"在亚组变量 '{subgroup_var}' 中没有有效数据进行分析。"}


    overall_results_for_subgroup_scope = meta_analysis(df_filtered_for_subgroup['SMD'], df_filtered_for_subgroup['Variance'])
    if "error" in overall_results_for_subgroup_scope:
        return {"error": f"对亚组 '{subgroup_var}' 进行总体分析时出错: {overall_results_for_subgroup_scope['error']}"}

    
    results = {}
    total_q_within_fixed = 0
    total_df_within = 0
    # Store effect sizes and variances for Q_between calculation using fixed effects model
    all_subgroup_pooled_es_fe = []
    all_subgroup_variances_fe = [] # Variance of the pooled ES for each subgroup under FE model
    all_subgroup_weights_fe = []


    grouped = df_filtered_for_subgroup.groupby(subgroup_var)
    num_valid_subgroups = 0

    for name, group_df in grouped:
        if len(group_df) >= 2: # Need at least 2 studies for a meta-analysis within a subgroup
            group_res = meta_analysis(group_df['SMD'], group_df['Variance']) # This now includes Egger's for the subgroup
            
            if "error" not in group_res:
                num_valid_subgroups += 1
                ci_fe_lower, ci_fe_upper = calculate_ci(group_res['fixed']['pooled_es'], 
                                                      group_res['fixed']['se'], conf_level)
                ci_re_lower, ci_re_upper = calculate_ci(group_res['random']['pooled_es'], 
                                                      group_res['random']['se'], conf_level)
                
                # Prediction interval for random effects model within subgroup
                pred_lower_sg, pred_upper_sg = (np.nan, np.nan)
                if np.isfinite(group_res['random']['se']) and np.isfinite(group_res['heterogeneity']['tau_squared']):
                     pred_se_sg = np.sqrt(group_res['heterogeneity']['tau_squared'] + group_res['random']['se']**2)
                     pred_lower_sg, pred_upper_sg = calculate_ci(group_res['random']['pooled_es'], pred_se_sg, conf_level)


                num_studies_in_group = group_res['k'] # k from meta_analysis is k_valid
                # Sample sizes - check if original sample size columns are present
                total_samples_ctrl_sg = group_df['Sample_ctrl'].sum() if 'Sample_ctrl' in group_df else 'N/A'
                total_samples_rt_sg = group_df['Sample_rt'].sum() if 'Sample_rt' in group_df else 'N/A'


                results[str(name)] = { 
                    "k": num_studies_in_group,
                    "fixed_es": group_res['fixed']['pooled_es'],
                    "fixed_se": group_res['fixed']['se'], # Store SE for Q_between
                    "fixed_ci": (ci_fe_lower, ci_fe_upper),
                    "fixed_p": group_res['fixed']['p_value'],
                    "random_es": group_res['random']['pooled_es'],
                    "random_se": group_res['random']['se'],
                    "random_ci": (ci_re_lower, ci_re_upper),
                    "random_p": group_res['random']['p_value'],
                    "I_squared": group_res['heterogeneity']['I_squared'],
                    "tau_squared": group_res['heterogeneity']['tau_squared'],
                    "Q_within": group_res['heterogeneity']['Q'], # This is Q_within_fixed for this subgroup
                    "df_within": group_res['heterogeneity']['df'],
                    "pred_int_random": (pred_lower_sg, pred_upper_sg),
                    "eggers_test_subgroup": group_res.get('eggers_test', {}), # Egger's test for this subgroup
                    "num_studies": num_studies_in_group,
                    "total_samples_ctrl": total_samples_ctrl_sg,
                    "total_samples_rt": total_samples_rt_sg
                }
                total_q_within_fixed += group_res['heterogeneity']['Q'] # Sum of Q-within from FE model
                total_df_within += group_res['heterogeneity']['df']

                # For Q_between calculation:
                all_subgroup_pooled_es_fe.append(group_res['fixed']['pooled_es'])
                all_subgroup_variances_fe.append(group_res['fixed']['se']**2) # Var(pooled_ES_fe) = SE_pooled_ES_fe^2
                all_subgroup_weights_fe.append(1.0 / (group_res['fixed']['se']**2) if group_res['fixed']['se']**2 > 0 else 0)


            else:
                results[str(name)] = {"error": f"组 '{name}' 分析错误: {group_res['error']}"}
        else:
            results[str(name)] = {"error": f"组 '{name}' 研究数不足 (<2)"}

    # Calculate Q_between (Test for subgroup differences)
    q_between = np.nan
    p_q_between = np.nan
    df_between = max(0, num_valid_subgroups - 1) # df for Q_between is number of groups - 1

    if num_valid_subgroups > 1 :
        q_total_fixed = overall_results_for_subgroup_scope['heterogeneity']['Q'] # Q from overall FE model on all studies in subgroups
        
        # Q_between = Q_total_fixed - sum(Q_within_fixed for each subgroup)
        q_between = round(max(0.0, q_total_fixed - total_q_within_fixed), 4)
        
        if df_between > 0 and np.isfinite(q_between):
            p_q_between = round(1 - stats.chi2.cdf(q_between, df_between), 4)
        elif df_between == 0: # Only one valid subgroup, no between-group comparison possible
            p_q_between = 1.0 # Or np.nan, conventionally p=1 if no difference can be tested
    
    return {
        "overall_for_subgroup_scope": overall_results_for_subgroup_scope, # Overall analysis restricted to studies in subgroups
        "subgroups": results,       
        "test": {                   
            "Q_between": q_between,
            "df": df_between,
            "p_value": p_q_between
        },
        "subgroup_var": subgroup_var 
    }