import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import matplotlib.patches as patches
import pandas as pd
import matplotlib # Import base matplotlib for font checking (optional)
import warnings

# It is assumed the 'core_logic' module with 'calculate_ci' is in the same directory.
from core_logic import calculate_ci
# Placeholder for calculate_ci if core_logic is not available
# def calculate_ci(mean, se, conf_level):
#     z_score = stats.norm.ppf(1 - (1 - conf_level) / 2)
#     ci_lower = mean - z_score * se
#     ci_upper = mean + z_score * se
#     return ci_lower, ci_upper


# --- Publication-Ready Aesthetics ---
# These defaults are chosen for clarity, professionalism, and suitability for SCI journals.
DEFAULT_TITLE_FONTSIZE = 12
DEFAULT_LABEL_FONTSIZE = 10
DEFAULT_TICK_FONTSIZE = 8
DEFAULT_STUDY_FONTSIZE = 9
DEFAULT_ANNOTATION_FONTSIZE = 8   # For table text
DEFAULT_HEADER_FONTSIZE = 9     # For column headers
DEFAULT_SUMMARY_FONTSIZE = 9      # For summary rows
DEFAULT_LEGEND_FONTSIZE = 9

DEFAULT_TITLE_STYLE = 'Bold'
DEFAULT_LABEL_STYLE = 'Normal'
DEFAULT_STUDY_STYLE = 'Normal'
DEFAULT_FONT_FAMILY = 'sans-serif' # Arial, Helvetica, or similar are standard choices

# Professional Color Scheme (Grayscale-friendly)
DEFAULT_STUDY_COLOR = '#000000'         # Black squares for individual studies
DEFAULT_OVERALL_COLOR = '#000000'       # Black diamond for overall result
DEFAULT_SUBGROUP_COLOR = '#000000'      # Black diamond for subgroup result
DEFAULT_NULL_LINE_COLOR = '#808080'     # Grey for null effect line
DEFAULT_POOLED_LINE_COLOR = '#000000'   # Black for pooled effect line
DEFAULT_FUNNEL_POINT_COLOR = '#000000'
DEFAULT_FUNNEL_MARKER = 'o'
DEFAULT_FUNNEL_CI_COLOR = '#808080'
DEFAULT_BOXPLOT_PALETTE = "Greys_r"     # Reversed gray palette for boxplots
DEFAULT_STRIPPLOT_COLOR = '#404040'     # Dark grey for individual points

# Layout Defaults
DEFAULT_FIG_WIDTH = 12 # Adjusted for a more compact, standard layout
DEFAULT_FIG_HEIGHT = 8
DEFAULT_XTICK_ROTATION = 0
DEFAULT_SHOW_LEGEND = False

# Default Plot Labels
DEFAULT_X_LABEL = "Standardised Mean Difference"
DEFAULT_Y_LABEL = ""
DEFAULT_FOREST_Y_LABEL = "Study"
DEFAULT_FUNNEL_X_LABEL = "Standardized Mean Difference (SMD)"
DEFAULT_FUNNEL_Y_LABEL = "Standard Error (SE)"
DEFAULT_BOX_X_LABEL = "Subgroup"
DEFAULT_BOX_Y_LABEL = "Standardized Mean Difference (SMD)"


def _get_font_properties(style):
    """Helper function to get weight and style from a combined style string."""
    weight = 'normal'
    fontstyle = 'normal'
    if style == 'Bold':
        weight = 'bold'
    elif style == 'Italic':
        fontstyle = 'italic'
    return weight, fontstyle

