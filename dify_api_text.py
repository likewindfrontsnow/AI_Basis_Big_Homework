import requests
import os
import json

def run_workflow_streaming(input_text: str, user: str, dify_api_key: str, input_variable_name: str):
    """
    (生成器版本) 运行Dify工作流并以事件流的形式产出结果。
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

    try:
        print("正在连接到 Dify 工作流 (流式模式)...")
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
                    # 产出核心的文本块
                    yield 'text_chunk', text_chunk
                
                elif event == 'workflow_finished':
                    if event_data.get('data', {}).get('status') == 'succeeded':
                        # 产出工作流成功结束的信号
                        yield 'workflow_finished', None
                    else:
                        error_msg = event_data.get('data', {}).get('error', '未知工作流错误')
                        yield 'error', f"Dify 工作流失败: {error_msg}"
                    return  # 正常结束生成器

                elif event == 'error':
                    yield 'error', f"Dify API 返回错误: {event_data.get('message', '未知API错误')}"
                    return  # 发生错误，结束生成器

            except json.JSONDecodeError:
                yield 'error', f"无法解析从Dify API收到的数据行: {json_str}"
                continue
    
    except requests.exceptions.RequestException as e:
        error_details = f"请求Dify API失败: {e}"
        if e.response is not None:
            error_details += f"\n状态码: {e.response.status_code}\n服务器响应: {e.response.text}"
        yield 'error', error_details
    except Exception as e:
        yield 'error', f"运行工作流时发生未知错误: {e}"
