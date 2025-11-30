# HTTP 配置指南

## 问题说明

如果登录后提示 "Failed to fetch"，通常是因为：
1. CORS 跨域问题
2. API 地址配置不正确
3. 后端服务未启动

## 解决方案

### 方案 1：使用 Next.js API 路由代理（推荐）

所有 API 请求现在都通过 Next.js API 路由代理，避免 CORS 问题。

**前端配置**（`frontend/.env.local` 或 `frontend/.env`）：
```bash
# 后端 API 地址（Next.js API 路由会代理到这个地址）
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**后端配置**（`.env`）：
```bash
# CORS 允许的源（多个用逗号分隔）
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000
```

### 方案 2：直接配置 CORS（如果使用不同域名）

如果前端和后端运行在不同域名或 IP，需要配置 CORS：

**后端 `.env` 文件**：
```bash
# 允许的 CORS 源（多个用逗号分隔）
CORS_ORIGINS=http://localhost:3000,http://192.168.1.100:3000,http://your-domain.com
```

**前端 `.env.local` 文件**：
```bash
# 后端 API 地址
NEXT_PUBLIC_API_BASE_URL=http://192.168.1.100:8000
# 或
NEXT_PUBLIC_API_BASE_URL=http://your-backend-domain.com:8000
```

## 配置步骤

### 1. 后端配置

在项目根目录的 `.env` 文件中添加或修改：

```bash
# CORS 配置（多个源用逗号分隔，不要有空格）
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### 2. 前端配置

在 `frontend` 目录下创建 `.env.local` 文件：

```bash
# 后端 API 地址
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. 重启服务

修改配置后需要重启服务：

```bash
# 重启后端
python start_api.py

# 重启前端
cd frontend
npm run dev
```

## 常见问题

### Q: 仍然提示 "Failed to fetch"

1. **检查后端是否运行**：
   ```bash
   curl http://localhost:8000/docs
   ```

2. **检查 CORS 配置**：
   确保 `.env` 文件中的 `CORS_ORIGINS` 包含前端地址

3. **检查浏览器控制台**：
   查看 Network 标签页，确认请求的 URL 和状态码

4. **检查防火墙**：
   确保端口 8000 没有被防火墙阻止

### Q: 如何查看当前配置

**后端 CORS 配置**：
```python
# 在 app/api/main.py 中查看
print(f"CORS Origins: {cors_origins}")
```

**前端 API 地址**：
```javascript
// 在浏览器控制台查看
console.log(process.env.NEXT_PUBLIC_API_BASE_URL)
```

## 使用 HTTP vs HTTPS

### HTTP（开发环境）
- 后端：`http://localhost:8000`
- 前端：`http://localhost:3000`
- CORS：`CORS_ORIGINS=http://localhost:3000`

### HTTPS（生产环境）
- 后端：`https://api.yourdomain.com`
- 前端：`https://yourdomain.com`
- CORS：`CORS_ORIGINS=https://yourdomain.com`

## 注意事项

1. **环境变量命名**：
   - 前端：`NEXT_PUBLIC_` 前缀的变量会暴露给浏览器
   - 后端：直接使用变量名（如 `CORS_ORIGINS`）

2. **重启服务**：
   - 修改 `.env` 文件后必须重启服务才能生效

3. **多个源**：
   - 用逗号分隔，不要有空格：`http://localhost:3000,http://localhost:3001`

4. **本地网络访问**：
   - 如果要在同一网络的其他设备访问，使用本机 IP：
     ```bash
     # 获取本机 IP
     ifconfig | grep "inet " | grep -v 127.0.0.1
     
     # 然后配置
     CORS_ORIGINS=http://192.168.1.100:3000
     NEXT_PUBLIC_API_BASE_URL=http://192.168.1.100:8000
     ```