def _apply_font_settings(element, font_family, fontsize, weight='normal', style='normal', color='black'):
    """Helper to apply font settings to text elements."""
    try:
        element.set_fontfamily(font_family)
        element.set_fontsize(fontsize)
        element.set_fontweight(weight)
        element.set_fontstyle(style)
        if hasattr(element, 'set_color'):
            element.set_color(color)
    except AttributeError:
        warnings.warn(f"Could not apply full font settings to element type: {type(element)}")
    except ValueError:
        try:
            element.set_fontfamily('sans-serif') # Fallback
            element.set_fontsize(fontsize)
            element.set_fontweight(weight)
            element.set_fontstyle(style)
            if hasattr(element, 'set_color'):
                element.set_color(color)
            warnings.warn(f"Font '{font_family}' not found. Using sans-serif.")
        except Exception as e:
            warnings.warn(f"Error applying fallback font settings: {e}")


def create_forest_plot(df_processed, overall_results, conf_level=0.95, model='random',
                       subgroup_results=None, subgroup_var=None,
                       # --- Aesthetics Arguments ---
                       fig_width=DEFAULT_FIG_WIDTH,
                       title_text="Forest Plot of Effect Sizes",
                       x_label_text=DEFAULT_X_LABEL,
                       show_summary_info=True,
                       title_fontsize=DEFAULT_TITLE_FONTSIZE,
                       label_fontsize=DEFAULT_LABEL_FONTSIZE,
                       tick_fontsize=DEFAULT_TICK_FONTSIZE,
                       study_fontsize=DEFAULT_STUDY_FONTSIZE,
                       annotation_fontsize=DEFAULT_ANNOTATION_FONTSIZE,
                       header_fontsize=DEFAULT_HEADER_FONTSIZE,
                       summary_fontsize=DEFAULT_SUMMARY_FONTSIZE,
                       title_style=DEFAULT_TITLE_STYLE,
                       label_style=DEFAULT_LABEL_STYLE,
                       study_style=DEFAULT_STUDY_STYLE,
                       font_family=DEFAULT_FONT_FAMILY,
                       study_marker_color=DEFAULT_STUDY_COLOR,
                       overall_diamond_color=DEFAULT_OVERALL_COLOR,
                       subgroup_diamond_color=DEFAULT_SUBGROUP_COLOR,
                       null_line_color=DEFAULT_NULL_LINE_COLOR,
                       pooled_line_color=DEFAULT_POOLED_LINE_COLOR
                       ):
    """
    Creates a publication-quality forest plot using Matplotlib.
    This version is optimized for SCI journal standards, featuring a clean layout,
    professional color scheme, and clear typography.
    """
    if subgroup_results and subgroup_var:
        title_text = f"Forest Plot by Subgroup: {subgroup_var}"

    valid_indices = overall_results.get('valid_indices', np.ones(len(df_processed), dtype=bool))
    df_display = df_processed.loc[valid_indices].copy() if valid_indices.any() else pd.DataFrame(columns=df_processed.columns)

    if df_display.empty:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "No valid studies to display.", ha='center', va='center', fontfamily=font_family)
        return fig

    # --- Data Preparation ---
    pooled_es = overall_results[model]['pooled_es']
    pooled_se = overall_results[model]['se']
    pooled_ci_lower, pooled_ci_upper = calculate_ci(pooled_es, pooled_se, conf_level)
    pooled_weight = 100.0

    weights_col_name = 'weights_random' if model == 'random' else 'weights_fixed'
    weights_full = overall_results.get(weights_col_name, np.ones(len(df_processed)))
    weights = weights_full[valid_indices]
    
    relative_weights = weights / np.nansum(weights) * 100 if np.nansum(weights) > 0 else np.zeros_like(weights)
    df_display['Weight'] = relative_weights
    
    z_score = stats.norm.ppf(1 - (1 - conf_level) / 2)
    df_display['CI_lower'] = df_display['SMD'] - z_score * df_display['SE']
    df_display['CI_upper'] = df_display['SMD'] + z_score * df_display['SE']

    # --- Subgroup Data Preparation ---
    subgroup_data = {}
    if subgroup_results and subgroup_var and 'subgroups' in subgroup_results and subgroup_var in df_display.columns:
        for group_name, group_df in df_display.groupby(subgroup_var):
            group_name_str = str(group_name)
            if group_name_str in subgroup_results['subgroups']:
                subgroup_data[group_name_str] = {
                    'df': group_df,
                    'results': subgroup_results['subgroups'][group_name_str]
                }

    # --- Layout Calculations ---
    num_studies = len(df_display)
    total_rows = num_studies + 2 # Studies + overall summary + header buffer
    if subgroup_data:
        total_rows += len(subgroup_data) * 2 # Add space for subgroup headers and summaries

    row_height = 0.35
    fig_height = max(5, total_rows * row_height)
    fig = plt.figure(figsize=(fig_width, fig_height))

    # Define plot and column positions (figure coordinates 0-1)
    plot_area_x_start = 0.52
    plot_area_x_end = 0.75
    text_area_y_bottom = 0.10
    text_area_y_top = 0.90
    
    ax = fig.add_axes([plot_area_x_start, text_area_y_bottom, plot_area_x_end - plot_area_x_start, text_area_y_top - text_area_y_bottom])
    
    col_pos = {
        "study": 0.02, "n_ctrl": 0.18, "mean_ctrl": 0.24, "sd_ctrl": 0.30,
        "n_ir": 0.36, "mean_ir": 0.42, "sd_ir": 0.48,
        "plot_start": plot_area_x_start, "plot_end": plot_area_x_end,
        "smd_ci": 0.85, "weight": 0.98
    }

    # --- Plot Area Setup ---
    all_cis = np.concatenate([df_display[['CI_lower', 'CI_upper']].values.flatten(), [pooled_ci_lower, pooled_ci_upper]])
    valid_cis = all_cis[np.isfinite(all_cis)]
    if len(valid_cis) > 0:
        data_range = max(valid_cis) - min(valid_cis)
        plot_min = min(valid_cis) - data_range * 0.15
        plot_max = max(valid_cis) + data_range * 0.15
    else:
        plot_min, plot_max = -2, 2
        
    ax.set_xlim(plot_min, plot_max)
    ax.set_ylim(-2, total_rows) # Y-axis data coordinates
    
    # Clean up plot aesthetics
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('black')
    ax.spines['bottom'].set_linewidth(0.8)
    ax.tick_params(axis='x', which='major', direction='in', length=4, width=0.8, colors='black')

    # Coordinate transformation for placing text
    ax_bbox = ax.get_position()
    def get_fig_y(data_y):
        ymin, ymax = ax.get_ylim()
        return ax_bbox.y0 + ((data_y - ymin) / (ymax - ymin)) * ax_bbox.height

    # --- Draw Vertical Lines ---
    y_min_norm, y_max_norm = (ax.get_ylim()[0] + 0.5) / ax.get_ylim()[1], 0.98
    ax.axvline(0, ymin=y_min_norm, ymax=y_max_norm, color=null_line_color, linestyle='--', linewidth=1, zorder=0)
    if np.isfinite(pooled_es):
        ax.axvline(pooled_es, ymin=y_min_norm, ymax=y_max_norm, color=pooled_line_color, linestyle=':', linewidth=1, alpha=0.9, zorder=0)

    # --- Draw Headers ---
    header_y_data = total_rows - 0.5
    header_y_fig = get_fig_y(header_y_data)
    group_header_y_fig = get_fig_y(header_y_data - 0.7)
    header_weight, header_style = 'bold', 'normal'

    fig.text(col_pos["study"], header_y_fig, "Study", ha='left', va='center', fontsize=header_fontsize, weight=header_weight, fontfamily=font_family)
    fig.text((col_pos["n_ctrl"] + col_pos["sd_ctrl"]) / 2, group_header_y_fig, "Control", ha='center', va='center', fontsize=header_fontsize, weight=header_weight, fontfamily=font_family)
    fig.text((col_pos["n_ir"] + col_pos["sd_ir"]) / 2, group_header_y_fig, "IR", ha='center', va='center', fontsize=header_fontsize, weight=header_weight, fontfamily=font_family)
    
    for x, label in [(col_pos["n_ctrl"], "N"), (col_pos["mean_ctrl"], "Mean"), (col_pos["sd_ctrl"], "SD"),
                     (col_pos["n_ir"], "N"), (col_pos["mean_ir"], "Mean"), (col_pos["sd_ir"], "SD")]:
        fig.text(x, header_y_fig, label, ha='center', va='center', fontsize=header_fontsize, weight=header_weight, fontfamily=font_family)

    fig.text((plot_area_x_start + plot_area_x_end)/2, header_y_fig, "SMD [95% CI]", ha='center', va='center', fontsize=header_fontsize, weight=header_weight, fontfamily=font_family)
    fig.text(col_pos["weight"], header_y_fig, "Weight(%)", ha='right', va='center', fontsize=header_fontsize, weight=header_weight, fontfamily=font_family)
    
    # --- Draw Main Content (Studies and Summaries) ---
    current_y = header_y_data - 2
    study_weight, study_fontstyle = _get_font_properties(study_style)

    def plot_row(y, row_data, is_summary=False, diamond_color=None):
        y_fig = get_fig_y(y)
        
        # Text alignment and formatting
        text_weight = 'bold' if is_summary else study_weight
        text_style = 'italic' if is_summary else study_fontstyle
        
        # Study name or summary label
        study_label = f"  {row_data['study']}" if not is_summary else row_data['study']
        fig.text(col_pos["study"], y_fig, study_label, ha='left', va='center', fontsize=study_fontsize, weight=text_weight, style=text_style, fontfamily=font_family)

        # Numerical data
        if not is_summary:
            fig.text(col_pos["n_ctrl"], y_fig, f"{int(row_data['Sample_ctrl'])}" if pd.notna(row_data['Sample_ctrl']) else "-", ha='center', va='center', fontsize=annotation_fontsize, fontfamily=font_family)
            fig.text(col_pos["mean_ctrl"], y_fig, f"{row_data['Ctrl']:.2f}" if pd.notna(row_data['Ctrl']) else "-", ha='center', va='center', fontsize=annotation_fontsize, fontfamily=font_family)
            fig.text(col_pos["sd_ctrl"], y_fig, f"{row_data['Ctrl_SD']:.2f}" if pd.notna(row_data['Ctrl_SD']) else "-", ha='center', va='center', fontsize=annotation_fontsize, fontfamily=font_family)
            fig.text(col_pos["n_ir"], y_fig, f"{int(row_data['Sample_rt'])}" if pd.notna(row_data['Sample_rt']) else "-", ha='center', va='center', fontsize=annotation_fontsize, fontfamily=font_family)
            fig.text(col_pos["mean_ir"], y_fig, f"{row_data['RT']:.2f}" if pd.notna(row_data['RT']) else "-", ha='center', va='center', fontsize=annotation_fontsize, fontfamily=font_family)
            fig.text(col_pos["sd_ir"], y_fig, f"{row_data['RT_SD']:.2f}" if pd.notna(row_data['RT_SD']) else "-", ha='center', va='center', fontsize=annotation_fontsize, fontfamily=font_family)
        
        # SMD, CI, and Weight
        smd_ci_text = f"{row_data['SMD']:.2f} [{row_data['CI_lower']:.2f}, {row_data['CI_upper']:.2f}]"
        fig.text(col_pos["smd_ci"], y_fig, smd_ci_text, ha='center', va='center', fontsize=annotation_fontsize, weight=text_weight, fontfamily=font_family)
        fig.text(col_pos["weight"], y_fig, f"{row_data['Weight']:.1f}", ha='right', va='center', fontsize=annotation_fontsize, weight=text_weight, fontfamily=font_family)
        
        # Plotting - Square for study, Diamond for summary
        if is_summary:
            diamond_half_width = (row_data['CI_upper'] - row_data['CI_lower']) / 2
            if np.isfinite(diamond_half_width) and diamond_half_width > 0:
                diamond = patches.Polygon([
                    (row_data['SMD'] - diamond_half_width, y), (row_data['SMD'], y + 0.4),
                    (row_data['SMD'] + diamond_half_width, y), (row_data['SMD'], y - 0.4)
                ], closed=True, color=diamond_color, zorder=3)
                ax.add_patch(diamond)
        else:
            if np.isfinite(row_data['CI_lower']) and np.isfinite(row_data['CI_upper']):
                ax.plot([row_data['CI_lower'], row_data['CI_upper']], [y, y], color=study_marker_color, linewidth=1, zorder=1)
            min_marker, max_marker = 4, 10
            marker_size = min_marker + (max_marker - min_marker) * (row_data['Weight'] / 100.0) if np.isfinite(row_data['Weight']) else min_marker
            ax.plot(row_data['SMD'], y, marker='s', color=study_marker_color, markersize=marker_size, zorder=2)
            
    # --- Loop through subgroups or all studies ---
    if subgroup_data:
        for group_name, data in subgroup_data.items():
            current_y -= 0.5
            fig.text(col_pos["study"], get_fig_y(current_y), f"{group_name}", ha='left', va='center', fontsize=summary_fontsize, weight='bold', fontfamily=font_family)
            current_y -= 1
            
            for _, row in data['df'].iterrows():
                plot_row(current_y, row)
                current_y -= 1
            
            group_results = data['results']
            if "error" not in group_results:
                sub_es = group_results[f'{model}_es']
                sub_ci = group_results[f'{model}_ci']
                sub_weight = data['df']['Weight'].sum()
                summary_data = {'study': '  Subgroup summary', 'SMD': sub_es, 'CI_lower': sub_ci[0], 'CI_upper': sub_ci[1], 'Weight': sub_weight}
                plot_row(current_y, summary_data, is_summary=True, diamond_color=subgroup_diamond_color)
                
                i_sq = group_results.get('I_squared', np.nan)
                p_q = 1 - stats.chi2.cdf(group_results.get('Q_within', np.nan), group_results.get('df_within', np.nan))
                hetero_text = f"$I^2$ = {i_sq:.1f}%, p = {p_q:.3f}"
                fig.text(col_pos["smd_ci"], get_fig_y(current_y - 0.9), hetero_text, ha='center', va='center', style='italic', fontsize=annotation_fontsize, fontfamily=font_family)
                current_y -= 1.5

    else: # No subgroups
        for i, row in df_display.iterrows():
            plot_row(current_y, row)
            current_y -= 1

    # --- Plot Overall Summary ---
    current_y -= 1
    overall_summary_data = {'study': f"Overall ({model.capitalize()})", 'SMD': pooled_es, 'CI_lower': pooled_ci_lower, 'CI_upper': pooled_ci_upper, 'Weight': pooled_weight}
    plot_row(current_y, overall_summary_data, is_summary=True, diamond_color=overall_diamond_color)

    # --- Final Formatting ---
    label_weight, label_style = _get_font_properties(label_style)
    ax.set_xlabel(x_label_text, fontsize=label_fontsize, weight=label_weight, style=label_style, fontfamily=font_family)
    for label in ax.get_xticklabels():
        _apply_font_settings(label, font_family, tick_fontsize, color='black')

    title_weight, title_style = _get_font_properties(title_style)
    fig.suptitle(title_text, fontsize=title_fontsize, weight=title_weight, style=title_style, fontfamily=font_family, y=text_area_y_top + 0.05)

    if show_summary_info:
        summary_y_fig = text_area_y_bottom - 0.08
        i2 = overall_results['heterogeneity']['I_squared']
        tau2 = overall_results['heterogeneity']['tau_squared']
        q_pval = overall_results['heterogeneity']['p_value_Q']
        summary_text = f"Heterogeneity: $I^2$ = {i2:.1f}%, $\\tau^2$ = {tau2:.3f}, p(Q) = {q_pval:.3f}"
        fig.text(plot_area_x_start, summary_y_fig, summary_text, ha='left', va='top', fontsize=summary_fontsize, fontfamily=font_family)

    if subgroup_results and 'test' in subgroup_results:
        q_b, df_b, p_b = subgroup_results['test']['Q_between'], subgroup_results['test']['df'], subgroup_results['test']['p_value']
        test_text = f"Test for subgroup differences: Q = {q_b:.2f}, df = {df_b}, p = {p_b:.3f}"
        fig.text(col_pos["study"], get_fig_y(current_y - 1.5), test_text, ha='left', va='center', fontsize=summary_fontsize, style='italic', fontfamily=font_family)

    fig.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.15)
    return fig


