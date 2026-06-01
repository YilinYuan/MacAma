# prompts.py

# 从 few_shot_examples.py 导入范例
# 确保这个文件存在，并且包含您需要的范例变量
try:
    from few_shot_examples import (
        INTRODUCTION_FEW_SHOT_EXAMPLE, METHODS_FEW_SHOT_EXAMPLE,
        RESULTS_FEW_SHOT_EXAMPLE, DISCUSSION_FEW_SHOT_EXAMPLE
    )
except ImportError:
    print("Warning: few_shot_examples.py not found or missing examples. Using placeholder text.")
    INTRODUCTION_FEW_SHOT_EXAMPLE = "(A high-quality introduction example would be placed here.)"
    METHODS_FEW_SHOT_EXAMPLE = "(A high-quality methods section example would be placed here.)"
    RESULTS_FEW_SHOT_EXAMPLE = "(A high-quality results section example, as provided by the user, would be placed here.)"
    DISCUSSION_FEW_SHOT_EXAMPLE = "(A high-quality discussion section example would be placed here.)"


# --- 通用提示模板 ---
HYDE_PROMPT_TEMPLATE = """
Based on the user query "{query}", generate a short, hypothetical academic abstract or document snippet (around 50-100 words) that this query might be trying to find. This hypothetical document should sound like a relevant search result. Do not state that it is hypothetical. Focus on capturing the core concepts and terminology related to the query.
User Query: "{original_topic}"
"""

JUDGING_PROMPT_TEMPLATE = """
You are an AI assistant that analyzes expert feedback to determine if revisions are necessary.
Read the following "Expert Feedback" provided for an academic manuscript section.

Expert Feedback:
{expert_feedback}

Based *only* on the text of the "Expert Feedback", decide if the feedback suggests that the manuscript section *needs modification* or if the feedback indicates the section is *acceptable as is* (e.g., purely positive comments, or explicit statements that no changes are needed, such as "requires no further modifications.").

Respond with one of the following two phrases ONLY:
- NEEDS_REVISION
- LOOKS_GOOD

Do not add any other explanation or text.
"""

# --- 叙事性转换提示模板 (新增) ---
METHODS_NARRATIVE_GENERATION_PROMPT = """
You are an expert methodologist. Your task is to convert the following structured JSON data for a "Materials and Methods" section into a series of clear, narrative paragraphs.

**Input Data (JSON)**:
{details_json}

**Instructions**:
For each key-value pair in the input JSON, write a corresponding narrative paragraph. Your output MUST be a single JSON object where the keys are the narrative placeholders I provide below, and the values are the paragraphs you write. Ensure the tone is formal, academic, and suitable for a scientific publication.

**Output JSON Keys to use**:
- "narrative_protocol_registration"
- "narrative_eligibility_criteria"
- "narrative_search_strategy"
- "narrative_study_selection"
- "narrative_data_extraction"
- "narrative_bias_assessment"
- "narrative_data_synthesis"
- "narrative_subgroup_analysis"
- "narrative_protocol_deviations"

**Example**:
If the input for "user_registration_info" is "PROSPERO CRD123", your output value for the "narrative_protocol_registration" key might be: "The protocol for this systematic review was pre-registered in the PROSPERO international prospective register of systematic reviews under the registration number CRD123."

Now, generate the complete JSON object with all the narrative paragraphs based on the provided Input Data.
"""

RESULTS_NARRATIVE_GENERATION_PROMPT = """
You are an experienced academic writer. Your task is to convert the following structured JSON data for a "Results" section into a series of narrative paragraphs that tell a compelling story.

**Input Data (JSON)**:
{details_json}

**Instructions**:
For each key in the input JSON, write a corresponding narrative paragraph. Your output MUST be a single JSON object where the keys are the narrative placeholders I provide below, and the values are the paragraphs you write. Focus on creating natural transitions and highlighting the significance of the findings, rather than just listing numbers.

**Output JSON Keys to use**:
- "narrative_prisma_flow"
- "narrative_study_characteristics"
- "narrative_meta_analysis_results"
- "narrative_subgroup_analyses"
- "narrative_publication_bias"

**Example**:
If the input for "user_prisma_flow_data" is `{{"initial_records": 1200, "after_duplicates_removed": 1000, "studies_included": 37}}`, your output value for the "narrative_prisma_flow" key might be: "Our initial literature search yielded 1,200 records. After the removal of duplicates, 1,000 articles were screened, ultimately resulting in the inclusion of 37 studies for the final synthesis."

Now, generate the complete JSON object with all the narrative paragraphs based on the provided Input Data.
"""


