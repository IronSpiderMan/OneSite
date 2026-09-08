import React, { useState } from "react";
import {
  Alert,
  Form,
  Input,
  Modal,
  Radio,
  Select,
  Checkbox,
  Space,
  Typography,
} from "@arco-design/web-react";
import {
  st,
  api,
  run,
  commit,
  edit,
  notify,
  adopt,
  closeModal,
  newModelSpec,
  snake,
  relationTargets,
  newField,
  save,
  confirmAction,
  persistDraft,
} from "./state";
import { CodeEditor, Labeled } from "./editors";

export const TEMPLATES = {
  "app/backend/api/health.py":
    'from fastapi import APIRouter\n\nrouter = APIRouter(prefix="/health", tags=["health"])\n\n@router.get("")\nasync def health():\n    return {"status": "ok"}\n',
  "app/utils/helpers.py": '"""Shared application helpers."""\n',
  "app/tools/example.py":
    'async def run(**kwargs):\n    return {"message": "Hello", "inputs": kwargs}\n',
  "app/tasks/example.py":
    'async def run(**kwargs):\n    return {"status": "ok"}\n',
  "app/integrations/example.py":
    '"""External provider / message callback implementations."""\n',
  "app/frontend/features/example.tsx":
    "export default function Example() {\n  return <section>Hello, OneSite</section>;\n}\n",
  "app/agent_hooks.py": "async def before_run(context):\n    pass\n",
  "app/agent_tools/example.py":
    'async def run(**kwargs):\n    return {"status": "ok"}\n',
};

