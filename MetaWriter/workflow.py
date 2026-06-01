import json
import re
import nltk
import os
from openai import OpenAI
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import numpy as np
from rank_bm25 import BM25Okapi

# 从 prompts.py 导入所有提示模板
from prompts import (
    HYDE_PROMPT_TEMPLATE, JUDGING_PROMPT_TEMPLATE,
    INTRODUCTION_GENERATION_PROMPT_TEMPLATE, INTRODUCTION_REVISION_PROMPT_TEMPLATE, INTRODUCTION_EXPERT_REVIEW_PROMPT_TEMPLATE,
    METHODS_GENERATION_PROMPT_TEMPLATE, METHODS_REVISION_PROMPT_TEMPLATE, METHODS_EXPERT_REVIEW_PROMPT_TEMPLATE,
    RESULTS_GENERATION_PROMPT_TEMPLATE, RESULTS_REVISION_PROMPT_TEMPLATE, RESULTS_EXPERT_REVIEW_PROMPT_TEMPLATE,
    DISCUSSION_GENERATION_PROMPT_TEMPLATE, DISCUSSION_REVISION_PROMPT_TEMPLATE, DISCUSSION_EXPERT_REVIEW_PROMPT_TEMPLATE,
    TITLE_GENERATION_PROMPT_TEMPLATE, ABSTRACT_GENERATION_PROMPT_TEMPLATE,
    METHODS_NARRATIVE_GENERATION_PROMPT, RESULTS_NARRATIVE_GENERATION_PROMPT
)

# --- 配置信息 ---
KNOWLEDGE_BASE_FILE = "knowledge_base.json"
USER_INPUT_JSON_FILE = "user_manuscript_input.json"
FINAL_MANUSCRIPT_FILE = "final_manuscript_qwenmax.md"
TOP_N_ARTICLES = 20
MIN_BM25_SCORE = 0.0
MAX_REVISIONS = 3

# --- LLM API 配置 ---
DASHSCOPE_API_KEY_ENV_VAR = "DASHSCOPE_API_KEY"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# LLM_MODEL_NAME = "deepseek-v3"
LLM_MODEL_NAME = "qwen-max"

# --- NLTK 资源下载与路径设置 (修正后) ---
def setup_nltk():
    """
    检查NLTK数据包并下载（如果缺失）。
    同时显式添加Colab的NLTK数据路径以解决脚本模式下的查找错误。
    """
    # 步骤 1: 显式添加常见的 Colab NLTK 数据路径
    nltk_data_path = '/root/nltk_data'
    if os.path.exists(nltk_data_path) and nltk_data_path not in nltk.data.path:
        nltk.data.path.append(nltk_data_path)
        print(f"NLTK: Explicitly added data path '{nltk_data_path}'")

    # 步骤 2: 检查数据包并按需下载
    try:
        stopwords.words('english')
        word_tokenize("test")
        print("NLTK resources 'stopwords' and 'punkt' are available.")
    except LookupError:
        print("NLTK resources missing, attempting download...")
        try:
            nltk.download('stopwords', quiet=True)
            nltk.download('punkt', quiet=True)
            # 重新检查以确认下载成功
            stopwords.words('english')
            word_tokenize("test")
            print("NLTK resources downloaded successfully.")
        except Exception as e:
            print(f"FATAL: NLTK resource download/load failed: {e}")
            print("Please try running 'import nltk; nltk.download(\"punkt\"); nltk.download(\"stopwords\")' in a separate cell and restart the runtime.")
            exit() # 如果下载失败则终止脚本

# --- LLM API 调用函数 (已修正) ---
def call_llm_api(prompt: str, max_tokens: int = 4096, temperature: float = 0.7) -> str:
    """
    使用 openai 库和环境变量/Colab Secrets调用阿里云百炼 LLM API。
    """
    api_key = os.getenv(DASHSCOPE_API_KEY_ENV_VAR)
    # 如果环境变量中没有，则尝试从 Colab Secrets 中获取
    if not api_key:
        try:
            from google.colab import userdata
            api_key = userdata.get(DASHSCOPE_API_KEY_ENV_VAR)
        except (ImportError, Exception): # 捕获导入错误或userdata不可用的情况
            api_key = None
    
    if not api_key:
        print(f"错误: 环境变量和 Colab Secret '{DASHSCOPE_API_KEY_ENV_VAR}' 均未设置。")
        return f"错误: API Key 未配置。"
        
    try:
        client = OpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)
        print(f"正在调用 Dashscope API，模型: {LLM_MODEL_NAME} (max_tokens: {max_tokens}, temp: {temperature})...")
        
        completion = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )

        if hasattr(completion.choices[0].message, 'reasoning_content') and completion.choices[0].message.reasoning_content:
            print("--- LLM 思考过程 ---")
            print(completion.choices[0].message.reasoning_content)
            print("--------------------")

        final_content = completion.choices[0].message.content
        if not final_content or not final_content.strip():
             print("警告: LLM API 返回了空内容。")
             return "错误: LLM 返回空内容。"
        return final_content.strip()

    except Exception as e:
        print(f"调用 Dashscope API 时出错: {e}")
        return f"错误: LLM API 调用失败。 {e}"