# --- 标题 (Title) 和摘要 (Abstract) 提示模板 ---
TITLE_GENERATION_PROMPT_TEMPLATE = """
Based on the full text of the academic manuscript provided below, generate a concise, formal, and academic title. The title should accurately reflect the main topic, findings, and scope of the systematic review/meta-analysis.

Original Topic: {topic}

Full Manuscript Text:
{full_manuscript_text}

Generate only the title.
"""

ABSTRACT_GENERATION_PROMPT_TEMPLATE = """
Based on the full text of the academic manuscript provided below, write a structured abstract of approximately 250-300 words. The abstract should be divided into the following sections: Background, Methods, Results, and Conclusion.

Full Manuscript Text:
{full_manuscript_text}

Structure your response as follows:
**Abstract**
**Background:** [Briefly introduce the context and purpose of the study.]
**Methods:** [Summarize the key methods used for the systematic review and meta-analysis, including search strategy, inclusion criteria, and data analysis.]
**Results:** [Summarize the most important findings from the results section, including key statistics from the meta-analysis.]
**Conclusion:** [State the main conclusions and their implications.]

Write in formal academic English.
"""

# --- 引言 (Introduction) 提示模板 ---
INTRODUCTION_GENERATION_PROMPT_TEMPLATE = f"""
You are an expert academic writer. Your task is to draft the "Introduction" section for a systematic review.

**Topic**: {{topic}}

**Your Input Data**:
- User-Supplied Background Summary (Optional): {{user_intro_background_summary}}
- References for Citation: {{references_string}}

**Writing Instructions & Objectives**:
1.  **Establish Context and Broad Importance**: Start with the broad context and importance of the topic.
2.  **Summarize Existing Knowledge**: Briefly summarize what is known, citing key literature from the provided references.
3.  **Identify Gaps and Rationale**: Clearly state the gap in the current literature and provide a compelling rationale for conducting this review.
4.  **Referencing**: Use numerical in-text citations `[X]` corresponding to the provided reference list. Append a "**References**" section at the end, listing all cited works from the provided list, formatted as: `[X] Author(s), Title, DOI/URL.`

**Example of a Well-Written Introduction (Follow this style and structure, using YOUR input data):**
--- BEGIN EXAMPLE ---
{INTRODUCTION_FEW_SHOT_EXAMPLE}
--- END EXAMPLE ---

Now, write the "Introduction" section based on the provided topic and references. Output only the "Introduction" section and its "References" list.
"""

INTRODUCTION_EXPERT_REVIEW_PROMPT_TEMPLATE = """
You are an expert academic reviewer. Your task is to critically evaluate the drafted "Introduction" section.

**Provided Draft Introduction**:
{generated_section_text}

**Evaluation Criteria & Scoring**:
Please provide a score from 1 (poor) to 10 (excellent) for each criterion, along with specific, actionable feedback.

1.  **Clarity and Structure (Score: __/10)**:
    - Feedback: (Is the introduction well-structured? Does it logically flow from broad context to the specific rationale? Is it easy to understand?)

2.  **Content and Accuracy (Score: __/10)**:
    - Feedback: (Does the introduction accurately summarize the background? Are the gaps and rationale clearly stated? Is the information consistent with what might be expected from the provided references?)

3.  **Adherence to Style and Referencing (Score: __/10)**:
    - Feedback: (Does the writing style match the provided few-shot example? Are citations `[X]` used correctly? Is the "References" section formatted correctly?)

**Overall Assessment**:
- Provide a summary of the key strengths and weaknesses.
- If the section is of high quality and requires no changes, please state "The Introduction is well-written and requires no further modifications."
"""

