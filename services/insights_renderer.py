import html
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


INSIGHTS_COLUMN_CSS = """
<style>
/* Keep Repository Insights column content inside bounds */
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) .stMarkdown,
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) .stExpander {
    max-width: 100%;
}
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) .stMarkdown p,
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) .stMarkdown li,
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) .stMarkdown blockquote,
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) .insights-text {
    word-wrap: break-word;
    overflow-wrap: anywhere;
    white-space: normal;
    max-width: 100%;
    font-size: 0.92rem;
    line-height: 1.45;
}
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) .stMarkdown code {
    white-space: pre-wrap;
    word-break: break-word;
}
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(3) .stMarkdown table {
    display: block;
    overflow-x: auto;
    max-width: 100%;
    font-size: 0.85rem;
}
.insights-priority-label {
    font-weight: 600;
    color: #fafafa;
}
.insights-muted {
    color: #9ca3af;
    font-size: 0.85rem;
    margin-bottom: 0.25rem;
}
</style>
"""


def split_overview_and_priorities(text: str) -> Tuple[str, str]:
    if not text:
        return "", ""

    match = re.search(
        r"(?:^|\n)\s{0,3}#{1,3}\s+.*(?:top\s*5|testing\s+priorit)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return text[: match.start()].strip(), text[match.start() :].strip()
    return text.strip(), ""


def parse_priority_sections(priorities_text: str) -> List[dict]:
    """Parse ### Priority N: Title blocks."""
    rows = []
    if not priorities_text:
        return rows

    pattern = re.compile(
        r"^\s{0,3}#{1,3}\s+"
        r"(?:priority\s*)?(\d+)\s*[:\-\.]?\s*(.+?)\s*$"
        r"\n([\s\S]*?)(?=^\s{0,3}#{1,3}\s+|\Z)",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    for num, title, body in pattern.findall(priorities_text):
        rows.append(
            {
                "num": num.strip(),
                "focus": title.strip(),
                "risk": body.strip(),
            }
        )
    return rows


def parse_priority_table(priorities_text: str) -> List[dict]:
    """Parse markdown table rows: | # | Focus | Why |."""
    rows = []
    if not priorities_text:
        return rows

    header_seen = False
    for line in priorities_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|[\s\-:|]+\|$", line):
            continue

        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue

        first = cells[0].lower().strip("#").strip()
        if first in ("#", "no", "num", "number") or "focus" in first:
            header_seen = True
            continue

        if not header_seen and not re.match(r"^\d+$", cells[0]):
            continue

        num = cells[0]
        focus = cells[1] if len(cells) > 1 else "Priority"
        risk = cells[2] if len(cells) > 2 else ""
        if len(cells) > 3:
            risk = " | ".join(cells[2:])

        rows.append({"num": num, "focus": focus, "risk": risk})

    return rows


def parse_testing_priorities(text: str) -> List[dict]:
    _, priorities_block = split_overview_and_priorities(text)
    source = priorities_block or text

    rows = parse_priority_sections(source)
    if rows:
        return rows[:5]

    rows = parse_priority_table(source)
    if rows:
        return rows[:5]

    return []


def parse_overview_bullets(overview_text: str) -> List[str]:
    bullets = []
    for line in overview_text.splitlines():
        m = re.match(r"^\s*[-*•]\s+(.+)", line)
        if m:
            bullets.append(m.group(1).strip())
    return bullets


def _read_artifact_id(repo_path: Optional[str]) -> Optional[str]:
    if not repo_path:
        return None
    pom = os.path.join(repo_path, "pom.xml")
    if not os.path.isfile(pom):
        return None
    try:
        with open(pom, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(8000)
        m = re.search(r"<artifactId>([^<]+)</artifactId>", content)
        return m.group(1).strip() if m else None
    except OSError:
        return None


def _extract_controller_snippet(file_path: str, max_chars: int = 1200) -> Optional[str]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return None

    if "@RestController" not in content and "@Controller" not in content:
        return None

    pkg = ""
    m_pkg = re.search(r"package\s+([\w.]+)\s*;", content)
    if m_pkg:
        pkg = m_pkg.group(1)

    cls = ""
    m_cls = re.search(r"public\s+class\s+(\w+)", content)
    if m_cls:
        cls = m_cls.group(1)

    base = ""
    m_base = re.search(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?"([^"]+)"', content)
    if m_base:
        base = m_base.group(1)

    mappings = re.findall(
        r"@(?:(Get|Post|Put|Delete|Patch)Mapping)\s*\(\s*\"([^\"]+)\"",
        content,
        flags=re.IGNORECASE,
    )
    mapping_lines = [
        f"  - {verb.upper()} {path}" for verb, path in mappings[:12]
    ]

    imports = re.findall(r"^import\s+([\w.]+);", content, re.MULTILINE)
    notable = [
        i
        for i in imports
        if not i.startswith("java.") and not i.startswith("javax.")
    ][:8]

    methods = re.findall(
        r"public\s+[\w<>,\s\[\]]+\s+(\w+)\s*\([^)]*\)",
        content,
    )
    methods = [m for m in methods if m not in ("equals", "hashCode", "toString")][:6]

    lines = [f"Controller: {pkg}.{cls}" if pkg and cls else f"Controller: {cls or os.path.basename(file_path)}"]
    if base:
        lines.append(f"Base path: {base}")
    if mapping_lines:
        lines.append("Mappings:")
        lines.extend(mapping_lines)
    if methods:
        lines.append("Public methods: " + ", ".join(methods))
    if notable:
        lines.append("Key imports: " + ", ".join(notable))

    snippet = "\n".join(lines)
    return snippet[:max_chars]


def collect_repo_evidence(
    repo_path: Optional[str],
    traversal_context: Optional[Dict[str, Any]],
    ftl_context: Optional[Dict[str, Any]],
    endpoint_details: Optional[List[dict]],
    technologies: Optional[dict],
) -> Dict[str, Any]:
    """Gather concrete facts from the scanned repo for a grounded LLM summary."""
    traversal_context = traversal_context or {}
    ftl_context = ftl_context or {}

    evidence: Dict[str, Any] = {
        "controller_snippets": [],
        "endpoints": endpoint_details or [],
        "workflow_objects": list(traversal_context.get("workflow_objects", []))[:20],
        "utility_classes": list(traversal_context.get("utility_classes", []))[:25],
        "top_method_calls": [],
        "enterprise_imports": [],
        "ftl_files": list(ftl_context.get("ftl_files", []))[:15],
        "graphql_operations": list(ftl_context.get("graphql_operations", []))[:15],
        "ftl_variables": list(ftl_context.get("variables", []))[:20],
        "ftl_conditions": list(ftl_context.get("conditions", []))[:10],
    }

    calls = traversal_context.get("method_calls", [])
    if calls:
        evidence["top_method_calls"] = [
            name for name, _ in Counter(calls).most_common(15)
        ]

    imports = traversal_context.get("imports", [])
    enterprise = [
        i
        for i in imports
        if any(
            k in i
            for k in (
                "enterprise",
                "workflow",
                "graphql",
                "gql",
                "hasura",
                "util",
                "action",
                "command",
            )
        )
    ]
    evidence["enterprise_imports"] = list(dict.fromkeys(enterprise))[:20]

    if repo_path and os.path.isdir(repo_path):
        controller_names = set(traversal_context.get("controllers", []))
        snippets = []
        for root, _, files in os.walk(repo_path):
            if len(snippets) >= 3:
                break
            for fname in files:
                if not fname.endswith(".java"):
                    continue
                if controller_names and fname not in controller_names:
                    continue
                path = os.path.join(root, fname)
                snippet = _extract_controller_snippet(path)
                if snippet:
                    snippets.append(snippet)
                if len(snippets) >= 3:
                    break
        evidence["controller_snippets"] = snippets

    return evidence


def _format_evidence_block(evidence: Dict[str, Any], technologies: dict) -> str:
    lines = []

    endpoints = evidence.get("endpoints", [])
    if endpoints:
        lines.append("DETECTED HTTP ENDPOINTS (use these exact paths in priorities):")
        for e in endpoints[:25]:
            lines.append(f"  - {e.get('method', '').upper()} {e.get('path', '')}")
    else:
        lines.append("DETECTED HTTP ENDPOINTS: none — base priorities on controllers/workflows below.")

    snippets = evidence.get("controller_snippets", [])
    if snippets:
        lines.append("")
        lines.append("CONTROLLER EVIDENCE (from source scan):")
        for i, snip in enumerate(snippets, 1):
            lines.append(f"--- Controller {i} ---")
            lines.append(snip)

    if evidence.get("workflow_objects"):
        lines.append("")
        lines.append("WORKFLOW / DOMAIN OBJECTS: " + ", ".join(evidence["workflow_objects"]))

    if evidence.get("utility_classes"):
        lines.append("INSTANTIATED COLLABORATORS (new X(...)): " + ", ".join(evidence["utility_classes"]))

    if evidence.get("top_method_calls"):
        lines.append("FREQUENT METHOD CALLS: " + ", ".join(evidence["top_method_calls"]))

    if evidence.get("enterprise_imports"):
        lines.append("ENTERPRISE / INTEGRATION IMPORTS: " + ", ".join(evidence["enterprise_imports"]))

    if evidence.get("ftl_files"):
        lines.append("")
        lines.append("FTL TEMPLATES: " + ", ".join(evidence["ftl_files"]))

    if evidence.get("graphql_operations"):
        lines.append("GRAPHQL OPERATIONS: " + ", ".join(evidence["graphql_operations"]))

    ftl_vars = evidence.get("ftl_variables", [])
    if ftl_vars:
        lines.append("FTL VARIABLES (payload fields): " + ", ".join(ftl_vars[:15]))

    if technologies:
        lines.append("")
        lines.append("DETECTED TECH STACK: " + str(technologies))

    return "\n".join(lines)


def build_structured_summary_prompt(
    repo_name,
    technologies,
    api_style,
    build_tool,
    endpoint_details,
    traversal_context=None,
    ftl_context=None,
    repo_path=None,
    repo_stats=None,
    controllers=None,
    ftl_vars=None,
):
    """
    Build a repo-grounded summary prompt. Pass traversal_context + ftl_context
    (preferred) or legacy controllers/ftl_vars lists.
    """
    traversal_context = traversal_context or {}
    if controllers and not traversal_context.get("controllers"):
        traversal_context = {**traversal_context, "controllers": controllers}

    ftl_context = ftl_context or {}
    if ftl_vars and not ftl_context.get("variables"):
        ftl_context = {**ftl_context, "variables": ftl_vars}

    evidence = collect_repo_evidence(
        repo_path,
        traversal_context,
        ftl_context,
        endpoint_details,
        technologies,
    )
    evidence_text = _format_evidence_block(evidence, technologies or {})
    artifact_id = _read_artifact_id(repo_path)
    project_label = artifact_id or repo_name or "unknown"

    stats_line = ""
    if repo_stats:
        stats_line = (
            f"Repository size: {repo_stats.get('total_files', '?')} files, "
            f"{repo_stats.get('total_folders', '?')} folders."
        )

    endpoint_count = len(endpoint_details or [])

    return "\n".join(
        [
            "You are a principal engineer who has just reviewed THIS specific repository scan.",
            "Write a project summary and testing priorities that could ONLY apply to this codebase.",
            "",
            "STRICT GROUNDING RULES:",
            "1. Every Project Summary bullet MUST name at least one concrete artifact from REPOSITORY EVIDENCE",
            "   (controller class, endpoint path, workflow object, FTL variable, GraphQL operation, or utility class).",
            "2. Each of the 5 testing priorities MUST tie to a specific detected endpoint, controller method,",
            "   FTL/GraphQL flow, or collaborator listed in the evidence — include the exact path or class name.",
            "3. Do NOT invent endpoints, microservices, databases, or features not present in the evidence.",
            "4. Do NOT use generic phrases like 'ensure security', 'validate CRUD', 'test all APIs',",
            "   'banking best practices', or 'standard Spring Boot' unless you link them to a named artifact here.",
            "5. If orchestration/workflow/FTL patterns appear in evidence, describe THAT flow — not a textbook architecture.",
            f"6. Prioritize the {endpoint_count} detected endpoint(s) and controller evidence first.",
            "",
            "PROJECT IDENTITY:",
            f"- Repository folder: {repo_name or 'unknown'}",
            f"- Maven artifact (if any): {artifact_id or 'not found'}",
            f"- Label for summary title: {project_label}",
            f"- API style (heuristic): {api_style or 'Unknown'}",
            f"- Build tool: {build_tool or 'Unknown'}",
            stats_line,
            "",
            "REPOSITORY EVIDENCE (single source of truth — do not go beyond this):",
            evidence_text,
            "",
            "OUTPUT FORMAT (follow exactly; no markdown tables; no intro paragraph):",
            "",
            f"## Project Summary ({project_label})",
            "- Bullet 1: <specific architecture/flow fact citing class or endpoint>",
            "- Bullet 2: ...",
            "- (4-6 bullets total, each grounded in evidence)",
            "",
            "## Top 5 Testing Priorities",
            "### Priority 1: <short title referencing endpoint or class>",
            "2-4 sentences: what breaks, which class/path/FTL field is involved, and exact test focus.",
            "### Priority 2: ...",
            "### Priority 3: ...",
            "### Priority 4: ...",
            "### Priority 5: ...",
            "",
            "Before writing, mentally map each priority to a different item from the evidence (no duplicates).",
        ]
    ).strip()


def render_project_insights(
    summary_text: str,
    repo_name: Optional[str] = None,
) -> None:
    import streamlit as st

    if not summary_text or not summary_text.strip():
        return

    st.markdown(INSIGHTS_COLUMN_CSS, unsafe_allow_html=True)

    overview, priorities_block = split_overview_and_priorities(summary_text)
    priorities = parse_testing_priorities(summary_text)
    bullets = parse_overview_bullets(overview)

    summary_title = (
        f"Project Summary ({repo_name})" if repo_name else "Project Summary"
    )

    with st.expander(summary_title, expanded=False):
        if bullets:
            items = "".join(
                f"<li>{html.escape(b)}</li>" for b in bullets
            )
            st.markdown(
                f'<ul class="insights-text">{items}</ul>',
                unsafe_allow_html=True,
            )
        else:
            clean = re.sub(
                r"^\s{0,3}#{1,6}\s+.*project\s+summary.*\s*$",
                "",
                overview,
                flags=re.IGNORECASE | re.MULTILINE,
            ).strip()
            if clean:
                st.markdown(clean)
            else:
                st.caption("No summary bullets parsed.")

    if priorities:
        st.markdown("##### Top 5 Testing Priorities")
        for row in priorities:
            num = row.get("num", "")
            focus = row.get("focus", "Priority")
            label = f"#{num} {focus}" if num else focus
            with st.expander(label, expanded=False):
                risk = (row.get("risk") or "").strip()
                if risk:
                    st.markdown(
                        f'<p class="insights-text">{html.escape(risk)}</p>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("No details for this priority.")
    elif priorities_block:
        with st.expander("Testing priorities (raw)", expanded=False):
            st.markdown(
                f'<div class="insights-text">{priorities_block}</div>',
                unsafe_allow_html=True,
            )
