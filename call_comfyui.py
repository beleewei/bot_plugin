import random
import os
import threading
import time

import requests
import json

server_url = "http://124.223.45.165:22105/api"


# 从文件中读取 workflow_data
def load_workflow_data(level='high'):
    file_path = os.path.join(os.path.dirname(__file__), f'flux_{level}.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"未找到 {file_path} 文件，请检查文件路径。")
        return {}
    except json.JSONDecodeError:
        print(f"{file_path} 文件内容不是有效的 JSON 格式，请检查文件内容。")
        return {}


def call_comfyui_workflow(prompt_text, level='middle'):
    """
    调用 ComfyUI 工作流 API
    :param prompt_text:
    :return:
    :param api_url: ComfyUI API 服务的 URL
    :param workflow_data: 工作流的 JSON 数据
    :return: 返回生成的图像 URL 或错误信息
    """
    # 示例调用
    workflow_data = load_workflow_data(level)
    print('提示词：', workflow_data['6']['inputs']['text'])
    workflow_data['6']['inputs']['text'] = prompt_text
    headers = {"Content-Type": "application/json"}
    param_data = {"prompt": workflow_data}
    url = f"{server_url}/prompt"
    response = requests.post(url, data=json.dumps(param_data), headers=headers)
    print('求请成功！')
    if response.status_code == 200:
        result = response.json()
        print('调用结果：', result)
        print('本次调度id:', result.get("prompt_id", "error"))
        return result.get("prompt_id", "error")
    else:
        print(f"Request failed with status code {response.status_code} from {url}")
        return "error"


def query_running_queue():
    headers = {"Content-Type": "application/json"}
    query_url = f'{server_url}/queue'
    response = requests.get(query_url, headers=headers)

    if response.status_code == 200:
        result = response.json()
        # print('running_queue调用结果：', result)
        if len(result['queue_running']) > 0:
            running_id = result['queue_running'][0][1]
            print('正在运行的任务：', running_id)
            return running_id
        else:
            print('comfyui 处于空闲状态')
            return 'idle'
    else:
        print(f"Request failed with status code {response.status_code}")
        return 'error'


def download_prompt_output(prompt_id):
    test_result = query_task(prompt_id)
    if not test_result.get('code', 200) == 200:
        return {'code': 999}
    filename = test_result.get("filename", '')
    # 构造完整的 URL
    url = test_result.get('img_url')
    try:
        print('download-link:', url)
        # 发送请求
        response = requests.get(url)
        # 检查响应状态
        if response.status_code == 200:
            # 获取图片内容
            image_content = response.content
            # 保存图片到本地
            save_path = os.path.join("downloaded_images", filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as file:
                file.write(image_content)
            print(f"图片已成功保存到 {save_path}")
            return {'code': 200, 'file_path': save_path, 'file_url': url}
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return {'code': response.status_code}
    except Exception as e:
        print(f"下载图片时发生错误：{e}")
        return {'code': 999}


def query_task(prompt_id):
    """查询任务状态"""
    headers = {"Content-Type": "application/json"}
    query_url = f'{server_url}/history?max_items=64'
    response = requests.get(query_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        # print('task-result---------:\n', result, '\n-----------')
        if prompt_id in result and 'status' in result[prompt_id] and result[prompt_id]['status'].get('completed'):
            output = result[prompt_id]['outputs']['9']['images'][0]
            print(f'{prompt_id}:', result[prompt_id])
            print('任务状态', output)
            output['code'] = 200
            filename = output.get("filename", '')
            folder = output.get('subfolder', '')
            output_type = output.get('type', '')
            # 构造完整的 URL
            img_url = f"{server_url}/view?filename={filename}&subfolder={folder}&type={output_type}&rand={random.random()}"
            output['img_url'] = img_url
            return output
        else:
            return {'code': 999}
    else:
        return {'code': response.status_code}


def check_task_async(prompt_id, block=True, callback=None):
    def task_checker():
        interval = 5  # 初始间隔为5秒
        total_time = 0  # 统计总轮询时间
        while True:
            time.sleep(interval)
            total_time += interval  # 累加轮询时间
            interval = max(1, interval - 1)  # 递减间隔，最低1秒
            if query_running_queue() == prompt_id:
                print(f"执行中,继续等待...总轮询时间: {total_time} 秒")
                continue
            # 查询任务状态
            task_result = query_task(prompt_id)
            if task_result.get('code', 200) == 200:
                print(f"即将下载图片: {task_result.get('filename')}")
                result = download_prompt_output(prompt_id)
                if callback and result.get('code') == 200:
                    callback(result)
                break
            elif not task_result.get('code') == 999:
                print("flux 调用失败")
                break
            else:
                print(f"继续等待...总轮询时间: {total_time} 秒")

    # 启动新线程进行任务检查
    t = threading.Thread(target=task_checker)
    t.start()
    if block:
        t.join()


def call_create_image(prompt_text='a pretty girl face to the camera with smile',
                      level='middle',
                      block=True,
                      callback=None):
    p_id = query_running_queue()
    if not p_id == 'idle':
        print('服务正忙,调度失败')
        if callback:
            callback(None)
        return
    prompt_id = call_comfyui_workflow(prompt_text, level)
    if prompt_id == 'error':
        print('服务异常,调度失败')
        if callback:
            callback(None)
        return
    check_task_async(prompt_id, block, callback)


if __name__ == "__main__":
    print('start')
    query_task('ebcb68b5-78fa-47e1-913e-fa77d8ed0b02')
    # query_running_queue()
    # download_prompt_output('33387261-bcda-41bb-831a-29c92fcbbb35')
    # call_comfyui_workflow('The heroine in a sweet pink dress stands in a cherry blossom shower, holding a bouquet of flowers')
    prompt_text = 'A beautiful girl in a red dress, standing in a cherry blossom shower, holding a bouquet of flowers,a yellow dog stand by her'
    call_create_image(prompt_text, 'normal', block=True, callback=lambda x: print('下载完成:', x))
