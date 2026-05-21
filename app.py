import os
import re
import streamlit as st
from services.git_service import get_remote_branches
from services.repository_service import clone_repository, validate_local_repository
from services.scanner_service import build_tree
from services.detector_service import detect_technologies

from services.analyzer_service import (
    count_files_and_folders,
    extract_repository_name,
    detect_build_tool,
    detect_api_style
)

from services.enterprise_prompt_builder import (
    build_enterprise_prompt
)

from services.test_output_parser import (
    parse_generated_test_files
)

from services.insights_renderer import (
    build_structured_summary_prompt,
    render_project_insights,
)

from services.navbar import render_navbar, show_coming_soon_if_needed


from services.ftl_extractor_service import (
    extract_ftl_context
)

from services.traversal_service import (
    traverse_repository,
    extract_endpoint_details
)

from services.java_scanner_service import (
    scan_java_controllers
)

from services.ai.prompt_service import (
    build_testcase_prompt
)

from services.ai.openrouter_service import (
    generate_test_cases
)


st.set_page_config(page_title="RepoSage AI", layout="wide")

if "repo_loaded" not in st.session_state:
    st.session_state["repo_loaded"] = False

render_navbar()
show_coming_soon_if_needed()

if st.session_state.get("repo_loaded"):
    st.caption(
        f"Workspace · {st.session_state.get('repo_name', 'repository')} · "
        "AI-Powered Repository Intelligence"
    )
else:
    st.caption("AI-Powered Repository Intelligence Platform · Load a repository to begin")

st.markdown("---")


def render_markdown_with_code(md_text):
    """Render markdown while extracting fenced code blocks as separate st.code boxes.

    This prevents very long code/JSON blocks from overflowing column width and makes them
    scrollable and nicely formatted.
    """
    if not md_text:
        return

    # Find fenced code blocks (```lang\n...\n```) and split
    parts = re.split(r"(```[\s\S]*?```)", md_text)

    for part in parts:
        if part.startswith("```") and part.endswith("```"):
            # strip backticks
            inner = part.strip().strip("`")
            # first word might be language
            lines = inner.splitlines()
            if len(lines) == 0:
                continue
            lang = lines[0].strip()
            code = "\n".join(lines[1:]) if len(lines) > 1 else ""
            # show code with language if possible
            try:
                if code:
                    st.code(code, language=lang if lang else None)
            except Exception:
                st.code(code)
        else:
            # regular markdown
            if part.strip():
                st.markdown(part)


def render_generated_test_files(generated_files, raw_content=""):
    """Render parsed test files from session state (survives widget reruns)."""
    if not generated_files and not raw_content:
        return

    with st.expander("Generated Test Files", expanded=True):
        if generated_files:
            st.success(
                f"Parsed {len(generated_files)} Java test file(s). "
                "Copy into your project or download below."
            )
            for idx, (path, source) in enumerate(generated_files):
                with st.expander(path, expanded=False):
                    st.code(source, language="java")
                    st.download_button(
                        label=f"Download {os.path.basename(path)}",
                        data=source,
                        file_name=os.path.basename(path),
                        mime="text/x-java-source",
                        key=f"dl_test_{idx}",
                    )
        else:
            st.warning(
                "Could not parse test files from the model response. "
                "Expected `===FILE: src/test/java/...===` blocks. "
                "Show raw output to debug."
            )
            show_raw = st.checkbox(
                "Show raw model output",
                value=True,
                key="show_raw_test_output",
            )
            if show_raw:
                render_markdown_with_code(raw_content)


