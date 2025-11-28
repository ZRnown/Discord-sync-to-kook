# 交易监控前端

这是一个基于 Next.js 的交易监控前端应用，用于展示 Discord 交易信号的实时状态。

## 功能特性

- 📊 实时交易单监控
- 📈 价格进度条可视化
- 🔍 多维度筛选（状态、方向、交易对）
- 📱 响应式设计
- ⚡ 实时数据更新（3秒轮询）
- 🎨 美观的 UI 界面

## 快速开始

### 1. 安装依赖

```bash
npm install
# 或
yarn install
# 或
pnpm install
```

### 2. 配置环境变量

创建 `.env.local` 文件（参考 `.env.example`）：

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**注意**：请确保后端 API 服务已启动，并且地址配置正确。

### 3. 启动开发服务器

```bash
npm run dev
# 或
yarn dev
# 或
pnpm dev
```

打开 [http://localhost:3000](http://localhost:3000) 查看应用。

## API 配置

前端通过 Next.js API 路由代理到后端 API。详细配置说明请查看 [API_SETUP.md](./API_SETUP.md)。

### 后端 API 要求

后端需要提供以下 API 端点：

- `GET /api/trades` - 获取交易单列表
- `GET /api/trades/{id}` - 获取交易单详情
- `GET /api/prices` - 获取实时价格
- `GET /api/traders` - 获取交易员列表

## 项目结构

```
frontend/
├── app/                    # Next.js App Router
│   ├── api/               # API 路由（代理到后端）
│   ├── page.tsx           # 主页面
│   └── layout.tsx         # 布局
├── components/            # React 组件
│   ├── trade-card.tsx     # 交易单卡片
│   ├── price-progress-bar.tsx  # 价格进度条
│   └── ui/                # UI 组件库
├── hooks/                 # React Hooks
│   └── use-trades.ts      # 交易数据 Hook
├── lib/                   # 工具函数
│   ├── api-client.ts      # API 客户端
│   ├── api-config.ts      # API 配置
│   ├── types.ts           # TypeScript 类型
│   └── trade-utils.ts     # 交易工具函数
└── public/                # 静态资源
```

## 技术栈

- **框架**: Next.js 16 (App Router)
- **UI**: Radix UI + Tailwind CSS
- **状态管理**: SWR (数据获取)
- **类型**: TypeScript
- **图表**: Recharts

## 开发

### 构建生产版本

```bash
npm run build
npm start
```

### 代码检查

```bash
npm run lint
```

## 故障排除

### 无法连接到后端 API

1. 检查后端服务是否运行
2. 确认 `NEXT_PUBLIC_API_BASE_URL` 环境变量配置正确
3. 检查浏览器控制台的错误信息
4. 确认后端 CORS 配置允许前端域名访问

### 数据不更新

1. 检查网络连接
2. 查看浏览器控制台是否有错误
3. 确认后端 API 返回的数据格式正确

## 更多信息

- [API 配置文档](./API_SETUP.md)
- [Next.js 文档](https://nextjs.org/docs)
