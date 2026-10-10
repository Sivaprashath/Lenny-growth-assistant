"""
Artifact Generation Skill — produces renderable Markdown or HTML/CSS artifacts.
Security: HTML artifacts are sandboxed (no scripts, no external resources).
"""

ARTIFACT_SYSTEM_PROMPT = """You are an expert content architect who generates clean, \
well-structured Markdown documents and self-contained HTML/CSS artifacts.

## Markdown Artifacts:
- Use proper heading hierarchy (H1 → H2 → H3)
- Include a table of contents for documents > 500 words
- Use tables, code blocks, and callouts where appropriate
- Every claim must reference the source transcripts

## HTML Artifacts (STRICT SECURITY RULES):
- Generate COMPLETE, self-contained HTML (includes <html>, <head>, <body>)
- Include all CSS inline in a <style> tag — NO external stylesheets
- Use modern, beautiful CSS: gradients, cards, responsive grid
- Color palette: professional blues, grays, accent colors
- NO <script> tags — pure HTML/CSS only (security requirement)
- NO external URLs in src/href attributes (images, fonts, etc.)
- NO form actions pointing to external URLs
- NO iframes
- Use Google Fonts via @import if fonts are needed (safe: read-only)
- The artifact must look beautiful and polished when rendered

## Content Rules:
- All data and claims MUST come from the provided transcript context
- Do not fabricate statistics, quotes, or examples
- Structure the artifact around the user's specific request
- Return ONLY the artifact content — no explanation, no preamble"""


def build_artifact_prompt(
    user_request: str,
    context: str,
    recent_conversation: str,
    artifact_type: str
) -> str:
    type_instruction = {
        "markdown": (
            "Generate a complete, beautifully structured MARKDOWN document. "
            "Use rich markdown: headers, tables, code blocks, bold, callouts (> Note:). "
            "Start with a # H1 title."
        ),
        "html": (
            "Generate a complete, self-contained HTML page with embedded CSS. "
            "Make it visually stunning — use modern design with gradients, cards, and clean typography. "
            "SECURITY: No <script> tags, no external resource URLs (except Google Fonts @import). "
            "Start with <!DOCTYPE html>."
        ),
    }[artifact_type]

    return f"""USER REQUEST: {user_request}

ARTIFACT TYPE: {artifact_type.upper()}
INSTRUCTION: {type_instruction}

RECENT CONVERSATION CONTEXT:
{recent_conversation if recent_conversation else "(No prior conversation)"}

TRANSCRIPT KNOWLEDGE BASE (ground all content here):
{context if context else "(No specific context retrieved — use general product/growth principles from transcripts)"}

Generate the {artifact_type} artifact now. Return ONLY the artifact content."""
