#!/usr/bin/env python3
"""
Push markdown under lumen/docs/ to Notion as child pages of NOTION_WIKI_PARENT_PAGE_ID.

Requires NOTION_API_KEY and NOTION_WIKI_PARENT_PAGE_ID (integration must be invited to the parent page).

Page identity is stored in docs/notion-page-map.json (relative path -> Notion page UUID).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

NOTION_API = "https://api.notion.com/v1"
DEFAULT_VERSION = "2022-06-28"
MAX_RICH_TEXT = 2000
APPEND_BATCH = 100
SLEEP_BETWEEN_DELETES = 0.05


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _lumen_root() -> Path:
    return _script_dir().parent


def _docs_dir() -> Path:
    return _lumen_root() / "docs"


def _map_path() -> Path:
    return _docs_dir() / "notion-page-map.json"


def _headers() -> dict[str, str]:
    token = os.environ.get("NOTION_API_KEY", "").strip()
    if not token:
        print("Missing NOTION_API_KEY", file=sys.stderr)
        sys.exit(1)
    version = os.environ.get("NOTION_API_VERSION", DEFAULT_VERSION).strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": version,
    }


def _parent_page_id() -> str:
    raw = os.environ.get("NOTION_WIKI_PARENT_PAGE_ID", "").strip()
    if not raw:
        print("Missing NOTION_WIKI_PARENT_PAGE_ID", file=sys.stderr)
        sys.exit(1)
    return raw.replace("-", "")


def _uuid_with_dashes(page_id: str) -> str:
    p = page_id.replace("-", "")
    if len(p) != 32:
        return page_id
    return f"{p[0:8]}-{p[8:12]}-{p[12:16]}-{p[16:20]}-{p[20:32]}"


def _split_rich_text(text: str) -> list[str]:
    if len(text) <= MAX_RICH_TEXT:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + MAX_RICH_TEXT])
        start += MAX_RICH_TEXT
    return chunks


def _rich_text(content: str) -> list[dict[str, Any]]:
    return [
        {"type": "text", "text": {"content": chunk, "link": None}}
        for chunk in _split_rich_text(content)
    ]


def _paragraph_block(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rich_text(text)},
    }


def _heading_block(level: int, text: str) -> dict[str, Any]:
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": _rich_text(text)}}


def _bullet_block(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": _rich_text(text)},
    }


def _code_block(code: str, language: str) -> dict[str, Any]:
    lang = (language or "plain text").strip() or "plain text"
    # Notion allows a subset of language strings; unknown values still work for display.
    return {
        "object": "block",
        "type": "code",
        "code": {
            "caption": [],
            "rich_text": _rich_text(code),
            "language": lang,
        },
    }


def _divider_block() -> dict[str, Any]:
    return {"object": "block", "type": "divider", "divider": {}}


def md_to_blocks(md: str) -> list[dict[str, Any]]:
    """Convert markdown to Notion block payloads (best-effort, no inline HTML)."""
    lines = md.splitlines()
    blocks: list[dict[str, Any]] = []
    para: list[str] = []
    in_code = False
    code_lines: list[str] = []
    code_lang = "plain text"

    def flush_para() -> None:
        nonlocal para
        if not para:
            return
        text = "\n".join(para).strip()
        para = []
        if not text:
            return
        blocks.append(_paragraph_block(text))

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            flush_para()
            if in_code:
                blocks.append(_code_block("\n".join(code_lines), code_lang))
                code_lines = []
                code_lang = "plain text"
                in_code = False
            else:
                in_code = True
                rest = line.strip()[3:].strip()
                code_lang = rest if rest else "plain text"
                code_lines = []
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        stripped = line.strip()
        if stripped in ("---", "***", "___"):
            flush_para()
            blocks.append(_divider_block())
            i += 1
            continue

        if not stripped:
            flush_para()
            i += 1
            continue

        m = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if m:
            flush_para()
            level = len(m.group(1))
            blocks.append(_heading_block(level, m.group(2).strip()))
            i += 1
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            flush_para()
            blocks.append(_bullet_block(stripped[2:].strip()))
            i += 1
            continue

        para.append(line)
        i += 1

    flush_para()
    if in_code and code_lines:
        blocks.append(_code_block("\n".join(code_lines), code_lang))

    if not blocks:
        blocks.append(_paragraph_block("(empty document)"))
    return blocks


def extract_title(md: str, fallback: str) -> str:
    for line in md.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return fallback


def load_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object (path -> page id)")
    out: dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v.replace("-", "")
    return out


def save_map(path: Path, mapping: dict[str, str]) -> None:
    pretty: dict[str, str] = {k: _uuid_with_dashes(v) for k, v in sorted(mapping.items())}
    path.write_text(json.dumps(pretty, indent=2) + "\n", encoding="utf-8")


def list_markdown_files(docs: Path) -> list[Path]:
    return sorted(p for p in docs.glob("*.md") if p.is_file())


def notion_get(client: httpx.Client, path: str) -> dict[str, Any]:
    r = client.get(f"{NOTION_API}{path}")
    r.raise_for_status()
    return r.json()


def notion_post(client: httpx.Client, path: str, body: dict[str, Any]) -> dict[str, Any]:
    r = client.post(f"{NOTION_API}{path}", json=body)
    if r.status_code >= 400:
        print(r.text, file=sys.stderr)
    r.raise_for_status()
    return r.json()


def notion_patch(client: httpx.Client, path: str, body: dict[str, Any]) -> dict[str, Any]:
    r = client.patch(f"{NOTION_API}{path}", json=body)
    if r.status_code >= 400:
        print(r.text, file=sys.stderr)
    r.raise_for_status()
    return r.json()


def notion_delete_block(client: httpx.Client, block_id: str) -> None:
    r = client.delete(f"{NOTION_API}/blocks/{block_id}")
    if r.status_code >= 400:
        print(r.text, file=sys.stderr)
    r.raise_for_status()


def fetch_all_child_block_ids(client: httpx.Client, page_id: str) -> list[str]:
    ids: list[str] = []
    cursor: str | None = None
    while True:
        q = "?page_size=100"
        if cursor:
            q += f"&start_cursor={cursor}"
        data = notion_get(client, f"/blocks/{page_id}/children{q}")
        for b in data.get("results", []):
            bid = b.get("id")
            if isinstance(bid, str):
                ids.append(bid.replace("-", ""))
        if data.get("has_more"):
            cursor = data.get("next_cursor")
            if not isinstance(cursor, str):
                break
        else:
            break
    return ids


def clear_page_content(client: httpx.Client, page_id: str) -> None:
    pid = page_id.replace("-", "")
    for bid in fetch_all_child_block_ids(client, pid):
        notion_delete_block(client, bid)
        time.sleep(SLEEP_BETWEEN_DELETES)


def append_blocks(client: httpx.Client, page_id: str, blocks: list[dict[str, Any]]) -> None:
    pid = page_id.replace("-", "")
    for i in range(0, len(blocks), APPEND_BATCH):
        batch = blocks[i : i + APPEND_BATCH]
        notion_patch(client, f"/blocks/{pid}/children", {"children": batch})


def create_page(
    client: httpx.Client, parent_id: str, title: str, blocks: list[dict[str, Any]]
) -> str:
    body: dict[str, Any] = {
        "parent": {"type": "page_id", "page_id": parent_id.replace("-", "")},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": title[:MAX_RICH_TEXT]}}],
            }
        },
    }
    created = notion_post(client, "/pages", body)
    page_id = created.get("id")
    if not isinstance(page_id, str):
        raise RuntimeError(f"Unexpected create response: {created}")
    pid = page_id.replace("-", "")
    if blocks:
        append_blocks(client, pid, blocks)
    return pid


def update_page_title(client: httpx.Client, page_id: str, title: str) -> None:
    pid = page_id.replace("-", "")
    notion_patch(
        client,
        f"/pages/{pid}",
        {
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": title[:MAX_RICH_TEXT]}}],
                }
            }
        },
    )


def verify_parent(client: httpx.Client, parent_id: str) -> None:
    pid = parent_id.replace("-", "")
    notion_get(client, f"/pages/{pid}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync lumen/docs/*.md to Notion wiki pages.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without calling Notion (except --check).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate env and that the parent page is readable, then exit.",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(_lumen_root() / ".env")
    except ImportError:
        pass

    docs = _docs_dir()
    map_path = _map_path()
    if not docs.is_dir():
        print(f"Docs directory not found: {docs}", file=sys.stderr)
        sys.exit(1)

    mapping = load_map(map_path)

    if args.dry_run:
        for path in list_markdown_files(docs):
            rel = path.name
            md = path.read_text(encoding="utf-8")
            title = extract_title(md, path.stem.replace("_", " ").title())
            blocks = md_to_blocks(md)
            page_id = mapping.get(rel)
            action = "update" if page_id else "create"
            print(f"[dry-run] {action}: {rel!r} -> title={title!r} blocks={len(blocks)}")
        return

    headers = _headers()
    parent = _parent_page_id()

    with httpx.Client(headers=headers, timeout=60.0) as client:
        if args.check:
            verify_parent(client, parent)
            print("OK: parent page is reachable and token is valid.")
            return

        verify_parent(client, parent)

        for path in list_markdown_files(docs):
            rel = path.name
            md = path.read_text(encoding="utf-8")
            title = extract_title(md, path.stem.replace("_", " ").title())
            blocks = md_to_blocks(md)
            page_id = mapping.get(rel)

            if page_id:
                print(f"Updating {rel} ({_uuid_with_dashes(page_id)}) …")
                update_page_title(client, page_id, title)
                clear_page_content(client, page_id)
                append_blocks(client, page_id, blocks)
            else:
                print(f"Creating {rel} …")
                new_id = create_page(client, parent, title, blocks)
                mapping[rel] = new_id
                print(f"  new page id: {_uuid_with_dashes(new_id)}")

        save_map(map_path, mapping)
        print(f"Wrote {map_path}")


if __name__ == "__main__":
    main()
