"""
Central registry for prompt strings keyed by logical name and version.

Week 2+: move bodies to `prompts/versions/*.yaml` or `.md` and load here.
"""

from __future__ import annotations

# Example structure — replace with file-backed content.
PROMPTS: dict[str, dict[str, str]] = {
    "synthesize_v1": {
        "system": "You are Lumen, a careful research assistant. Cite sources using provided ids.",
        "user_template": "Question:\n{question}\n\nPassages:\n{passages}",
    },
}


def get_prompt(name: str, *, version_key: str = "system") -> str:
    if name not in PROMPTS:
        raise KeyError(f"Unknown prompt bundle: {name}")
    return PROMPTS[name][version_key]
