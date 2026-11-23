import requests

BASE_URL = "http://localhost:5409"

# 平台类型映射
PLATFORM_NAMES = {
    1: "小红书",
    2: "视频号",
    3: "抖音",
    4: "快手"
}

# 1. 上传视频
with open(r'E:\social-auto-upload-main\social-auto-upload-main\videos\demo.mp4', 'rb') as f:
    response = requests.post(
        f"{BASE_URL}/uploadSave",
        files={'file': f}
    )
video_filepath = response.json()['data']['filepath']

# 2. 选择平台和账号
platform_type = 3  # 1=小红书, 2=视频号, 3=抖音, 4=快手
account_name = "鹿鸣之音"  # 填写你要使用的账号名称（userName）

# 获取所有账号
accounts = requests.get(f"{BASE_URL}/getAccounts").json()['data']

# 在指定平台下查找匹配的账号名称
account_filepath = None
for acc in accounts:
    # acc格式: [id, type, filePath, userName, status]
    if acc[1] == platform_type and acc[3] == account_name:  # 匹配平台类型和账号名称
        account_filepath = acc[2]  # filePath
        platform_name = PLATFORM_NAMES.get(platform_type, f"平台{platform_type}")
        print(f"✅ 找到账号: {account_name} ({platform_name})")
        break

if account_filepath is None:
    # 列出该平台下的所有账号，方便用户查看
    platform_accounts = [acc for acc in accounts if acc[1] == platform_type]
    platform_name = PLATFORM_NAMES.get(platform_type, f"平台{platform_type}")
    
    if platform_accounts:
        print(f"❌ 在{platform_name}下未找到账号 '{account_name}'")
        print(f"{platform_name}下的可用账号:")
        for acc in platform_accounts:
            status = "正常" if acc[4] == 1 else "异常"
            print(f"  - {acc[3]} (状态: {status})")
    else:
        print(f"❌ {platform_name}下没有任何账号")
    raise Exception(f"未找到匹配的账号: 平台={platform_name}({platform_type}), 账号名称={account_name}")

# 3. 发布视频
publish_data = {
    "type": platform_type,  # 使用选择的平台类型
    "title": "我的视频标题",
    "tags": ["话题1", "话题2"],
    "fileList": [video_filepath],
    "accountList": [account_filepath],
    "category": 0,
    "enableTimer": 0,  # 0=立即发布, 1=定时发布
    "videosPerDay": 1,
    "dailyTimes": ["10:00"],
    "startDays": 0,
    "isDraft": False
}

response = requests.post(
    f"{BASE_URL}/postVideo",
    json=publish_data
)
print(response.json())