INTRODUCTION_REVISION_PROMPT_TEMPLATE = """
You are an expert academic writer. Your task is to revise the "Introduction" section based on expert feedback.

**Original Topic**: {topic}
**User-Supplied Background Summary (Optional)**: {user_intro_background_summary}
**Provided References**: {references_string}

**Current "Introduction" Section**:
{current_section_text}

**Expert Feedback (including scores and comments)**:
{expert_feedback}

**Revision Goal**:
Address all points in the expert feedback to improve the clarity, accuracy, and style of the introduction. Pay close attention to improving any low-scoring areas.

**Instructions**:
- Incorporate the feedback thoroughly.
- Ensure the final text adheres to the structure and style of a high-quality academic introduction.
- Follow all referencing instructions (`[X]` citations and final "References" list).
- Output only the **revised "Introduction" section** and its "References" list.
"""


# --- 材料与方法 (Materials and Methods) 提示模板 ---
METHODS_GENERATION_PROMPT_TEMPLATE = f"""
You are a methodologist and academic writer. Your task is to draft the "Materials and Methods" section for a systematic review by weaving the provided narrative points into a cohesive text that follows the style of a high-quality example.

**Topic**: {{topic}}

**Your Input Data (Narrative Points)**:
- Protocol and Registration Narrative: {{narrative_protocol_registration}}
- Eligibility Criteria Narrative: {{narrative_eligibility_criteria}}
- Information Sources and Search Strategy Narrative: {{narrative_search_strategy}}
- Study Selection Narrative: {{narrative_study_selection}}
- Data Extraction Narrative: {{narrative_data_extraction}}
- Risk of Bias Assessment Narrative: {{narrative_bias_assessment}}
- Data Synthesis and Meta-analysis Narrative: {{narrative_data_synthesis}}
- Subgroup Analysis Narrative: {{narrative_subgroup_analysis}}
- Protocol Deviations Narrative: {{narrative_protocol_deviations}}

**Writing Instructions & Objectives**:
Weave the provided narrative points for each sub-topic into a single, cohesive, well-structured "Materials and Methods" section. The writing must be clear, precise, and reproducible. The section must be structured with the following subheadings, mirroring the provided example. Cite any methodological papers (e.g., PRISMA guidelines) from the provided references if applicable.

**Example of a Well-Written Methods Section (Follow this style and structure):**
--- BEGIN EXAMPLE ---
{METHODS_FEW_SHOT_EXAMPLE}
--- END EXAMPLE ---

Now, write the "Materials and Methods" section using the narrative points provided. Output only the "Materials and Methods" section and its "References" list if any citations were made.
"""

METHODS_EXPERT_REVIEW_PROMPT_TEMPLATE = """
You are an expert methodologist. Review the drafted "Materials and Methods" section.

**Provided Draft "Materials and Methods"**:
{generated_section_text}

**Original Narrative Points (for your reference)**:
- Protocol and Registration: {narrative_protocol_registration}
- Eligibility Criteria: {narrative_eligibility_criteria}
- Search Strategy: {narrative_search_strategy}
- Study Selection: {narrative_study_selection}
- Data Extraction: {narrative_data_extraction}
- Bias Assessment: {narrative_bias_assessment}
- Data Synthesis: {narrative_data_synthesis}
- Subgroup Analysis: {narrative_subgroup_analysis}
- Protocol Deviations: {narrative_protocol_deviations}

**Evaluation Criteria & Scoring**:
Please provide a score from 1 (poor) to 10 (excellent) for each criterion, along with specific, actionable feedback.

1.  **Narrative Integration & Accuracy (Score: __/10)**:
    - Feedback: (Does the section successfully weave all the provided narrative points into a coherent text? Are there any omissions or misrepresentations of the original points?)

2.  **Clarity & Reproducibility (Score: __/10)**:
    - Feedback: (Is the methodology described clearly enough for another researcher to reproduce it? Is the language precise and unambiguous?)

3.  **Adherence to Style and Structure (Score: __/10)**:
    - Feedback: (Does the writing style and subheading structure match the provided few-shot example? Are citations used correctly if any?)

**Overall Assessment**:
- Provide a summary of the key strengths and weaknesses.
- If high quality, confirm this (e.g., "The Materials and Methods section is well-written and requires no further modifications.").
"""

