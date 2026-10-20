# OneSite Studio 本地可视化编辑器

安装 OneSite 后，在希望保存项目的目录运行：

```bash
site web
```

也可以在源码仓库运行 `.venv/bin/site web`，或继续使用独立入口 `python webui.py`。默认自动打开
`http://127.0.0.1:8765`，项目保存到**启动命令时所在目录**的 `projects/<项目名>/`。

```bash
site web --port 9000 --projects-dir /path/to/projects --no-browser
site web --python /path/to/venv/bin/python
site web my_app                 # 打开 ./my_app，不存在则创建
site web .                      # 打开当前项目
site web /path/to/my_app         # 打开指定路径，不存在则创建
```

指定项目路径后，网页会自动进入该项目。相对路径基于启动命令时的当前目录，
`--projects-dir` 仍用于网页中新建项目的存放位置。已有的非项目目录会报错，不会被覆盖。

WebUI 自身只使用 Python 标准库，HTML/CSS/JavaScript 全部内嵌在 `webui.py`，不需要安装
前端依赖、构建编辑器或连接 CDN。应用运行所需的依赖仍由 OneSite 项目管理。

界面使用 React + Arco Design，与 OneSite 的 `arco` 主题共享主色、背景、圆角和字体风格。
表单、选择器、表格、权限矩阵、抽屉、弹窗和消息提示均使用 Arco 组件。

## 工作流程

1. **新建或打开项目**：输入名称创建项目，或点击“打开项目”选择已有项目目录。macOS 会直接弹出系统原生文件夹选择窗口，
   取消选择会保留当前项目；其他系统或原生窗口不可用时使用网页目录选择器，可以点击文件夹进入、
   返回上级，或快速跳转到主目录和工作空间。项目目录需包含 `site_config.py` 或 `site_config.json`。
   直接编辑原目录，无需复制到 `projects/`；源码编辑沿用当前 `app/` 布局。已打开的外部项目会加入
   本次 Studio 服务的项目列表，刷新网页后仍可选择；重启服务后需重新选择目录。
2. **模型设计**：新建数据表、单例、关联表或 JSON 值对象；编辑字段、权限和 Hook。
3. **站点配置**：编辑 `site_config.py` 的常用设置和完整配置。
4. **保存**：写入源文件；`⌘ S` / `Ctrl S` 也可保存。
5. **Sync**：自动保存后执行 `site sync`，可选择 `--install` 和 `--build-cmd`。
6. **Run**：自动保存后执行 `site run . --component all|backend|frontend --host 127.0.0.1`。
   首次使用先 Sync；缺少依赖时在 Sync 中选择安装依赖。运行前端需要 Node.js/npm。
7. **停止**：在运行与日志页面停止该命令及其子进程。关闭 WebUI 服务也会清理它启动的命令。
   关闭网页标签页不会停止本地服务；重新打开项目后可继续查看日志和停止命令。

输出仍是标准 OneSite 项目，可脱离 WebUI 使用 CLI：

```text
projects/example/
├── site_config.py
├── visualizations.py
├── app/                    # 用户源码
│   ├── models/
│   ├── backend/
│   ├── frontend/
│   ├── utils/
│   └── resources.py
├── generated/              # site sync 生成
└── deploy/
```

## 配置覆盖

| 范围 | 编辑方式 |
| --- | --- |
| 模型类型、类名、表名 | 表单；支持普通表、单例、关联表、非表值对象 |
| 字段 | Python 类型、默认值/default_factory、主键、索引、唯一性、nullable、长度和数值约束 |
| 关系 | 外键向导、目标主键、手动外键表达式；多对多配置和 Relationship 可通过 JSON / 源码编辑 |
| 权限 | 模型 CRUD 与字段 CRU 角色矩阵；前端 `visible`、`owner_field`、`special_me_permissions` 独立配置 |
| 表单组件 | textarea、image、images、file、json、video_stream、location；搜索、创建/更新可选 |
| 字段扩展 | 完整 `site_props` JSON 与 `Field` 参数表达式；支持条件表单、级联、分组、翻译、固定 JSON 键等 |
| 模型扩展 | 当前 `OneSiteConfig` 的全部 schema 字段，以及尚未类型化的扩展键 |
| Hook | 11 个 CRUD / 批量删除生命周期模板，自动生成 classmethod；可编辑任意同步/异步方法 |
| 站点 | 当前 `SiteConfig` 的全部 schema 字段，包括主题、导航、消息集成、任务、Agent、插件、桌面端、自定义功能和公开仪表盘等 |
| 源码扩展 | `app/` 下的 Python、TS/TSX、JS、CSS、JSON、SQL、Rust、Go 等文本源码 |
| 其他 | `visualizations.py`、`deploy/.env`、`deploy/.env.example`、旧 `site_config.json` 的源码编辑 |

