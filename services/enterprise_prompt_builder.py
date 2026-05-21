import os


def _load_base_prompt() -> str:
    root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    prompt_path = os.path.join(root, "prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_enterprise_prompt(
    traversal_context,
    ftl_context,
    technologies,
    endpoint_details,
    repo_name=None,
    build_tool=None,
):
    formatted_endpoints = "\n".join(
        f"- {e['method']} {e['path']}" for e in endpoint_details
    ) or "- (none detected — derive tests from controllers only)"

    controllers = traversal_context.get("controllers", [])[:30]
    utility_classes = traversal_context.get("utility_classes", [])[:40]
    workflow_objects = traversal_context.get("workflow_objects", [])[:30]
    imports_sample = traversal_context.get("imports", [])[:50]
    method_calls_sample = traversal_context.get("method_calls", [])[:50]

    graphql_ops = ftl_context.get("graphql_operations", [])[:20]
    ftl_variables = ftl_context.get("variables", [])[:15]

    base = _load_base_prompt()

    context = f"""
================================================================================
REPOSITORY CONTEXT
================================================================================

Repository: {repo_name or "unknown"}
Build tool: {build_tool or "unknown"}

Tech stack (detected):
{technologies}

Detected endpoints (generate tests ONLY for these unless controller code implies additional mapped paths):
{formatted_endpoints}

Controller / handler files:
{controllers}

Sample imports (use to infer dependencies and enterprise utilities):
{imports_sample}

Instantiated utility / collaborator classes (from `new ClassName(`):
{utility_classes}

Sample method calls (`.methodName(`):
{method_calls_sample}

Workflow-related identifiers:
{workflow_objects}

GraphQL operations (from FTL):
{graphql_ops}

FTL variables (sample):
{ftl_variables}

================================================================================
END OF CONTEXT — produce 5–6 ===FILE: blocks now. No other output.
================================================================================
"""

    return f"{base}\n\n{context}"
