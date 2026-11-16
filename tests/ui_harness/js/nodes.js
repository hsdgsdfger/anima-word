/** 节点注册：把按钮 / 隐藏控件挂到新插件节点上。 */
import { app } from "../../scripts/app.js";
import { installNodeHooks } from "./studio.js";

app.registerExtension({
  name: "Anima.PromptStudio.Nodes",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    installNodeHooks(nodeType, nodeData);
  },
});
