# 禾光商家中心 Demo

一个供单商家本地使用的电商管理后台演示，包含商品、订单、客户、客服工作台、售后审批和同步设置。

## 查看效果

在 Windows 上双击 `start.bat`。

脚本会自动准备 Python 与前端环境、构建 Vue 页面并打开：

`http://127.0.0.1:8000/login`

演示账号：

- 用户名：`admin`
- 密码：`admin123`

也可以直接打开客户咨询演示页：

`http://127.0.0.1:8000/chat`

## 已实现的演示功能

- 商家管理员登录与本地会话。
- 经营概览、销售趋势和最近订单。
- 商品搜索、筛选、新增、编辑和归档。
- 订单列表、多商品详情和状态切换。
- 客户列表、客户详情、标签、备注及历史订单。
- 三栏客服工作台、会话接管和人工回复。
- 补偿、退款类售后审批。
- OpenAI 兼容大模型配置与连接测试。
- 商品批量同步接口示例与同步日志。
- SQLite 本地持久化。

## 技术结构

- 后端：Python、FastAPI、SQLite。
- 前端：Vue 3、Vue Router、Vite、JavaScript。
- 页面由 FastAPI 托管，浏览器和 API 使用同一来源。
`.gitignore` 已排除本地数据库、虚拟环境和构建依赖。

## 手动运行

后端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

前端开发模式：

```powershell
cd frontend
npm run dev
```

开发模式地址为 `http://127.0.0.1:5173`，API 请求会代理到 `8000` 端口。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
cd frontend
npm test
```

## Demo 边界

这是用于查看页面与交互效果的第一版演示：

- 真实大模型需要你在设置页填写兼容接口地址、模型名称和 API Key。
- 同步接口目前演示了商品批量录入，其余同步端点将在正式实现中补齐。
- 售后执行为模拟流程，不进行真实资金退款。
- 当前只有一个商家管理员，不包含团队角色、多租户和公网部署。
