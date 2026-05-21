import re
from typing import List, Tuple


def parse_generated_test_files(content: str) -> List[Tuple[str, str]]:
    """
    Parse LLM output into (relative_path, java_source) pairs.
    Supports ===FILE: path=== and legacy FILE PATH: blocks.
    """
    if not content or not content.strip():
        return []

    files: List[Tuple[str, str]] = []

    # Primary: ===FILE: src/test/java/.../FooTest.java===
    file_block = re.findall(
        r"===FILE:\s*(.+?)\s*===\s*```(?:java)?\s*([\s\S]*?)```",
        content,
        flags=re.IGNORECASE,
    )
    for path, source in file_block:
        path = path.strip()
        source = source.strip()
        if path.endswith(".java") and source:
            files.append((path, source))

    if files:
        return files

    # Legacy: FILE PATH: ... FILE CONTENT: ```java ... ```
    legacy = re.findall(
        r"FILE\s*PATH:\s*(.+?)\s*FILE\s*CONTENT:\s*```(?:java)?\s*([\s\S]*?)```",
        content,
        flags=re.IGNORECASE,
    )
    for path, source in legacy:
        path = path.strip()
        source = source.strip()
        if path.endswith(".java") and source:
            files.append((path, source))

    if files:
        return files

    # Fallback: any fenced java block with a path on the preceding line
    for match in re.finditer(
        r"(?:^|\n)\s*(?:FILE\s*PATH:?\s*|Path:?\s*)?(`?)(src/test/java/[^\s`]+\.java)\1?\s*\n```java\s*([\s\S]*?)```",
        content,
        flags=re.IGNORECASE,
    ):
        files.append((match.group(2).strip(), match.group(3).strip()))

    return files