def create_funnel_plot(df_processed, overall_results, model='random',
                       fig_width=8, fig_height=6, # Adjusted for standard aspect ratio
                       title_text="Funnel Plot", x_label_text=DEFAULT_FUNNEL_X_LABEL,
                       y_label_text=DEFAULT_FUNNEL_Y_LABEL, show_legend=DEFAULT_SHOW_LEGEND,
                       legend_fontsize=DEFAULT_LEGEND_FONTSIZE, marker_style=DEFAULT_FUNNEL_MARKER,
                       title_fontsize=DEFAULT_TITLE_FONTSIZE, label_fontsize=DEFAULT_LABEL_FONTSIZE,
                       tick_fontsize=DEFAULT_TICK_FONTSIZE, title_style=DEFAULT_TITLE_STYLE,
                       label_style=DEFAULT_LABEL_STYLE, font_family=DEFAULT_FONT_FAMILY,
                       point_color=DEFAULT_FUNNEL_POINT_COLOR, pooled_line_color=DEFAULT_POOLED_LINE_COLOR,
                       ci_line_color=DEFAULT_FUNNEL_CI_COLOR):
    """
    Creates a publication-quality funnel plot.
    """
    valid_indices = overall_results.get('valid_indices', np.ones(len(df_processed), dtype=bool))
    df_display = df_processed.loc[valid_indices].copy() if valid_indices.any() else pd.DataFrame(columns=df_processed.columns)
    
    if df_display.empty or 'SMD' not in df_display.columns or 'SE' not in df_display.columns:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No valid data for funnel plot.", ha='center', va='center', fontfamily=font_family)
        return fig

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    pooled_es = overall_results[model]['pooled_es']
    se, effect_sizes = df_display['SE'], df_display['SMD']

    valid_plot_mask = np.isfinite(effect_sizes) & np.isfinite(se) & (se > 0)
    if not valid_plot_mask.any():
        ax.text(0.5, 0.5, "No valid studies with SE > 0.", ha='center', va='center')
        return fig

    # Plot individual studies (hollow circles for better overlap visibility)
    ax.scatter(effect_sizes[valid_plot_mask], se[valid_plot_mask], facecolors='none',
               edgecolors=point_color, marker=marker_style, label='Studies')

    # Plot pooled effect and confidence interval lines
    if np.isfinite(pooled_es):
        ax.axvline(pooled_es, color=pooled_line_color, linestyle='-', linewidth=1.2, label=f'Pooled SMD ({model.capitalize()})')
        se_max = se[valid_plot_mask].max() * 1.1
        se_range = np.linspace(0, se_max, 100)
        upper_ci = pooled_es + 1.96 * se_range
        lower_ci = pooled_es - 1.96 * se_range
        ax.plot(upper_ci, se_range, color=ci_line_color, linestyle='--', linewidth=1, label='Expected 95% CI')
        ax.plot(lower_ci, se_range, color=ci_line_color, linestyle='--', linewidth=1)

    # --- Formatting and Aesthetics ---
    ax.invert_yaxis()
    label_weight, label_style = _get_font_properties(label_style)
    ax.set_xlabel(x_label_text, fontsize=label_fontsize, weight=label_weight, style=label_style, fontfamily=font_family)
    ax.set_ylabel(y_label_text, fontsize=label_fontsize, weight=label_weight, style=label_style, fontfamily=font_family)
    
    # Clean up spines and ticks
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('black')
    ax.spines['left'].set_linewidth(0.8)
    ax.spines['bottom'].set_color('black')
    ax.spines['bottom'].set_linewidth(0.8)
    ax.tick_params(colors='black', width=0.8, length=4)

    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        _apply_font_settings(label, font_family, tick_fontsize)

    if show_legend:
        ax.legend(prop={'family': font_family, 'size': legend_fontsize}, frameon=False)
        
    title_weight, title_style = _get_font_properties(title_style)
    plt.title(title_text, fontsize=title_fontsize, weight=title_weight, style=title_style, fontfamily=font_family)
    plt.tight_layout()
    return fig