# --- 数据加载和处理函数 ---
def load_json_file(filepath: str, file_description: str) -> dict | list | None:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误: {file_description} 文件 '{filepath}' 未找到。")
        return None
    except json.JSONDecodeError:
        print(f"错误: 无法解码 {file_description} 文件 '{filepath}' 中的 JSON。")
        return None

def load_user_manuscript_details(filepath: str) -> dict | None:
    details = load_json_file(filepath, "用户输入")
    if not details or not isinstance(details, dict):
        return None
    return details

def load_knowledge_base(filepath: str) -> list | None:
    kb = load_json_file(filepath, "知识库")
    if kb and isinstance(kb, list):
        return kb
    return None

# --- 叙事性转换函数 ---
def generate_narratives_with_llm(details_json_str: str, prompt_template: str, max_tokens: int) -> dict:
    prompt = prompt_template.format(details_json=details_json_str)
    
    narrative_json_str = call_llm_api(prompt, max_tokens=max_tokens, temperature=0.5)
    
    if "错误:" in narrative_json_str:
        print("错误: LLM在生成叙事性描述时失败。")
        return {"error": "LLM failed to generate narrative."}
        
    try:
        if narrative_json_str.strip().startswith("```json"):
            narrative_json_str = re.sub(r"```json\n(.*?)\n```", r"\1", narrative_json_str, flags=re.DOTALL)
        
        narratives = json.loads(narrative_json_str)
        if not isinstance(narratives, dict):
            raise ValueError("LLM did not return a valid JSON object.")
        print("--- 成功生成叙事性描述。 ---")
        return narratives
    except (json.JSONDecodeError, ValueError) as e:
        print(f"错误: 无法解析LLM返回的叙事性JSON: {e}")
        print(f"LLM返回内容: {narrative_json_str}")
        return {"error": "Failed to parse narrative JSON from LLM."}

def preprocess_text_for_bm25(text: str) -> list:
    if not text or not isinstance(text, str): return []
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    return [word for word in tokens if word not in stop_words and len(word) > 1]

def actual_hyde_expansion(query_text: str, original_topic: str) -> str:
    prompt = HYDE_PROMPT_TEMPLATE.format(query=query_text, original_topic=original_topic)
    hypothetical_doc_snippet = call_llm_api(prompt, max_tokens=150, temperature=0.5)
    if "错误:" in hypothetical_doc_snippet:
        print(f"警告: HyDE 生成失败。回退到基本查询。")
        return query_text
    return hypothetical_doc_snippet

def construct_query(topic: str, use_hyde: bool = True) -> str:
    cleaned_topic_for_direct_use = re.sub(r'[^\w\s]', '', topic.lower())
    if use_hyde:
        return actual_hyde_expansion(cleaned_topic_for_direct_use, original_topic=topic)
    return cleaned_topic_for_direct_use

def retrieve_relevant_articles_bm25(query_text: str, articles: list, top_n: int) -> list:
    if not articles: return []
    tokenized_corpus = [preprocess_text_for_bm25(f"{a.get('title','')} {a.get('abstract','')}") for a in articles]
    valid_indices = [i for i, tokens in enumerate(tokenized_corpus) if tokens]
    if not valid_indices: return []
    valid_tokenized_corpus = [tokenized_corpus[i] for i in valid_indices]
    
    bm25 = BM25Okapi(valid_tokenized_corpus)
    tokenized_query = preprocess_text_for_bm25(query_text)
    if not tokenized_query: return []

    doc_scores_valid = bm25.get_scores(tokenized_query)
    all_doc_scores = np.full(len(articles), -np.inf) 
    for i, original_idx in enumerate(valid_indices):
        all_doc_scores[original_idx] = doc_scores_valid[i]
    
    relevant_indices = [i for i, score in enumerate(all_doc_scores) if score > MIN_BM25_SCORE]
    sorted_relevant_indices = sorted(relevant_indices, key=lambda i: all_doc_scores[i], reverse=True)
    top_indices = sorted_relevant_indices[:top_n]
    
    return [articles[i] for i in top_indices]

