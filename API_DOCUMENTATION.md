# 视频上传 API 文档

本文档说明如何通过 API 调用方式上传视频到各个社交平台。

## 基础信息

- **服务地址**: `http://localhost:5409` (默认端口)
- **最大文件大小**: 160MB
- **支持平台**: 
  - 1: 小红书
  - 2: 视频号
  - 3: 抖音
  - 4: 快手

---

## API 端点列表

### 1. 上传视频文件

#### 1.1 简单上传 (`/upload`)
只上传文件，不保存到数据库。

**请求方式**: `POST`

**请求格式**: `multipart/form-data`

**请求参数**:
- `file` (file, required): 视频文件

**响应示例**:
```json
{
  "code": 200,
  "msg": "File uploaded successfully",
  "data": "uuid_filename.mp4"
}
```

**使用示例** (Python):
```python
import requests

url = "http://localhost:5409/upload"
files = {'file': open('video.mp4', 'rb')}
response = requests.post(url, files=files)
print(response.json())
```

**使用示例** (cURL):
```bash
curl -X POST http://localhost:5409/upload \
  -F "file=@video.mp4"
```

---

#### 1.2 上传并保存 (`/uploadSave`)
上传文件并保存到数据库，推荐使用此接口。

**请求方式**: `POST`

**请求格式**: `multipart/form-data`

**请求参数**:
- `file` (file, required): 视频文件
- `filename` (string, optional): 自定义文件名（不含扩展名）

**响应示例**:
```json
{
  "code": 200,
  "msg": "File uploaded and saved successfully",
  "data": {
    "filename": "my_video.mp4",
    "filepath": "uuid_my_video.mp4"
  }
}
```

**使用示例** (Python):
```python
import requests

url = "http://localhost:5409/uploadSave"
files = {'file': open('video.mp4', 'rb')}
data = {'filename': 'my_custom_name'}  # 可选
response = requests.post(url, files=files, data=data)
print(response.json())
```

**使用示例** (cURL):
```bash
curl -X POST http://localhost:5409/uploadSave \
  -F "file=@video.mp4" \
  -F "filename=my_custom_name"
```

---

### 2. 获取文件列表

#### 2.1 获取所有已上传文件 (`/getFiles`)

**请求方式**: `GET`

**响应示例**:
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "id": 1,
      "filename": "video.mp4",
      "filesize": 50.5,
      "upload_time": "2024-01-01 12:00:00",
      "file_path": "uuid_video.mp4",
      "uuid": "uuid"
    }
  ]
}
```

**使用示例** (Python):
```python
import requests

url = "http://localhost:5409/getFiles"
response = requests.get(url)
print(response.json())
```

---

#### 2.2 获取单个文件 (`/getFile`)

**请求方式**: `GET`

**请求参数**:
- `filename` (string, required): 文件名（包含UUID前缀）

**响应**: 返回文件流

**使用示例** (Python):
```python
import requests

url = "http://localhost:5409/getFile"
params = {'filename': 'uuid_video.mp4'}
response = requests.get(url, params=params)
with open('downloaded_video.mp4', 'wb') as f:
    f.write(response.content)
```

---

### 3. 获取账号列表

#### 3.1 获取所有账号 (`/getAccounts`)

**请求方式**: `GET`

**响应示例**:
```json
{
  "code": 200,
  "msg": None,
  "data": [
    [1, 2, "cookie_file_path.json", "账号名称", 1]
  ]
}
```

**数据格式说明**:
- `[0]`: id (账号ID)
- `[1]`: type (平台类型: 1=小红书, 2=视频号, 3=抖音, 4=快手)
- `[2]`: filePath (Cookie文件路径)
- `[3]`: userName (账号名称)
- `[4]`: status (状态: 0=异常, 1=正常)

**使用示例** (Python):
```python
import requests

url = "http://localhost:5409/getAccounts"
response = requests.get(url)
accounts = response.json()['data']
for account in accounts:
    print(f"ID: {account[0]}, 平台: {account[1]}, 名称: {account[3]}")
