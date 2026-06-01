import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
import os
import warnings
import zipfile  # Added for zip functionality

# Import local modules
from utils import validate_dataframe
from core_logic import preprocess_data_r_logic, meta_analysis, calculate_ci, subgroup_analysis
from plotting import (create_forest_plot, create_funnel_plot, create_box_plot,
                      DEFAULT_TITLE_FONTSIZE, DEFAULT_LABEL_FONTSIZE, DEFAULT_TICK_FONTSIZE,
                      DEFAULT_STUDY_FONTSIZE, DEFAULT_ANNOTATION_FONTSIZE, DEFAULT_LEGEND_FONTSIZE,
                      DEFAULT_HEADER_FONTSIZE, DEFAULT_SUMMARY_FONTSIZE,
                      DEFAULT_TITLE_STYLE, DEFAULT_LABEL_STYLE, DEFAULT_STUDY_STYLE,
                      DEFAULT_FONT_FAMILY, DEFAULT_FIG_WIDTH, DEFAULT_FIG_HEIGHT,
                      DEFAULT_X_LABEL, DEFAULT_Y_LABEL, DEFAULT_FOREST_Y_LABEL,
                      DEFAULT_FUNNEL_X_LABEL, DEFAULT_FUNNEL_Y_LABEL, DEFAULT_BOX_X_LABEL,
                      DEFAULT_BOX_Y_LABEL, DEFAULT_XTICK_ROTATION, DEFAULT_SHOW_LEGEND,
                      DEFAULT_FUNNEL_MARKER, DEFAULT_STUDY_COLOR, DEFAULT_OVERALL_COLOR,
                      DEFAULT_SUBGROUP_COLOR, DEFAULT_NULL_LINE_COLOR, DEFAULT_POOLED_LINE_COLOR,
                      DEFAULT_FUNNEL_POINT_COLOR, DEFAULT_FUNNEL_CI_COLOR,
                      DEFAULT_BOXPLOT_PALETTE, DEFAULT_STRIPPLOT_COLOR)
from llm_utils import generate_analysis_description

# --- Helper function for creating ZIP archive ---
def create_zip_archive(artifacts, model_name):
    """Creates a zip archive in memory containing all plots and result tables."""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        # Add overall forest plot
        if artifacts.get("overall_forest_plot"):
            img_bytes = artifacts["overall_forest_plot"].getvalue()
            zip_file.writestr(f"forest_plot_overall_{model_name}.png", img_bytes)

        # Add funnel plot
        if artifacts.get("funnel_plot"):
            img_bytes = artifacts["funnel_plot"].getvalue()
            zip_file.writestr(f"funnel_plot_{model_name}.png", img_bytes)

        # Add subgroup details
        subgroup_details = artifacts.get("subgroup_details", {})
        for var, details in subgroup_details.items():
            # Add results table as CSV
            if details.get("table_df") is not None and not details["table_df"].empty:
                csv_string = details["table_df"].to_csv(index=False)
                zip_file.writestr(f"subgroup_results_{var}.csv", csv_string)
            # Add box plot image
            if details.get("box_plot"):
                img_bytes = details["box_plot"].getvalue()
                zip_file.writestr(f"subgroup_boxplot_{var}.png", img_bytes)
            # Add subgroup forest plot image
            if details.get("forest_plot"):
                img_bytes = details["forest_plot"].getvalue()
                zip_file.writestr(f"subgroup_forest_plot_{var}.png", img_bytes)
    
    zip_buffer.seek(0)
    return zip_buffer


# --- Session State Initialization ---
if 'analysis_run' not in st.session_state:
    st.session_state.analysis_run = False
if 'overall_results' not in st.session_state:
    st.session_state.overall_results = None
if 'df_processed' not in st.session_state:
    st.session_state.df_processed = None
if 'potential_subgroup_cols' not in st.session_state:
    st.session_state.potential_subgroup_cols = []
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None
if 'analysis_artifacts' not in st.session_state:
    st.session_state.analysis_artifacts = {
        "overall_forest_plot": None,
        "funnel_plot": None,
        "subgroup_details": {},
        "ai_texts": {},
        "overall_summary_texts": {},
        "publication_bias_texts": {}
    }
if 'show_subgroup_plots' not in st.session_state:
    st.session_state.show_subgroup_plots = {}


st.set_page_config(layout="wide")

st.title("📊 MetaFlow Analyzer")
st.write("""
Upload an Excel file containing study data. The expected column names are based on a specific format, for example:
`Article_ID`, `CTRL_Sample`, `CTRL`, `Ctrl_Error_Bar_Max`, `IR_Sample`, `IR`, `IR_Error_Bar_Max`,
and subgroup variables like `Strain`, `Gender`, `Age`, `Cancer`, `Dosage`, etc.

This tool will calculate the **Standardized Mean Difference (SMD)** as the effect size, perform a meta-analysis (including Egger's test),
and generate forest plots and funnel plots. Subgroup analysis will be automatically performed for predefined variables.
Subgroup charts can be displayed on-demand using buttons.
The AI interpretation feature uses a fixed model and requires the `DASHSCOPE_API_KEY` to be configured in the environment.
""")
st.markdown("---")

