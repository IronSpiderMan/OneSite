import { vi, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
Object.defineProperty(window, "matchMedia", {
  value: vi.fn((query) => ({
    matches: false,
    media: query,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
  })),
});
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
const getStyle = window.getComputedStyle;
window.getComputedStyle = (element) => getStyle(element);
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});
