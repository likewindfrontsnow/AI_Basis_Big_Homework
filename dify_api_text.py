# dify_api_text.py
import requests
import os
import json
import time

def run_workflow_streaming(input_text: str, user: str, dify_api_key: str, input_variable_name: str, max_retries=3, delay=3):
    """
    (生成器版本) 运行Dify工作流并以事件流的形式产出结果。
    - 包含重试逻辑，用于处理网络请求错误。
    - 产出事件: ('text_chunk', 数据), ('workflow_finished', None), ('node_started', 节点标题), ('error', 错误信息)
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

    attempts = 0
    while attempts < max_retries:
        try:
            print(f"正在连接到 Dify 工作流 (流式模式)... 尝试次数 {attempts + 1}/{max_retries}")
            response = requests.post(workflow_url, headers=headers, json=data, stream=True)
            response.raise_for_status()

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

                    if event == 'node_started':
                        node_title = event_data.get('data', {}).get('title', '未知节点')
                        yield 'node_started', node_title
                    elif event == 'text_chunk':
                        text_chunk = event_data.get('data', {}).get('text', '')
                        yield 'text_chunk', text_chunk
                    elif event == 'workflow_finished':
                        if event_data.get('data', {}).get('status') == 'succeeded':
                            yield 'workflow_finished', None
                        else:
                            error_msg = event_data.get('data', {}).get('error', '未知工作流错误')
                            yield 'error', f"Dify 工作流失败: {error_msg}"
                        return
                    elif event == 'error':
                        # This is an error reported by the Dify API itself (e.g., bad input)
                        # It's unlikely to be resolved by retrying the request.
                        yield 'error', f"Dify API 返回错误: {event_data.get('message', '未知API错误')}"
                        return

                except json.JSONDecodeError:
                    yield 'error', f"无法解析从Dify API收到的数据行: {json_str}"
                    continue
            
            # If the loop completes successfully, exit the retry loop
            return

        except requests.exceptions.RequestException as e:
            attempts += 1
            error_details = f"请求Dify API失败: {e}"
            if e.response is not None:
                error_details += f"\n状态码: {e.response.status_code}\n服务器响应: {e.response.text}"
            
            if attempts >= max_retries:
                yield 'error', f"Dify API 请求在 {max_retries} 次尝试后仍然失败。最终错误: {error_details}"
                return
            
            print(f"{error_details}\n将在 {delay} 秒后重试...")
            time.sleep(delay)
        
        except Exception as e:
            # Catch any other unexpected errors
            yield 'error', f"运行工作流时发生未知错误: {e}"
            return