export function EditorDialog() {
  const type = st.modal;
  const [name, setName] = useState(type === "model" ? "Product" : "");
  const [template, setTemplate] = useState("table");
  const [file, setFile] = useState("app/utils/helpers.py");
  const [content, setContent] = useState(TEMPLATES["app/utils/helpers.py"]);
  const [component, setComponent] = useState("all");
  const [install, setInstall] = useState(false);
  const [buildCmd, setBuildCmd] = useState(false);
  const targets = relationTargets();
  const [target, setTarget] = useState(targets[0]?.table || "");
  const [field, setField] = useState((targets[0]?.table || "target") + "_id");
  const [key, setKey] = useState("id");
  const [fieldType, setFieldType] = useState("Optional[int]");
  const titles = {
    project: "创建项目",
    model: "新建模型",
    file: "新建源文件",
    foreignKey: "添加外键关系",
    sync: "生成项目代码",
    run: "运行项目",
  };
  async function submit() {
    if (type === "project") {
      if (st.dirty) {
        persistDraft();
        if (
          !(await confirmAction(
            "创建另一个项目",
            "当前项目的修改已保存在本机草稿，继续创建并切换项目？",
            false,
            "继续创建",
          ))
        )
          return;
      }
      const project = await api("create", { name });
      st.boot.projects.push({ name: project.name, path: project.path });
      adopt(project);
    } else if (type === "model") {
      await commit();
      const path = `app/models/${snake(name)}.py`;
      if (path in st.files) throw Error("该模型文件已存在");
      const spec = newModelSpec(name, template);
      const { source } = await api("render", { kind: "model", spec });
      st.files[path] = source;
      st.path = path;
      st.spec = spec;
      st.kind = "model";
      st.page = "models";
      st.mode = "form";
      st.tab = "fields";
      st.parseError = "";
      edit();
    } else if (type === "file") {
      await commit();
      if (file in st.files) throw Error("文件已存在");
      await api("validate", { files: { [file]: content } });
      st.files[file] = content;
      st.path = file;
      st.spec = null;
      st.formDirty = false;
      st.page = "files";
      st.mode = "source";
      st.parseError = "";
      edit();
    } else if (type === "foreignKey") {
      if (!target) throw Error("请先创建一个目标数据表模型");
      if (st.spec.fields.some((f) => f.name === field))
        throw Error("字段名已存在");
      const item = {
        ...newField(field, fieldType),
        kwargs: {
          foreign_key: JSON.stringify(`${target}.${key}`),
          index: "True",
          ...(fieldType.includes("Optional") ? { default: "None" } : {}),
        },
      };
      await api("render", {
        kind: "model",
        spec: { ...st.spec, fields: [...st.spec.fields, item] },
      });
      st.spec.fields.push(item);
      edit();
    } else {
      await save();
      const job = await api("start", {
        name: st.project,
        action: type,
        revision: st.revision,
        options: { component, install, build_cmd: buildCmd },
      });
      st.jobs[job.id] = { ...job, text: job.logs.map((v) => v.text).join("") };
      st.cursors[job.id] = job.cursor;
      st.selectedJob = job.id;
      st.page = "jobs";
      st.spec = null;
      st.formDirty = false;
    }
    closeModal();
  }
  return (
    <Modal
      title={titles[type]}
      visible
      maskClosable={false}
      style={{
        width: type === "file" ? 760 : 560,
        maxWidth: "calc(100vw - 32px)",
      }}
      confirmLoading={st.busy}
      okText={
        type === "sync"
          ? "保存并 Sync"
          : type === "run"
            ? "保存并 Run"
            : titles[type]
      }
      cancelText="取消"
      onCancel={() => {
        if (!st.busy) closeModal();
      }}
      onOk={() => run(submit)}
    >
      <Form layout="vertical" disabled={st.busy}>
        {type === "project" && (
          <>
            <Typography.Paragraph type="secondary">
              创建标准 OneSite 项目，保存在当前工作目录的 projects/ 下。
            </Typography.Paragraph>
            <Labeled
              label="项目名称"
              hint="英文字母开头，可包含字母、数字、下划线和连字符。"
            >
              <Input
                autoFocus
                value={name}
                onChange={setName}
                placeholder="my_workspace"
              />
            </Labeled>
          </>
        )}
        {type === "model" && (
          <>
            <Labeled label="模型类名">
              <Input
                autoFocus
                value={name}
                onChange={setName}
                placeholder="Product"
              />
            </Labeled>
            <Labeled label="模型类型">
              <Select
                value={template}
                onChange={setTemplate}
                options={[
                  { value: "table", label: "数据表 · 标准 CRUD" },
                  { value: "singleton", label: "单例 · 全局配置" },
                  { value: "link", label: "关联表 · 多对多" },
                  { value: "value", label: "值对象 · JSON 子模型" },
                ]}
              />
            </Labeled>
            <Alert
              type="info"
              content={`保存路径：app/models/${snake(name || "Product")}.py`}
            />
          </>
        )}
        {type === "file" && (
          <>
            <Labeled label="起始模板">
              <Select
                showSearch
                value={Object.hasOwn(TEMPLATES, file) ? file : undefined}
                placeholder="选择模板，或直接填写文件路径"
                options={Object.keys(TEMPLATES)}
                onChange={(v) => {
                  setFile(v);
                  setContent(TEMPLATES[v]);
                }}
              />
            </Labeled>
            <Labeled label="项目内相对路径">
              <Input value={file} onChange={setFile} />
            </Labeled>
            <Labeled label="文件内容">
              <Input.TextArea
                className="studio-code"
                value={content}
                onChange={setContent}
                autoSize={{ minRows: 10, maxRows: 18 }}
                spellCheck={false}
              />
            </Labeled>
          </>
        )}
        {type === "foreignKey" && (
          <>
            <Labeled label="目标模型">
              <Select
                value={target || undefined}
                onChange={(v) => {
                  setTarget(v);
                  setField(v + "_id");
                }}
                options={targets.map((t) => ({
                  value: t.table,
                  label: `${t.name} · ${t.table}`,
                }))}
              />
            </Labeled>
            <Labeled label="字段名">
              <Input value={field} onChange={setField} />
            </Labeled>
            <div className="form-grid">
              <Labeled label="目标主键">
                <Input value={key} onChange={setKey} />
              </Labeled>
              <Labeled label="字段类型">
                <Input value={fieldType} onChange={setFieldType} />
              </Labeled>
            </div>
            <Alert content="默认生成可选整型外键。请根据目标主键调整类型；多对多可以使用关联表与 m2m 配置。" />
          </>
        )}
        {["sync", "run"].includes(type) && (
          <>
            <Alert
              type="info"
              content="执行前自动保存项目。运行期间请先停止命令，再保存源文件。"
            />
            <div className="dialog-command">
              <Typography.Text code>
                {type === "sync"
                  ? `site sync${install ? " --install" : ""}${buildCmd ? " --build-cmd" : ""}`
                  : `site run . --component ${component}`}
              </Typography.Text>
            </div>
            {type === "sync" ? (
              <Space direction="vertical" size="large">
                <Checkbox checked={install} onChange={setInstall}>
                  安装后端和前端依赖（--install）
                </Checkbox>
                <Checkbox checked={buildCmd} onChange={setBuildCmd}>
                  构建 app/cmd 命令项目（--build-cmd）
                </Checkbox>
              </Space>
            ) : (
              <Labeled label="运行组件">
                <Radio.Group
                  type="button"
                  value={component}
                  onChange={setComponent}
                  options={[
                    { value: "all", label: "全部" },
                    { value: "backend", label: "仅后端" },
                    { value: "frontend", label: "仅前端" },
                  ]}
                />
              </Labeled>
            )}
          </>
        )}
        {st.error && (
          <Alert className="dialog-error" type="error" content={st.error} />
        )}
      </Form>
    </Modal>
  );
}
