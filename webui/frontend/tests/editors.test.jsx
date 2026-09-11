import React, { useSyncExternalStore } from "react";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { FieldEditor, JsonEditor } from "../src/editors";
import {
  confirmAction,
  st,
  newField,
  subscribe,
  snapshot,
  ensureValid,
  persistDraft,
  draftKey,
  adopt,
  restoreDraft,
  save,
  openProject,
} from "../src/state";

beforeEach(() => {
  st.boot = { root: "/tmp/arco-tests" };
  adopt({
    name: "Demo",
    files: { "app/models/product.py": "original" },
    revision: "rev1",
  });
  st.path = "app/models/product.py";
  st.spec = { fields: [newField("price", "float")] };
});
function FieldHarness() {
  useSyncExternalStore(subscribe, snapshot);
  return <FieldEditor field={st.spec.fields[0]} index={0} />;
}
function JsonHarness() {
  useSyncExternalStore(subscribe, snapshot);
  return (
    <JsonEditor
      value={st.spec.config || {}}
      onChange={(v) => (st.spec.config = v)}
      id="settings"
      object
    />
  );
}

it("edits field defaults, custom types and independent role permissions through Arco", async () => {
  const user = userEvent.setup();
  const { container } = render(<FieldHarness />);
  expect(container.querySelector("select")).toBeNull();
  await user.click(screen.getByRole("combobox", { name: "Python 类型" }));
  await waitFor(() =>
    expect(
      getComputedStyle(screen.getByText("int", { exact: true })).pointerEvents,
    ).not.toBe("none"),
  );
  await user.click(screen.getByText("int", { exact: true }));
  expect(st.spec.fields[0].type).toBe("int");
  fireEvent.change(screen.getByLabelText("默认值"), { target: { value: "0" } });
  fireEvent.change(screen.getByLabelText("default_factory"), {
    target: { value: "uuid4" },
  });
  expect(st.spec.fields[0].kwargs).toEqual({ default_factory: "uuid4" });
  await user.click(screen.getByRole("button", { name: "设置角色权限" }));
  await user.click(
    screen.getByRole("checkbox", { name: "字段 CRU 权限 user c" }),
  );
  await user.click(
    screen.getByRole("checkbox", { name: "字段 CRU 权限 user u" }),
  );
  expect(st.spec.fields[0].props.permissions).toEqual({
    user: "r",
    admin: "cru",
    developer: "cru",
  });
});

it("keeps invalid JSON through rerender and local draft recovery, blocking save until repaired", () => {
  const view = render(<JsonHarness />);
  fireEvent.change(screen.getByLabelText("JSON 配置"), {
    target: { value: '{"visible":' },
  });
  expect(() => ensureValid()).toThrow("请先修正");
  act(() => persistDraft());
  const saved = JSON.parse(localStorage.getItem(draftKey()));
  expect(saved.buffers).toContainEqual(["settings", '{"visible":']);
  view.unmount();
  act(() => restoreDraft(saved));
  render(<JsonHarness />);
  expect(screen.getByLabelText("JSON 配置").value).toBe('{"visible":');
  fireEvent.change(screen.getByLabelText("JSON 配置"), {
    target: { value: '{"visible":["admin"]}' },
  });
  expect(() => ensureValid()).not.toThrow();
  expect(st.spec.config).toEqual({ visible: ["admin"] });
});

it("uses an Arco confirmation dialog and resolves both cancel and confirmation", async () => {
  const native = vi.spyOn(window, "confirm").mockImplementation(() => {
    throw Error("Native dialog is forbidden");
  });
  const user = userEvent.setup();
  let result;
  act(() => {
    result = confirmAction("放弃草稿", "确定放弃？");
  });
  await user.click(screen.getByRole("button", { name: "取消" }));
  expect(await result).toBe(false);
  await waitFor(() => expect(screen.queryByText("确定放弃？")).toBeNull());
  act(() => {
    result = confirmAction("继续编辑", "确定继续？", false, "继续");
  });
  await user.click(screen.getByRole("button", { name: "继续", exact: true }));
  expect(await result).toBe(true);
  expect(native).not.toHaveBeenCalled();
});

it("saves rendered model with baseline and only clears local draft after server success", async () => {
  st.kind = "model";
  st.formDirty = true;
  st.dirty = true;
  persistDraft();
  const fetch = vi.fn(async (url, options) => ({
    ok: true,
    json: async () =>
      url.endsWith("render")
        ? { source: "rendered" }
        : url.endsWith("save")
          ? { files: { [st.path]: "rendered" }, revision: "rev2" }
          : { fields: [] },
  }));
  vi.stubGlobal("fetch", fetch);
  await act(async () => {
    await save();
  });
  const payload = JSON.parse(
    fetch.mock.calls.find(([url]) => url.endsWith("save"))[1].body,
  );
  expect(payload.files[st.path]).toBe("rendered");
  expect(payload.baseline[st.path]).toBe("original");
  expect(st.revision).toBe("rev2");
  expect(st.dirty).toBe(false);
  expect(localStorage.getItem(draftKey())).toBeNull();
});


it("opens an external directory and keeps a single project entry", async () => {
  st.boot.projects = [];
  localStorage.clear();
  const project = { name: "/external/Demo", path: "/external/Demo", files: { "site_config.json": "{}" }, revision: "external" };
  const fetch = vi.fn(async (url) => ({ ok: true, json: async () => url.endsWith("open") ? project : { jobs: [] } }));
  vi.stubGlobal("fetch", fetch);
  await openProject(undefined, "/external/Demo");
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ path: "/external/Demo" });
  expect(st.project).toBe(project.name);
  expect(st.files).toEqual(project.files);
  await openProject(project.name);
  expect(st.boot.projects).toEqual([{ name: project.name, path: project.path }]);
  fetch.mockImplementation(async () => ({ ok: false, json: async () => ({ error: "项目不存在" }) }));
  await expect(openProject(undefined, "/missing")).rejects.toThrow("项目不存在");
  expect(st.project).toBe(project.name);
  expect(st.files).toEqual(project.files);
});

it("uses the native picker, leaves the project on cancel, and falls back on failure", async () => {
  const { chooseProject } = await import("../src/state");
  st.boot.native_picker = true;
  st.boot.projects = [];
  localStorage.clear();
  const project = { name: "/native/Demo", path: "/native/Demo", files: {}, revision: "native" };
  const fetch = vi.fn(async (url) => ({ ok: true, json: async () =>
    url.endsWith("select-directory") ? { path: project.path } : url.endsWith("open") ? project : { jobs: [] }
  }));
  vi.stubGlobal("fetch", fetch);
  await chooseProject();
  expect(st.project).toBe(project.name);
  expect(JSON.parse(fetch.mock.calls.find(([url]) => url.endsWith("open"))[1].body)).toEqual({ path: project.path });
  fetch.mockClear();
  fetch.mockImplementation(async () => ({ ok: true, json: async () => ({ path: null }) }));
  await chooseProject();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(st.project).toBe(project.name);
  fetch.mockImplementation(async () => ({ ok: false, json: async () => ({ error: "不可用" }) }));
  await expect(chooseProject()).rejects.toThrow("不可用");
  expect(st.modal).toBe("openProject");
  st.modal = null;
});
