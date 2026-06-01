# MacAma

一个面向系统综述与 Meta 分析的半自动化工具集，覆盖从文献检索与筛选，到统计分析与图表生成，再到 AI 辅助论文写作的完整流程。

## Workflow 总览

项目对应的标准流程如下：

1. **文献检索（Retrieval）**：根据检索式批量获取候选文献。
2. **初筛（Initial Screening）**：基于题名/摘要进行纳入排除判断。
3. **复筛（Secondary Screening）**：基于全文信息进行二次筛选与结构化提取。
4. **Meta 分析（MetaflowAnalyser）**：对连续型指标计算 SMD，输出统计结果与图表。
5. **稿件生成（MetaWriter）**：结合结构化输入和知识库生成论文草稿并迭代修订。

`workflow/` 目录提供了 3 个流程资源包：

- `workflow/retrieval.zip`
- `workflow/initial_screening.zip`
- `workflow/secondary_screening.zip`

它们可作为检索/筛选工作流的模板或示例资源使用。

## 核心模块

### 1) literature_screening.py

文献检索与筛选主脚本，核心能力包括：

- 基于检索条件批量获取文献记录（如 PubMed URL/PMID）。
- 调用大模型工作流执行初筛、复筛、信息提取与统计辅助。
- 批量处理与结果落盘（`xlsx` + `json` + `md`）。

脚本内可配置项主要包括：

- API 配置：`API_KEY`、多个 `APP_ID_*`。
- 路径配置：`screening_result_dir`、`pmids_dir`、`articles_dir` 等。
- 输出文件：如 `included.xlsx`、`included_data.xlsx`、分步骤结果目录。

运行方式：

```bash
python literature_screening.py
```

注意：该脚本依赖你本地可用的工作流应用 ID 与 API Key，建议先根据你的课题修改检索参数和输出目录。

### 2) MetaflowAnalyser/

基于 Streamlit 的 Meta 分析可视化应用。

主要功能：

- 读取 Excel 数据并校验字段。
- 计算连续变量效应量（SMD）与置信区间。
- 支持固定效应/随机效应模型。
- 输出森林图、漏斗图、亚组分析图。
- 可打包下载图表与结果（ZIP）。
- 可选 AI 文本解读（需环境变量 `DASHSCOPE_API_KEY`）。

启动方式：

```bash
cd MetaflowAnalyser
streamlit run app.py
```

推荐输入列示例：

- `Article_ID`
- `CTRL_Sample`, `CTRL`, `Ctrl_Error_Bar_Max`
- `IR_Sample`, `IR`, `IR_Error_Bar_Max`
- 亚组变量：`Strain`, `Gender`, `Age`, `Cancer`, `Dosage` 等

### 3) MetaWriter/

AI 辅助学术写作模块，用于生成 Meta 分析论文初稿。

主要机制：

- 从 `user_manuscript_input.json` 读取分章节写作输入。
- 从本地知识库（`knowledge_base.json`）做 BM25 + HyDE 检索。
- 按章节执行 “生成 -> 专家评审 -> 判断 -> 修订” 循环。
- 默认输出稿件文件（如 `final_manuscript_qwenmax.md`）。

核心文件：

- `MetaWriter/workflow.py`：主流程脚本。
- `MetaWriter/prompts.py`：章节提示词模板。
- `MetaWriter/user_manuscript_input.json`：用户输入样例。
- `MetaWriter/academic_workflow.ipynb`：Notebook 形式流程。

运行前请配置：

- 环境变量 `DASHSCOPE_API_KEY`

## Case Study

`case_study/` 提供了“放疗与抗肿瘤免疫”案例数据与过程记录，按流程拆分为：

- `01_input_queries/`：检索输入示例。
- `02_retrieval_records/`：检索结果与输入记录。
- `03_initial_screening/`：初筛输出示例。
- `04_full_text_screening/`：全文复筛输入输出与批量结果。
- `05_meta_analysis_data/`：各指标 MetaFlow 分析输入与输出压缩包。
- `06_manuscript_generation/`：AI 生成稿与人工修订稿。
- `07_benchmark_evaluation/`：筛选任务 benchmark 数据集（含初筛与复筛）。

## 环境安装

建议使用独立虚拟环境：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 快速开始

1. 先配置 API Key / workflow APP ID。
2. 用 `literature_screening.py` 完成检索与筛选。
3. 将整理后的结构化数据导入 `MetaflowAnalyser` 做统计与作图。
4. 用 `MetaWriter` 生成论文草稿，并进行人工修订。
5. 参考 `case_study/` 对照检查每一步输入输出格式。

## 许可证

本项目采用 [MIT License](LICENSE)。

## 免责声明

本项目的 AI 输出仅用于研究辅助，不构成医学或学术结论。所有结果均需研究者人工核验与最终负责。
