import requests
import os
import certifi

def download_file(url, save_folder, filename=None):
    os.makedirs(save_folder, exist_ok=True)

    if filename is None:
        filename = url.split('/')[-1]

    # 完整的文件路径
    file_path = os.path.join(save_folder, filename)

    # 如果文件已经存在，则不下载
    if os.path.exists(file_path):
        print(f"文件 {file_path} 已存在，跳过下载.")
        return file_path


    try:
        # 发送 HTTP 请求
        response = requests.get(url, stream=True, verify=certifi.where())
        response.raise_for_status()  # 检查请求是否成功

        # 保存文件
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return file_path

    except requests.exceptions.RequestException as e:
        print(f"下载文件时出错: {e}")
        

def remove_file(file_path):
    try:
        os.remove(file_path)
        print(f"文件 {file_path} 已成功删除.")
    except FileNotFoundError:
        print(f"文件 {file_path} 不存在.")
    except Exception as e:
        print(f"删除文件时出错: {e}")
