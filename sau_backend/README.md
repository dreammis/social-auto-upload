# MPP 后端项目文档

## 项目概述

MPP (MediaPublishPlatform) 后端是一个基于 Flask 框架构建的自媒体发布平台后端服务，提供多平台内容发布、账号管理、任务调度等核心功能。

## 技术栈

- **Web 框架**: Flask 2.0+
- **浏览器自动化**: Playwright 1.30+
- **数据库**: SQLite 3
- **异步处理**: asyncio
- **文件管理**: pathlib
- **日志管理**: 自定义日志模块
- **API 设计**: RESTful API

## 快速开始

### 环境要求

- Python 3.10
- Chrome 浏览器

### 安装与配置

1. **安装依赖**
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

2. **初始化数据库**
   ```bash
   # 删除旧数据库（如果存在）
   rm -f ../db/database.db
   # 运行数据库初始化脚本
   python ../db/createTable.py
   ```

3. **配置 Chrome 浏览器路径**
   修改 `conf.py` 文件底部的 `LOCAL_CHROME_PATH` 为本地 Chrome 浏览器地址：
   ```python
   # Windows 示例
   LOCAL_CHROME_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
   
   # Linux 示例  
   LOCAL_CHROME_PATH = "/usr/bin/google-chrome"
   
   # macOS 示例
   LOCAL_CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
   ```

4. **启动服务**
   ```bash
   python sau_backend.py
   ```

   后端服务将在 `http://localhost:5409` 启动。

## 项目结构

```
sau_backend/
├── README.md                  # 后端说明文档
├── conf.py                    # 配置文件
├── sau_backend.py             # 后端主入口文件
├── myUtils/                   # 核心工具模块
│   ├── auth.py               # 认证相关功能
│   └── login.py              # 登录相关功能
├── newFileUpload/             # 新版文件上传实现（推荐）
│   ├── baseFileUploader.py    # 通用上传器基类
│   ├── multiFileUploader.py   # 多文件上传处理
│   └── platform_configs.py    # 平台配置
├── oldFileUpload/             # 旧版文件上传实现（备用）
│   ├── examples/              # 示例脚本
│   └── uploader/              # 各平台上传器实现
└── utils/                     # 工具函数
    ├── base_social_media.py   # 社交媒体基础功能
    ├── log.py                 # 日志管理
    └── stealth.min.js         # 浏览器隐藏脚本
```

## 核心功能

### 文件上传系统

SAU 后端提供两种文件上传实现方式：

#### 新版文件上传（推荐）

**设计特点：**
- ✅ 统一基类架构，所有平台共享相同的上传流程
- ✅ 集中配置管理，便于维护和扩展
- ✅ 模块化设计，上传逻辑与平台配置分离
- ✅ 支持多平台批量发布
- ✅ 统一接口，简化调用方式

**核心文件：**
- `baseFileUploader.py` - 通用多平台上传器基类
- `multiFileUploader.py` - 多文件批量上传处理
- `platform_configs.py` - 平台配置管理

**支持平台：**
- 小红书
- 视频号
- 抖音
- 快手
- TikTok
- Instagram
- Facebook
- B站
- 百家号

#### 旧版文件上传（备用）

**设计特点：**
- ⚠️ 平台独立实现，每个平台有独立的上传器类
- ⚠️ 硬编码配置，平台特定配置在各自的上传器类中
- ⚠️ 分散式结构，代码分散在多个平台目录中
- ⚠️ 独立调用，每个平台需要单独调用对应的上传器

**支持平台：**
- 小红书
- 视频号
- 抖音
- 快手
- TikTok
- B站
- 百家号

### API 接口文档

#### 账号管理

| 接口 | 方法 | 描述 | 参数 | 返回 |
|------|------|------|------|------|
| `/getAccounts` | GET | 获取所有账号信息 | 无 | 账号列表 |
| `/getValidAccounts` | GET | 获取有效的账号信息 | 无 | 有效账号列表 |
| `/account` | POST | 添加账号 | JSON 数据 | 操作结果 |
| `/updateUserinfo` | POST | 更新账号信息 | JSON 数据 | 操作结果 |
| `/deleteAccount` | GET | 删除账号 | `id`：账号 ID | 操作结果 |
| `/downloadCookie` | GET | 下载 Cookie 文件 | `filePath`：文件路径 | Cookie 文件 |
| `/uploadCookie` | POST | 上传 Cookie 文件 | 文件数据 | 操作结果 |

#### 文件管理

| 接口 | 方法 | 描述 | 参数 | 返回 |
|------|------|------|------|------|
| `/upload` | POST | 上传文件 | 文件数据 | 文件唯一 ID |
| `/getFiles` | GET | 获取文件列表 | 无 | 文件列表 |

