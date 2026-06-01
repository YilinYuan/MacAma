import pandas as pd
from dashscope import Application
from http import HTTPStatus
import os
from datetime import datetime
import json
from tqdm import tqdm
from screening_result.counter import analyze_json_files, load_json,extract_fields_from_json, mark_errors_in_excel, count_error_entries, count_error_entries_in_single_xlsx, merge_xlsx, analysis_id
import time
from scraper import request_pubmed

# 你的应用ID和API密钥
APP_ID_PMIDS = '8a97409d47084f008b44ce8762076f94'
APP_ID_PRISCREEN = '697a0ce4f86a41c7aa575c182abdc7f0'
APP_ID_RESCREEN_CLI = 'f6779417e2a944f080238755255a960a'
APP_ID_RESCREEN_ANI = '821e658b9737419996f66adce0c3a66d'
APP_ID_QUA_ANI = 'ca8e3d33477842beba9887b662cc2e40'
API_KEY = 'sk-xxx'

##################################################################################
### 修改筛选结果保存目录
screening_result_dir = "screening/animal0208/results"
#################################################################################
### 修改所有文章URL文件夹位置和文件名
pmids_dir = "./screening/animal0208/articleURLs"
os.makedirs(pmids_dir, exist_ok=True)
articles_dir = "./screening/animal0208/articles"
os.makedirs(articles_dir, exist_ok=True)
PMIDs_filepath_pri = os.path.join(pmids_dir, "test3.xlsx")
### 进入复筛文章URL文件夹位置和文件名
PMIDs_filepath_re = os.path.join(pmids_dir, 'reURLs.xlsx')
### 初筛出错的URL
PMIDs_filepath_pri_err = os.path.join(pmids_dir, "errorURLs_pri.xlsx")
### 复筛出错的URL
PMIDs_filepath_re_err = os.path.join(pmids_dir, "errorURLs_re.xlsx")
### 复筛所有URL及status
PMIds_filepath_re_status = os.path.join(pmids_dir, "url_status.xlsx")
### 纳入文章所有URL
PMIDs_filepath_in= os.path.join(pmids_dir, "included.xlsx")
statistics_filename = 'animal0208.txt'

data_filepath = os.path.join(pmids_dir, 'included_data.xlsx')

### 初筛所有结果json文件保存路径
pri_json_files_dir = os.path.join(screening_result_dir, "primary_all/json_files")
os.makedirs(pri_json_files_dir, exist_ok=True)
### 初筛所有结果json文件
pri_json_files = [os.path.join(pri_json_files_dir, f) for f in os.listdir(pri_json_files_dir) if f.endswith('.json')]
### 复筛所有结果json文件保存路径
re_json_files_dir = os.path.join(screening_result_dir, "re_all/json_files")
os.makedirs(re_json_files_dir, exist_ok=True)
### 纳入文章json数据表保存路径
in_json_files_dir = os.path.join(screening_result_dir, "Included/json_files")
os.makedirs(in_json_files_dir, exist_ok=True)
# CD8 
PMIDs_filepath_CD8 = os.path.join(pmids_dir, "CD8test1.xlsx")
CD8_json_files_dir = os.path.join(screening_result_dir, "CD8")
os.makedirs(CD8_json_files_dir, exist_ok=True)
# data 
PMIDs_filepath_data = os.path.join(pmids_dir, "data.xlsx")
data_json_files_dir = os.path.join(screening_result_dir, "data")
os.makedirs(data_json_files_dir, exist_ok=True)
### 复筛所有结果json文件
re_json_files = [os.path.join(re_json_files_dir, f) for f in os.listdir(re_json_files_dir) if f.endswith('.json')]
##################################################################################
# 初筛排除结果md保存路径
md_priEx_path = os.path.join(screening_result_dir, 'PrimaryExcluded')
os.makedirs(md_priEx_path, exist_ok=True)
# 初筛纳入结果md保存路径
md_priIn_path = os.path.join(screening_result_dir, 'PrimaryIncluded')
os.makedirs(md_priIn_path, exist_ok=True) 
# 复筛排除结果md保存路径
md_reEx_path = os.path.join(screening_result_dir, 'ReExcluded')
os.makedirs(md_reEx_path, exist_ok=True)
# 复筛纳入结果md保存路径
md_in_path = os.path.join(screening_result_dir, 'Included')
os.makedirs(md_in_path, exist_ok=True)
# 图片分析结果md保存路径
img_text_path = os.path.join(screening_result_dir, 'Images')
os.makedirs(img_text_path, exist_ok=True)
item_path = os.path.join(screening_result_dir, 'Items')
os.makedirs(item_path, exist_ok=True)
# 期刊年份统计结果md保存路径
stat_text_path = os.path.join(screening_result_dir, "statistics")
os.makedirs(stat_text_path, exist_ok=True)
### 图片分析结果md文件
img_text_filepaths = [os.path.join(img_text_path, f) for f in os.listdir(img_text_path) if f.endswith('.md')]