METHODS_REVISION_PROMPT_TEMPLATE = """
You are an expert academic writer. Revise the "Materials and Methods" section based on expert feedback.

**Original Narrative Points**: (All narrative_... details are available for context)

**Current "Materials and Methods" Section**:
{current_section_text}

**Expert Feedback (including scores and comments)**:
{expert_feedback}

**Revision Goal**:
Address all points in the expert feedback, focusing on improving the flow, clarity, and narrative integration of the provided points.

**Instructions**:
- Incorporate the feedback thoroughly.
- Ensure the output follows the required subheading structure.
- Output only the **revised "Materials and Methods" section**.
"""


# --- 结果 (Results) 提示模板 ---
RESULTS_GENERATION_PROMPT_TEMPLATE = f"""
You are an experienced academic writer drafting the "Results" section for a systematic review. Transform the provided narrative data points into a compelling scientific narrative.

**Topic**: {{topic}}

**Your Input Data (Narrative Points)**:
- Narrative for Identification & Screening: {{narrative_prisma_flow}}
- Narrative for Study Characteristics: {{narrative_study_characteristics}}
- Narrative for Meta-analysis Results: {{narrative_meta_analysis_results}}
- Narrative for Subgroup Analyses: {{narrative_subgroup_analyses}}
- Narrative for Publication Bias: {{narrative_publication_bias}}
- Figure/Table References: {{user_figure_table_references_results}}
- Optional Note: {{user_optional_note_results}}

**Writing Instructions**:
Weave the provided narrative points for each sub-topic into a cohesive, well-structured "Results" section. Follow the detailed instructions on paragraph organization, sentence-level construction, and analytical depth to create a fluid and interpretive text, not just a list. Refer to figures and tables as specified.

**Example of a Well-Written Results Section (Follow this style and structure, using YOUR input data):**
--- BEGIN EXAMPLE ---
{RESULTS_FEW_SHOT_EXAMPLE}
--- END EXAMPLE ---

Now, write the "Results" section. Output only the “Results” section and its "References" list if any citations were made.
"""

RESULTS_EXPERT_REVIEW_PROMPT_TEMPLATE = """
You are a domain expert in systematic reviews. Your role is to critically evaluate the drafted "Results" section.

**Provided Draft Results**:
{generated_section_text}

**Original Narrative Points (for your reference)**:
(All narrative_... fields for results are available here for your review)

**Evaluation Criteria & Scoring**:
Please provide a score from 1 (poor) to 10 (excellent) for each criterion, along with specific, actionable feedback.

1.  **Data Accuracy and Narrative Integration (Score: __/10)**:
    - Feedback: (Does the text accurately reflect all the user-supplied narrative points? Are they woven together effectively or just listed?)

2.  **Narrative Quality and Clarity (Score: __/10)**:
    - Feedback: (Is the language clear, engaging, and does it follow the style of the few-shot example? Are transitions smooth?)

3.  **Interpretation and Context (Score: __/10)**:
    - Feedback: (Does the text provide appropriate interpretation without straying into Discussion territory?)

**Overall Assessment**:
- Provide a summary of the key strengths and weaknesses.
- If high quality, confirm this (e.g., "The Results section is well-written and requires no further modifications.").
"""

RESULTS_REVISION_PROMPT_TEMPLATE = """
You are a skilled academic writer tasked with revising the "Results" section based on expert feedback.

**Original Narrative Points**: (All narrative_... details for results are available for context)

**Current "Results" Section**:
{current_section_text}

**Expert Feedback (including scores and comments)**:
{expert_feedback}

**Revision Goal**:
Address all feedback points to improve the narrative flow and clarity. Pay special attention to low-scoring areas and aim to emulate the style of the few-shot example.

**Instructions**:
- Incorporate expert feedback thoroughly, ensuring the final text is a fluid narrative based on the original points.
- Output only the **revised “Results” section**.
"""


