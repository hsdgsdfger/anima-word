export const app = {
  graph: {
    setDirtyCanvas() {},
    _nodes: [],
  },
  registerExtension(ext) {
    window.__extensions = window.__extensions || [];
    window.__extensions.push(ext);
  },
};
