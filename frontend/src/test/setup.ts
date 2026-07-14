import "@testing-library/jest-dom/vitest";

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
});

Element.prototype.hasPointerCapture ??= (() => false) as typeof Element.prototype.hasPointerCapture;
Element.prototype.setPointerCapture ??= (() =>
  undefined) as typeof Element.prototype.setPointerCapture;
Element.prototype.releasePointerCapture ??= (() =>
  undefined) as typeof Element.prototype.releasePointerCapture;
Element.prototype.scrollIntoView ??= (() => undefined) as typeof Element.prototype.scrollIntoView;
