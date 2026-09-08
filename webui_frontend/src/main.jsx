import React, {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { createRoot } from "react-dom/client";
import {
  Alert,
  Avatar,
  Badge,
  Breadcrumb,
  Button,
  Card,
  ConfigProvider,
  Descriptions,
  Divider,
  Drawer,
  Dropdown,
  Empty,
  Form,
  Input,
  Layout,
  Link,
  Menu,
  Message,
  PageHeader,
  Radio,
  Select,
  Space,
  Spin,
  Statistic,
  Steps,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  Upload,
} from "@arco-design/web-react";
import zhCN from "@arco-design/web-react/es/locale/zh-CN";
import {
  IconApps,
  IconDashboard,
  IconStorage,
  IconSettings,
  IconCode,
  IconPlayArrow,
  IconSave,
  IconSync,
  IconPlus,
  IconFolder,
  IconFile,
  IconArrowRight,
  IconUpload,
  IconDownload,
  IconRefresh,
  IconRecordStop,
  IconEdit,
  IconCopy,
  IconDelete,
  IconUp,
  IconDown,
  IconLink,
  IconCommand,
  IconMenu,
} from "@arco-design/web-react/icon";
import "@arco-design/web-react/dist/css/arco.css";
import "./studio.css";
import {
  st,
  subscribe,
  snapshot,
  notify,
  edit,
  run,
  api,
  commit,
  ensureValid,
  prepare,
  navigate,
  chooseFile,
  modelPaths,
  openProject,
  save,
  reloadProject,
  deleteFile,
  exportDraft,
  restoreDraft,
  confirmAction,
  persistDraft,
  showModal,
  newField,
  pollJobs,
  forget,
} from "./state";
import {
  CodeEditor,
  FieldEditor,
  JsonEditor,
  Labeled,
  PermissionMatrix,
  SchemaEditor,
  TextValue,
} from "./editors";
import { EditorDialog } from "./dialogs";

const { Title, Text, Paragraph } = Typography;
const PAGES = [
  ["overview", "项目概览", IconDashboard],
  ["models", "模型设计", IconStorage],
  ["config", "站点配置", IconSettings],
  ["files", "源码与扩展", IconCode],
  ["jobs", "运行与日志", IconPlayArrow],
];
function Action({ onClick, children, disabled, ...props }) {
  return (
    <Button
      disabled={st.busy || disabled}
      {...props}
      onClick={() => run(onClick)}
    >
      {children}
    </Button>
  );
}
function Heading({ title, subtitle, extra }) {
  return (
    <PageHeader
      className="page-heading"
      backIcon={false}
      title={title}
      subTitle={subtitle}
      extra={extra}
    />
  );
}
function ProjectSelector({ compact = false }) {
  return (
    <Select
      aria-label="选择项目"
      className={compact ? "compact-project" : undefined}
      disabled={st.busy}
      showSearch
      placeholder="选择项目"
      value={st.project || undefined}
      options={(st.boot?.projects || []).map((p) => ({
        value: p.name,
        label: p.name,
      }))}
      onChange={(name) => run(() => openProject(name))}
    />
  );
}
function NavMenu({ horizontal = false }) {
  return (
    <Menu
      mode={horizontal ? "horizontal" : "vertical"}
      selectedKeys={[st.page]}
      onClickMenuItem={(key) => run(() => navigate(key))}
    >
      {PAGES.map(([key, label, Icon]) => (
        <Menu.Item key={key}>
          <Icon />
          {label}
        </Menu.Item>
      ))}
    </Menu>
  );
}
function DraftUpload() {
  return (
    <Upload
      accept=".json"
      autoUpload={false}
      showUploadList={false}
      disabled={st.busy}
      beforeUpload={async (file) => {
        await run(async () => {
          if (file.size > 16 * 1024 * 1024) throw Error("草稿文件超过 16 MiB");
          const value = JSON.parse(await file.text());
          if (value.version !== 1 || !value.files)
            throw Error("无效的 Studio 草稿");
          if (
            !(await confirmAction(
              "导入编辑草稿",
              `将草稿载入 ${st.project}，替换当前网页中的编辑内容？`,
              false,
              "导入草稿",
            ))
          )
            return;
          await api("validate", { files: value.files });
          restoreDraft(value, value.project === st.project);
          Message.success("草稿已载入，请检查后保存");
        });
        return false;
      }}
    >
      <Button icon={<IconUpload />}>导入草稿</Button>
    </Upload>
  );
}
function Overview() {
  const exists = !!st.project;
  return (
    <>
      <Heading
        title={exists ? st.project : "OneSite Studio"}
        subtitle={
          exists
            ? "从模型到应用，在这里完成。"
            : "在本地设计、生成和运行你的应用。"
        }
        extra={
          <Action
            type="primary"
            icon={<IconPlus />}
            onClick={() => showModal(exists ? "model" : "project")}
          >
            {exists ? "新建模型" : "创建项目"}
          </Action>
        }
      />
      <Card className="overview-card" bordered={false}>
        <div className="overview-intro">
          <div>
            <Space>
              <Tag color="arcoblue">LOCAL WORKSPACE</Tag>
              <Text type="secondary">模型驱动的应用开发</Text>
            </Space>
            <Title heading={3}>
              {exists ? "你的应用工作空间" : "从一个模型开始"}
            </Title>
            <Paragraph type="secondary">
              定义数据结构和业务行为，交给 OneSite 生成完整的前后端应用。
            </Paragraph>
          </div>
          <Avatar className="hero-icon" size={76} shape="square">
            <IconApps />
          </Avatar>
        </div>
        {exists ? (
          <>
            <div className="statistics">
              <Statistic title="模型文件" value={modelPaths().length} />
              <Statistic
                title="可编辑源文件"
                value={Object.keys(st.files).length}
              />
              <Statistic
                title="站点配置项"
                value={Object.keys(st.boot.catalog.site.properties).length}
              />
            </div>
            <div className="workspace-path">
              <IconFolder />
              <Text copyable>{st.boot.root + "/" + st.project}</Text>
            </div>
            <Space wrap className="overview-actions">
              <Action type="primary" onClick={() => navigate("models")}>
                设计模型 <IconArrowRight />
              </Action>
              <Action onClick={() => navigate("config")}>配置站点</Action>
              <Action onClick={() => navigate("files")}>浏览源码</Action>
            </Space>
          </>
        ) : (
          <Space>
            <Action
              type="primary"
              size="large"
              icon={<IconPlus />}
              onClick={() => showModal("project")}
            >
              创建第一个项目
            </Action>
            <Text type="secondary">
              源码保存在 projects/，随时可用编辑器继续开发。
            </Text>
          </Space>
        )}
      </Card>
      <div className="feature-grid">
        {[
          [
            IconStorage,
            "模型与关系",
            "字段、权限、外键、多对多与生命周期 Hook。",
            "models",
          ],
          [
            IconSettings,
            "完整的站点配置",
            "主题、导航、集成、任务、Agent 与扩展功能。",
            "config",
          ],
          [
            IconPlayArrow,
            "生成与运行",
            "执行 Sync / Run，实时查看日志和管理服务。",
            "jobs",
          ],
        ].map(([Icon, title, text, page]) => (
          <Card key={page} className="feature-card">
            <Avatar shape="square" className="feature-icon">
              <Icon />
            </Avatar>
            <Title heading={6}>{title}</Title>
            <Paragraph type="secondary">{text}</Paragraph>
            {exists && (
              <Action type="text" size="small" onClick={() => navigate(page)}>
                打开 <IconArrowRight />
              </Action>
            )}
          </Card>
        ))}
      </div>
      {exists && (
        <Card title="开发流程" className="workflow-card">
          <Steps size="small" current={st.dirty ? 1 : 2} type="navigation">
            <Steps.Step title="设计模型" />
            <Steps.Step title="保存配置" />
            <Steps.Step title="Sync 生成" />
            <Steps.Step title="Run 运行" />
          </Steps>
          <Divider />
          <Space wrap>
            <Action icon={<IconDownload />} onClick={exportDraft}>
              导出草稿
            </Action>
            <DraftUpload />
            <Action icon={<IconRefresh />} onClick={reloadProject}>
              重新加载
            </Action>
          </Space>
          <Paragraph className="draft-note" type="secondary">
            未保存修改会自动保存在本机浏览器草稿中。源码只在点击保存时写入项目。
          </Paragraph>
        </Card>
      )}
      {!st.boot.catalog.available && (
        <Alert
          type="warning"
          title="OneSite 环境不可用"
          content={st.boot.catalog.error}
        />
      )}
      {!!st.skipped.length && (
        <Alert
          type="info"
          content={"未加载的符号链接、二进制或大文件：" + st.skipped.join("、")}
        />
      )}
    </>
  );
}
function FileNavigation({ paths }) {
  const [query, setQuery] = useState("");
  const matches = paths.filter((p) =>
    p.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <Card className="file-panel" bodyStyle={{ padding: 12 }}>
      <Input.Search
        aria-label="搜索文件"
        placeholder="搜索文件"
        value={query}
        onChange={setQuery}
        allowClear
      />
      <Menu
        selectedKeys={st.path ? [st.path] : []}
        onClickMenuItem={(path) => run(() => chooseFile(path))}
      >
        {matches.map((path) => (
          <Menu.Item key={path}>
            <IconFile />
            <Text ellipsis={{ showTooltip: true }}>
              {st.page === "models" ? path.replace("app/models/", "") : path}
            </Text>
          </Menu.Item>
        ))}
      </Menu>
      {!matches.length && <Empty description="没有匹配的文件" />}
    </Card>
  );
}
function EditorToolbar({ switchable = true }) {
  return (
    <div className="editor-toolbar">
      <Space>
        <IconFile />
        <Text code>{st.path}</Text>
      </Space>
      <Space wrap>
        {switchable && (
          <Radio.Group
            type="button"
            value={st.mode}
            disabled={st.busy}
            onChange={(mode) =>
              run(async () => {
                await commit();
                if (mode === "form") await prepare();
                else {
                  st.spec = null;
                  st.mode = "source";
                }
                notify();
              })
            }
            options={[
              { value: "form", label: "可视化" },
              { value: "source", label: "Python 源码" },
            ]}
          />
        )}
        {!["site_config.py", "site_config.json"].includes(st.path) && (
          <Tooltip content="删除文件">
            <Action
              type="text"
              status="danger"
              aria-label="删除文件"
              icon={<IconDelete />}
              onClick={deleteFile}
            />
          </Tooltip>
        )}
      </Space>
    </div>
  );
}
function SourceEditor() {
  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      {st.parseError && st.page !== "files" && (
        <Alert type="info" content={st.parseError} />
      )}
      <Card
        className="source-card"
        title="源码编辑"
        extra={
          <Action
            size="small"
            icon={<IconCode />}
            onClick={async () => {
              await api("validate", {
                files: { [st.path]: st.files[st.path] },
              });
              Message.success("语法检查通过");
            }}
          >
            检查语法
          </Action>
        }
      >
        <CodeEditor
          label="文件源码"
          value={st.files[st.path]}
          onChange={(value) => (st.files[st.path] = value)}
          rows={24}
        />
      </Card>
      <Text type="secondary">
        支持完整 Python / 项目源码；保存时检查 Python 和 JSON
        语法。复杂继承、多类定义和动态表达式始终保留。
      </Text>
    </Space>
  );
}
function FieldsTable() {
  const [selected, setSelected] = useState(null);
  const fields = st.spec.fields;
  function open(index) {
    setSelected(index);
  }
  function add() {
    ensureValid();
    let index = fields.length + 1;
    while (fields.some((f) => f.name === "field_" + index)) index++;
    fields.push(newField("field_" + index));
    edit();
    open(fields.length - 1);
  }
  async function remove(index) {
    if (
      !(await confirmAction(
        "删除字段",
        `删除字段 ${fields[index].name}？保存并 Sync 后将使用更新后的模型。`,
        true,
        "删除字段",
      ))
    )
      return;
    fields.splice(index, 1);
    for (const id of [...st.buffers.keys(), ...st.errors.keys()])
      if (id.startsWith(st.path + ":field-")) forget(id);
    setSelected(null);
    edit();
  }
  function reorder(index, delta) {
    ensureValid();
    const other = index + delta;
    if (other < 0 || other >= fields.length) return;
    [fields[index], fields[other]] = [fields[other], fields[index]];
    for (const id of st.buffers.keys())
      if (id.startsWith(st.path + ":field-")) forget(id);
    edit();
  }
  const columns = [
    {
      title: "字段",
      dataIndex: "name",
      width: 200,
      render: (name, record, index) => (
        <Button type="text" className="field-name" onClick={() => open(index)}>
          {name}
        </Button>
      ),
    },
    {
      title: "类型",
      dataIndex: "type",
      width: 180,
      render: (value) => <Text code>{value}</Text>,
    },
    {
      title: "属性",
      render: (_, f) => (
        <Space size="mini" wrap>
          {f.kwargs.primary_key === "True" && <Tag color="arcoblue">主键</Tag>}
          {f.kwargs.foreign_key && <Tag color="purple">外键</Tag>}
          {f.kwargs.unique === "True" && <Tag>唯一</Tag>}
          {f.props.is_search_field && <Tag color="cyan">搜索</Tag>}
          {f.props.component && <Tag>{f.props.component}</Tag>}
        </Space>
      ),
    },
    {
      title: "操作",
      width: 190,
      align: "right",
      render: (_, f, index) => (
        <Space size={0}>
          <Tooltip content="上移">
            <Action
              size="mini"
              type="text"
              disabled={index === 0}
              aria-label={`上移 ${f.name}`}
              icon={<IconUp />}
              onClick={() => reorder(index, -1)}
            />
          </Tooltip>
          <Tooltip content="下移">
            <Action
              size="mini"
              type="text"
              disabled={index === fields.length - 1}
              aria-label={`下移 ${f.name}`}
              icon={<IconDown />}
              onClick={() => reorder(index, 1)}
            />
          </Tooltip>
          <Tooltip content="复制字段">
            <Action
              size="mini"
              type="text"
              aria-label={`复制 ${f.name}`}
              icon={<IconCopy />}
              onClick={() => {
                ensureValid();
                const next = structuredClone(f);
                let name = f.name + "_copy";
                while (fields.some((v) => v.name === name)) name += "_copy";
                next.name = name;
                fields.push(next);
                edit();
              }}
            />
          </Tooltip>
          <Tooltip content="编辑字段">
            <Button
              size="mini"
              type="text"
              aria-label={`编辑 ${f.name}`}
              icon={<IconEdit />}
              onClick={() => open(index)}
            />
          </Tooltip>
          <Tooltip content="删除字段">
            <Action
              size="mini"
              type="text"
              status="danger"
              aria-label={`删除 ${f.name}`}
              icon={<IconDelete />}
              onClick={() => remove(index)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];
  return (
    <>
      <Card
        title={
          <Space>
            字段与关系<Tag>{fields.length}</Tag>
          </Space>
        }
        extra={
          <Space wrap>
            <Action
              size="small"
              icon={<IconLink />}
              onClick={() => showModal("foreignKey")}
            >
              外键
            </Action>
            <Action
              size="small"
              onClick={() => {
                ensureValid();
                for (const name of ["created_at", "updated_at"])
                  if (!fields.some((f) => f.name === name))
                    fields.push({
                      ...newField(name, "datetime"),
                      kwargs: {
                        default_factory: "lambda: datetime.now(timezone.utc)",
                      },
                      props: {
                        permissions: name === "created_at" ? "r" : "ru",
                      },
                    });
                edit();
              }}
            >
              时间戳
            </Action>
            <Action
              type="primary"
              size="small"
              icon={<IconPlus />}
              onClick={add}
            >
              添加字段
            </Action>
          </Space>
        }
      >
        <Table
          columns={columns}
          data={fields.map((f, i) => ({ ...f, key: i }))}
          pagination={false}
          border={false}
          scroll={{ x: 800 }}
          noDataElement={
            <Empty description="还没有字段，添加字段或通过外键向导创建关系。" />
          }
        />
      </Card>
      <Drawer
        title={
          selected !== null && fields[selected]
            ? `编辑字段 · ${fields[selected].name}`
            : "编辑字段"
        }
        visible={selected !== null}
        width={700}
        className="field-drawer"
        maskClosable={false}
        onCancel={() => setSelected(null)}
        footer={
          <Space>
            <Button onClick={() => setSelected(null)}>关闭</Button>
            <Action
              type="primary"
              onClick={() => {
                ensureValid();
                setSelected(null);
              }}
            >
              完成编辑
            </Action>
          </Space>
        }
      >
        {selected !== null && fields[selected] && (
          <FieldEditor
            key={`${st.path}:${selected}`}
            field={fields[selected]}
            index={selected}
          />
        )}
      </Drawer>
    </>
  );
}
function HooksEditor() {
  const [hook, setHook] = useState("on_before_create");
  const metadata = st.boot.catalog.hooks;
  return (
    <Card title="生命周期与自定义方法">
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Space className="hook-toolbar">
          <Select
            aria-label="选择 Hook"
            value={hook}
            onChange={setHook}
            options={Object.keys(metadata)}
            style={{ width: 320 }}
          />
          <Action
            icon={<IconPlus />}
            onClick={() => {
              if (new RegExp("def\\s+" + hook + "\\s*\\(").test(st.spec.hooks))
                throw Error("此 Hook 已存在");
              const [args, description] = metadata[hook];
              st.spec.hooks +=
                (st.spec.hooks.trim() ? "\n\n" : "") +
                (args.startsWith("cls") ? "@classmethod\n" : "") +
                `async def ${hook}(${args}):\n    # ${description}\n    pass\n`;
              edit();
            }}
          >
            插入 Hook
          </Action>
        </Space>
        <Alert content={metadata[hook][1]} />
        <CodeEditor
          label="Hook 源码"
          value={st.spec.hooks}
          onChange={(v) => (st.spec.hooks = v)}
          rows={20}
        />
        <Text type="secondary">
          支持同步 / 异步方法及自定义动作。事务内 Hook 可回滚，on_after_commit_*
          在提交后执行。
        </Text>
      </Space>
    </Card>
  );
}
function ModelEditor() {
  const m = st.spec;
  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card
        title={m.name}
        extra={
          <Tag color="arcoblue">{m.table ? "数据表" : "值对象"} · SQLModel</Tag>
        }
      >
        <Form layout="vertical">
          <div className="form-grid three">
            <Labeled label="模型类名">
              <TextValue value={m.name} onChange={(v) => (m.name = v)} />
            </Labeled>
            <Labeled label="数据库表名" hint="留空时自动使用 snake_case。">
              <TextValue
                value={m.table_name}
                onChange={(v) => (m.table_name = v)}
                placeholder="自动生成"
              />
            </Labeled>
            <Labeled label="数据库表">
              <Switch
                checked={m.table}
                onChange={(v) => {
                  m.table = v;
                  edit();
                }}
                checkedText="是"
                uncheckedText="否"
              />
            </Labeled>
          </div>
        </Form>
        <Text type="secondary">
          重命名后请调整关联模型的导入与外键。表单会规范化源码格式；精确保留注释时请使用源码模式。
        </Text>
      </Card>
      <Tabs
        activeTab={st.tab}
        onChange={(tab) =>
          run(async () => {
            await commit();
            st.tab = tab;
            notify();
          })
        }
      >
        <Tabs.TabPane key="fields" title="字段与关系" />
        <Tabs.TabPane key="config" title="模型配置" />
        <Tabs.TabPane key="hooks" title="Hooks 与方法" />
        <Tabs.TabPane key="advanced" title="导入与类扩展" />
      </Tabs>
      {st.tab === "fields" && <FieldsTable key={st.path} />}
      {st.tab === "config" && (
        <>
          <PermissionMatrix
            value={m.config.permissions}
            onChange={(v) => {
              if (v === undefined) delete m.config.permissions;
              else m.config.permissions = v;
            }}
            title="模型 CRUD 权限"
          />
          <SchemaEditor
            values={m.config}
            onChange={(v) => (m.config = v)}
            schema={st.boot.catalog.model}
            scope="model"
            title="__onesite__ 配置"
          />
        </>
      )}
      {st.tab === "hooks" && <HooksEditor />}
      {st.tab === "advanced" && (
        <Card title="模块与类扩展">
          <Form layout="vertical">
            <Labeled label="模块导入 / 类定义之前的代码">
              <CodeEditor
                value={m.prefix}
                onChange={(v) => (m.prefix = v)}
                rows={10}
              />
            </Labeled>
            <Labeled label="类内额外代码">
              <CodeEditor
                value={m.extra}
                onChange={(v) => (m.extra = v)}
                rows={8}
              />
            </Labeled>
            <Labeled label="类定义之后的代码">
              <CodeEditor
                value={m.suffix}
                onChange={(v) => (m.suffix = v)}
                rows={6}
              />
            </Labeled>
          </Form>
        </Card>
      )}
    </Space>
  );
}
function Models() {
  return (
    <>
      <Heading
        title="模型设计"
        subtitle="定义数据结构、访问权限与业务行为。"
        extra={
          <Action
            type="primary"
            icon={<IconPlus />}
            onClick={() => showModal("model")}
          >
            新建模型
          </Action>
        }
      />
      <div className="editor-layout">
        <FileNavigation paths={modelPaths()} />
        <div className="editor-main">
          {st.path ? (
            <>
              <EditorToolbar />
              {st.mode === "form" && st.spec ? (
                <ModelEditor />
              ) : (
                <SourceEditor />
              )}
            </>
          ) : (
            <Card>
              <Empty description="还没有模型" />
              <Action type="primary" onClick={() => showModal("model")}>
                创建模型
              </Action>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
function ConfigPage() {
  const spec = st.spec;
  const commonInput = (key, label) =>
    spec.expressions[key] ? (
      <CodeEditor
        label={label + " Python 表达式"}
        value={spec.expressions[key]}
        onChange={(v) => (spec.expressions[key] = v)}
        rows={2}
      />
    ) : (
      <TextValue
        value={spec.values[key]}
        onChange={(v) => (spec.values[key] = v)}
      />
    );
  return (
    <>
      <Heading
        title="站点配置"
        subtitle="管理主题、导航、连接和应用扩展能力。"
        extra={<Tag color="arcoblue">site_config.py</Tag>}
      />
      <div className="stack">
        <EditorToolbar />
        {st.mode === "source" || !spec ? (
          <SourceEditor />
        ) : (
          <>
            <Card title="常用设置">
              <Form layout="vertical">
                <div className="form-grid three">
                  <Labeled label="应用名称">
                    {commonInput("project_name", "应用名称")}
                  </Labeled>
                  <Labeled label="应用主题">
                    <Select
                      value={spec.values.theme || spec.values.style || "normal"}
                      options={["normal", "industrial", "neuron", "arco"]}
                      onChange={(v) => {
                        spec.values.style = v;
                        delete spec.values.theme;
                        delete spec.expressions.style;
                        delete spec.expressions.theme;
                        edit();
                      }}
                    />
                  </Labeled>
                  <Labeled label="数据库 URL">
                    {commonInput("database_url", "数据库 URL")}
                  </Labeled>
                </div>
              </Form>
              <Text type="secondary">
                env(...) 等 Python
                表达式保持原样，编辑时不读取环境变量的实际内容。
              </Text>
            </Card>
            <SchemaEditor
              values={spec.values}
              onChange={(v) => (spec.values = v)}
              expressions={spec.expressions}
              schema={st.boot.catalog.site}
              scope="site"
              title="完整站点配置"
            />
          </>
        )}
      </div>
    </>
  );
}
function Files() {
  return (
    <>
      <Heading
        title="源码与扩展"
        subtitle="编辑 app/ 开发源码、可视化和项目配置。"
        extra={
          <Action
            type="primary"
            icon={<IconPlus />}
            onClick={() => showModal("file")}
          >
            新建文件
          </Action>
        }
      />
      <div className="editor-layout">
        <FileNavigation paths={Object.keys(st.files).sort()} />
        <div className="editor-main">
          {st.path ? (
            <>
              <EditorToolbar switchable={false} />
              <SourceEditor />
            </>
          ) : (
            <Empty description="选择或创建源文件" />
          )}
        </div>
      </div>
    </>
  );
}
function Jobs() {
  const jobs = Object.values(st.jobs).sort((a, b) => b.started - a.started),
    selected = st.jobs[st.selectedJob];
  const terminal = useRef(null),
    autoScroll = useRef(true);
  useEffect(() => {
    if (terminal.current && autoScroll.current)
      terminal.current.scrollTop = terminal.current.scrollHeight;
  }, [selected?.text, st.selectedJob]);
  return (
    <>
      <Heading
        title="运行与日志"
        subtitle="执行标准 OneSite 命令，查看实时输出。"
        extra={
          <Space>
            <Action icon={<IconSync />} onClick={() => showModal("sync")}>
              Sync
            </Action>
            <Action
              type="primary"
              icon={<IconPlayArrow />}
              onClick={() => showModal("run")}
            >
              Run
            </Action>
          </Space>
        }
      />
      {st.connectionError && (
        <Alert type="error" content={st.connectionError} />
      )}
      {!jobs.length ? (
        <Card className="empty-card">
          <Empty description="先 Sync 生成应用，再 Run 启动服务。" />
          <Action type="primary" onClick={() => showModal("sync")}>
            执行 Sync
          </Action>
        </Card>
      ) : (
        <Card title="命令记录">
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            data={jobs}
            border={false}
            columns={[
              {
                title: "命令",
                render: (_, j) => (
                  <Button
                    type="text"
                    onClick={() => {
                      st.selectedJob = j.id;
                      autoScroll.current = true;
                      notify();
                    }}
                  >
                    {j.action.toUpperCase()}
                  </Button>
                ),
              },
              {
                title: "启动时间",
                render: (_, j) =>
                  new Date(j.started * 1000).toLocaleTimeString(),
              },
              {
                title: "状态",
                render: (_, j) => (
                  <Tag
                    color={
                      j.running
                        ? "arcoblue"
                        : j.code === 0
                          ? "green"
                          : undefined
                    }
                  >
                    {j.stopping
                      ? j.running
                        ? "停止中"
                        : "已停止"
                      : j.running
                        ? "运行中"
                        : "退出码 " + j.code}
                  </Tag>
                ),
              },
              {
                title: "操作",
                align: "right",
                render: (_, j) =>
                  j.running ? (
                    <Action
                      type="text"
                      status="danger"
                      icon={<IconRecordStop />}
                      onClick={async () => {
                        await api("stop", { id: j.id });
                        await pollJobs();
                      }}
                    >
                      停止
                    </Action>
                  ) : (
                    <Text type="secondary">已结束</Text>
                  ),
              },
            ]}
          />
          <div className="terminal-toolbar">
            <Text type="secondary">
              实时输出 · {selected?.action.toUpperCase()}
            </Text>
            <Space wrap>
              <Action
                size="small"
                icon={<IconCopy />}
                onClick={async () => {
                  await navigator.clipboard.writeText(selected?.text || "");
                  Message.success("日志已复制");
                }}
              >
                复制日志
              </Action>
              <Link href="http://127.0.0.1:5173" target="_blank" rel="noopener">
                前端 ↗
              </Link>
              <Link
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                rel="noopener"
              >
                API 文档 ↗
              </Link>
            </Space>
          </div>
          <div
            className="terminal"
            role="log"
            aria-label="命令日志"
            ref={terminal}
            onScroll={(e) => {
              const n = e.currentTarget;
              autoScroll.current =
                n.scrollHeight - n.scrollTop - n.clientHeight < 65;
            }}
          >
            <Text>
              {(selected?.text || "等待命令输出…").replace(
                /\x1b\[[0-?]*[ -/]*[@-~]/g,
                "",
              )}
            </Text>
          </div>
          <Paragraph type="secondary" className="draft-note">
            链接使用常用默认端口，实际启动结果和地址以日志为准。关闭网页后可重新打开项目管理运行中的命令。
          </Paragraph>
        </Card>
      )}
    </>
  );
}
export function App() {
  useSyncExternalStore(subscribe, snapshot);
  useEffect(() => {
    run(async () => {
      st.boot = await api("bootstrap");
      notify();
    });
    const timer = setInterval(pollJobs, 1200);
    const keys = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (st.project) run(save);
      }
    };
    window.addEventListener("keydown", keys);
    window.addEventListener("pagehide", persistDraft);
    return () => {
      clearInterval(timer);
      window.removeEventListener("keydown", keys);
      window.removeEventListener("pagehide", persistDraft);
    };
  }, []);
  const activeJobs = Object.values(st.jobs).filter((j) => j.running).length;
  return (
    <ConfigProvider locale={zhCN} size="default">
      <Layout className="studio-layout">
        <Layout.Sider width={232} className="studio-sider">
          <div className="brand">
            <Avatar shape="square" size={34}>
              <IconApps />
            </Avatar>
            <Title heading={5}>
              OneSite <Text type="secondary">Studio</Text>
            </Title>
          </div>
          <div className="project-picker">
            <Text type="secondary" className="section-caption">
              工作空间
            </Text>
            <ProjectSelector />
            <Action
              type="text"
              long
              icon={<IconPlus />}
              onClick={() => showModal("project")}
            >
              新建项目
            </Action>
          </div>
          <NavMenu />
          <div className="sidebar-footer">
            <Badge status="processing" text="本地开发环境" />
            <Paragraph
              type="secondary"
              ellipsis={{ rows: 3, showTooltip: true }}
            >
              {st.boot?.root}
            </Paragraph>
            <Tag size="small" color="arcoblue">
              ARCO DESIGN
            </Tag>
          </div>
        </Layout.Sider>
        <Layout className="studio-body">
          <Layout.Header className="studio-header">
            <Space className="header-context">
              <Dropdown droplist={<NavMenu />} trigger="click">
                <Button
                  className="mobile-nav"
                  icon={<IconMenu />}
                  aria-label="页面导航"
                />
              </Dropdown>
              <Breadcrumb>
                <Breadcrumb.Item>工作空间</Breadcrumb.Item>
                <Breadcrumb.Item>{st.project || "开始构建"}</Breadcrumb.Item>
              </Breadcrumb>
              <Tag size="small" className="desktop-tag">
                本地
              </Tag>
            </Space>
            <Space size="small" className="header-actions">
              <Tag color={st.dirty ? "orange" : "green"}>
                {st.project
                  ? st.dirty
                    ? "未保存 · 本机草稿"
                    : "已保存"
                  : "未选择项目"}
              </Tag>
              <Tooltip content="⌘ S / Ctrl S">
                <Action
                  disabled={!st.project}
                  icon={<IconSave />}
                  onClick={save}
                >
                  保存
                </Action>
              </Tooltip>
              <Action
                disabled={!st.project || !!activeJobs}
                icon={<IconSync />}
                onClick={() => showModal("sync")}
              >
                Sync
              </Action>
              <Action
                type="primary"
                disabled={!st.project || !!activeJobs}
                icon={<IconPlayArrow />}
                onClick={() => showModal("run")}
              >
                Run
              </Action>
            </Space>
          </Layout.Header>
          <div className="mobile-project">
            <ProjectSelector compact />
            <Action icon={<IconPlus />} onClick={() => showModal("project")}>
              新建项目
            </Action>
          </div>
          <Layout.Content className="studio-content">
            <Spin loading={st.busy} tip="正在处理…" className="workspace-spin">
              <div
                className={
                  st.busy ? "page-content busy-content" : "page-content"
                }
              >
                {st.error && (
                  <Alert
                    className="global-error"
                    type="error"
                    title="操作未完成"
                    content={st.error}
                    action={
                      st.project && (
                        <Button size="small" onClick={() => run(exportDraft)}>
                          导出草稿
                        </Button>
                      )
                    }
                    closable
                    onClose={() => {
                      st.error = "";
                      notify();
                    }}
                  />
                )}
                {st.storageError && (
                  <Alert type="warning" content={st.storageError} />
                )}
                {st.errors.size > 0 && (
                  <Alert
                    className="global-error"
                    type="warning"
                    content={`${st.errors.size} 处配置格式需要修正；原始输入已保留在草稿中。`}
                  />
                )}
                {!st.boot ? (
                  <Card className="loading-card">
                    <Spin tip="加载工作空间…" />
                  </Card>
                ) : !st.project || st.page === "overview" ? (
                  <Overview />
                ) : st.page === "models" ? (
                  <Models />
                ) : st.page === "config" ? (
                  <ConfigPage />
                ) : st.page === "files" ? (
                  <Files />
                ) : (
                  <Jobs />
                )}
              </div>
            </Spin>
          </Layout.Content>
        </Layout>
        {st.modal && <EditorDialog key={st.modal} />}
        <Drawer
          visible={!!st.schemaPanel}
          width={640}
          title={
            st.schemaPanel ? st.schemaPanel.name + " · 配置结构" : "配置结构"
          }
          footer={
            <Button
              onClick={() => {
                st.schemaPanel = null;
                notify();
              }}
            >
              关闭
            </Button>
          }
          onCancel={() => {
            st.schemaPanel = null;
            notify();
          }}
        >
          <CodeEditor
            readOnly
            label="配置结构"
            value={st.schemaPanel?.content || ""}
            rows={30}
          />
        </Drawer>
      </Layout>
    </ConfigProvider>
  );
}

if (document.getElementById("root"))
  createRoot(document.getElementById("root")).render(<App />);
