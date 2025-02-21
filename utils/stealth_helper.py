import requests
import os

class StealthHelper:
    @staticmethod
    def check_and_download():
        local_file_path = 'utils/stealth.min.js'
        remote_url = 'https://cdn.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js'

        # 读取本地文件的生成日期
        with open(local_file_path, 'r') as file:
            local_content = file.readlines()
            local_generated_on = [line for line in local_content if 'Generated on:' in line]
            local_date = local_generated_on[0].split(': ')[1].strip() if local_generated_on else None

        # 获取远程文件内容
        response = requests.get(remote_url)
        if response.status_code == 200:
            remote_content = response.text
            remote_generated_on = [line for line in remote_content.split('\n') if 'Generated on:' in line]
            remote_date = remote_generated_on[0].split(': ')[1].strip() if remote_generated_on else None

            # 比较日期
            if local_date != remote_date:
                # 下载并保存文件
                with open(local_file_path, 'w') as local_file:
                    local_file.write(response.text)
                print('文件已更新。')
            else:
                print('文件是最新的。')
        else:
            print('无法访问远程文件。') 
            
if __name__ == "__main__":
    StealthHelper.check_and_download()