def create_box_plot(df, effect_size_col, subgroup_var,
                      fig_width=8, fig_height=6, # Adjusted for standard aspect ratio
                      title_text="Subgroup Analysis", x_label_text=DEFAULT_BOX_X_LABEL,
                      y_label_text=DEFAULT_BOX_Y_LABEL, xtick_rotation=DEFAULT_XTICK_ROTATION,
                      title_fontsize=DEFAULT_TITLE_FONTSIZE, label_fontsize=DEFAULT_LABEL_FONTSIZE,
                      tick_fontsize=DEFAULT_TICK_FONTSIZE, title_style=DEFAULT_TITLE_STYLE,
                      label_style=DEFAULT_LABEL_STYLE, font_family=DEFAULT_FONT_FAMILY,
                      palette=DEFAULT_BOXPLOT_PALETTE, point_color=DEFAULT_STRIPPLOT_COLOR):
    """
    Creates a publication-quality box plot for subgroup analysis using Seaborn.
    """
    if x_label_text == DEFAULT_BOX_X_LABEL:
        x_label_text = subgroup_var # Use the variable name as default label

    df_plot = df.dropna(subset=[effect_size_col, subgroup_var])
    if df_plot.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, f"No data for {effect_size_col} by {subgroup_var}.", ha='center', va='center')
        return fig

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    try:
        import seaborn as sns
        sns.boxplot(x=subgroup_var, y=effect_size_col, data=df_plot, ax=ax,
                    palette=palette, showfliers=False,
                    boxprops=dict(edgecolor='black', linewidth=1),
                    whiskerprops=dict(color='black', linewidth=1),
                    capprops=dict(color='black', linewidth=1),
                    medianprops=dict(color='red', linewidth=1.5)) # Red median for emphasis
        sns.stripplot(x=subgroup_var, y=effect_size_col, data=df_plot, ax=ax,
                      color=point_color, size=5, alpha=0.6, jitter=True)
        sns.despine() # Remove top and right spines
    except ImportError:
        warnings.warn("Seaborn not found. Using Matplotlib for boxplot. Aesthetics may differ.")
        df_plot.boxplot(column=effect_size_col, by=subgroup_var, ax=ax, grid=False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    label_weight, label_style = _get_font_properties(label_style)
    ax.set_xlabel(x_label_text, fontsize=label_fontsize, weight=label_weight, style=label_style, fontfamily=font_family)
    ax.set_ylabel(y_label_text, fontsize=label_fontsize, weight=label_weight, style=label_style, fontfamily=font_family)
    
    ax.tick_params(colors='black', width=0.8, length=4)
    for label in ax.get_xticklabels():
        _apply_font_settings(label, font_family, tick_fontsize)
        label.set_rotation(xtick_rotation)
        if xtick_rotation > 0: label.set_ha('right')
    for label in ax.get_yticklabels():
        _apply_font_settings(label, font_family, tick_fontsize)

    plt.suptitle('') # Remove default suptitle from pandas boxplot
    title_weight, title_style = _get_font_properties(title_style)
    plt.title(title_text, fontsize=title_fontsize, weight=title_weight, style=title_style, fontfamily=font_family)
    plt.tight_layout()
    return fig