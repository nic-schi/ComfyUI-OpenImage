def get_node_name(extra_pnginfo, unique_id, display_name):
    node_name = "Unknown Node"

    if extra_pnginfo is not None:
        workflow = extra_pnginfo.get("workflow")

        if workflow is not None:
            for node in workflow.get("nodes", []):
                if str(node.get("id")) == str(unique_id):
                    node_name = node.get("title") or node.get("name") or display_name or node.get("type")
                    break

    return node_name
