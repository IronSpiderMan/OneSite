import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { DirectoryPicker } from "../src/dialogs";

it("browses folders and selects only project directories without text input", async () => {
  const onSelect = vi.fn();
  const fetch = vi.fn(async (_, options) => {
    const { path = "/workspace" } = JSON.parse(options.body);
    return { ok: true, json: async () => ({
      path, parent: "/", home: "/home", root: "/workspace",
      is_project: path === "/workspace/项目",
      directories: path === "/workspace" ? [{ name: "项目", path: "/workspace/项目" }] : [],
    }) };
  });
  vi.stubGlobal("fetch", fetch);
  render(<DirectoryPicker onSelect={onSelect} />);
  fireEvent.click(await screen.findByRole("button", { name: /项目/ }));
  await screen.findByText("已选择 OneSite 项目，可以打开。");
  expect(onSelect).toHaveBeenLastCalledWith("/workspace/项目");
  expect(screen.queryByRole("textbox")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "返回上级" }));
  await waitFor(() => expect(screen.getByText("/", { exact: true })).toBeTruthy());
  expect(onSelect).toHaveBeenLastCalledWith("");
  fireEvent.click(screen.getByRole("button", { name: "主目录" }));
  await screen.findByText("/home", { exact: true });
});

it("shows directory errors without leaving a project selected", async () => {
  const onSelect = vi.fn();
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, json: async () => ({ error: "没有权限读取该目录" }) })));
  render(<DirectoryPicker onSelect={onSelect} />);
  await screen.findByText("没有权限读取该目录");
  expect(onSelect).toHaveBeenLastCalledWith("");
});
