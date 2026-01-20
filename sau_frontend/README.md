# MPP 前端项目文档

## 项目概述

MPP (MediaPublishPlatform) 前端是一个基于 Vue 3 + Element Plus 构建的自媒体发布平台前端界面，提供直观易用的用户界面，用于管理和发布自媒体内容到多个平台。

## 🚀 特性

- ⚡️ **Vite** - 极速的构建工具
- 🖖 **Vue 3** - 渐进式 JavaScript 框架
- 🎨 **Element Plus** - 基于 Vue 3 的组件库
- 🗂 **Vue Router** - 官方路由管理器（WebHash 模式）
- 📦 **Pinia** - 新一代状态管理
- 🔗 **Axios** - HTTP 请求库（已封装）
- 🎯 **Sass** - CSS 预处理器
- 📁 **规范化目录结构** - views 存放页面，components 存放组件
- 🔧 **完整配置** - 包含开发和生产环境配置

## 📦 安装

### 环境要求

- Node.js 18+
- npm 9+

### 安装步骤

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 📁 项目结构

```
src/
├── api/                 # API 接口
│   ├── index.js        # API 统一导出
│   └── publish.js      # 发布相关 API
├── components/          # 公共组件
├── router/             # 路由配置
│   └── index.js        # 路由主文件
├── stores/             # 状态管理
│   └── index.js        # Pinia 配置
├── styles/             # 样式文件
│   ├── index.scss      # 主样式文件
│   ├── reset.scss      # 重置样式
│   └── variables.scss  # 样式变量
├── utils/              # 工具函数
│   └── request.js      # HTTP 请求封装
├── views/              # 页面组件
│   ├── Dashboard.vue           # 首页仪表盘
│   ├── PublishTaskRecords.vue  # 任务发布记录
│   ├── MaterialManagement.vue  # 素材管理
│   ├── AccountManagement.vue   # 账号管理
│   └── PublishCenter.vue       # 发布中心
├── App.vue             # 根组件
└── main.js             # 入口文件
```

## 🔧 项目说明

### 核心功能

1. **仪表盘**：显示账号统计、平台分布、任务统计和最近发布任务
2. **素材管理**：上传、管理和预览媒体素材
3. **账号管理**：管理各平台自媒体账号
4. **发布中心**：创建和管理发布任务
5. **任务记录**：查看和管理发布任务记录，支持重试和取消操作

### 技术架构

- **前端框架**：Vue 3 + Composition API
- **UI 组件**：Element Plus
- **状态管理**：Pinia
- **路由管理**：Vue Router (WebHash 模式)
- **HTTP 客户端**：Axios
- **样式预处理器**：Sass
- **构建工具**：Vite

## 📦 API 接口说明

### 发布相关 API

```javascript
// 获取发布任务记录
publishApi.getPublishTaskRecords(params)

// 发布视频到单个平台
publishApi.postVideo(data)

// 批量发布多个文件到多个平台
publishApi.postVideosToMultiplePlatforms(data)

// 取消发布任务
publishApi.cancelPublishTask(taskId)

// 获取发布任务状态
publishApi.getPublishTaskStatus(taskId)

// 获取平台特定参数配置
publishApi.getPlatformConfig(platformType)
```

### 账号相关 API

```javascript
// 获取所有账号信息
accountApi.getAccounts()

// 获取有效的账号信息
accountApi.getValidAccounts()

// 添加账号
accountApi.addAccount(data)

// 更新账号信息
accountApi.updateUserinfo(data)

// 删除账号
accountApi.deleteAccount(id)

// 下载 Cookie 文件
accountApi.downloadCookie(filePath)

// 上传 Cookie 文件
accountApi.uploadCookie(file)
```

### 文件相关 API

```javascript
// 上传文件
fileApi.uploadFile(file)

// 获取文件列表
fileApi.getFiles()
```

## 📱 功能模块

### 1. 仪表盘

- **账号统计**：显示总账号数、正常账号数、异常账号数
- **平台分布**：显示各平台账号数量和占比
- **任务统计**：显示总任务数、完成任务数、进行中任务数、失败任务数
- **最近发布任务**：显示最近的发布任务记录，支持查看详情、重试和取消操作

### 2. 发布任务记录

- **搜索与筛选**：支持按文件名、平台、状态搜索和筛选
- **任务详情**：显示任务的文件名、平台、账号、状态、创建时间、更新时间
- **操作功能**：支持查看详情、重试失败任务、取消进行中或待发布任务
- **分页查询**：支持分页显示任务记录
- **实时更新**：任务状态变更时自动更新列表和统计数据
- **多平台支持**：支持小红书、抖音、快手、视频号、TikTok、Instagram、Facebook、B站、百家号等多平台任务记录查询

### 3. 账号管理

