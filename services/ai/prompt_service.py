def build_testcase_prompt(api_summary):
    """Legacy helper — prefer build_enterprise_prompt + prompt.txt."""

    endpoints_text = "\n".join(api_summary)

    return f"""
Generate executable JUnit 5 Java test files for these APIs only:
{endpoints_text}

Output format (no markdown reports):
===FILE: src/test/java/<package>/ClassNameTest.java===
```java
<complete file>
```
"""