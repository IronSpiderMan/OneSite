import { Message, Modal } from "@arco-design/web-react";

export const st = {
  boot: null,
  project: null,
  files: {},
  baseline: {},
  revision: "",
  page: "overview",
  path: null,
  mode: "form",
  spec: null,
  kind: null,
  tab: "fields",
  dirty: false,
  formDirty: false,
  busy: false,
  error: "",
  parseError: "",
  skipped: [],
  modal: null,
  schemaPanel: null,
  jobs: {},
  cursors: {},
  selectedJob: null,
  errors: new Map(),
  buffers: new Map(),
};
let version = 0;
const listeners = new Set();
export const subscribe = (fn) => {
  listeners.add(fn);
  return () => listeners.delete(fn);
};
export const snapshot = () => version;
export function notify() {
  version++;
  listeners.forEach((fn) => fn());
}
export const draftKey = (name) =>
  `onesite-studio:${st.boot?.root}:${name || st.project}`;
let persistTimer;
export function draft() {
  return {
    version: 1,
    project: st.project,
    files: st.files,
    baseline: st.baseline,
    revision: st.revision,
    updated: Date.now(),
    active: st.spec
      ? { path: st.path, kind: st.kind, spec: st.spec, tab: st.tab }
      : null,
    buffers: [...st.buffers],
    errors: [...st.errors],
  };
}
export function persistDraft() {
  clearTimeout(persistTimer);
  if (!st.project || !st.dirty) return;
  try {
    localStorage.setItem(draftKey(), JSON.stringify(draft()));
  } catch {
    st.storageError = "浏览器草稿空间不足，请保存项目或导出草稿。";
    notify();
  }
}
export function edit() {
  st.dirty = true;
  if (st.spec) st.formDirty = true;
  clearTimeout(persistTimer);
  persistTimer = setTimeout(persistDraft, 400);
  notify();
}
export function forget(id) {
  st.buffers.delete(id);
  st.errors.delete(id);
}
export function ensureValid() {
  if (st.errors.size)
    throw Error("请先修正配置格式：" + [...st.errors.keys()].join("、"));
}
export async function api(path, data = {}) {
  const token = document.querySelector('meta[name="studio-token"]')?.content;
  const response = await fetch("/api/" + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Studio-Token": token },
    body: JSON.stringify(data),
  });
  let result;
  try {
    result = await response.json();
  } catch {
    throw Error("本地服务响应异常，请检查终端或重新启动 site web。");
  }
  if (!response.ok) throw Error(result.error || response.statusText);
  return result;
}
export async function run(fn) {
  if (st.busy) return false;
  st.busy = true;
  st.error = "";
  notify();
  try {
    const result = await fn();
    return result === false ? false : true;
  } catch (error) {
    st.error = error.message || String(error);
    Message.error(st.error);
    return false;
  } finally {
    st.busy = false;
    notify();
  }
}
export function confirmAction(
  title,
  content,
  dangerous = false,
  okText = "确认",
) {
  return new Promise((resolve) =>
    Modal.confirm({
      title,
      content,
      okText,
      cancelText: "取消",
      maskClosable: false,
      okButtonProps: dangerous ? { status: "danger" } : {},
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    }),
  );
}
export async function commit() {
  ensureValid();
  if (st.spec && st.formDirty) {
    const { source } = await api("render", { kind: st.kind, spec: st.spec });
    st.files[st.path] = source;
    st.formDirty = false;
  }
}
export const modelPaths = () =>
  Object.keys(st.files)
    .filter(
      (p) =>
        p.startsWith("app/models/") &&
        p.endsWith(".py") &&
        !p.endsWith("/__init__.py"),
    )
    .sort();