def format_references_for_prompt(retrieved_articles: list) -> str:
    if not retrieved_articles: return "No relevant references found to use for citation."
    references_output_list = []
    for i, article in enumerate(retrieved_articles):
        authors_list = article.get('authors', 'Unknown Authors')
        authors = ", ".join(authors_list) if isinstance(authors_list, list) else str(authors_list)
        title = str(article.get('title', 'Untitled Article'))
        doi_val = article.get('doi')
        source_link = f"[https://doi.org/](https://doi.org/){doi_val}" if doi_val else "Source link not available"
        references_output_list.append(f"[{i+1}] {authors}, {title}, {source_link}.")
    return "\n".join(references_output_list)

def llm_judge_feedback(feedback_to_judge: str) -> str:
    prompt = JUDGING_PROMPT_TEMPLATE.format(expert_feedback=feedback_to_judge)
    decision = call_llm_api(prompt, max_tokens=20, temperature=0.2)
    decision_cleaned = decision.strip().upper()
    if "NEEDS_REVISION" in decision_cleaned: return "NEEDS_REVISION"
    if "LOOKS_GOOD" in decision_cleaned: return "LOOKS_GOOD"
    print(f"警告: 判断智能体返回了意外的决策: '{decision}'. 默认认为需要修改。")
    return "NEEDS_REVISION"

def process_manuscript_section(
    section_name: str,
    generation_prompt_template: str,
    revision_prompt_template: str,
    expert_review_prompt_template: str,
    topic: str,
    references_string: str,
    max_tokens_generate: int,
    max_tokens_revise: int,
    max_tokens_review: int,
    user_supplied_details: dict 
) -> str:
    print(f"\n\n--- 开始处理手稿部分: {section_name} ---")

    format_kwargs = {"topic": topic, "references_string": references_string}
    format_kwargs.update(user_supplied_details)

    try:
        initial_generation_prompt = generation_prompt_template.format(**format_kwargs)
    except KeyError as e:
        print(f"错误: 生成 {section_name} 的提示时缺少键: {e}。请检查提示模板和用户输入JSON的键。")
        print(f"可用的 format_kwargs 键: {list(format_kwargs.keys())}")
        return f"错误: {section_name} 部分生成提示失败 (缺少键: {e})。"

    current_section_text = call_llm_api(initial_generation_prompt, max_tokens=max_tokens_generate, temperature=0.7)
    if "错误:" in current_section_text:
        print(f"LLM 生成 {section_name} 失败。错误: {current_section_text}")
        return f"错误: {section_name} 部分生成失败。"
    print(f"\n--- LLM 生成的初始 {section_name} ---\n{current_section_text}\n(字数估算: {len(current_section_text.split())})\n------------------------------------------")

    for revision_attempt in range(MAX_REVISIONS):
        print(f"\n--- {section_name}: 开始第 {revision_attempt + 1}/{MAX_REVISIONS}轮 评审与修改 ---")
        
        review_format_kwargs = format_kwargs.copy() 
        review_format_kwargs["generated_section_text"] = current_section_text 
        try:
            expert_review_prompt = expert_review_prompt_template.format(**review_format_kwargs)
        except KeyError as e:
            print(f"错误: 生成 {section_name} 的专家评审提示时缺少键: {e}。"); continue

        expert_feedback = call_llm_api(expert_review_prompt, max_tokens=max_tokens_review, temperature=0.6)
        if "错误:" in expert_feedback: print(f"{section_name} 专家评审出错。"); continue
        print(f"\n--- {section_name}: LLM 返回的专家评审反馈（包含评分） ---\n{expert_feedback}\n----------------------------------------")

        judgement = llm_judge_feedback(expert_feedback)
        if "错误:" in judgement: print(f"{section_name} 判断评审意见出错。"); judgement = "NEEDS_REVISION"
        if judgement == "LOOKS_GOOD" or "requires no further modifications" in expert_feedback.lower(): 
            print(f"\n判断智能体或专家反馈表明 {section_name} 已符合要求。")
            break
        
        if judgement == "NEEDS_REVISION":
            print(f"\n判断智能体认为 {section_name} 需要修改。准备修订...")
            revision_format_kwargs = format_kwargs.copy() 
            revision_format_kwargs["current_section_text"] = current_section_text
            revision_format_kwargs["expert_feedback"] = expert_feedback
            try:
                revision_prompt_filled = revision_prompt_template.format(**revision_format_kwargs)
            except KeyError as e:
                print(f"错误: 生成 {section_name} 的修订提示时缺少键: {e}。"); continue
            
            revised_section_text = call_llm_api(revision_prompt_filled, max_tokens=max_tokens_revise, temperature=0.65)
            if "错误:" in revised_section_text: print(f"{section_name} 修订出错。保留当前版本。")
            else:
                current_section_text = revised_section_text
                print(f"\n--- {section_name}: LLM 修订后的版本 ---\n{current_section_text}\n(字数估算: {len(current_section_text.split())})\n------------------------------------------")
        
        if revision_attempt == MAX_REVISIONS - 1: print(f"\n{section_name}: 已达到最大修改次数。")
    print(f"\n--- {section_name} 部分处理完成 ---")
    return current_section_text