# --- 讨论 (Discussion) 提示模板 ---
DISCUSSION_GENERATION_PROMPT_TEMPLATE = f"""
You are a senior academic author writing the "Discussion" section of a systematic review. Your task is to interpret the results from the provided "Results Section Text", compare them with existing literature from the "References for Comparison", and provide a clear, impactful discussion that concludes the paper.

**Topic**: {{topic}}

**Key Information to Integrate**:
- **Full Text of the preceding Results Section**: {{results_section_text}}
- **References for Comparison (from RAG search)**: {{references_string}}
- **(Optional) User-Provided Key Discussion Points**: {{user_discussion_points}}

**Writing Instructions**:
Your discussion should be a cohesive narrative, not just a list of points. Structure it as follows:

1.  **Opening Summary of Principal Findings**: Start with a concise paragraph that summarizes the most important findings presented in the `results_section_text`.
2.  **Comparison with Existing Literature**: This is the core of the discussion.
    - **Critically compare and contrast the findings from `results_section_text` with relevant studies from the `references_string`.**
    - Explicitly cite them (e.g., `[X]`).
    - Highlight where your findings **confirm**, **contradict**, or **extend** previous work.
    - Offer plausible explanations for discrepancies (e.g., differences in methodology, populations, follow-up times between your synthesized data and the cited literature).
3.  **Strengths and Limitations**:
    - Objectively discuss the methodological strengths and limitations of the review.
4.  **Implications and Future Directions**:
    - Discuss the broader implications for research and practice.
    - Propose specific, actionable recommendations for future research.
5.  **Conclusion**: End with a strong concluding paragraph that provides a final, balanced summary of the evidence and its implications, reiterating the main takeaway message.

**Example of a Well-Written Discussion (Follow this style and structure, using YOUR input data):**
--- BEGIN EXAMPLE ---
{DISCUSSION_FEW_SHOT_EXAMPLE}
--- END EXAMPLE ---

Now, write the "Discussion" section. Output only the "Discussion" section and its "References" list.
"""

DISCUSSION_EXPERT_REVIEW_PROMPT_TEMPLATE = """
You are a domain expert in systematic reviews, evaluating the "Discussion" section of a manuscript.

**Provided Draft "Discussion" Section**:
{generated_section_text}

**Context (for your reference)**:
- Topic: {topic}
- Preceding Results Section: {results_section_text}
- Literature for Comparison: {references_string}

**Evaluation Criteria & Scoring**:
Please provide a score from 1 (poor) to 10 (excellent) for each criterion, along with specific, actionable feedback.

1.  **Interpretation and Synthesis (Score: __/10)**:
    - Feedback: (Does the discussion accurately and insightfully interpret the key findings from the Results section? Does it synthesize them into a coherent narrative?)

2.  **Literature Comparison (Score: __/10)**:
    - Feedback: (How well does the discussion **compare and contrast** the study's findings with the provided literature from the reference list? Is the comparison critical and analytical, or just a simple statement of agreement/disagreement? Are citations used appropriately and effectively?)

3.  **Critical Analysis (Score: __/10)**:
    - Feedback: (Is the discussion of strengths and limitations balanced, specific, and insightful? Are the implications and future directions logical and well-supported?)

**Overall Assessment**:
- Provide a summary of the key strengths and weaknesses.
- If high quality, confirm this (e.g., "The Discussion is insightful, well-argued, and requires no further modifications.").
"""

DISCUSSION_REVISION_PROMPT_TEMPLATE = """
You are an expert academic writer. Revise the "Discussion" section based on expert feedback.

**Original Topic**: {topic}
**Full Text of the preceding Results Section (for context)**: {results_section_text}
**References for Comparison**: {references_string}
**(Optional) User-Provided Key Discussion Points**: {user_discussion_points}

**Current "Discussion" Section**:
{current_section_text}

**Expert Feedback (including scores and comments)**:
{expert_feedback}

**Revision Goal**:
Address all feedback, especially focusing on strengthening the literature comparison and the critical analysis of the findings. Aim to match the style of a high-quality academic discussion as exemplified in the generation prompt.

**Instructions**:
- Incorporate the feedback thoroughly.
- Ensure a deep and critical engagement with the provided references.
- Output only the **revised "Discussion" section** and its "References" list.
"""