```

---

#### 3.2 获取有效账号 (`/getValidAccounts`)

**请求方式**: `GET`

**说明**: 会验证Cookie有效性，更新账号状态

**响应格式**: 同 `/getAccounts`

---

### 4. 发布视频 (`/postVideo`)

**这是核心API，用于将已上传的视频发布到各个社交平台。**

**请求方式**: `POST`

**请求格式**: `application/json`

**请求参数**:
```json
{
  "type": 2,                    // 平台类型: 1=小红书, 2=视频号, 3=抖音, 4=快手
  "title": "视频标题",           // 视频标题
  "tags": ["话题1", "话题2"],    // 话题标签列表（不带#号）
  "fileList": [                 // 视频文件路径列表（使用上传后返回的filepath）
    "uuid_video1.mp4",
    "uuid_video2.mp4"
  ],
  "accountList": [               // 账号Cookie文件路径列表
    "account1.json",
    "account2.json"
  ],
  "category": 0,                 // 分类: 0=非原创, 其他值根据平台而定
  "enableTimer": 1,             // 是否启用定时发布: 0=立即发布, 1=定时发布
  "videosPerDay": 1,             // 每天发布视频数量 (1-55)
  "dailyTimes": ["10:00", "14:00"], // 每天发布时间点列表
  "startDays": 0,                // 从今天开始计算的发布天数: 0=明天, 1=后天
  "productLink": "",             // 商品链接（抖音平台）
  "productTitle": "",            // 商品名称（抖音平台）
  "thumbnail": "",               // 缩略图路径（抖音平台）
  "isDraft": false               // 是否保存为草稿（仅视频号平台）
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": None,
  "data": None
}
```

**使用示例** (Python):
```python
import requests
import json

url = "http://localhost:5409/postVideo"

# 首先上传视频文件
upload_url = "http://localhost:5409/uploadSave"
with open('video.mp4', 'rb') as f:
    upload_response = requests.post(
        upload_url, 
        files={'file': f}
    )
upload_data = upload_response.json()
video_filepath = upload_data['data']['filepath']

# 获取账号列表
accounts_url = "http://localhost:5409/getAccounts"
accounts_response = requests.get(accounts_url)
accounts = accounts_response.json()['data']

# 选择要使用的账号（这里选择第一个账号）
account_filepath = accounts[0][2]  # filePath字段

# 发布视频
publish_data = {
    "type": 2,  # 视频号
    "title": "我的视频标题",
    "tags": ["话题1", "话题2"],
    "fileList": [video_filepath],
    "accountList": [account_filepath],
    "category": 0,
    "enableTimer": 0,  # 立即发布
    "videosPerDay": 1,
    "dailyTimes": ["10:00"],
    "startDays": 0,
    "productLink": "",
    "productTitle": "",
    "thumbnail": "",
    "isDraft": False
}

response = requests.post(
    url,
    json=publish_data,
    headers={'Content-Type': 'application/json'}
)

print(response.json())
```

**使用示例** (cURL):
```bash
curl -X POST http://localhost:5409/postVideo \
  -H "Content-Type: application/json" \
  -d '{
    "type": 2,
    "title": "我的视频标题",
    "tags": ["话题1", "话题2"],
    "fileList": ["uuid_video.mp4"],
    "accountList": ["account.json"],
    "category": 0,
    "enableTimer": 0,
    "videosPerDay": 1,
    "dailyTimes": ["10:00"],
    "startDays": 0,
    "productLink": "",
    "productTitle": "",
    "thumbnail": "",
    "isDraft": false
  }'
```

---

### 5. 批量发布视频 (`/postVideoBatch`)

**请求方式**: `POST`

**请求格式**: `application/json`

**请求参数**: 数组格式，每个元素同 `/postVideo` 的参数

**使用示例** (Python):
```python
import requests

url = "http://localhost:5409/postVideoBatch"

batch_data = [
    {
        "type": 2,
        "title": "视频1",
        "tags": ["话题1"],
        "fileList": ["uuid_video1.mp4"],
        "accountList": ["account1.json"],
        "category": 0,
        "enableTimer": 0,
        "videosPerDay": 1,
        "dailyTimes": ["10:00"],
        "startDays": 0
    },
    {
        "type": 3,
        "title": "视频2",
        "tags": ["话题2"],
        "fileList": ["uuid_video2.mp4"],
        "accountList": ["account2.json"],
        "category": 0,
        "enableTimer": 0,
        "videosPerDay": 1,
        "dailyTimes": ["10:00"],
        "startDays": 0
    }
]

response = requests.post(url, json=batch_data)
print(response.json())
```

---

## 完整工作流程示例

以下是一个完整的Python脚本示例，展示如何通过API上传并发布视频：

```python
import requests
import json