############## 
def batch_items(input_file):
    # 读取输入文件
    df = pd.read_excel(input_file)
    inputs = df.iloc[:, 0].tolist()  # 假设输入参数在第一列
    ids = df.iloc[:, 1].tolist()[:] # id在第二列

    start_time = datetime.now()  # 记录总的开始时间
    
    for i, input_param in enumerate(tqdm(inputs, desc="Processing items", unit="item")):
        # 工作流和智能体编排应用自定义输入参数透传
        biz_params = {"data": input_param}
        output_file = f'article{ids[i]}.md'
        output_filepath = os.path.join(item_path, output_file)
        call_agent_app_items(biz_params, output_filepath)  
        
    end_time = datetime.now()  # 记录总的结束时间
    total_duration = (end_time - start_time).total_seconds()
    print(f'\nTotal processing time: {total_duration:.2f} seconds')

def batch_scraper(input_file):
    # 读取输入文件
    df = pd.read_excel(input_file)
    inputs = df.iloc[:, 0].tolist()  # 假设输入参数在第一列

    start_time = datetime.now()  # 记录总的开始时间
    for i, input_param in enumerate(tqdm(inputs, desc="Processing items", unit="item")):
        # 工作流和智能体编排应用自定义输入参数透传
        biz_params = {"url": input_param}
        output_file = f'article{i+1}.md'
        output_filepath = os.path.join(articles_dir, output_file)
        call_agent_app_scraper_abs(biz_params, output_filepath)  
        
    end_time = datetime.now()  # 记录总的结束时间
    total_duration = (end_time - start_time).total_seconds()
    print(f'\nTotal processing time: {total_duration:.2f} seconds')