def show_repository_input():
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.markdown(
            """<style>

            .main {
                background-color: #0E1117;
            }

            .tree-node {
                color: white !important;
            }

            li[role="treeitem"] span {
                color: white !important;
            }

            </style>""",
            unsafe_allow_html=True,
        )

        st.markdown("<div class='card'>", unsafe_allow_html=True)

        st.markdown(
            "<div class='section-title'> Repository Input</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            Provide either:
            - Git repository URL
            - Local repository path
            """
        )

        git_tab, local_tab = st.tabs(["Git Repository", "Local Repository"])

        # GIT TAB
        with git_tab:
            repo_url = st.text_input(
                "Git Repository URL", placeholder="https://github.com/org/repo.git"
            )

            fetch_button = st.button("Fetch Branches", use_container_width=True)

            if fetch_button:
                if not repo_url:
                    st.error("Please provide repository URL")
                else:
                    with st.spinner("Fetching branches..."):
                        try:
                            branches = get_remote_branches(repo_url)
                            st.session_state["repo_source"] = "git"
                            st.session_state["repo_url"] = repo_url
                            st.session_state["branches"] = branches
                            st.success("Branches fetched successfully")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            if "branches" in st.session_state:
                selected_branch = st.selectbox(
                    "Select Branch", st.session_state["branches"]
                )
                st.session_state["selected_branch"] = selected_branch

                load_repo_button = st.button("Load Repository", use_container_width=True)
                if load_repo_button:
                    with st.spinner("Cloning repository..."):
                        try:
                            repo_path = clone_repository(
                                st.session_state["repo_url"], selected_branch
                            )
                            st.session_state["repo_path"] = repo_path
                            folder_tree = build_tree(repo_path)
                            st.session_state["folder_tree"] = folder_tree
                            technologies = detect_technologies(repo_path)
                            st.session_state["technologies"] = technologies
                            repo_stats = count_files_and_folders(
                            repo_path
                            )
                            st.session_state["repo_stats"] = repo_stats
                            repo_name = extract_repository_name(
                                repo_path
                            )
                            st.session_state["repo_name"] = repo_name
                            build_tool = detect_build_tool(
                                repo_path
                            )
                            st.session_state["build_tool"] = build_tool
                            api_style = detect_api_style(
                                repo_path
                            )
                            st.session_state["api_style"] = api_style
                            st.session_state["repo_loaded"] = True
                            st.success("Repository loaded successfully")
                        except Exception as e:
                            st.error(str(e))

        # LOCAL TAB
        with local_tab:
            local_path = st.text_input(
                "Local Repository Path", placeholder="C:/Projects/payment-service"
            )

            local_button = st.button("Use Local Repository", use_container_width=True)
            if local_button:
                if not local_path:
                    st.error("Please provide local path")
                else:
                    try:
                        repo_path = validate_local_repository(local_path)
                        st.session_state["repo_source"] = "local"
                        st.session_state["local_path"] = local_path
                        st.session_state["repo_path"] = repo_path
                        folder_tree = build_tree(repo_path)
                        st.session_state["folder_tree"] = folder_tree
                        technologies = detect_technologies(repo_path)
                        st.session_state["technologies"] = technologies
                        repo_stats = count_files_and_folders(
                            repo_path
                        )

                        st.session_state["repo_stats"] = repo_stats
                        repo_name = extract_repository_name(
                            repo_path
                        )
                        st.session_state["repo_name"] = repo_name
                        build_tool = detect_build_tool(
                            repo_path
                        )

                        st.session_state["build_tool"] = build_tool
                        api_style = detect_api_style(
                            repo_path
                        )

                        st.session_state["api_style"] = api_style
                        st.session_state["repo_loaded"] = True
                        st.success("Local repository loaded successfully")
                        st.code(local_path)
                    except Exception as e:
                        st.error(str(e))

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(
            "<div class='section-title'>About RepoSage AI</div>", unsafe_allow_html=True
        )

        st.markdown(
            """
            RepoSage AI is an AI-powered repository intelligence platform
            designed to accelerate SDLC understanding and engineering productivity.

            The platform analyzes repositories and automatically generates
            engineering artifacts such as:

            ### AI Generated Outputs
            - Functional Test Cases
            - Edge Cases
            - Risk Analysis
            - Architecture Summary
            - README Documentation
            - API Discovery

            ### Core Capabilities
            - Repository Analysis
            - Branch-Aware Processing
            - Technology Detection
            - Framework Identification
            - AI-Powered SDLC Acceleration

            ### Supported Inputs
            - Git Repositories
            - Local Repository Paths

            ### Target Users
            - QA Engineers
            - Developers
            - DevOps Teams
            - Architects
            - Engineering Leads
            """,
        )

        st.markdown("---")
        st.markdown("### Workflow")
        st.code(
            """
        Input Repository
                ↓
        Repository Scan
                ↓
        Technology Detection
                ↓
        AI Analysis
                ↓
        Artifact Generation
            """
        )


def show_workspace():
    # Give more room to the AI workspace and the insights column
    col1, col2, col3 = st.columns([1, 1.85, 1.35])

    with col1:
        st.subheader(" Repository Explorer")

        def render_tree(nodes, level=0):
            for node in nodes:
                label = node.get("label", "")
                children = node.get("children", [])

                if children:
                    with st.expander(label, expanded=False):
                        render_tree(children, level + 1)
                else:
                    st.markdown(
                        f"{'&nbsp;' * (level * 4)} {label.replace('📄 ', '')}",
                        unsafe_allow_html=True,
                    )

        render_tree(st.session_state.get("folder_tree", []))

    # ==========================================
    # COLUMN 2 — AI WORKSPACE
    # ==========================================

    with col2:

        st.subheader(" AI Workspace")

        st.info(
            "AI-generated executable Java test files will appear here."
        )

        if st.button(
            "Generate Test Cases",
            use_container_width=True
        ):

            with st.spinner(
                "Analyzing Spring Boot APIs..."
            ):

                try:

                    repo_path = st.session_state[
                        "repo_path"
                    ]

                    # ======================================
                    # TRAVERSAL CONTEXT
                    # ======================================

                    traversal_context = traverse_repository(
                        repo_path
                    )

                    # ======================================
                    # End Point Details
                    # ======================================

                    endpointDetails = extract_endpoint_details(
                        repo_path
                    )

                    # ======================================
                    # FTL CONTEXT
                    # ======================================

                    ftl_context = extract_ftl_context(
                        repo_path
                    )

                    # ======================================
                    # TECHNOLOGIES
                    # ======================================

                    technologies = st.session_state.get(
                        "technologies",
                        {}
                    )

                    # ======================================
                    # BUILD ENTERPRISE PROMPT
                    # ======================================

                    prompt = build_enterprise_prompt(
                        traversal_context,
                        ftl_context,
                        technologies,
                        endpointDetails,
                        repo_name=st.session_state.get("repo_name"),
                        build_tool=st.session_state.get("build_tool"),
                    )

                    # OPTIONAL DEBUG
                    # st.code(prompt)

                    # ======================================
                    # GENERATE TEST CASES
                    # ======================================

                    # Single LLM call that returns markdown for the detected endpoints
                    result = generate_test_cases(prompt)

                    try:
                        summary_prompt_str = build_structured_summary_prompt(
                            repo_name=st.session_state.get("repo_name"),
                            technologies=technologies,
                            api_style=st.session_state.get("api_style"),
                            build_tool=st.session_state.get("build_tool"),
                            endpoint_details=endpointDetails,
                            traversal_context=traversal_context,
                            ftl_context=ftl_context,
                            repo_path=repo_path,
                            repo_stats=st.session_state.get("repo_stats"),
                        )
                        project_summary = generate_test_cases(summary_prompt_str)
                        st.session_state["project_summary"] = project_summary
                    except Exception as e:
                        st.session_state["project_summary"] = f"Project summary generation failed: {e}"

                    content = result or ""
                    generated_files = parse_generated_test_files(content)
                    st.session_state["generated_test_files"] = generated_files
                    st.session_state["generated_test_raw"] = content

                except Exception as e:

                    st.error(str(e))

        render_generated_test_files(
            st.session_state.get("generated_test_files"),
            st.session_state.get("generated_test_raw", ""),
        )
    with col3:
        st.subheader(" Repository Insights")

        project_summary = st.session_state.get("project_summary")
        if project_summary:
            render_project_insights(
                project_summary,
                repo_name=st.session_state.get("repo_name"),
            )

        st.markdown("---")
        st.markdown("##### Detected Technologies")

        technologies = st.session_state.get("technologies", {})
        for category, techs in technologies.items():
            with st.expander(category.title(), expanded=False):
                if techs:
                    for tech in techs:
                        st.success(tech)
                else:
                    st.caption("Not detected")


if not st.session_state["repo_loaded"]:
    show_repository_input()
else:
    show_workspace()
