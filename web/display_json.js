import { app } from "../../scripts/app.js"
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "nic_schi.display_json",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "DisplayJSONNode") return;

        const WIDGET_NAME = "json_output";

        const makeReadOnly = (widget) => {
            if (widget.inputEl) {
                widget.inputEl.readOnly = true;
                widget.inputEl.style.opacity = 0.7;
                widget.inputEl.style.height = "200px";
                widget.inputEl.style.overflowY = "scroll";
                widget.inputEl.style.wordBreak = "break-all";
            } else {
                setTimeout(() => makeReadOnly(widget), 10);
            }
        };

        function updateDisplayWidget(text) {
            let widget = this.widgets?.find((w) => w.name === WIDGET_NAME);

            if (!widget) {
                // Sicherstellen, dass multiline wirklich aktiv ist
                widget = ComfyWidgets["STRING"](
                    this,
                    WIDGET_NAME,
                    ["STRING", { multiline: true }],
                    app
                ).widget;
                makeReadOnly(widget);
            }

            const finalString = Array.isArray(text) ? text[0] : text;
            widget.value = finalString;

            this.size[1] = Math.max(this.size[1], 250);
            this.setDirtyCanvas?.(true);
        }

        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            onExecuted?.apply(this, arguments);
            if (message?.text !== undefined) {
                const text = Array.isArray(message.text) ? message.text[0] : message.text;
                updateDisplayWidget.call(this, text);
            }
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (config) {
            onConfigure?.apply(this, arguments);
            if (config?.widgets_values?.length > 1) {
                const savedText = config.widgets_values.find((_, i) => this.widgets?.[i]?.name === WIDGET_NAME)
                                 || config.widgets_values[1];
                updateDisplayWidget.call(this, savedText);
            }
        };
    },
});
