# OneSite WebUI

独立的本地项目编辑器和CLI管理器，内置HTTP服务器提供Web UI。

## 目录结构

```
webui/
├── __init__.py            # 包初始化
├── __main__.py            # 入口点（支持 python -m webui）
├── src/                   # Python 后端源码
│   ├── __init__.py
│   ├── constants.py       # 常量定义
│   ├── exceptions.py      # 自定义异常
│   ├── utils.py           # 通用工具函数
│   ├── parsers.py         # Python AST解析器
│   ├── file_utils.py      # 文件操作工具
│   ├── job.py             # 子进程作业管理
│   ├── studio.py          # 核心业务逻辑（Studio类）
│   ├── handler.py         # HTTP请求处理器
│   └── assets.py          # 前端静态资源（自动生成）
└── frontend/              # 前端源码（React + Arco Design）
    ├── package.json       # Node.js 依赖
    ├── build.mjs          # 构建脚本（esbuild）
    ├── src/               # React 源码
    ├── tests/             # 前端测试
    └── node_modules/      # Node.js 依赖（构建时）
```

## 运行方式

### 向后兼容（推荐）
```bash
python webui.py [--port 8765] [--projects-dir ./projects] [--no-browser]
```

### 模块化运行
```bash
python -m webui [--port 8765] [--projects-dir ./projects] [--no-browser]
```

## 开发工作流

### 1. Python 后端开发

后端代码在 `webui/src/` 目录下，使用纯 Python 标准库，无需额外依赖。

**模块职责：**
- `constants.py`: 所有常量定义
- `exceptions.py`: 自定义异常类
- `utils.py`: 通用工具函数（Python语法验证等）
- `parsers.py`: 配置和模型解析器（site_config.py, model.py）
- `file_utils.py`: 文件操作（安全路径、哈希计算）
- `job.py`: 子进程作业管理
- `studio.py`: 核心业务逻辑（项目管理、文件操作）
- `handler.py`: HTTP请求处理器

**代码规范：**
- 200-400行/文件（最佳实践）
- 高内聚低耦合
- 详细的docstring

### 2. 前端开发

前端使用 React + Arco Design，代码在 `webui/frontend/` 目录下。

**构建流程：**
```bash
cd webui/frontend
npm install          # 安装依赖
npm run build        # 构建并生成 assets.py
npm test             # 运行测试
```

**构建产物：**
- 构建脚本将 React 代码打包、压缩
- 生成 Base64 编码的 ASSETS 字典
- 写入 `webui/src/assets.py`

**开发模式：**
```bash
cd webui/frontend
npm run dev          # 启动开发服务器（如果配置了）
```

## 技术栈

### 后端
- **Python 3.10+**
- **标准库**: http.server, subprocess, ast, threading
- **无第三方依赖**

### 前端
- **React 18**
- **Arco Design 2.66** (字节跳动的企业级UI库)
- **esbuild** (打包工具)
- **Vitest** (测试框架)

## 架构设计

### 分层架构

```
┌─────────────────────────────────┐
│       HTTP Layer (handler.py)    │  ← 请求处理、安全防护
├─────────────────────────────────┤
│      Business Layer (studio.py)  │  ← 核心业务逻辑
├─────────────────────────────────┤
│      Parsing Layer (parsers.py)  │  ← Python AST解析
├─────────────────────────────────┤
│        Util Layer (utils.py)     │  ← 通用工具函数
├─────────────────────────────────┤
│    Constants (constants.py)      │  ← 常量定义
└─────────────────────────────────┘
```

### 数据流

1. **请求进入**: Handler 接收 HTTP 请求
2. **安全验证**: guard() 检查 Host/Origin/Token
3. **路由分发**: dispatch() 根据路径调用相应方法
4. **业务处理**: Studio 执行具体操作
5. **响应返回**: Handler 发送 JSON/HTML 响应

### 前后端集成

```
前端源码 (React/JSX)
       ↓
   esbuild 打包压缩
       ↓
   Base64+gzip 编码
       ↓
   写入 assets.py
       ↓
   Python 导入 ASSETS 字典
       ↓
   HTTP 响应返回给浏览器
```

## 测试

### 后端测试
```bash
# 测试各个模块的导入
python -c "from webui.src import studio, handler; print('OK')"

# 测试解析器功能
python -c "
from webui.src.parsers import parse_config
# 添加测试代码
"
```

### 前端测试
```bash
cd webui/frontend
npm test
```

## 部署

### 开发环境
```bash
# 启动服务
python -m webui --port 8765 --no-browser

# 或者使用向后兼容方式
python webui.py --port 8765 --no-browser
```

### 生产环境
```bash
# 构建前端资源（如果修改了前端代码）
cd webui/frontend
npm run build

# 启动服务
python -m webui --port 8765
```

## 常见问题

### Q: 为什么前端代码嵌入到 Python 中？
A: 使得最终用户只需运行 Python脚本，无需安装 Node.js 或 npm。前端代码在构建时编译并压缩，嵌入到 Python 模块中。

### Q: 如何修改前端代码？
A: 
1. 进入 `webui/frontend/` 目录
2. 修改 `src/` 中的 React 代码
3. 运行 `npm run build` 重新构建
4. 重启 Python 服务

### Q: 如何添加新的 API 端点？
A: 
1. 在 `handler.py` 的 `dispatch()` 方法中添加路由
2. 在 `studio.py` 中实现业务逻辑
3. 如果需要新的解析功能，在 `parsers.py` 中添加

### Q: 模块间的导入关系是怎样的？
A: 
```
__main__.py
    ↓
handler.py → studio.py → job.py
    ↓            ↓
parsers.py   file_utils.py
    ↓            ↓
utils.py     constants.py
    ↓
exceptions.py
```

## 性能优化

### 后端
- 使用多线程处理并发请求（ThreadingHTTPServer）
- 增量日志读取，避免内存溢出
- 文件哈希用于冲突检测，避免不必要的磁盘 I/O

### 前端
- esbuild 极快的打包速度
- gzip 压缩减少传输大小
- Base64 编码避免额外的 HTTP 请求

## 安全特性

- ✅ Host/Origin 验证（防止 DNS 重绑定）
- ✅ CSRF Token 验证
- ✅ CSP（Content Security Policy）头
- ✅ 路径遍历防护
- ✅ 文件大小限制
- ✅ Python 语法验证

## 扩展点

### 添加新的解析器
在 `parsers.py` 中添加：
```python
def parse_new_format(source: str) -> dict[str, Any]:
    # 实现解析逻辑
    pass

def render_new_format(spec: dict[str, Any]) -> str:
    # 实现渲染逻辑
    pass
```

### 添加新的文件类型
在 `constants.py` 的 `TEXT_EXTENSIONS` 中添加扩展名。

### 添加新的 Hook
在 `constants.py` 的 `HOOKS` 字典中添加定义。

## 版本历史

### v1.0.0 (重构版)
- ✅ 模块化重构（从 5472 行单文件拆分为 11 个模块）
- ✅ 前后端分离（src/ + frontend/）
- ✅ 向后兼容（支持原命令）
- ✅ 完整的功能保持

## 许可证

参见 `webui/frontend/THIRD_PARTY_NOTICES.txt` 了解前端依赖的许可证信息。

## 贡献指南

1. **后端修改**: 编辑 `webui/src/` 中的 Python 文件
2. **前端修改**: 编辑 `webui/frontend/src/` 中的 React 文件
3. **测试**: 运行相应的测试命令
4. **文档**: 更新本 README

## 联系方式

如有问题，请查看项目文档或提交 issue。