# --- File Uploader ---
uploaded_file = st.file_uploader("Select Excel file (.xlsx, .xls)", type=["xlsx", "xls"])

# --- Sample Data Download ---
@st.cache_data
def load_sample_data_r_format():
    n_studies = 15
    data = {
        'Article_ID': [f'Paper {chr(65+i)}' for i in range(n_studies)],
        'CTRL_Sample': np.random.randint(8, 25, n_studies),
        'CTRL': np.random.normal(10, 2, n_studies),
        'IR_Sample': np.random.randint(8, 25, n_studies),
        'IR': lambda df_lambda: df_lambda['CTRL'] + np.random.normal(2, 3, n_studies),
        'Dosage': np.random.choice(['Low', 'Medium', 'High'], n_studies, p=[0.3, 0.4, 0.3]),
        'Cancer': np.random.choice(['Lung', 'Breast', 'Colon', 'Prostate'], n_studies, p=[0.25, 0.25, 0.25, 0.25]),
        'Age': np.random.choice(['Young', 'Old'], n_studies),
        'Strain': np.random.choice(['StrainA', 'StrainB'], n_studies),
        'Gender': np.random.choice(['Male', 'Female'], n_studies)
    }
    sample_df = pd.DataFrame(data)
    sample_df['IR'] = sample_df.apply(sample_df['IR'], axis=1) # type: ignore
    ctrl_sd_sim = np.random.uniform(1.0, 4.0, n_studies)
    ir_sd_sim = np.random.uniform(1.5, 5.0, n_studies)
    sample_df['Ctrl_Error_Bar_Max'] = sample_df['CTRL'] + ctrl_sd_sim / np.sqrt(sample_df['CTRL_Sample'])
    sample_df['IR_Error_Bar_Max'] = sample_df['IR'] + ir_sd_sim / np.sqrt(sample_df['IR_Sample'])
    num_cols_to_round = ['CTRL', 'Ctrl_Error_Bar_Max', 'IR', 'IR_Error_Bar_Max']
    sample_df[num_cols_to_round] = sample_df[num_cols_to_round].round(2)
    return sample_df

