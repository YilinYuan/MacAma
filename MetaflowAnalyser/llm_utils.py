import os
import json
from typing import Dict, Any, Optional
import numpy as np
from openai import OpenAI, APIConnectionError, AuthenticationError, APIStatusError

# It's good practice to define the model name as a constant if it's fixed
DEFAULT_AI_MODEL = "deepseek-r1" # 假设这是您选择的模型

# 添加示例数据作为参考
EXAMPLE_META_ANALYSIS = """对于CD8+ T细胞比例的Meta分析（纳入15项研究，共850个样本）显示，超声治疗显著增加了肿瘤组织中的CD8+ T细胞比例（标准化均数差 SMD = 0.75, 95% CI [0.55, 0.95], p < 0.001; I² = 65%）。对于Treg细胞比例的Meta分析（纳入12项研究）显示，超声治疗有降低趋势，但不显著（SMD = -0.20, 95% CI [-0.45, 0.05], p = 0.12; I² = 72%）。"""

# 旧的 EXAMPLE_SUBGROUP_ANALYSIS (单个亚组变量的概要) - 保留以防直接调用，但主要使用新的 all_subgroups 示例
EXAMPLE_SUBGROUP_ANALYSIS = """亚组分析显示，HIFU对CD8+ T细胞的提升效果在黑色素瘤模型中更为显著（SMD = 0.90）相较于其他肿瘤类型（SMD = 0.60）。在低强度超声亚组中，异质性显著降低（I² = 25%）。"""

EXAMPLE_FUNNEL_ANALYSIS = """漏斗图显示轻微不对称。Egger's检验截距为1.52 (p = 0.08)，提示可能存在发表偏倚（边界显著性）。综合来看，结果的稳健性可能受到一定影响，需谨慎解读。未来如进行Trim-and-fill分析可进一步评估此偏倚的影响程度。"""

# 更新后的 EXAMPLE_ALL_SUBGROUPS_ANALYSIS，包含各类别具体效应量和解读
EXAMPLE_ALL_SUBGROUPS_ANALYSIS = """
对预设的多个亚组变量进行了分析，结果如下：

**1. 基于“年龄”的亚组分析：**
   - 组间异质性检验结果：Q_between = 5.2, df = 1, p = 0.02。这表明不同年龄组间的效应量存在统计学上的显著差异，“年龄”可能解释了部分研究间的异质性。
   - 各年龄组具体效应：
     - **年轻组 (Young)**: 共纳入5项研究，合并SMD为 0.85 (95% CI [0.60, 1.10])，显示出较强的正向效应。该亚组内异质性为 I² = 30.0%。解读：年轻组的干预效果显著且效应量较大。
     - **年老组 (Old)**: 共纳入7项研究，合并SMD为 0.40 (95% CI [0.15, 0.65])，显示出中等强度的正向效应。该亚组内异质性为 I² = 10.5%。解读：年老组的干预效果同样显著，但效应量低于年轻组。
   - 该亚组变量小结：年龄是效应量的一个重要调节因素，年轻患者群体的治疗效果似乎更为显著。

**2. 基于“剂量”的亚组分析：**
   - 组间异质性检验结果：Q_between = 1.5, df = 2, p = 0.45。这表明不同剂量水平间的效应量未发现统计学上的显著差异，“剂量”在本分析中未能解释研究间的异质性。
   - 各剂量组具体效应：
     - **低剂量组 (Low)**: 共纳入4项研究，合并SMD为 0.60 (95% CI [0.30, 0.90])，显示正向效应。该亚组内无异质性 (I² = 0.0%)。解读：低剂量组显示出统计学上显著的积极效果。
     - **中剂量组 (Medium)**: 共纳入5项研究，合并SMD为 0.65 (95% CI [0.40, 0.90])，显示正向效应。该亚组内异质性为 I² = 22.0%。解读：中剂量组同样显示出统计学上显著的积极效果，效应量与低剂量组相似。
     - **高剂量组 (High)**: 共纳入3项研究，合并SMD为 0.55 (95% CI [0.20, 0.90])，显示正向效应。该亚组内异质性为 I² = 45.0%。解读：高剂量组也显示出积极效果，但效应量略低于中低剂量组，且组内异质性相对较高。
   - 该亚组变量小结：不同剂量水平的效应量相似，均显示正向效应，未观察到明显的剂量依赖关系。

**3. 基于“癌症类型”的亚组分析（以IFNγ为例）：**
   - 组间异质性检验结果：Q_between = 6.3682, df = 3, p值 = 0.095。这表明不同癌症类型间的效应量差异接近统计学显著性界限 (p < 0.10)，提示“癌症类型”可能部分解释了研究间的异质性。
   - 各癌症类型具体效应：
     - **结肠癌 (Colon)**: 共纳入6项研究，合并SMD为 1.231 (95% CI [0.430, 2.032])，显示出强的正向效应。该亚组内异质性为 I² = 57.967%。解读：在结肠癌模型中，干预措施对IFNγ的提升效应非常显著且效应量大。
     - **肺癌 (Lung)**: 共纳入11项研究，合并SMD为 0.185 (95% CI [-0.343, 0.713])，效应不显著，置信区间跨越0。该亚组内异质性为 I² = 20.550%。解读：在肺癌模型中，当前数据显示干预措施对IFNγ的提升效应不明显。
     - **黑色素瘤 (Melanoma)**: 共纳入11项研究，合并SMD为 0.795 (95% CI [0.198, 1.392])，显示出中等偏强的正向效应。该亚组内异质性为 I² = 55.799%。解读：在黑色素瘤模型中，干预效果显著。
     - **头颈癌 (head and neck)**: 共纳入2项研究，合并SMD为 0.656 (95% CI [-0.058, 1.371])，效应不显著，置信区间跨越0。该亚组内无异质性 (I² = 0.0%)。解读：头颈癌亚组由于研究数量过少（k=2），结果不确定性大，尚不能得出明确结论。
   - 该亚组变量小结：不同癌症类型间的效应量存在一些差异，结肠癌和黑色素瘤亚组观察到较强的正向效应，而肺癌亚组效应不明显。癌症类型可能是一个效应修饰因素，但头颈癌的数据不足。

**综合结论：**
在本次分析中，“年龄”是唯一在统计学上显著调节治疗效果的亚组因素，年轻患者的效应量更高。 “剂量”未能解释研究间的异质性，不同剂量水平效应相似。“癌症类型”对效应量的影响接近显著，结肠癌和黑色素瘤亚组观察到的效应更强，值得进一步研究。这些亚组分析有助于理解效应量变异的潜在来源，并为后续研究或临床决策提供线索。
"""