def call_agent_app_items(input_param, output_filepath):
    response = Application.call(app_id=APP_ID_ANIMAL_ITEM,
                                biz_params = input_param,
                                prompt=' ',
                                api_key=API_KEY,)

    if response.status_code != HTTPStatus.OK:
        print('request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
    else:
        # 提取 text 字段的内容
        text_content = response.output.get('text', '')
        with open(output_filepath, 'w', encoding='utf-8') as file:
            file.write(text_content)

def call_agent_app_scraper_abs(input_param, output_filepath):
    response = Application.call(app_id=APP_ID_SCRAPER_ABS,
                                biz_params = input_param,
                                prompt=' ',
                                api_key=API_KEY,)

    if response.status_code != HTTPStatus.OK:
        print('request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
    else:
        # 提取 text 字段的内容
        text_content = response.output.get('text', '')
        with open(output_filepath, 'w', encoding='utf-8') as file:
            file.write(text_content)


def batch_run_statistics(input_file):    
    # 读取输入文件
    df = pd.read_excel(input_file)
    inputs = df.iloc[:, 0].tolist()  # 假设输入参数在第一列

    start_time = datetime.now()  # 记录总的开始时间
    
    for i, input_param in enumerate(tqdm(inputs, desc="Processing items", unit="item")):
        # 工作流和智能体编排应用自定义输入参数透传
        biz_params = {"url": input_param, "filename":statistics_filename}
        output_file = f'article{i+1}.md'
        output_filepath = os.path.join(stat_text_path, output_file)
        call_agent_app_statistics(biz_params, output_filepath)  
        
    end_time = datetime.now()  # 记录总的结束时间
    total_duration = (end_time - start_time).total_seconds()
    print(f'\nTotal processing time: {total_duration:.2f} seconds')

def call_agent_app_statistics(input_param, output_filepath):
    response = Application.call(app_id=APP_ID_STATISTICS,
                                biz_params = input_param,
                                prompt=' ',
                                api_key=API_KEY,)

    if response.status_code != HTTPStatus.OK:
        print('request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
    else:
        # 提取 text 字段的内容
        text_content = response.output.get('text', '')
        with open(output_filepath, 'w', encoding='utf-8') as file:
            file.write(text_content)


def batch_run_images_content(md_filepaths, batch_size, output_dir):    

    total_batches = (len(md_filepaths) + batch_size - 1) // batch_size  # 计算总批次数
    start_time = datetime.now()  # 记录总的开始时间
    results = []

    for i, md_filepath in enumerate(tqdm(md_filepaths, desc="Processing items", unit="item")):
        # 工作流和智能体编排应用自定义输入参数透传
        with open(md_filepath, 'r', encoding='utf-8') as file:
            input_param = file.read()
        biz_params = {"image_text": input_param}
        output_file = md_filepath.split('\\')[-1]
        output_filepath = os.path.join(output_dir, output_file)
        call_agent_app_images_content(biz_params, output_filepath)

        
    end_time = datetime.now()  # 记录总的结束时间
    total_duration = (end_time - start_time).total_seconds()
    print(f'\nTotal processing time: {total_duration:.2f} seconds')

def call_agent_app_images_content(input_param, output_filepath):
    response = Application.call(app_id=APP_ID_IMAGES_CONTENT,
                                biz_params = input_param,
                                prompt=' ',
                                api_key=API_KEY,)

    if response.status_code != HTTPStatus.OK:
        print('request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
    else:
        # 提取 text 字段的内容
        text_content = response.output.get('text', '')
        with open(output_filepath, 'w', encoding='utf-8') as file:
            file.write(text_content)


def call_agent_app_images_text(input_param, output_filepath):
    response = Application.call(app_id=APP_ID_IMAGES_TEXT,
                                biz_params = input_param,
                                prompt=' ',
                                api_key=API_KEY,)

    if response.status_code != HTTPStatus.OK:
        print('request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
    else:
        # 提取 text 字段的内容
        text_content = response.output.get('text', '')
        with open(output_filepath, 'w', encoding='utf-8') as file:
            file.write(text_content)

def batch_run_images_text(input_file):    
    # 读取输入文件
    df = pd.read_excel(input_file)
    inputs = df.iloc[:, 0].tolist()  # 假设输入参数在第一列
    ids = df.iloc[:, 1].tolist()[:] # id在第二列

    start_time = datetime.now()  # 记录总的开始时间
    
    for i, input_param in enumerate(tqdm(inputs, desc="Processing items", unit="item")):
        # 工作流和智能体编排应用自定义输入参数透传
        biz_params = {"url": input_param}
        output_file = f'article{ids[i]}.md'
        output_filepath = os.path.join(img_text_path, output_file)
        call_agent_app_images_text(biz_params, output_filepath)  
        
    end_time = datetime.now()  # 记录总的结束时间
    total_duration = (end_time - start_time).total_seconds()
    print(f'\nTotal processing time: {total_duration:.2f} seconds')


# PMIDs工作流
def call_agent_app_pmids(input_param, output_file, output_dir):
    response = Application.call(app_id=APP_ID_PMIDS,
                                biz_params = input_param,
                                prompt=' ',
                                api_key=API_KEY,)

    if response.status_code != HTTPStatus.OK:
        print('request_id=%s, code=%s, message=%s\n' % (response.request_id, response.status_code, response.message))
    else:
        print(response.output)
        # 提取 text 字段的内容
        text_content = response.output.get('text', '')
        try:
            # 将 text 字段的内容解析为字典
            data = json.loads(text_content)
            
            # 检查 pmidURLs 是否存在于解析后的数据中
            if 'pmidURLs' in data:
                pmid_links = data['pmidURLs']
                
                # 创建输出目录（如果它不存在）
                os.makedirs(output_dir, exist_ok=True)
                
                # 构建完整的输出文件路径
                output_file = os.path.join(output_dir, output_file)
                
                # 将所有 URL 存储到 DataFrame 中
                output_df = pd.DataFrame(pmid_links, columns=['URL'])
                # 新增一列 ID，从 1 开始编号
                output_df['ID'] = range(1, len(output_df) + 1)
                
                # 将 DataFrame 写入 Excel 文件
                output_df.to_excel(output_file, index=False, engine='openpyxl')
                
                print(f'Saved {len(pmid_links)} URLs to {output_file}')
            else:
                print("The key 'pmidURLs' was not found in the parsed JSON.")
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")

# 筛选工作流
def call_agent_app_screening(input_param, ScreenStage):
    if ScreenStage == 0:
        appid = APP_ID_PRISCREEN
    elif ScreenStage == 1:
        appid = APP_ID_RESCREEN_ANI
    elif ScreenStage == 2:
        appid = APP_ID_RESCREEN_CLI
    elif ScreenStage == 3:
        appid = APP_ID_TABLE_ANI
    elif ScreenStage == 4:
        appid = APP_ID_QUA_ANI
    try:
        # 尝试调用API
        response = Application.call(
            app_id=appid,
            biz_params=input_param,  # 传递输入参数
            prompt=" ",
            api_key=API_KEY
        )
    except Exception as e:
        # 捕获所有异常并打印错误信息
        print(f"Error occurred: {e}")
        return None
    
    if response.status_code != HTTPStatus.OK:
        print(f'request_id={response.request_id}, code={response.status_code}, message={response.message}')
        return None
    else:
        # 提取 text 字段的内容
        text_content = response.output.get('text', None)
        if text_content is None:
            print("Error: text_content is None")
            return None
        try:
            # 将 text 字段的内容解析为字典
            result_dict = json.loads(text_content)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            result_dict = {"error": "JSON parsing failed"}
        
        return result_dict

# 将筛选结果保存到md文件中
def write_md(analysis_in, analysis_ex, stage):     
    # 排除结果保存
    for index, entry in enumerate(analysis_ex):
        # 初筛排除
        if stage == 0: 
            # 初筛字段提取
            field_ex = 'PriExcluded'
            
            # 初筛结果保存文件路径
            analy_file_name = os.path.join(md_priEx_path, f"article{index+1}_analy.md")  # 中断
            analy_ex = entry['output'][field_ex]
            with open(analy_file_name, 'w', encoding='utf-8') as file:
                file.write(analy_ex)
            # data_ex_file_name = os.path.join(md_priEx_path, f"{index+1}_data.md")
        # # 复筛排除
        # else:
        #      # 复筛字段提取
        #     field_ex = 'ReExcluded'
            
        #     # 复筛结果保存文件路径
        #     reason_file_name = os.path.join(md_reEx_path, f"{index+1}_reason.md")
        #     data_ex_file_name = os.path.join(md_reEx_path, f"{index+1}_data.md")
            
        # reason = entry['output'][field_ex]["reason"]
        # data_ex = entry['output'][field_ex]["data"]
        # with open(reason_file_name, 'w', encoding='utf-8') as file:
        #     file.write(reason)
        # with open(data_ex_file_name, 'w', encoding='utf-8') as file:
        #     file.write(data_ex)

        
    # 纳入结果保存       
    for index, entry in enumerate(analysis_in):
        # 初筛纳入
        if stage == 0: 
            # 初筛字段提取
            field_in = 'PriIncluded'
            analy_in = entry['output'][field_in]
            # data_in = entry['output'][field_in]["data"]

            # 初筛结果保存文件路径
            analy_file_name = os.path.join(md_priIn_path, f"article{index+1}_analy.md") # 中断
            # data_in_file_name = os.path.join(md_priIn_path, f"{index+1}_data.md")
            with open(analy_file_name, 'w', encoding='utf-8') as file:
                file.write(analy_in)
        #     with open(data_in_file_name, 'w', encoding='utf-8') as file:
        #         file.write(data_in)
        # # 复筛纳入
        # else:
        #      # 复筛字段提取
        #     field_in = 'Included'
            
        #     # 复筛结果保存文件路径
        #     anlys_file_name = os.path.join(md_in_path, f"{index+1}_anlys.md")
        #     assess_file_name = os.path.join(md_in_path, f"{index+1}_assess.md") 
        #     data_in_file_name = os.path.join(md_in_path, f"{index+1}_data.md")

        #     anlys = entry['output'][field_in]["fulltext_anlys"]
        #     assess = entry['output'][field_in]["assess"]
        #     data_in = entry['output'][field_in]["data"]
         
        #     with open(anlys_file_name, 'w', encoding='utf-8') as file:
        #         file.write(anlys)
        #     with open(assess_file_name, 'w', encoding='utf-8') as file:
        #         file.write(assess) 
        #     with open(data_in_file_name, 'w', encoding='utf-8') as file:
        #         file.write(data_in)   
        
            

# 批量筛选多篇文献
def batch_run(input_file, output_dir, output_prefix, batch_size, stage):
    # 读取输入文件
    df = pd.read_excel(input_file)
    inputs = df.iloc[:, 0].tolist()[:] # 假设输入参数在第一列
    ids = df.iloc[:, 1].tolist()[:] # id在第二列

    results = []
    total_batches = (len(inputs) + batch_size - 1) // batch_size  # 计算总批次数
    start_time = datetime.now()  # 记录总的开始时间
    
    for i, input_param in enumerate(tqdm(inputs, desc="Processing items", unit="item")):
        # 打印当前处理的轮次
        if (i % batch_size == 0) or (i == len(inputs) - 1):
            current_batch = (i // batch_size) + 1
            batch_start_time = datetime.now()  # 记录当前批次的开始时间
            print(f'\nProcessing batch {current_batch} of {total_batches}')
        
        # 工作流和智能体编排应用自定义输入参数透传
        biz_params = {"url": input_param}
        
        # 错误处理机制
        retry_count = 0
        max_retries = 3
        result = None
        
        while retry_count < max_retries:
            result = call_agent_app_screening(biz_params, stage)
            if result is not None:
                break
            retry_count += 1
            print(f"Retrying {retry_count} of {max_retries} for input: {input_param}")
        
        if result is not None:
            # 将结果添加到 results 列表中
            results.append({'input': input_param, 'output': result, 'id': ids[i]})
        else:
            print(f"Failed to process input {input_param} after {max_retries} retries")
        
        # 每处理batch_size个结果或到达最后一个结果时保存一次
        if (i + 1) % batch_size == 0 or (i + 1) == len(inputs):
            output_file = f'{output_prefix}_article{ids[i]}.json' # 中断
            output_filepath = os.path.join(output_dir, output_file)
            
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            
            batch_end_time = datetime.now()  # 记录当前批次的结束时间
            batch_duration = (batch_end_time - batch_start_time).total_seconds()
            print(f'Saved {len(results)} results to {output_filepath}')
            print(f'Batch {current_batch} processing time: {batch_duration:.2f} seconds')
            results = []  # 清空结果列表，准备下一批数据
            if stage <= 2:
                if stage==0:
                    url_file = PMIDs_filepath_pri
                    url_file_error = PMIDs_filepath_pri_err
                    json_files = pri_json_files
                    json_files_dir = pri_json_files_dir
                    output_url_file = PMIDs_filepath_re
                else:
                    url_file = PMIDs_filepath_re
                    url_file_error = PMIDs_filepath_re_err
                    json_files = re_json_files
                    json_files_dir = re_json_files_dir
                    output_url_file = PMIds_filepath_re_status

                ### 分析结果处理
                #### 1.在url_file中标记Error列为1记录处理过程中出错的文章
                # mark_errors_in_excel(url_file, json_files)
                # print(f"出错文章已在{url_file} Error列标记为1")
                category_counts = {
                    "PriExcluded": 0,  
                    "PriIncluded": 0,  # status = 1
                    "ReExcluded": 0,  # status = 2
                    "Included": 0,  # status = 3
                    "AScraperFailed": 0,  # status = 5
                    "FScraperFailed": 0,  # status = 4
                    "Error": 0,
                    "All": 0,
                }
                #### 2.统计文章总数和出错数目,并记录所有出错文章URL到文件中
                # category_counts['All'], category_counts['Error'] = count_error_entries(url_file, url_file_error)
                # print(f"出错文章URL已记录到文件{url_file_error}中")

                #### 3.分析json文件, 按类别统计并保存分析结果为md格式
                category_counts, all_included_alyses, all_excluded_alyses = analyze_json_files(json_files_dir, output_url_file, category_counts, stage)
                # write_md(all_included_alyses, all_excluded_alyses, stage)
                # print(f"md格式分析结果已保存到{md_in_path}")
                #### 4.打印类别统计结果
                print("Category Counts:", category_counts)
                print('\n')
                
                

    end_time = datetime.now()  # 记录总的结束时间
    total_duration = (end_time - start_time).total_seconds()
    print(f'\nTotal processing time: {total_duration:.2f} seconds')


if __name__ == '__main__':
    biz_params = {
                    "term": "((((Tumor) OR (Neoplasia) OR (Neoplasm) OR (Cancer) OR (Malignant Neoplasm) OR (Malignancy) OR (Malignant) OR (Benign Neoplasms) OR (carcinoma)) AND ((X ray) OR (Roentgenotherapy) OR (X Ray Therapy))) AND ((Animal)) AND ((immunity) OR (immune) OR (Immune Response) OR (Immune Systems) OR (Immunogenic Cell Death))",
                    "minDate": "2010/01/01",
                    "maxDate": "2025/02/08"
                 }
    
     
    # call_agent_app_pmids(input_param=biz_params, output_file = "PMIDs.xlsx", output_dir=pmids_dir)
    # 获取当前时间
    now = datetime.now()

    # 将当前时间格式化为字符串
    # 注意：在文件名中使用某些字符可能会导致问题，比如冒号 (:) 在 Windows 系统中是不允许的
    # 因此，这里我们使用年-月-日_小时-分钟-秒的格式
    formatted_time = now.strftime('%Y-%m-%d_%H-%M-%S')
    output_prefix = f'{formatted_time}_'  # 输出文件前缀
    # batch_scraper(PMIDs_filepath_pri)
    # batch_run_statistics(PMIDs_filepath_pri)
    # batch_run_statistics("screening\\flur\\articleURLs\\urls_error.xlsx")


    # 初筛
    # batch_run(PMIDs_filepath_pri, pri_json_files_dir,  output_prefix, batch_size=1, stage=0)

    # 动物复筛
    # batch_run(PMIDs_filepath_re, re_json_files_dir,  output_prefix, batch_size=1, stage=1)
    # 质量评估
    # batch_run(PMIDs_filepath_in, in_json_files_dir,  output_prefix, batch_size=1, stage=4)
    # CD8
    # batch_run(PMIDs_filepath_CD8, CD8_json_files_dir,  output_prefix, batch_size=1, stage=3)
    # items
    # batch_items(data_filepath)
    # CD8
    batch_run(PMIDs_filepath_data, data_json_files_dir,  output_prefix, batch_size=1, stage=3)

    # 临床复筛
    # batch_run(PMIDs_filepath_re, re_json_files_dir,  output_prefix, batch_size=5, stage=2)

    # batch_run(PMIDs_filepath_in, in_json_files_dir,  output_prefix, batch_size=1, stage=3)

    # 图表分析
    # batch_run_images_text(PMIDs_filepath_in)
    # output_dir=os.path.join(img_text_path, 'IFN-gamma')
    # os.makedirs(output_dir, exist_ok=True)
    # batch_run_images_content(img_text_filepaths, 1, output_dir)

    # stage = 0
    # if stage==0:
    #     url_file = PMIDs_filepath_pri
    #     url_file_error = PMIDs_filepath_pri_err
    #     json_files = pri_json_files
    #     json_files_dir = pri_json_files_dir
    #     output_url_file = PMIDs_filepath_re
    # else:
    #     url_file = PMIDs_filepath_re
    #     url_file_error = PMIDs_filepath_re_err
    #     json_files = re_json_files
    #     json_files_dir = re_json_files_dir
    #     output_url_file = PMIds_filepath_re_status

    ### 分析结果处理
    #### 1.在url_file中标记Error列为1记录处理过程中出错的文章
    # mark_errors_in_excel(url_file, json_files)
    # print(f"出错文章已在{url_file} Error列标记为1")
    # category_counts = {
    #     "PrimaryExcluded": 0,  
    #     "PrimaryIncluded": 0,  # status = 1
    #     "ReExcluded": 0,  # status = 2
    #     "Included": 0,  # status = 3
    #     "AScraperFailed": 0,  # status = 5
    #     "FScraperFailed": 0,  # status = 4
    #     "Error": 0,
    #     "All": 0,
    # }
    # #### 2.统计文章总数和出错数目,并记录所有出错文章URL到文件中
    # category_counts['All'], category_counts['Error'] = count_error_entries(url_file, url_file_error)
    # print(f"出错文章URL已记录到文件{url_file_error}中")

    # #### 3.分析json文件, 按类别统计并保存分析结果为md格式
    # category_counts, all_included_alyses, all_excluded_alyses = analyze_json_files(json_files_dir, output_url_file, category_counts, stage)
    # write_md(all_included_alyses, all_excluded_alyses, stage)
    # print(f"md格式分析结果已保存到{md_in_path}")
    # #### 4.打印类别统计结果
    # print("Category Counts:", category_counts)
    # print('\n')