sample_df_r = load_sample_data_r_format()
buffer_r = BytesIO()
sample_df_r.to_excel(buffer_r, index=False, engine='openpyxl')
buffer_r.seek(0)
st.download_button(
    label="Download Sample Data (with subgroups)",
    data=buffer_r,
    file_name="sample_meta_data_with_subgroups.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.markdown("---")

# --- Sidebar Settings ---
st.sidebar.header("⚙️ Analysis Settings")
conf_level_percent = st.sidebar.slider("Confidence Level (%)", 90, 99, 95, 1, key="conf_level_slider")
conf_level = conf_level_percent / 100.0
heterogeneity_threshold_i2 = st.sidebar.slider("I² Threshold for Subgroup Analysis (%)", 0, 100, 50, 5, key="i2_thresh_slider")
heterogeneity_threshold_q = st.sidebar.slider("Q-test p-value Threshold for Subgroup Analysis", 0.01, 0.20, 0.10, 0.01, key="q_thresh_slider")
analysis_model = st.sidebar.selectbox("Primary Reporting Model", ["random", "fixed"], index=0, key="model_select", help="Select the model (random-effects or fixed-effect) to be primarily displayed in results and plots.")

st.sidebar.markdown("---")
st.sidebar.header("🎨 Plot Appearance Settings")

with st.sidebar.expander("General Settings", expanded=False):
    st.subheader("Font")
    font_style_options = ['Normal', 'Bold', 'Italic']
    font_options = ['sans-serif', 'serif', 'monospace', 'DejaVu Sans', 'DejaVu Serif', 'Arial', 'Times New Roman', 'Helvetica', 'Calibri']
    default_font_index = font_options.index(DEFAULT_FONT_FAMILY) if DEFAULT_FONT_FAMILY in font_options else 0
    selected_font = st.selectbox("Chart Font", font_options, index=default_font_index, key="font_family_select",
                                     help="Select the font for chart text. Note: Availability of non-default fonts depends on the system environment.")
    st.caption("Tip: 'sans-serif', 'serif', 'monospace' will map to your system's default font. Other fonts require system installation.")

    title_st = st.selectbox("Title Style", font_style_options, index=font_style_options.index(DEFAULT_TITLE_STYLE), key="title_st")
    label_st = st.selectbox("Axis Label Style", font_style_options, index=font_style_options.index(DEFAULT_LABEL_STYLE), key="label_st")

    st.subheader("Font Size")
    title_fs = st.slider("Title Font Size", 8, 24, DEFAULT_TITLE_FONTSIZE, 1, key="title_fs")
    label_fs = st.slider("Axis Label Font Size", 6, 20, DEFAULT_LABEL_FONTSIZE, 1, key="label_fs")
    tick_fs = st.slider("Axis Tick Font Size", 5, 18, DEFAULT_TICK_FONTSIZE, 1, key="tick_fs")
    legend_fs = st.slider("Legend Font Size", 5, 18, DEFAULT_LEGEND_FONTSIZE, 1, key="legend_fs")

    st.subheader("Figure Size")
    fig_width = st.slider("Figure Width (inches)", 4, 20, DEFAULT_FIG_WIDTH, 1, key="fig_width")
    fig_height_other = st.slider("Funnel/Box Plot Height (inches)", 3, 15, DEFAULT_FIG_HEIGHT, 1, key="fig_height_other")
    output_dpi = st.slider("Image Resolution (DPI)", 75, 600, 300, 25, key="output_dpi")

with st.sidebar.expander("Forest Plot Settings", expanded=True):
    st.subheader("Text & Labels")
    title_text_forest = st.text_input("Title", value="Forest Plot", key="title_forest")
    x_label_text_forest = st.text_input("X-axis Label (Plot Area)", value=DEFAULT_X_LABEL, key="xlabel_forest")
    study_fs = st.slider("Study/Summary Label Font Size", 5, 18, DEFAULT_STUDY_FONTSIZE, 1, key="study_fs_forest")
    study_st = st.selectbox("Study Label Style", font_style_options, index=font_style_options.index(DEFAULT_STUDY_STYLE), key="study_st_forest")
    anno_fs = st.slider("Table Text Font Size (N/Mean/SD/SMD...)", 5, 14, DEFAULT_ANNOTATION_FONTSIZE, 1, key="anno_fs_forest")
    header_fs = st.slider("Column Header Font Size", 6, 16, DEFAULT_HEADER_FONTSIZE, 1, key="header_fs_forest")
    summary_fs = st.slider("Bottom Summary Font Size", 6, 16, DEFAULT_SUMMARY_FONTSIZE, 1, key="summary_fs_forest")

    st.subheader("Colors")
    col1_f, col2_f = st.columns(2)
    with col1_f:
        study_col = st.color_picker("Study Marker Color (Square)", DEFAULT_STUDY_COLOR, key="study_col_forest")
        overall_col = st.color_picker("Overall Diamond Color", DEFAULT_OVERALL_COLOR, key="overall_col_forest")
        subgroup_col = st.color_picker("Subgroup Diamond Color", DEFAULT_SUBGROUP_COLOR, key="subgroup_col_forest")
    with col2_f:
        null_line_col = st.color_picker("Null Line Color", DEFAULT_NULL_LINE_COLOR, key="null_line_col_forest")
        pooled_line_col = st.color_picker("Pooled Line Color", DEFAULT_POOLED_LINE_COLOR, key="pooled_line_col_forest")
    st.subheader("Other")
    show_summary_info_forest = st.checkbox("Show Bottom Summary Info", value=True, key="show_summary_info_forest")

with st.sidebar.expander("Funnel Plot Settings", expanded=False):
    st.subheader("Text & Labels")
    title_text_funnel = st.text_input("Title", value="Funnel Plot", key="title_funnel")
    y_label_text_funnel = st.text_input("Y-axis Label", value=DEFAULT_FUNNEL_Y_LABEL, key="ylabel_funnel")
    x_label_text_funnel = st.text_input("X-axis Label", value=DEFAULT_FUNNEL_X_LABEL, key="xlabel_funnel")
    st.subheader("Markers & Lines")
    marker_options = ['o', 's', '^', 'D', 'x', '+', '*']
    marker_style_funnel = st.selectbox("Marker Style", marker_options, index=marker_options.index(DEFAULT_FUNNEL_MARKER), key="marker_funnel")
    funnel_pt_col = st.color_picker("Point Color", DEFAULT_FUNNEL_POINT_COLOR, key="funnel_pt_col")
    funnel_pooled_line_col = st.color_picker("Pooled Line Color", DEFAULT_POOLED_LINE_COLOR, key="pooled_line_col_funnel")
    funnel_ci_col = st.color_picker("CI Line Color", DEFAULT_FUNNEL_CI_COLOR, key="funnel_ci_col")
    st.subheader("Legend")
    show_legend_funnel = st.checkbox("Show Legend", value=DEFAULT_SHOW_LEGEND, key="show_legend_funnel")

with st.sidebar.expander("Box Plot Settings", expanded=False):
    st.subheader("Text & Labels")
    title_text_box = st.text_input("Title", value="Subgroup Box Plot", key="title_box")
    y_label_text_box = st.text_input("Y-axis Label", value=DEFAULT_BOX_Y_LABEL, key="ylabel_box")
    x_label_text_box = st.text_input("X-axis Label", value=DEFAULT_BOX_X_LABEL, key="xlabel_box", help="Defaults to the subgroup variable name")
    xtick_rotation_box = st.slider("X-axis Tick Rotation Angle", 0, 90, DEFAULT_XTICK_ROTATION, 5, key="xtick_rot_box")
    st.subheader("Colors & Style")
    available_palettes = ["Set3", "Pastel1", "Paired", "viridis", "magma", "Blues", "Greens", "Default"]
    boxplot_pal_selected = st.selectbox("Color Theme (Palette)", available_palettes,
                                          index=available_palettes.index(DEFAULT_BOXPLOT_PALETTE) if DEFAULT_BOXPLOT_PALETTE in available_palettes else 0,
                                          key="boxplot_pal_box")
    boxplot_pal = None if boxplot_pal_selected == "Default" else boxplot_pal_selected
    box_strip_col = st.color_picker("Data Point Color", DEFAULT_STRIPPLOT_COLOR, key="box_strip_col")

st.sidebar.markdown("---")
st.sidebar.header("🤖 AI Interpretation Settings")
st.sidebar.info(
    "The AI interpretation feature uses a fixed model for analysis. "
    "Please ensure the `DASHSCOPE_API_KEY` environment variable is set correctly in the application's runtime environment."
)

# --- Main Logic ---
if uploaded_file is not None:
    if uploaded_file.name != st.session_state.get('uploaded_file_name'):
        st.info("New file detected, resetting analysis-related state...")
        # Preserve UI settings across runs
        keys_to_preserve = [key for key in st.session_state.keys() if key.endswith(('_slider', '_select', '_st', '_fs', '_col', '_funnel', '_box', '_forest', '_other', '_dpi', '_rot_box', '_pal_box'))]
        for key in list(st.session_state.keys()):
            if key not in keys_to_preserve:
                del st.session_state[key]

        # Reset analysis state
        st.session_state.analysis_run = False
        st.session_state.overall_results = None
        st.session_state.df_processed = None
        st.session_state.potential_subgroup_cols = []
        st.session_state.uploaded_file_name = uploaded_file.name
        st.session_state.file_processed_first_time = False
        st.session_state.analysis_artifacts = {
            "overall_forest_plot": None, "funnel_plot": None,
            "subgroup_details": {}, "ai_texts": {},
            "overall_summary_texts": {}, "publication_bias_texts": {}
        }
        st.session_state.show_subgroup_plots = {}
        st.rerun()

    try:
        df_orig = pd.read_excel(uploaded_file)
        if not st.session_state.get('file_processed_first_time', False):
            st.success(f"✅ File '{uploaded_file.name}' uploaded successfully!")
            st.session_state.file_processed_first_time = True

        with st.expander("Preview Uploaded Data (first 5 rows)"):
            st.dataframe(df_orig.head())

        if 'df_validated' not in st.session_state or st.session_state.uploaded_file_name != uploaded_file.name:
            df_validated, is_ok, errors, warnings_list, potential_subgroup_cols = validate_dataframe(df_orig)
            st.session_state.df_validated = df_validated
            st.session_state.is_ok = is_ok
            st.session_state.errors = errors
            st.session_state.warnings_list = warnings_list
            st.session_state.potential_subgroup_cols = potential_subgroup_cols
        else:
            df_validated = st.session_state.df_validated
            is_ok = st.session_state.is_ok
            errors = st.session_state.errors
            warnings_list = st.session_state.warnings_list

        if errors:
            is_ok = False
            for error in errors: st.error(error)
        if warnings_list:
            for warning_msg in warnings_list: st.warning(warning_msg)

        if is_ok:
            if st.button("🚀 Run Meta-Analysis", key="run_button"):
                plt.close('all')
                st.session_state.analysis_artifacts = {
                    "overall_forest_plot": None, "funnel_plot": None,
                    "subgroup_details": {}, "ai_texts": {},
                    "overall_summary_texts": {}, "publication_bias_texts": {}
                }
                st.session_state.show_subgroup_plots = {}

                with st.spinner("Preprocessing data and running analysis... Please wait..."):
                    try:
                        df_processed_calc = preprocess_data_r_logic(st.session_state.df_validated)
                        if df_processed_calc.empty or len(df_processed_calc) < 2:
                            st.error("Error: Insufficient valid data (less than 2 studies) for meta-analysis after preprocessing.")
                            st.session_state.analysis_run = False
                        else:
                            overall_results_calc = meta_analysis(df_processed_calc['SMD'], df_processed_calc['Variance'])
                            if "error" in overall_results_calc:
                                st.error(f"Analysis Error: {overall_results_calc['error']}")
                                st.session_state.analysis_run = False
                            else:
                                st.session_state.analysis_run = True
                                st.session_state.overall_results = overall_results_calc
                                st.session_state.df_processed = df_processed_calc
                                st.success("✅ Main analysis complete! Generating plots and AI interpretations...")

                                # --- Populate Analysis Artifacts ---
                                pooled_es_val = overall_results_calc[analysis_model]['pooled_es']
                                pooled_se_val = overall_results_calc[analysis_model]['se']
                                ci_lower_val, ci_upper_val = calculate_ci(pooled_es_val, pooled_se_val, conf_level)
                                heterogeneity_stats = overall_results_calc['heterogeneity']
                                prediction_interval = overall_results_calc.get('prediction', {})
                                st.session_state.analysis_artifacts["overall_summary_texts"] = {
                                    'analysis_model': analysis_model.capitalize(),
                                    'pooled_es_val': pooled_es_val, 'ci_lower_val': ci_lower_val, 'ci_upper_val': ci_upper_val,
                                    'p_value': overall_results_calc[analysis_model]['p_value'], 'k': overall_results_calc['k'],
                                    'conf_level_percent': conf_level_percent,
                                    'i_squared': heterogeneity_stats['I_squared'], 'q_stat': heterogeneity_stats['Q'],
                                    'df_q': heterogeneity_stats['df'], 'p_value_q': heterogeneity_stats['p_value_Q'],
                                    'tau_squared': heterogeneity_stats['tau_squared'],
                                    'pi_lower': prediction_interval.get('lower', np.nan),
                                    'pi_upper': prediction_interval.get('upper', np.nan)
                                }

                                overall_ai_params = {
                                    'pooled_es': pooled_es_val, 'ci_lower': ci_lower_val, 'ci_upper': ci_upper_val,
                                    'p_value': overall_results_calc[analysis_model]['p_value'], 'k': overall_results_calc['k'],
                                    'i_squared': heterogeneity_stats['I_squared'], 'q': heterogeneity_stats['Q'],
                                    'df': heterogeneity_stats['df'], 'q_p': heterogeneity_stats['p_value_Q'],
                                    'tau_squared': heterogeneity_stats['tau_squared']
                                }
                                st.session_state.analysis_artifacts["ai_texts"]["overall"] = generate_analysis_description(overall_ai_params, analysis_type="overall")

                                forest_fig_obj = create_forest_plot(
                                    df_processed_calc, overall_results_calc, conf_level, analysis_model,
                                    fig_width=fig_width, title_text=title_text_forest, x_label_text=x_label_text_forest,
                                    show_summary_info=show_summary_info_forest, title_fontsize=title_fs, label_fontsize=label_fs,
                                    tick_fontsize=tick_fs, study_fontsize=study_fs, annotation_fontsize=anno_fs,
                                    header_fontsize=header_fs, summary_fontsize=summary_fs, title_style=title_st,
                                    label_style=label_st, study_style=study_st, font_family=selected_font,
                                    study_marker_color=study_col, overall_diamond_color=overall_col, subgroup_diamond_color=subgroup_col,
                                    null_line_color=null_line_col, pooled_line_color=pooled_line_col
                                )
                                img_forest_io = BytesIO()
                                forest_fig_obj.savefig(img_forest_io, format='png', dpi=output_dpi, bbox_inches='tight')
                                st.session_state.analysis_artifacts["overall_forest_plot"] = img_forest_io
                                plt.close(forest_fig_obj)

                                funnel_fig_obj = create_funnel_plot(
                                    df_processed_calc, overall_results_calc, analysis_model,
                                    fig_width=fig_width, fig_height=fig_height_other, title_text=title_text_funnel,
                                    x_label_text=x_label_text_funnel, y_label_text=y_label_text_funnel, show_legend=show_legend_funnel,
                                    legend_fontsize=legend_fs, marker_style=marker_style_funnel, title_fontsize=title_fs,
                                    label_fontsize=label_fs, tick_fontsize=tick_fs, title_style=title_st, label_style=label_st,
                                    font_family=selected_font, point_color=funnel_pt_col, pooled_line_color=funnel_pooled_line_col,
                                    ci_line_color=funnel_ci_col
                                )
                                img_funnel_io = BytesIO()
                                funnel_fig_obj.savefig(img_funnel_io, format='png', dpi=output_dpi, bbox_inches='tight')
                                st.session_state.analysis_artifacts["funnel_plot"] = img_funnel_io
                                plt.close(funnel_fig_obj)

                                eggers_res = overall_results_calc.get("eggers_test", {})
                                eggers_text = "Egger's Test: "
                                if "error" in eggers_res:
                                    eggers_text += eggers_res["error"]
                                elif np.isnan(eggers_res.get("p_value", np.nan)):
                                    eggers_text += "Could not be calculated or insufficient data."
                                else:
                                    eggers_text += (
                                        f"Intercept = {eggers_res['intercept']:.2f} "
                                        f"(SE = {eggers_res['se_intercept']:.2f}), "
                                        f"t = {eggers_res['t_value']:.2f}, "
                                        f"p-value = {eggers_res['p_value']:.3f} "
                                        f"(df={eggers_res.get('df_resid','N/A')})"
                                    )
                                st.session_state.analysis_artifacts["publication_bias_texts"]["eggers_text"] = eggers_text

                                funnel_ai_params = {
                                    'eggers_intercept': eggers_res.get('intercept', 'N/A'),
                                    'eggers_p_value': eggers_res.get('p_value', 'N/A')
                                }
                                st.session_state.analysis_artifacts["ai_texts"]["funnel"] = generate_analysis_description(funnel_ai_params, analysis_type="funnel")

                                predefined_subgroup_vars = ["Strain", "Gender", "Age", "Cancer", "Dosage"]
                                available_subgroup_vars = [
                                    var for var in predefined_subgroup_vars
                                    if var in st.session_state.get('potential_subgroup_cols', []) and df_processed_calc[var].nunique() > 1
                                ]
                                all_subgroup_ai_params_list = []
                                if (heterogeneity_stats['I_squared'] > heterogeneity_threshold_i2 or heterogeneity_stats['p_value_Q'] < heterogeneity_threshold_q) and available_subgroup_vars:
                                    for var in available_subgroup_vars:
                                        sub_res_full = subgroup_analysis(df_processed_calc, var, conf_level)
                                        if not (isinstance(sub_res_full, dict) and "error" in sub_res_full) and sub_res_full is not None:
                                            sub_data = sub_res_full.get("subgroups", {})
                                            sub_test_stats = sub_res_full.get("test", {})
                                            df_list = []
                                            for name, item in sub_data.items():
                                                if isinstance(item, dict) and "error" not in item:
                                                    df_list.append({
                                                        'Subgroup': name, 'k': item.get('k', 'N/A'),
                                                        f'{analysis_model}_SMD': item.get(f'{analysis_model}_es', np.nan),
                                                        f'{analysis_model}_{conf_level_percent}%_CI_L': item.get(f'{analysis_model}_ci', [np.nan, np.nan])[0],
                                                        f'{analysis_model}_{conf_level_percent}%_CI_U': item.get(f'{analysis_model}_ci', [np.nan, np.nan])[1],
                                                        'I² (%)': item.get('I_squared', np.nan)
                                                    })
                                            sub_df = pd.DataFrame(df_list).round(3)

                                            box_fig = create_box_plot(df_processed_calc, 'SMD', var, fig_width=fig_width, fig_height=fig_height_other, title_text=f"{title_text_box} ({var})",palette=boxplot_pal)
                                            img_box_io = BytesIO()
                                            box_fig.savefig(img_box_io, format='png', dpi=output_dpi, bbox_inches='tight')
                                            plt.close(box_fig)

                                            forest_sub_fig = create_forest_plot(df_processed_calc, overall_results_calc, conf_level, analysis_model, subgroup_results=sub_res_full, subgroup_var=var, fig_width=fig_width, title_text=f"{title_text_forest} (Subgroup: {var})")
                                            img_forest_sub_io = BytesIO()
                                            forest_sub_fig.savefig(img_forest_sub_io, format='png', dpi=output_dpi, bbox_inches='tight')
                                            plt.close(forest_sub_fig)

                                            st.session_state.analysis_artifacts["subgroup_details"][var] = {
                                                "table_df": sub_df,
                                                "box_plot": img_box_io,
                                                "forest_plot": img_forest_sub_io,
                                                "test_stats": sub_test_stats
                                            }
                                            if sub_test_stats and np.isfinite(sub_test_stats.get('Q_between', np.nan)):
                                                all_subgroup_ai_params_list.append({
                                                    'subgroup_var': var, 'q_between': sub_test_stats.get('Q_between'),
                                                    'df_between': sub_test_stats.get('df'), 'p_between': sub_test_stats.get('p_value'),
                                                    'subgroup_data_summary': sub_df.to_dict(orient='records')
                                                })
                                if all_subgroup_ai_params_list:
                                    st.session_state.analysis_artifacts["ai_texts"]["all_subgroups"] = generate_analysis_description(
                                        {"subgroup_analyses_results": all_subgroup_ai_params_list}, analysis_type="all_subgroups"
                                    )
                                st.success("✅ All plots and AI interpretations are ready!")

                    except Exception as e:
                        st.error(f"An unexpected error occurred during the analysis or artifact generation: {e}")
                        st.exception(e)
                        st.session_state.analysis_run = False

            # --- Display Results ---
            if st.session_state.get('analysis_run', False):
                overall_results = st.session_state.overall_results
                df_processed = st.session_state.df_processed
                analysis_artifacts_display = st.session_state.analysis_artifacts

                if overall_results is None or df_processed is None:
                    st.warning("Analysis results have not been generated or were lost.")
                else:
                    st.markdown("---")
                    st.header("📊 Overall Results")

                    # --- ADDED: Download All Button ---
                    zip_buffer = create_zip_archive(analysis_artifacts_display, analysis_model)
                    st.download_button(
                        label="📥 Download All Results & Plots (.zip)",
                        data=zip_buffer,
                        file_name=f"metaflow_analysis_results_{analysis_model}.zip",
                        mime="application/zip",
                        help="Download all generated plots and subgroup tables in a single zip file."
                    )
                    # --- END ADDED SECTION ---

                    summary_texts_disp = analysis_artifacts_display.get("overall_summary_texts", {})
                    col1_res, col2_res, col3_res = st.columns(3)
                    with col1_res:
                        st.subheader(f"Pooled Effect Size ({summary_texts_disp.get('analysis_model', 'N/A')})")
                        st.metric(label="Pooled SMD", value=f"{summary_texts_disp.get('pooled_es_val', 0):.3f}")
                        st.write(f"{summary_texts_disp.get('conf_level_percent', 95)}% CI: [{summary_texts_disp.get('ci_lower_val', 0):.3f}, {summary_texts_disp.get('ci_upper_val', 0):.3f}]")
                        st.write(f"P-value: {summary_texts_disp.get('p_value', 0):.4f}")
                        st.write(f"Number of studies (k): {summary_texts_disp.get('k', 'N/A')}")
                    with col2_res:
                        st.subheader("Heterogeneity")
                        st.metric(label="I²", value=f"{summary_texts_disp.get('i_squared', 0):.1f}%")
                        st.write(f"Q: {summary_texts_disp.get('q_stat', 0):.2f} (df={summary_texts_disp.get('df_q', 'N/A')}, p={summary_texts_disp.get('p_value_q', 0):.4f})")
                        st.write(f"Tau² (τ²): {summary_texts_disp.get('tau_squared', 0):.4f} (D-L Method)")
                    with col3_res:
                        st.subheader("Prediction Interval (Random)")
                        if np.isfinite(summary_texts_disp.get('pi_lower', np.nan)):
                            st.write(f"{summary_texts_disp.get('conf_level_percent',95)}% PI: [{summary_texts_disp.get('pi_lower'):.3f}, {summary_texts_disp.get('pi_upper'):.3f}]")
                            st.caption("Predicts the range of effect sizes in future similar studies")
                        else:
                            st.write("Not applicable or could not be calculated")

                    st.markdown("---")
                    st.subheader("💬 AI Interpretation of Overall Results")
                    ai_overall_text = analysis_artifacts_display.get("ai_texts", {}).get("overall", "AI interpretation is generating or unavailable.")
                    if ai_overall_text.startswith("Error:") or ai_overall_text.startswith("AI service"): st.warning(ai_overall_text)
                    else: st.info("AI Overall Analysis Interpretation:"); st.markdown(ai_overall_text)

                    st.markdown("---")
                    st.header("📈 Visualization & Publication Bias Assessment")
                    st.subheader("Forest Plot")
                    if analysis_artifacts_display.get("overall_forest_plot"):
                        st.image(analysis_artifacts_display["overall_forest_plot"], caption="Overall Forest Plot")
                        st.download_button(label="Download Forest Plot", data=analysis_artifacts_display["overall_forest_plot"].getvalue(), file_name=f'forest_plot_{analysis_model}.png', mime="image/png")
                    else: st.warning("Forest plot could not be displayed.")

                    st.subheader("Funnel Plot")
                    if analysis_artifacts_display.get("funnel_plot"):
                        st.image(analysis_artifacts_display["funnel_plot"], caption="Funnel Plot")
                        st.download_button(label="Download Funnel Plot", data=analysis_artifacts_display["funnel_plot"].getvalue(), file_name=f'funnel_plot_{analysis_model}.png', mime="image/png")
                    else: st.warning("Funnel plot could not be displayed.")

                    st.subheader("Egger's Regression Test (Publication Bias)")
                    eggers_display_text = analysis_artifacts_display.get("publication_bias_texts", {}).get("eggers_text", "Egger's test results are unavailable.")
                    st.text(eggers_display_text)


                    st.subheader("💬 AI Interpretation of Funnel Plot & Bias")
                    ai_funnel_text = analysis_artifacts_display.get("ai_texts",{}).get("funnel", "AI interpretation is generating or unavailable.")
                    if ai_funnel_text.startswith("Error:") or ai_funnel_text.startswith("AI service"): st.warning(ai_funnel_text)
                    else: st.info("AI Funnel Plot & Publication Bias Interpretation:"); st.markdown(ai_funnel_text)


                    # --- Conditional Subgroup Analysis Display ---
                    st.markdown("---")
                    st.header("🔬 Subgroup Analysis")
                    heterogeneity_stats_disp = overall_results['heterogeneity']
                    is_heterogeneous_disp = (heterogeneity_stats_disp['I_squared'] > heterogeneity_threshold_i2 or
                                             heterogeneity_stats_disp['p_value_Q'] < heterogeneity_threshold_q)

                    subgroup_details_disp = analysis_artifacts_display.get("subgroup_details", {})
                    if is_heterogeneous_disp and subgroup_details_disp:
                        st.info(f"Significant heterogeneity detected. The following are the available preset subgroup analysis results. Click buttons to view detailed plots for each subgroup.")
                        
                        # --- MODIFIED: Dynamic Show/Hide Button Logic ---
                        for var_name, details in subgroup_details_disp.items():
                            is_visible = st.session_state.show_subgroup_plots.get(var_name, False)
                            button_label = f"➖ Hide '{var_name}' Results" if is_visible else f"➕ Show '{var_name}' Results"
                            
                            if st.button(button_label, key=f"toggle_subgroup_{var_name}"):
                                st.session_state.show_subgroup_plots[var_name] = not is_visible
                                st.rerun()

                            if st.session_state.show_subgroup_plots.get(var_name, False):
                                with st.container(border=True):
                                    st.markdown(f"#### Details for '{var_name}' Subgroup")
                                    if details.get("table_df") is not None:
                                        st.dataframe(details["table_df"])

                                    test_stats_disp = details.get("test_stats", {})
                                    if test_stats_disp and np.isfinite(test_stats_disp.get('Q_between', np.nan)):
                                        st.write(f"**Test for Subgroup Differences:** Q_between = {test_stats_disp['Q_between']:.2f} (df={test_stats_disp.get('df','N/A')}, p={test_stats_disp.get('p_value', np.nan):.4f})")
                                    else:
                                        st.write("Test for Subgroup Differences: Could not be calculated or insufficient subgroups.")

                                    if details.get("box_plot"):
                                        st.image(details["box_plot"], caption=f"'{var_name}' Subgroup Box Plot")
                                        st.download_button(label=f"Download Box Plot ({var_name})", data=details["box_plot"].getvalue(), file_name=f'boxplot_{var_name}.png', mime="image/png", key=f"dl_box_{var_name}")

                                    if details.get("forest_plot"):
                                        st.image(details["forest_plot"], caption=f"Forest Plot with '{var_name}' Subgroups")
                                        st.download_button(label=f"Download Subgroup Forest Plot ({var_name})", data=details["forest_plot"].getvalue(), file_name=f'forest_plot_subgroup_{var_name}.png', mime="image/png", key=f"dl_forest_sub_{var_name}")
                        # --- END MODIFIED SECTION ---

                        ai_all_subgroups_text = analysis_artifacts_display.get("ai_texts",{}).get("all_subgroups")
                        if ai_all_subgroups_text:
                            st.subheader("💬 AI Interpretation of All Subgroup Analyses")
                            if ai_all_subgroups_text.startswith("Error:") or ai_all_subgroups_text.startswith("AI service"): st.warning(ai_all_subgroups_text)
                            else: st.info("AI Comprehensive Subgroup Analysis Interpretation:"); st.markdown(ai_all_subgroups_text)
                        elif is_heterogeneous_disp:
                                st.info("Subgroup analysis was attempted for preset variables, but no results were generated for a comprehensive AI interpretation.")
                    elif is_heterogeneous_disp and not subgroup_details_disp:
                        st.warning("Significant heterogeneity was detected, but none of the predefined subgroup variables could be successfully analyzed or were applicable to the current data.")
                    else:
                        st.write(f"Heterogeneity is low and does not meet the threshold for recommending subgroup analysis. Therefore, automatic subgroup analysis was not performed.")


        else:
            if not (errors or warnings_list):
                st.error("Data validation failed. Please check the uploaded file format and content.")

    except pd.errors.EmptyDataError:
        st.error("Error: The uploaded Excel file is empty or cannot be read. Please check the file's contents.")
    except ValueError as ve:
        st.error(f"A value or format error occurred while processing the Excel file: {ve}.")
    except Exception as e:
        st.error(f"An unexpected error occurred while processing the uploaded file or running the analysis: {e}")
        st.exception(e)
        st.session_state.analysis_run = False

else:
    if st.session_state.get('analysis_run', False):
        st.info("File not uploaded or has been removed. Resetting analysis-related state.")
        # Preserve UI settings
        keys_to_preserve = [key for key in st.session_state.keys() if key.endswith(('_slider', '_select', '_st', '_fs', '_col', '_funnel', '_box', '_forest', '_other', '_dpi', '_rot_box', '_pal_box'))]
        for key in list(st.session_state.keys()):
            if key not in keys_to_preserve:
                del st.session_state[key]
        # Reset analysis state
        st.session_state.analysis_run = False
        st.session_state.uploaded_file_name = None
        st.session_state.analysis_artifacts = {
            "overall_forest_plot": None, "funnel_plot": None,
            "subgroup_details": {}, "ai_texts": {},
            "overall_summary_texts": {}, "publication_bias_texts": {}
        }
        st.session_state.show_subgroup_plots = {}
        st.rerun()
    st.info("☝️ Please upload an Excel data file with the required format to begin the analysis.")

st.markdown("---")
st.caption(
    "MetaFlow Analyzer - For demonstration and educational purposes only. Calculation results may vary slightly from professional statistical software."
    " AI interpretations (Model: deepseek-r1) are for reference only and do not constitute professional advice."
)