def generate_analysis_description(
    analysis_results: Dict[str, Any],
    analysis_type: str = "overall",
    subgroup_var: Optional[str] = None, 
    model_name_for_columns: str = "random", 
    conf_level_percent_for_columns: int = 95, 
    model: str = DEFAULT_AI_MODEL
) -> str:
    """
    Calls the large language model API to generate a description of the analysis results.
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        return "错误：未在环境变量中配置DASHSCOPE_API_KEY，无法生成AI分析描述。"

    prompt = "" 

    if analysis_type == "overall":
        prompt = f"""
        作为一名专业的Meta分析专家，请根据以下Meta分析结果提供简明扼要的解释和建议：

        合并效应量 (SMD): {analysis_results.get('pooled_es', 'N/A')}
        {conf_level_percent_for_columns}% 置信区间: [{analysis_results.get('ci_lower', 'N/A')}, {analysis_results.get('ci_upper', 'N/A')}]
        P值: {analysis_results.get('p_value', 'N/A')}
        研究数量(k): {analysis_results.get('k', 'N/A')}
        异质性I²: {analysis_results.get('i_squared', 'N/A')}%
        Q统计量: {analysis_results.get('q', 'N/A')} (df={analysis_results.get('df', 'N/A')}, p={analysis_results.get('q_p', 'N/A')})
        Tau²: {analysis_results.get('tau_squared', 'N/A')}

        请参考以下格式给出回答：
        "{EXAMPLE_META_ANALYSIS}"
        
        请根据上述数据，使用类似的格式，提供一个简洁明了的Meta分析结果解释，包括：
        1. 纳入研究数量和样本量（如果有）
        2. 效应量大小、方向和统计显著性 (使用提供的置信水平)。
        3. 异质性评估及其影响。
        4. 对研究问题的结论性意见。

        回答应当简洁明了，逻辑清晰，语言专业，不超过300字。
        """
    elif analysis_type == "subgroup": 
        prompt = f"""
        作为一名专业的Meta分析专家，请根据以下针对变量 '{subgroup_var}' 的亚组分析结果提供简明扼要的解释和建议：

        亚组变量: {subgroup_var}
        组间异质性检验Q统计量 (Q_between): {analysis_results.get('q_between', 'N/A')}
        组间异质性检验自由度 (df_between): {analysis_results.get('df_between', 'N/A')}
        组间异质性检验P值 (p_between): {analysis_results.get('p_between', 'N/A')}

        请参考以下格式给出回答：
        "{EXAMPLE_SUBGROUP_ANALYSIS}"
        
        请根据上述数据，使用类似的格式，提供一个简洁明了的亚组分析结果解释，包括：
        1. 明确指出基于P值，亚组间是否存在统计学上显著的差异。
        2. 讨论 '{subgroup_var}' 这个变量是否能够解释研究间的部分异质性。
        3. 不同亚组的效应量差异及其可能的临床或实践意义。

        回答应当简洁明了，逻辑清晰，语言专业，不超过300字。
        """
    elif analysis_type == "funnel":
        prompt = f"""
        作为一名专业的Meta分析专家，请对提供的漏斗图进行解读，并结合Egger's检验结果。
        漏斗图主要用于评估研究间可能存在的发表偏倚或系统性异质性。
        Egger's检验结果:
        - Intercept: {analysis_results.get('eggers_intercept', 'N/A')}
        - P-value: {analysis_results.get('eggers_p_value', 'N/A')}

        请描述：
        1. 漏斗图的视觉对称性：点是否大致对称分布在合并效应量周围？是否存在明显的不对称（例如，图形一侧底部缺失研究点）？
        2. 基于Egger's检验的P值，是否存在统计学上显著的发表偏倚迹象？（通常P值 < 0.10 或 < 0.05 被认为可能提示偏倚）
        3. 综合漏斗图的视觉评估和Egger's检验结果，对发表偏倚的风险给出判断。
        4. （如果未来提供Trim-and-fill结果，请在此处添加解读）

        请参考以下示例格式：
        "{EXAMPLE_FUNNEL_ANALYSIS}"

        请提供一个简洁明了的漏斗图和发表偏倚解读。
        回答应当简洁明了，逻辑清晰，语言专业，不超过250字。
        """
    elif analysis_type == "all_subgroups":
        subgroup_details_for_prompt_list = []
        results_list = analysis_results.get("subgroup_analyses_results", [])
        if not results_list:
            return "错误：未提供有效的亚组分析结果供AI解读。"

        for res_idx, res_item in enumerate(results_list):
            var_name = res_item.get('subgroup_var', f'未知变量_{res_idx+1}')
            q_b_val = res_item.get('q_between') # Keep as number for formatting
            p_b_val = res_item.get('p_between') # Keep as number for formatting
            df_b_val = res_item.get('df_between') # Keep as number for formatting
            
            q_b_str = f"{q_b_val:.4f}" if isinstance(q_b_val, (int, float)) and np.isfinite(q_b_val) else "N/A"
            p_b_str = f"{p_b_val:.4f}" if isinstance(p_b_val, (int, float)) and np.isfinite(p_b_val) else "N/A"
            df_b_str = str(int(df_b_val)) if isinstance(df_b_val, (int, float)) and np.isfinite(df_b_val) else "N/A"


            categories_summary_list = []
            for cat_data in res_item.get('subgroup_data_summary', []):
                cat_name = cat_data.get('Subgroup', '未知类别')
                cat_k = cat_data.get('k', 'N/A')
                
                smd_col_name = f"{model_name_for_columns}_SMD"
                ci_l_col_name = f"{model_name_for_columns}_{conf_level_percent_for_columns}%_CI_L"
                ci_u_col_name = f"{model_name_for_columns}_{conf_level_percent_for_columns}%_CI_U"
                i2_col_name = "I² (%)" 

                cat_smd_val = cat_data.get(smd_col_name)
                cat_ci_l_val = cat_data.get(ci_l_col_name)
                cat_ci_u_val = cat_data.get(ci_u_col_name)
                cat_i2_val = cat_data.get(i2_col_name)

                cat_smd_str = f"{cat_smd_val:.3f}" if isinstance(cat_smd_val, (int, float)) and np.isfinite(cat_smd_val) else "N/A"
                cat_ci_l_str = f"{cat_ci_l_val:.3f}" if isinstance(cat_ci_l_val, (int, float)) and np.isfinite(cat_ci_l_val) else "N/A"
                cat_ci_u_str = f"{cat_ci_u_val:.3f}" if isinstance(cat_ci_u_val, (int, float)) and np.isfinite(cat_ci_u_val) else "N/A"
                cat_i2_str = f"{cat_i2_val:.1f}" if isinstance(cat_i2_val, (int, float)) and np.isfinite(cat_i2_val) else "N/A"
                
                ci_str = f"[{cat_ci_l_str}, {cat_ci_u_str}]" if cat_ci_l_str != 'N/A' and cat_ci_u_str != 'N/A' else "N/A"
                categories_summary_list.append(
                    f"  - **{cat_name}**: k={cat_k}, 合并SMD={cat_smd_str} ({conf_level_percent_for_columns}% CI {ci_str}), 组内I²={cat_i2_str}%"
                )
            categories_details_str = "\n".join(categories_summary_list)

            subgroup_details_for_prompt_list.append(
                f"**亚组变量 '{var_name}':**\n" # Made subgroup variable bold
                f"  组间异质性: Q_between={q_b_str}, df={df_b_str}, p值={p_b_str}\n"
                f"  各类别详情:\n{categories_details_str}"
            )
        
        all_subgroup_details_str = "\n\n".join(subgroup_details_for_prompt_list)

        prompt = f"""
        作为一名专业的Meta分析专家，请根据以下对多个预定义变量进行的亚组分析结果，提供一个详细且有条理的解释。
        Meta分析的目的是探讨这些变量是否能解释研究间的异质性，并了解不同亚组类别内的具体效应。

        以下是各亚组变量的分析详情：
        ---
        {all_subgroup_details_str}
        ---

        请参考以下综合亚组分析示例的格式和深度。您的回答需要针对上面“各亚组变量的分析详情”中提供的所有数据进行解读，确保覆盖每一个亚组变量及其下的所有类别：
        "{EXAMPLE_ALL_SUBGROUPS_ANALYSIS}"

        请按以下结构进行解读：
        对于每一个亚组变量 (例如 '年龄', '剂量'):
        1.  **标题**: (例如 “**1. 基于“年龄”的亚组分析：**”)
        2.  **组间异质性检验**: 报告 Q_between, df, 和 p值。明确指出基于此p值，该亚组变量的不同类别间效应量是否存在统计学上的显著差异，以及这是否意味着该变量可能解释了研究间的总体异质性。
        3.  **各类别具体效应**:
            对于该亚组变量下的每一个类别 (例如 ‘**年轻组 (Young)**’):
            a.  清晰标出类别名称 (如示例中的粗体)。
            b.  报告该类别的研究数量 (k)。
            c.  报告该类别的合并SMD及其{conf_level_percent_for_columns}%置信区间。
            d.  对该类别的效应大小、方向和统计显著性进行简要评价 (例如，“显示出强的正向效应，且统计学显著”，“效应不显著，因置信区间包含0”等)。
            e.  报告该类别内部的异质性 (I²)，并简要说明其水平（例如“异质性较低”，“存在中等程度异质性”）。
        4.  **该亚组变量小结**: 对该亚组变量的分析结果进行简短总结，说明该变量是否为效应修饰因素，以及各类别效应的主要特点或差异。

        在解读完所有单个亚组变量后，请提供一个：
        5.  **综合结论**: 总结所有亚组分析的结果，指出哪些因素似乎是异质性的重要来源或效应修饰因素，哪些因素影响不显著。讨论这些发现的潜在临床或实践意义，以及是否有需要进一步研究的地方。

        回答应当结构清晰，逻辑严谨，语言专业，全面覆盖所提供的数据。总字数可根据亚组变量数量调整，但每个亚组变量的解读应力求简洁明了。请使用Markdown加粗等方式突出重要信息，如亚组标题和类别名称。
        """
    else:
        return "错误：无效的分析类型被传递给AI解读模块。"

    if not prompt: 
        return "错误：未能为指定的分析类型生成AI提示。"

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, 
            max_tokens=4000 # 进一步增加了max_tokens以容纳更全面和详细的亚组解读
        )
        return completion.choices[0].message.content.strip()
    except APIConnectionError as e:
        return f"AI服务连接失败: 请检查网络连接、防火墙或代理设置。错误: {str(e)}"
    except AuthenticationError as e:
        return f"AI服务认证失败: 请确保DASHSCOPE_API_KEY环境变量设置正确。错误: {str(e)}"
    except APIStatusError as e:
        return f"AI服务返回错误状态: {e.status_code}. 响应: {e.response.text if e.response else 'N/A'}"
    except Exception as e:
        return f"生成AI描述时发生未知错误: {str(e)}"

