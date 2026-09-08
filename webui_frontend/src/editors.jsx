import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Collapse,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "@arco-design/web-react";
import {
  IconCode,
  IconDelete,
  IconSettings,
} from "@arco-design/web-react/icon";
import {
  st,
  edit,
  notify,
  forget,
  resolved,
  schemaDefault,
  expandSchema,
} from "./state";

export function Labeled({ label, hint, children }) {
  return (
    <Form.Item label={label} extra={hint}>
      {React.isValidElement(children)
        ? React.cloneElement(children, {
            "aria-label": children.props["aria-label"] || label,
          })
        : children}
    </Form.Item>
  );
}
export function TextValue({ value, onChange, ...props }) {
  return (
    <Input
      value={value ?? ""}
      onChange={(v) => {
        onChange(v);
        edit();
      }}
      {...props}
    />
  );
}
export function CodeEditor({
  value,
  onChange,
  label = "源码编辑器",
  rows = 16,
  readOnly = false,
  ...props
}) {
  return (
    <Input.TextArea
      aria-label={label}
      className="studio-code"
      value={value ?? ""}
      autoSize={false}
      style={{ height: rows * 22 + 24 }}
      readOnly={readOnly}
      spellCheck={false}
      onChange={(v) => {
        onChange?.(v);
        if (!readOnly) edit();
      }}
      {...props}
    />
  );
}
export function JsonEditor({
  value,
  onChange,
  id,
  label = "JSON 配置",
  object = false,
  rows = 6,
}) {
  const serialized = JSON.stringify(value, null, 2);
  const previous = useRef(serialized);
  const [raw, setRaw] = useState(() => st.buffers.get(id) ?? serialized);
  useEffect(() => {
    // Only external semantic changes replace the editor buffer. Invalid JSON and
    // in-progress whitespace survive parent renders and schema filtering.
    if (serialized !== previous.current) {
      previous.current = serialized;
      if (!st.errors.has(id)) {
        setRaw(serialized);
        st.buffers.delete(id);
      }
    }
  }, [serialized, id]);
  const error = st.errors.get(id);
  return (
    <div className="json-editor">
      <Input.TextArea
        aria-label={label}
        className="studio-code"
        spellCheck={false}
        value={raw}
        status={error ? "error" : undefined}
        autoSize={{ minRows: rows, maxRows: Math.max(20, rows) }}
        onChange={(text) => {
          setRaw(text);
          st.buffers.set(id, text);
          try {
            const parsed = JSON.parse(text);
            if (
              object &&
              (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
            )
              throw Error("请输入 JSON 对象 {}");
            previous.current = JSON.stringify(parsed, null, 2);
            onChange(parsed);
            st.errors.delete(id);
          } catch (e) {
            st.errors.set(id, e.message);
          }
          edit();
        }}
      />
      {error && (
        <Typography.Text type="error" className="editor-error">
          {error}
        </Typography.Text>
      )}
    </div>
  );
}
export function PermissionMatrix({
  value,
  onChange,
  chars = "crud",
  title = "角色权限",
}) {
  const structured =
    value && typeof value === "object" && !Array.isArray(value);
  const columns = [
    { title: "角色", dataIndex: "role", width: 130 },
    ...[...chars].map((char) => ({
      title: { c: "创建", r: "读取", u: "更新", d: "删除" }[char],
      align: "center",
      render: (_, row) => (
        <Checkbox
          aria-label={`${title} ${row.role} ${char}`}
          checked={(value[row.role] || "").includes(char)}
          onChange={(checked) => {
            const perms = new Set(value[row.role] || "");
            checked ? perms.add(char) : perms.delete(char);
            onChange({
              ...value,
              [row.role]: [...chars].filter((c) => perms.has(c)).join(""),
            });
            edit();
          }}
        />
      ),
    })),
  ];
  return (
    <Card
      className="subcard"
      title={title}
      extra={
        <Button
          size="small"
          type="text"
          onClick={() => {
            onChange(
              value === undefined
                ? { user: chars, admin: chars, developer: chars }
                : undefined,
            );
            edit();
          }}
        >
          {value === undefined ? "设置角色权限" : "恢复继承"}
        </Button>
      }
    >
      {structured ? (
        <Table
          columns={columns}
          data={["user", "admin", "developer"].map((role) => ({
            role,
            key: role,
          }))}
          pagination={false}
          size="small"
          border={false}
        />
      ) : (
        <Typography.Paragraph type="secondary" className="no-margin">
          {value === undefined
            ? "当前继承默认权限。设置后，三个角色可以分别配置。"
            : `兼容格式：${JSON.stringify(value)}。可在完整配置中修改，或恢复继承后使用角色矩阵。`}
        </Typography.Paragraph>
      )}
    </Card>
  );
}
function ShapeButton({ name, schema, root }) {
  return (
    <Tooltip content="查看完整结构、枚举和必填项">
      <Button
        type="text"
        size="mini"
        icon={<IconCode />}
        aria-label={`查看 ${name} 结构`}
        onClick={() => {
          st.schemaPanel = {
            name,
            content: JSON.stringify(expandSchema(schema, root), null, 2),
          };
          notify();
        }}
      />
    </Tooltip>
  );
}
export function SchemaEditor({
  values,
  onChange,
  schema,
  expressions,
  scope,
  title,
}) {
  const [query, setQuery] = useState("");
  const idFor = (name) => `${st.path}:${scope}.${name}`;
  function set(name, value) {
    onChange({ ...values, [name]: value });
    edit();
  }
  function reset(name) {
    const next = { ...values };
    delete next[name];
    if (expressions) delete expressions[name];
    forget(idFor(name));
    onChange(next);
    edit();
  }
  return (
    <Card
      title={title}
      className="schema-card"
      extra={
        <Tag color="arcoblue">
          {Object.keys(schema.properties || {}).length} 项配置
        </Tag>
      }
    >
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Typography.Text type="secondary">
          配置结构来自当前 OneSite。复杂值使用 JSON；未知扩展键会完整保留。
        </Typography.Text>
        <Input.Search
          aria-label="搜索配置项"
          placeholder="搜索配置项，例如 navigation、reports、agents"
          allowClear
          value={query}
          onChange={setQuery}
        />
        <div className="schema-grid">
          {Object.entries(schema.properties || {})
            .filter(([name]) =>
              name.toLowerCase().includes(query.toLowerCase()),
            )
            .map(([name, definition]) => {
              const id = idFor(name),
                active = Object.hasOwn(values, name),
                expr = expressions && Object.hasOwn(expressions, name);
              let shape = resolved(definition, schema);
              const variants = shape.anyOf
                ?.map((v) => resolved(v, schema))
                .filter((v) => v.type !== "null");
              if (variants?.length === 1) shape = variants[0];
              const enumShape = variants?.find((v) => v.enum);
              const enumValues =
                shape.enum ||
                (enumShape &&
                variants.every((v) => v.type === "string" || v.enum)
                  ? enumShape.enum
                  : null);
              let control;
              if (expr)
                control = (
                  <CodeEditor
                    label={`${name} Python 表达式`}
                    rows={3}
                    value={expressions[name]}
                    onChange={(v) => {
                      expressions[name] = v;
                    }}
                  />
                );
              else if (!active)
                control = (
                  <Space className="schema-default">
                    <Typography.Text
                      type="secondary"
                      ellipsis={{ showTooltip: true }}
                    >
                      默认：{JSON.stringify(schemaDefault(definition, schema))}
                    </Typography.Text>
                    <Button
                      size="small"
                      onClick={() =>
                        set(name, schemaDefault(definition, schema, true))
                      }
                    >
                      配置
                    </Button>
                  </Space>
                );
              else if (enumValues)
                control = (
                  <Select
                    aria-label={name}
                    options={enumValues}
                    value={values[name]}
                    allowClear
                    allowCreate={
                      !!variants?.some((v) => v.type === "string" && !v.enum)
                    }
                    onChange={(v) => set(name, v ?? null)}
                  />
                );
              else if (shape.type === "boolean")
                control = (
                  <Switch
                    aria-label={name}
                    checked={!!values[name]}
                    onChange={(v) => set(name, v)}
                    checkedText="开启"
                    uncheckedText="关闭"
                  />
                );
              else if (["integer", "number"].includes(shape.type))
                control = (
                  <InputNumber
                    aria-label={name}
                    value={values[name] ?? undefined}
                    min={shape.minimum}
                    max={shape.maximum}
                    precision={shape.type === "integer" ? 0 : undefined}
                    onChange={(v) => set(name, v ?? null)}
                    style={{ width: "100%" }}
                  />
                );
              else if (shape.type === "string")
                control = /password|secret_key/.test(name) ? (
                  <Input.Password
                    aria-label={name}
                    value={values[name] ?? ""}
                    onChange={(v) => set(name, v)}
                  />
                ) : (
                  <Input
                    aria-label={name}
                    value={values[name] ?? ""}
                    onChange={(v) => set(name, v)}
                  />
                );
              else
                control = (
                  <JsonEditor
                    value={values[name]}
                    onChange={(v) => onChange({ ...values, [name]: v })}
                    id={id}
                    label={`${name} JSON`}
                    rows={4}
                  />
                );
              return (
                <div className="schema-entry" key={name}>
                  <Space className="schema-label">
                    <Typography.Text code>{name}</Typography.Text>
                    {!active && !expr && <Tag size="small">继承默认</Tag>}
                    <ShapeButton
                      name={name}
                      schema={definition}
                      root={schema}
                    />
                  </Space>
                  {control}
                  {(active || expr) && (
                    <Space size="mini" className="schema-actions">
                      <Button
                        type="text"
                        size="mini"
                        onClick={() => reset(name)}
                      >
                        恢复默认
                      </Button>
                      {expressions && (
                        <Button
                          type="text"
                          size="mini"
                          onClick={() => {
                            if (expr) {
                              delete expressions[name];
                              set(
                                name,
                                schemaDefault(definition, schema, true),
                              );
                            } else {
                              expressions[name] = "None";
                              const next = { ...values };
                              delete next[name];
                              forget(id);
                              onChange(next);
                              edit();
                            }
                          }}
                        >
                          {expr ? "改为表单值" : "使用 Python 表达式"}
                        </Button>
                      )}
                    </Space>
                  )}
                </div>
              );
            })}
        </div>
        <Collapse bordered={false}>
          <Collapse.Item name="full" header="完整 JSON / 添加扩展配置">
            <JsonEditor
              value={values}
              onChange={onChange}
              id={idFor("$full")}
              label="完整配置 JSON"
              object
              rows={12}
            />
          </Collapse.Item>
        </Collapse>
      </Space>
    </Card>
  );
}

export function FieldEditor({ field, index }) {
  const f = field,
    kw = f.kwargs,
    id = `${st.path}:field-${index}`;
  const setProp = (name, v) => {
    if (v === undefined || v === "") delete f.props[name];
    else f.props[name] = v;
    edit();
  };
  const setKw = (name, v) => {
    if (v === "") delete kw[name];
    else kw[name] = v;
    edit();
  };
  const unquote = (v) => {
    if (!v) return "";
    try {
      return JSON.parse(v);
    } catch {
      return v.replace(/^['"]|['"]$/g, "");
    }
  };
  return (
    <Form layout="vertical" className="field-form">
      <div className="form-grid">
        <Labeled label="字段名">
          <TextValue value={f.name} onChange={(v) => (f.name = v)} />
        </Labeled>
        <Labeled label="Python 类型">
          <Select
            showSearch
            allowCreate
            options={[
              "str",
              "int",
              "float",
              "bool",
              "datetime",
              "date",
              "Decimal",
              "UUID",
              "Optional[int]",
              "Optional[str]",
              "dict[str, Any]",
              "list[str]",
            ]}
            value={f.type}
            onChange={(v) => {
              f.type = v;
              edit();
            }}
          />
        </Labeled>
      </div>
      {f.value === null ? (
        <>
          <Labeled label="数据库属性">
            <Space wrap>
              {["primary_key", "index", "unique", "nullable"].map((name) => (
                <Checkbox
                  key={name}
                  checked={kw[name] === "True"}
                  onChange={(v) => setKw(name, v ? "True" : "")}
                >
                  {name}
                </Checkbox>
              ))}
            </Space>
          </Labeled>
          <div className="form-grid">
            <Labeled label="默认值" hint="Python 表达式；必填字段留空。">
              <Input
                value={kw.default || ""}
                placeholder='None / 0 / "文本"'
                onChange={(v) => {
                  if (v) delete kw.default_factory;
                  setKw("default", v);
                }}
              />
            </Labeled>
            <Labeled
              label="default_factory"
              hint="例如 uuid4 或 lambda: datetime.now(timezone.utc)"
            >
              <Input
                value={kw.default_factory || ""}
                onChange={(v) => {
                  if (v) delete kw.default;
                  setKw("default_factory", v);
                }}
              />
            </Labeled>
            <Labeled label="外键目标" hint="目标表名.主键">
              <Input
                value={unquote(kw.foreign_key)}
                placeholder="category.id"
                onChange={(v) =>
                  setKw("foreign_key", v ? JSON.stringify(v) : "")
                }
              />
            </Labeled>
            <Labeled label="表单组件">
              <Select
                placeholder="自动识别"
                value={f.props.component}
                options={[
                  "textarea",
                  "image",
                  "images",
                  "file",
                  "json",
                  "video_stream",
                  "location",
                ]}
                allowClear
                onChange={(v) => setProp("component", v)}
              />
            </Labeled>
          </div>
          <Space wrap className="field-flags">
            {[
              ["is_search_field", "可搜索"],
              ["create_optional", "创建时可选"],
              ["update_optional", "更新时可选"],
            ].map(([key, label]) => (
              <Checkbox
                key={key}
                checked={!!f.props[key]}
                onChange={(v) => setProp(key, v ? true : undefined)}
              >
                {label}
              </Checkbox>
            ))}
          </Space>
          <PermissionMatrix
            title="字段 CRU 权限"
            chars="cru"
            value={f.props.permissions}
            onChange={(v) => {
              if (v === undefined) delete f.props.permissions;
              else f.props.permissions = v;
            }}
          />
          <Collapse bordered={false}>
            <Collapse.Item name="constraints" header="长度与数值约束">
              <div className="form-grid three">
                {["max_length", "min_length", "ge", "le", "gt", "lt"].map(
                  (key) => (
                    <Labeled key={key} label={key}>
                      <Input
                        value={kw[key] || ""}
                        onChange={(v) => setKw(key, v)}
                      />
                    </Labeled>
                  ),
                )}
              </div>
            </Collapse.Item>
            <Collapse.Item
              name="kwargs"
              header="高级 Field 参数 · Python 表达式字符串"
            >
              <JsonEditor
                value={kw}
                onChange={(v) => (f.kwargs = v)}
                id={`${id}.kwargs`}
                label="高级 Field 参数 JSON"
                object
              />
            </Collapse.Item>
            <Collapse.Item
              name="props"
              header="完整 site_props · 条件、级联、翻译、JSON 等"
            >
              <JsonEditor
                value={f.props}
                onChange={(v) => (f.props = v)}
                id={`${id}.props`}
                label="字段 site_props JSON"
                object
              />
              <Typography.Paragraph type="secondary">
                支持
                visible_when、required_when、cascade、reverse、group、fixed_keys、lock_keys、translations、importable、exportable
                等。
              </Typography.Paragraph>
            </Collapse.Item>
          </Collapse>
        </>
      ) : (
        <>
          <Labeled
            label="自定义赋值"
            hint="保留 Relationship(...) 或直接赋值等 Python 表达式。"
          >
            <CodeEditor
              value={f.value}
              onChange={(v) => (f.value = v)}
              rows={5}
            />
          </Labeled>
          <Button
            icon={<IconSettings />}
            onClick={() => {
              f.value = null;
              edit();
            }}
          >
            转换为 Field 参数
          </Button>
        </>
      )}
    </Form>
  );
}