export async function prepare() {
  st.spec = null;
  st.formDirty = false;
  st.parseError = "";
  st.kind = st.path === "site_config.py" ? "config" : "model";
  if (!st.path || st.page === "files") {
    st.mode = "source";
    return;
  }
  try {
    st.spec = await api("parse", { kind: st.kind, source: st.files[st.path] });
    st.mode = "form";
  } catch (error) {
    st.parseError = error.message;
    st.mode = "source";
  }
}
export async function navigate(page) {
  await commit();
  st.page = page;
  st.spec = null;
  st.formDirty = false;
  if (st.project) {
    if (page === "config") {
      st.path =
        "site_config.py" in st.files ? "site_config.py" : "site_config.json";
      await prepare();
    } else if (page === "models") {
      if (!modelPaths().includes(st.path)) st.path = modelPaths()[0] || null;
      if (st.path) await prepare();
    } else if (page === "files") {
      if (!(st.path in st.files))
        st.path = Object.keys(st.files).sort()[0] || null;
      st.mode = "source";
    }
  }
  notify();
}
export async function chooseFile(path) {
  await commit();
  st.path = path;
  st.tab = "fields";
  await prepare();
  notify();
}
export function adopt(project) {
  st.project = project.name;
  st.files = project.files;
  st.baseline = structuredClone(project.files);
  st.revision = project.revision;
  st.dirty = false;
  st.formDirty = false;
  st.spec = null;
  st.path = null;
  st.errors.clear();
  st.buffers.clear();
  st.jobs = {};
  st.cursors = {};
  st.selectedJob = null;
  st.skipped = project.skipped || [];
  st.page = "overview";
  st.storageError = "";
  st.error = "";
  st.parseError = "";
  notify();
}
export function restoreDraft(saved, sameProject = true) {
  if (saved.version !== 1 || !saved.files || Array.isArray(saved.files))
    throw Error("无效的 Studio 草稿");
  st.files = saved.files;
  st.spec = null;
  st.mode = "source";
  st.formDirty = false;
  if (sameProject && saved.baseline && saved.revision) {
    st.baseline = saved.baseline;
    st.revision = saved.revision;
  }
  st.path = Object.keys(st.files).sort()[0];
  st.page = "files";
  if (saved.active) {
    st.path = saved.active.path;
    st.kind = saved.active.kind;
    st.spec = saved.active.spec;
    st.formDirty = true;
    st.mode = "form";
    st.tab = saved.active.tab || "fields";
    st.page = st.kind === "config" ? "config" : "models";
  }
  st.buffers = new Map(saved.buffers || []);
  st.errors = new Map(saved.errors || []);
  edit();
}
export async function openProject(name) {
  if (st.dirty) {
    persistDraft();
    if (
      !(await confirmAction(
        "切换项目",
        "当前修改已保存在本机草稿中。切换后可再次打开此项目恢复。",
        false,
        "切换项目",
      ))
    )
      return;
  }
  adopt(await api("open", { name }));
  let saved;
  try {
    saved = JSON.parse(localStorage.getItem(draftKey(name)) || "null");
  } catch {
    /* Invalid browser data is ignored. */
  }
  if (
    saved &&
    (await confirmAction(
      "恢复未保存草稿",
      `发现 ${name} 的本机草稿，是否恢复继续编辑？`,
      false,
      "恢复草稿",
    ))
  )
    restoreDraft(saved);
  await pollJobs();
  notify();
}
export async function save() {
  await commit();
  const result = await api("save", {
    name: st.project,
    files: st.files,
    revision: st.revision,
    baseline: st.baseline,
  });
  st.files = result.files;
  st.baseline = structuredClone(result.files);
  st.revision = result.revision;
  st.dirty = false;
  st.storageError = "";
  clearTimeout(persistTimer);
  try {
    localStorage.removeItem(draftKey());
  } catch {
    /* Project files have already been saved. */
  }
  if (st.spec) await prepare();
  Message.success("项目已保存");
  notify();
}
export async function reloadProject() {
  if (
    st.dirty &&
    !(await confirmAction(
      "重新加载项目",
      "放弃当前未保存修改，重新读取磁盘文件？也可先导出草稿。",
      true,
      "重新加载",
    ))
  )
    return;
  const name = st.project;
  adopt(await api("open", { name }));
  try {
    localStorage.removeItem(draftKey(name));
  } catch {
    /* Optional cache. */
  }
}
export async function deleteFile() {
  if (["site_config.py", "site_config.json"].includes(st.path))
    throw Error("请保留项目配置文件，可以直接编辑它的内容。");
  if (
    !(await confirmAction(
      "删除源文件",
      `${st.path} 将在保存项目时删除。`,
      true,
      "删除文件",
    ))
  )
    return;
  const old = st.path;
  delete st.files[old];
  st.spec = null;
  st.path = null;
  st.formDirty = false;
  for (const id of st.errors.keys()) if (id.startsWith(old + ":")) forget(id);
  edit();
  await navigate(st.page);
}
export function download(name, text) {
  const url = URL.createObjectURL(
    new Blob([text], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function exportDraft() {
  try {
    await commit();
  } catch {
    /* Preserve invalid editor buffers in the draft too. */
  }
  download(st.project + ".studio.json", JSON.stringify(draft(), null, 2));
  Message.success("草稿已导出");
}
export function showModal(type) {
  st.modal = type;
  st.error = "";
  notify();
}
export function closeModal() {
  st.modal = null;
  notify();
}
export function snake(name) {
  return name
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1_$2")
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .toLowerCase();
}
export const newField = (name = "name", type = "str") => ({
  name,
  type,
  kwargs: {},
  props: {},
  value: null,
});
export function newModelSpec(name, template) {
  return {
    name,
    table: template !== "value",
    table_name: "",
    prefix: st.boot.model_imports,
    suffix: "",
    config:
      template === "singleton"
        ? { is_singleton: true }
        : template === "link"
          ? { is_link_table: true }
          : {},
    fields: ["value", "link"].includes(template)
      ? []
      : [
          {
            ...newField("id", "Optional[int]"),
            kwargs: { default: "None", primary_key: "True" },
          },
          { ...newField(), props: { is_search_field: true } },
        ],
    hooks: "",
    extra: "",
  };
}
export function relationTargets() {
  return modelPaths().flatMap((path) => {
    const source = st.files[path],
      match = source.match(/class\s+(\w+)\([^)]*table\s*=\s*True[^)]*\)/);
    if (!match) return [];
    return [
      {
        name: match[1],
        table:
          source.match(/__tablename__\s*=\s*['"]([^'"]+)['"]/)?.[1] ||
          snake(match[1]),
      },
    ];
  });
}
let polling = false;
export async function pollJobs() {
  if (!st.project || polling) return;
  polling = true;
  const name = st.project;
  try {
    const { jobs } = await api("jobs", { name, cursors: st.cursors });
    if (name !== st.project) return;
    for (const job of jobs) {
      const previous = st.jobs[job.id];
      const text =
        (job.truncated ? "[较早的日志已截断]\n" : previous?.text || "") +
        job.logs.map((line) => line.text).join("");
      st.jobs[job.id] = { ...job, text: text.slice(-750000) };
      st.cursors[job.id] = job.cursor;
    }
    if (!st.selectedJob && jobs.length) st.selectedJob = jobs.at(-1).id;
    st.connectionError = "";
    notify();
  } catch {
    st.connectionError = "与本地服务的连接已中断";
    notify();
  } finally {
    polling = false;
  }
}
export function resolved(schema = {}, root) {
  return schema.$ref
    ? resolved(root.$defs?.[schema.$ref.split("/").pop()] || {}, root)
    : schema;
}
export function schemaDefault(schema, root, active = false, depth = 0) {
  const s = resolved(schema, root);
  if ("default" in s && (!active || s.default !== null))
    return structuredClone(s.default);
  if ("const" in s) return s.const;
  if (s.enum) return s.enum[0];
  if (s.anyOf)
    return schemaDefault(
      s.anyOf.find((v) => v.type !== "null") || {},
      root,
      active,
      depth,
    );
  if (s.properties || s.type === "object") {
    if (depth > 4) return {};
    return Object.fromEntries(
      Object.entries(s.properties || {})
        .filter(([k, v]) => (s.required || []).includes(k) || "default" in v)
        .map(([k, v]) => [k, schemaDefault(v, root, false, depth + 1)]),
    );
  }
  if (s.type === "array") return [];
  if (s.type === "boolean") return false;
  if (["integer", "number"].includes(s.type)) return s.minimum ?? 0;
  return "";
}
export function expandSchema(schema, root, depth = 0) {
  const s = resolved(schema, root);
  if (depth > 4) return s;
  const value = { ...s };
  if (s.properties)
    value.properties = Object.fromEntries(
      Object.entries(s.properties).map(([k, v]) => [
        k,
        expandSchema(v, root, depth + 1),
      ]),
    );
  if (s.items) value.items = expandSchema(s.items, root, depth + 1);
  if (s.anyOf)
    value.anyOf = s.anyOf.map((v) => expandSchema(v, root, depth + 1));
  if (typeof s.additionalProperties === "object")
    value.additionalProperties = expandSchema(
      s.additionalProperties,
      root,
      depth + 1,
    );
  return value;
}