BASE_URL = "http://localhost:5409"

def upload_video(file_path, custom_name=None):
    """上传视频文件"""
    url = f"{BASE_URL}/uploadSave"
    files = {'file': open(file_path, 'rb')}
    data = {}
    if custom_name:
        data['filename'] = custom_name
    
    response = requests.post(url, files=files, data=data)
    files['file'].close()
    
    if response.json()['code'] == 200:
        return response.json()['data']['filepath']
    else:
        raise Exception(f"上传失败: {response.json()['msg']}")

def get_accounts():
    """获取账号列表"""
    url = f"{BASE_URL}/getAccounts"
    response = requests.get(url)
    
    if response.json()['code'] == 200:
        return response.json()['data']
    else:
        raise Exception(f"获取账号失败: {response.json()['msg']}")

def publish_video(video_filepath, account_filepath, platform_type, title, tags):
    """发布视频"""
    url = f"{BASE_URL}/postVideo"
    
    data = {
        "type": platform_type,  # 1=小红书, 2=视频号, 3=抖音, 4=快手
        "title": title,
        "tags": tags,
        "fileList": [video_filepath],
        "accountList": [account_filepath],
        "category": 0,
        "enableTimer": 0,  # 0=立即发布, 1=定时发布
        "videosPerDay": 1,
        "dailyTimes": ["10:00"],
        "startDays": 0,
        "productLink": "",
        "productTitle": "",
        "thumbnail": "",
        "isDraft": False
    }
    
    response = requests.post(
        url,
        json=data,
        headers={'Content-Type': 'application/json'}
    )
    
    return response.json()

# 使用示例
if __name__ == "__main__":
    try:
        # 1. 上传视频
        print("正在上传视频...")
        video_filepath = upload_video("my_video.mp4", "我的视频")
        print(f"上传成功，文件路径: {video_filepath}")
        
        # 2. 获取账号列表
        print("正在获取账号列表...")
        accounts = get_accounts()
        print(f"找到 {len(accounts)} 个账号")
        
        # 选择第一个账号（假设是视频号，type=2）
        account = accounts[0]
        account_filepath = account[2]  # filePath字段
        platform_type = account[1]     # type字段
        
        # 3. 发布视频
        print("正在发布视频...")
        result = publish_video(
            video_filepath=video_filepath,
            account_filepath=account_filepath,
            platform_type=platform_type,
            title="我的视频标题",
            tags=["话题1", "话题2"]
        )
        
        if result['code'] == 200:
            print("发布成功！")
        else:
            print(f"发布失败: {result['msg']}")
            
    except Exception as e:
        print(f"错误: {e}")
```

---

## 平台特定参数说明

### 小红书 (type=1)
- 不支持 `isDraft` 参数
- 不支持 `productLink` 和 `productTitle`

### 视频号 (type=2)
- 支持 `isDraft` 参数（保存为草稿）
- 不支持 `productLink` 和 `productTitle`
- 不支持 `thumbnail`

### 抖音 (type=3)
- 支持 `productLink` 和 `productTitle`（商品链接和名称）
- 支持 `thumbnail`（缩略图路径）
- 不支持 `isDraft`

### 快手 (type=4)
- 不支持 `isDraft` 参数
- 不支持 `productLink` 和 `productTitle`
- 不支持 `thumbnail`

---

## 错误处理

所有API响应都遵循以下格式：

**成功响应**:
```json
{
  "code": 200,
  "msg": "success message",
  "data": {...}
}
```

**错误响应**:
```json
{
  "code": 400/500,
  "msg": "error message",
  "data": None
}
```

常见错误码：
- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 注意事项

1. **文件路径**: `fileList` 中的路径必须是上传后返回的完整文件名（包含UUID前缀）
2. **账号路径**: `accountList` 中的路径是Cookie文件的相对路径，可通过 `/getAccounts` 获取
3. **定时发布**: 如果 `enableTimer=1`，需要设置 `videosPerDay`、`dailyTimes` 和 `startDays`
4. **文件大小**: 单个文件最大160MB
5. **并发**: 发布操作是异步的，API会立即返回，实际发布在后台进行

---

## 测试建议

1. 先使用 `/uploadSave` 上传一个测试视频
2. 使用 `/getFiles` 确认文件已上传
3. 使用 `/getAccounts` 获取可用账号
4. 使用 `/postVideo` 发布视频
5. 检查平台确认视频是否成功发布