def format_final_manuscript(title, abstract, final_sections):
    """将所有生成的部分格式化为一篇完整的Markdown文章。"""
    
    authors = "AI-Generated Author¹, Human Reviewer²"
    affiliations = "¹AI Writing Labs; ²Department of Human-AI Collaboration"
    
    full_text = f"# {title}\n\n"
    full_text += f"**{authors}**\n\n"
    full_text += f"*{affiliations}*\n\n"
    full_text += f"---\n\n"
    full_text += f"## Abstract\n{abstract}\n\n"
    full_text += f"---\n\n"
    
    section_order = ["Introduction", "Materials and Methods", "Results", "Discussion"]
    for i, section_title in enumerate(section_order):
        content = final_sections.get(section_title, f"*本章节 ({section_title}) 未能成功生成。*")
        content = re.sub(r'\n##+\s*References\s*\n', '\n', content, flags=re.IGNORECASE)
        full_text += f"## {i+1}. {section_title}\n\n{content}\n\n"
        
    return full_text

# --- 主工作流程 ---
def main_workflow():
    print("--- 启动：全自动学术手稿生成工作流 ---")
    setup_nltk()

    user_manuscript_data = load_user_manuscript_details(USER_INPUT_JSON_FILE)
    if not user_manuscript_data:
        print(f"错误: 无法从 '{USER_INPUT_JSON_FILE}' 加载有效的用户手稿数据。")
        return

    user_topic = user_manuscript_data.get("topic", "未提供主题")
    print(f"研究主题: {user_topic}")

    print("\n--- 步骤 1: 知识检索 (RAG) ---")
    query_content_for_retrieval = construct_query(user_topic, use_hyde=True)
    articles_kb = load_knowledge_base(KNOWLEDGE_BASE_FILE)
    if not articles_kb:
        print(f"无法加载知识库 '{KNOWLEDGE_BASE_FILE}'。流程终止。")
        return
    retrieved_articles = retrieve_relevant_articles_bm25(query_content_for_retrieval, articles_kb, TOP_N_ARTICLES)
    formatted_references_for_llm = format_references_for_prompt(retrieved_articles)
    print(f"检索到 {len(retrieved_articles)} 篇相关文章用于上下文。")

    final_manuscript_sections = {}

    # --- 步骤 2: 顺序生成正文所有章节 ---
    section_processing_order = [
        {"name": "Introduction", "gen_prompt": INTRODUCTION_GENERATION_PROMPT_TEMPLATE, "rev_prompt": INTRODUCTION_REVISION_PROMPT_TEMPLATE, "exp_prompt": INTRODUCTION_EXPERT_REVIEW_PROMPT_TEMPLATE, "details_key": "introduction_details", "narrative_gen_prompt": None, "gen_tokens": 6000, "rev_tokens": 6000, "exp_tokens": 6000},
        {"name": "Materials and Methods", "gen_prompt": METHODS_GENERATION_PROMPT_TEMPLATE, "rev_prompt": METHODS_REVISION_PROMPT_TEMPLATE, "exp_prompt": METHODS_EXPERT_REVIEW_PROMPT_TEMPLATE, "details_key": "methods_details", "narrative_gen_prompt": METHODS_NARRATIVE_GENERATION_PROMPT, "gen_tokens": 10000, "rev_tokens": 10000, "exp_tokens": 10000},
        {"name": "Results", "gen_prompt": RESULTS_GENERATION_PROMPT_TEMPLATE, "rev_prompt": RESULTS_REVISION_PROMPT_TEMPLATE, "exp_prompt": RESULTS_EXPERT_REVIEW_PROMPT_TEMPLATE, "details_key": "results_details", "narrative_gen_prompt": RESULTS_NARRATIVE_GENERATION_PROMPT, "gen_tokens": 10000, "rev_tokens": 10000, "exp_tokens": 10000},
        {"name": "Discussion", "gen_prompt": DISCUSSION_GENERATION_PROMPT_TEMPLATE, "rev_prompt": DISCUSSION_REVISION_PROMPT_TEMPLATE, "exp_prompt": DISCUSSION_EXPERT_REVIEW_PROMPT_TEMPLATE, "details_key": "discussion_details", "narrative_gen_prompt": None, "gen_tokens": 10000, "rev_tokens": 10000, "exp_tokens": 1000}
    ]

    for section in section_processing_order:
        # 依赖检查
        if section["name"] == "Discussion" and "错误:" in final_manuscript_sections.get("Results", "错误:"):
            print(f"跳过 {section['name']}，因为前置章节 'Results' 生成失败。")
            continue
        if section["name"] == "Results" and "错误:" in final_manuscript_sections.get("Materials and Methods", "错误:"):
            print(f"跳过 {section['name']}，因为前置章节 'Materials and Methods' 生成失败。")
            continue
        if section["name"] == "Materials and Methods" and "错误:" in final_manuscript_sections.get("Introduction", "错误:"):
            print(f"跳过 {section['name']}，因为前置章节 'Introduction' 生成失败。")
            continue

        user_details_raw = user_manuscript_data.get(section["details_key"], {})
        
        narrative_gen_prompt = section.get("narrative_gen_prompt")
        if narrative_gen_prompt:
            print(f"--- 正在为 {section['name']} 生成叙事性描述... ---")
            details_json_str = json.dumps(user_details_raw, ensure_ascii=False, indent=2)
            user_details = generate_narratives_with_llm(details_json_str, narrative_gen_prompt, max_tokens=2000)
            if "error" in user_details:
                print(f"生成 {section['name']} 的叙事性描述失败，流程终止。")
                return
            if section['name'] == 'Results':
                 user_details['user_figure_table_references_results'] = user_details_raw.get('user_figure_table_references_results', '')
                 user_details['user_optional_note_results'] = user_details_raw.get('user_optional_note_results', '')
        else:
            user_details = user_details_raw

        if section["name"] == "Discussion":
            user_details["results_section_text"] = final_manuscript_sections.get("Results", "The Results section was not generated successfully.")

        final_manuscript_sections[section["name"]] = process_manuscript_section(
            section_name=section["name"],
            generation_prompt_template=section["gen_prompt"],
            revision_prompt_template=section["rev_prompt"],
            expert_review_prompt_template=section["exp_prompt"],
            topic=user_topic, 
            references_string=formatted_references_for_llm,
            max_tokens_generate=section["gen_tokens"],
            max_tokens_revise=section["rev_tokens"],
            max_tokens_review=section["exp_tokens"],
            user_supplied_details=user_details
        )
        if "错误:" in final_manuscript_sections[section["name"]]:
            print(f"处理 {section['name']} 部分时遇到严重错误。工作流已停止。")
            return

    # --- 步骤 3: 生成标题和摘要 ---
    print("\n\n--- 开始生成标题和摘要 ---")
    full_text_for_summary = "\n\n".join(
        f"## {title}\n{content}" for title, content in final_manuscript_sections.items() if "错误:" not in content
    )
    
    title_prompt = TITLE_GENERATION_PROMPT_TEMPLATE.format(topic=user_topic, full_manuscript_text=full_text_for_summary)
    manuscript_title = call_llm_api(title_prompt, max_tokens=100, temperature=0.6)
    print(f"\n生成的标题: {manuscript_title}")

    abstract_prompt = ABSTRACT_GENERATION_PROMPT_TEMPLATE.format(full_manuscript_text=full_text_for_summary)
    manuscript_abstract = call_llm_api(abstract_prompt, max_tokens=1000, temperature=0.7)
    print(f"\n生成的摘要:\n{manuscript_abstract}")

    # --- 步骤 4: 整合并保存最终文稿 ---
    print(f"\n--- 正在整合完整手稿并保存至 {FINAL_MANUSCRIPT_FILE} ---")
    final_manuscript_content = format_final_manuscript(manuscript_title, manuscript_abstract, final_manuscript_sections)
    
    try:
        with open(FINAL_MANUSCRIPT_FILE, 'w', encoding='utf-8') as f:
            f.write(final_manuscript_content)
        print(f"完整手稿已成功保存到 '{FINAL_MANUSCRIPT_FILE}'。")
    except IOError as e:
        print(f"错误: 无法将最终手稿写入文件: {e}")

    print("\n\n--- 完整手稿工作流完成 ---")

if __name__ == "__main__":
    main_workflow()