- **账号列表**：显示所有平台账号及其状态
- **账号操作**：支持账号的添加、编辑、删除
- **状态管理**：显示账号状态和有效期
- **Cookie 管理**：支持 Cookie 文件的上传和下载

### 4. 素材管理

- **文件上传**：支持视频、图片等媒体素材的上传
- **素材管理**：支持素材的预览、编辑、删除
- **筛选功能**：支持按类型、时间等筛选素材
- **文件信息**：显示文件的名称、大小、类型、上传时间等信息

### 5. 发布中心

- **任务创建**：支持创建发布任务
- **平台选择**：支持选择多个平台和账号
- **参数设置**：支持设置发布时间和发布参数
- **批量发布**：支持批量选择文件进行发布
- **定时发布**：支持设置定时发布计划

## 🔧 开发配置

### 环境变量

创建 `.env.development` 文件配置开发环境：

```env
VITE_API_BASE_URL=http://localhost:5409
```

创建 `.env.production` 文件配置生产环境：

```env
VITE_API_BASE_URL=https://your-api-domain.com
```

### 路由配置

项目使用 Vue Router 4，配置为 WebHash 模式，路由文件位于 `src/router/index.js`。主要路由包括：

| 路由 | 组件 | 描述 |
|------|------|------|
| `/` | Dashboard.vue | 首页仪表盘 |
| `/account-management` | AccountManagement.vue | 账号管理 |
| `/material-management` | MaterialManagement.vue | 素材管理 |
| `/publish-center` | PublishCenter.vue | 发布中心 |
| `/publish-task-records` | PublishTaskRecords.vue | 任务发布记录 |

### 状态管理

使用 Pinia 进行状态管理，store 文件位于 `src/stores/` 目录。

### HTTP 请求

Axios 已经过封装，包含：
- 请求/响应拦截器
- 错误处理
- Token 自动添加
- 统一的响应格式处理

使用方式：
```javascript
import { http } from '@/utils/request'

// GET 请求
const data = await http.get('/api/users')

// POST 请求
const result = await http.post('/api/users', { name: 'John' })
```

### 样式系统

- 使用 Sass 作为 CSS 预处理器
- 已删除所有浏览器默认样式
- 提供了完整的样式变量和工具类
- 支持 Element Plus 主题定制

## 🎨 组件库

项目集成了 Element Plus，所有组件都可以直接使用：

```vue
<template>
  <el-button type="primary">按钮</el-button>
  <el-input v-model="input" placeholder="请输入内容"></el-input>
</template>
```

## 📝 开发规范

1. **页面组件** 放在 `src/views/` 目录
2. **公共组件** 放在 `src/components/` 目录
3. **使用 setup 语法糖** 编写组件
4. **样式使用 Sass** 并遵循 BEM 命名规范
5. **API 请求** 统一放在 `src/api/` 目录
6. **状态管理** 按模块划分，放在 `src/stores/` 目录

## 🚀 启动命令

```bash
# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 🚀 部署

### 本地开发环境

按照「安装步骤」中的命令部署到本地机器。

### 生产环境部署

1. **构建生产版本**
   ```bash
   npm run build
   ```

2. **部署静态文件**
   - 构建完成后，`dist` 目录包含所有静态文件
   - 可以部署到任何静态文件服务器
   - 推荐使用 Nginx、Apache 或 CDN 服务

3. **Nginx 配置示例**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           root /path/to/dist;
           index index.html;
           try_files $uri $uri/ /index.html;
       }
       
       # 代理 API 请求到后端服务
       location /api {
           proxy_pass http://localhost:5409;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

4. **Docker 部署**
   ```bash
   # 构建 Docker 镜像
   docker build -t sau-frontend .
   
   # 运行 Docker 容器
   docker run -d -p 80:80 --name sau-frontend sau-frontend
   ```

## 🔧 配置说明

### 主题定制

项目支持 Element Plus 主题定制，修改 `styles/variables.scss` 文件中的变量即可：

```scss
// 主色调
$primary-color: #409eff;

// 成功色
$success-color: #67c23a;

// 警告色
$warning-color: #e6a23c;

// 危险色
$danger-color: #f56c6c;

// 信息色
$info-color: #909399;
```

### API 代理配置

在 `vite.config.js` 中配置 API 代理：

```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5409',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

## 📄 许可证

MIT License

## 更新日志

### v1.0.0 (2026-01-13)

- ✨ 初始版本发布
- ✅ 实现完整的仪表盘功能
- ✅ 支持账号管理
- ✅ 支持素材管理
- ✅ 支持发布中心
- ✅ 支持任务发布记录查询
- ✅ 实现响应式设计
- ✅ 支持多平台发布

---

**感谢使用 SAU 自媒体智能运营系统！** 🚀