#### 发布管理

| 接口 | 方法 | 描述 | 参数 | 返回 |
|------|------|------|------|------|
| `/postVideo` | POST | 发布视频到单个平台 | JSON 数据 | 操作结果 |
| `/postVideosToMultiplePlatforms` | POST | 发布视频到多个平台 | JSON 数据 | 操作结果 |
| `/getPublishTaskRecords` | GET | 获取发布任务记录 | `page`：页码<br>`page_size`：每页记录数 | 任务记录列表 |
| `/getPlatformStats` | GET | 获取平台统计数据 | 无 | 平台统计信息 |
| `/cancelTask` | GET | 取消发布任务 | `id`：任务 ID | 操作结果 |
| `/taskStatus` | GET | 获取发布任务状态 | `id`：任务 ID | 任务状态 |
| `/platformConfig` | GET | 获取平台特定参数配置 | `type`：平台标识 | 平台配置 |

#### 登录接口

| 接口 | 方法 | 描述 | 参数 | 返回 |
|------|------|------|------|------|
| `/login` | GET | 登录接口（SSE 连接） | `id`：用户名<br>`type`：平台标识 | 登录二维码 |

### 平台标识对照表

| 平台 | type 字段值 | 平台标识 | 新版支持 | 旧版支持 |
|------|------------|----------|----------|----------|
| 小红书 | 1 | xiaohongshu | ✅ | ✅ |
| 腾讯视频号 | 2 | tencent | ✅ | ✅ |
| 抖音 | 3 | douyin | ✅ | ✅ |
| 快手 | 4 | kuaishou | ✅ | ✅ |
| TikTok | 5 | tiktok | ✅ | ✅ |
| Instagram | 6 | instagram | ✅ | ❌ |
| Facebook | 7 | facebook | ✅ | ❌ |
| B站 | 8 | bilibili | ✅ | ✅ |
| 百家号 | 9 | baijiahao | ✅ | ✅ |

## 数据库说明

数据库文件位于项目根目录的 `db` 文件夹中：
- `database.db` - SQLite 数据库文件
- `createTable.py` - 数据库初始化脚本

运行 `createTable.py` 可以重新创建数据库表结构，避免出现脏数据。

## 配置文件

### 主要配置项

| 配置项 | 类型 | 描述 |
|--------|------|------|
| `LOCAL_CHROME_PATH` | String | 本地 Chrome 浏览器路径 |
| `PORT` | Integer | 后端服务端口，默认 5409 |
| `DEBUG` | Boolean | 是否开启调试模式，默认 False |
| `VIDEO_FOLDER` | String | 视频文件存储目录 |
| `COOKIE_FOLDER` | String | Cookie 文件存储目录 |
| `DB_PATH` | String | 数据库文件路径 |

## 日志管理

日志文件位于 `logs` 文件夹中，包含：
- 系统运行日志
- API 请求日志
- 错误日志

## 常见问题

### 1. Cookie 过期怎么办？

当 Cookie 过期时，系统会自动检测到并标记账号状态为「失效」。您需要重新登录该账号以更新 Cookie：

1. 在账号管理页面，找到状态为「失效」的账号
2. 点击「重新登录」按钮
3. 按照提示完成登录操作
4. 系统会自动更新 Cookie 并恢复账号状态

### 2. 发布失败怎么办？

发布失败可能有多种原因，您可以：

1. 查看发布历史中的错误信息
2. 检查账号状态是否正常
3. 检查网络连接是否稳定
4. 确认平台是否有发布限制
5. 尝试重新发布

### 3. 如何添加新平台支持？

要添加新平台支持，您需要：

1. 在 `newFileUpload/platform_configs.py` 中添加平台配置
2. 在 `myUtils/login.py` 中添加登录逻辑
3. 在 `myUtils/auth.py` 中添加 Cookie 验证逻辑

## 部署

### 本地开发

按照「快速开始」中的步骤部署到本地机器。

### 生产环境

1. 配置 `conf.py` 中的生产环境参数
2. 使用 Gunicorn 或 uWSGI 启动服务
3. 配置 Nginx 反向代理
4. 设置系统服务（如 Systemd）管理进程

## 许可证

本项目采用 MIT 许可证：

```
MIT License

Copyright (c) 2026 SAU 项目团队

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 更新日志

### v1.0.0 (2026-01-13)

- ✨ 初始版本发布
- ✅ 支持小红书、腾讯视频号、抖音、快手、TikTok、Instagram 平台
- ✅ 实现视频和图文发布功能
- ✅ 支持定时发布和批量发布
- ✅ 提供完整的 Web 管理界面
- ✅ 实现新版文件上传系统（通用基类 + 平台配置）
- ✅ 保留旧版文件上传系统作为备用
