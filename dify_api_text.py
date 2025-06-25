# dify_api.py
import requests
import os
import json

def run_workflow(input_text: str, user: str, dify_api_key: str, input_variable_name: str, output_variable_name: str, local_save_path: str) -> bool:
    """
    以流式模式运行一个“文本输入、文本输出”的Dify工作流。

    该函数会：
    1. 将输入文本作为变量直接发送给工作流。
    2. 实时监听 'text_chunk' 事件，拼接完整的输出字符串。
    3. 在控制台以打字机效果实时打印输出。
    4. 在工作流成功结束后，将完整的输出文本保存到本地文件。
    5. 能够处理流式数据中的异常或损坏行。

    :param input_text: 要作为输入的完整文本字符串。
    :param user: 用户标识。
    :param dify_api_key: Dify 应用的 API Key。
    :param input_variable_name: 工作流中定义的输入文本变量名。
    :param output_variable_name: 工作流中定义的输出文本变量名 (此版本中主要用于逻辑清晰)。
    :param local_save_path: 最终输出文本的本地保存路径。
    :return: 如果工作流成功执行并保存文件，返回 True，否则返回 False。
    """
    workflow_url = "https://api.dify.ai/v1/workflows/run"
    headers = {
        "Authorization": f"Bearer {dify_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "inputs": {
            input_variable_name: input_text
        },
        "response_mode": "streaming",
        "user": user,
    }

    try:
        print("运行工作流 (文本模式)...")
        response = requests.post(workflow_url, headers=headers, json=data, stream=True)
        response.raise_for_status()

        print("\n--- 开始接收流式响应 ---")
        final_text_chunks = []
        workflow_succeeded = False

        for line in response.iter_lines():
            if not line:
                continue

            decoded_line = line.decode('utf-8')
            if not decoded_line.startswith('data:'):
                continue

            json_str = decoded_line[len('data:'):].strip()
            try:
                event_data = json.loads(json_str)
                event = event_data.get('event')

                # 实时打印节点状态，提供进度反馈
                if event == 'node_started':
                    node_title = event_data.get('data', {}).get('title', '')
                    print(f"\n> 节点 '{node_title}' 开始执行...")

                # 核心：监听 text_chunk 事件来构建输出
                elif event == 'text_chunk':
                    text_chunk = event_data.get('data', {}).get('text', '')
                    final_text_chunks.append(text_chunk)
                    print(text_chunk, end='', flush=True)

                # 监听最终事件以确认成功状态
                elif event == 'workflow_finished':
                    if event_data.get('data', {}).get('status') == 'succeeded':
                        print("\n\n工作流确认成功完成。")
                        workflow_succeeded = True
                    else:
                        error_msg = event_data.get('data', {}).get('error', '未知错误')
                        print(f"\n工作流执行失败: {error_msg}")
                    break  # 工作流结束

                elif event == 'error':
                    print(f"\nAPI返回错误事件: {event_data}")
                    break

            except json.JSONDecodeError:
                print(f"[警告] 收到损坏或无法解析的数据行，已跳过。内容: {json_str[:200]}...")
                continue

        # --- for 循环结束后，处理最终结果 ---
        if workflow_succeeded:
            print("\n--- 开始将流式输出结果写入文件 ---")
            final_text = "".join(final_text_chunks)
            try:
                with open(local_save_path, 'w', encoding='utf-8') as f:
                    f.write(final_text)
                print(f"文件成功保存到: {os.path.abspath(local_save_path)}")
                return True
            except IOError as e:
                print(f"写入文件时发生错误: {e}")
                return False
        else:
            print("\n--- 工作流未能成功完成 ---")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\n工作流请求失败: {e}")
        if e.response is not None:
            print(f"状态码: {e.response.status_code}\n服务器返回内容: {e.response.text}")
        return False
    except Exception as e:
        print(f"\n运行工作流时发生未知错误: {e}")
        return False