配置项通过独立子进程读取当前安装版本的 `SiteConfig` / `OneSiteConfig` JSON Schema，
不会在 WebUI 服务中导入 OneSite 核心。复杂配置使用 JSON 编辑，展开“查看结构”可以看到
嵌套字段、必填项和枚举。新增配置不会被旧表单白名单丢弃。

字段默认值和高级 `Field` 参数使用 **Python 表达式**，例如 `None`、`"hello"`、`uuid4`、
`lambda: datetime.now(timezone.utc)`。高级参数 JSON 的值应为这些表达式的字符串。
JSON 数据库字段可配置 `sa_column: "Column(JSON)"`，表单中的 `site_props` 会合并到
Column 的 `info`，保留已有元数据。动态 Column 表达式请直接编辑源码。

站点配置中的 `env(...)`、自定义函数调用等动态值保留为表达式，不求值、不展示环境变量
内容。继承、多类、装饰器或复杂定义顺序的模型采用源码模式；编辑器不会强行转换它们。
表单重新生成会规范化格式和类内布局；要保留原有注释和精确格式，请使用源码模式。

## 保存与运行行为

- 源码是唯一持久化来源，不依赖隐藏模型数据库。表单和源码切换前会同步当前有效编辑。
- 打开、预览、保存只解析/编译 Python，不执行项目代码。Python/JSON 语法错误会阻止保存；
  类型、关系、业务配置等完整语义校验交给真实 `site sync`，错误显示在日志中。
- 保存先检查全部文件，再暂存写入；写入失败会尝试恢复原文件。独立修改通过三方比较合并，
  保留 Sync 新增的迁移脚手架等文件；同一文件双方冲突时拒绝覆盖。
- 未保存编辑自动暂存在本机浏览器，重新打开项目时通过 Arco 弹窗选择恢复。
  草稿包含源码与配置，请在可信的本机浏览器使用；保存成功后自动清除该项目的本机草稿。
  也可在项目概览导出/导入 JSON。关闭页面不会弹出浏览器原生确认框。
- 每个项目同时只运行一个命令；命令执行期间禁止保存，避免生成过程读到一半的源文件。
- `generated/`、依赖目录、二进制文件、符号链接和单个超过 2 MiB 的文件不会被编辑器覆盖。
  支持每次最多 1500 个源文件，请求上限 16 MiB（含用于冲突检查的原始快照）。
- 日志及命令历史保存在服务进程内存中；支持增量读取、日志复制、停止和有限长度截断。
  页面中的前端/API 链接使用常用默认端口，实际地址与启动结果以 CLI 日志为准。
- WebUI 只监听回环地址，并检查 Host、Origin 和随机页面令牌。它是可信本地项目的开发工具，
  不是运行不可信 Python 的沙箱，也不提供公网多用户访问。

## 独立性

`webui.py` 不修改生成流水线或模板。它负责编辑 `app/` 和项目配置、管理本地编辑会话，
并用当前 Python 执行 `python -m onesite.main ...`（等价于 `site ...`）。后者避免 PATH
中另一个环境的 `site` 被误调用，也保留虚拟环境解释器路径。

`site web` 通过当前 Python 启动独立编辑器，保留调用目录和日志输出。发布的 wheel
包含同一份 `webui.py`，安装后无需源码仓库；开发环境则直接使用仓库中的独立文件。

部署、数据库迁移、构建镜像等其他 CLI 操作仍可从终端执行；WebUI 不会隐式执行这些操作。

## 修改编辑器界面

仅编辑器开发者需要 Node.js。修改 `webui_frontend/src/` 后运行：

```bash
cd webui_frontend
npm ci
npm test
npm run build
```

构建会将 React、Arco 及编辑器代码压缩并写入 `webui.py` 的生成资源区；请同时提交前端源码、
锁文件和更新后的 `webui.py`。不要手动修改编码资源。发布 wheel 仍只携带独立 Python 入口，
用户直接运行 `site web` 即可。
