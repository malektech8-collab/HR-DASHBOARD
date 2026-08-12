import '@testing-library/jest-dom';

/**
 * jsdom has no ResizeObserver, and recharts' ResponsiveContainer requires one.
 * Without this, rendering ANY page that draws a chart throws — which is most of
 * them, and which is a large part of why no page had a test.
 *
 * A stub rather than a polyfill: the tests here assert what is rendered, not
 * how it is laid out, and a real implementation would only add flakiness.
 */
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver ?? (ResizeObserverStub as never);
