"""Splits markdown source documents into section-aware chunks for embedding.

Chunking strategy:
  1. Split the body on ``##``/``###`` headers — each header opens a new section.
  2. Within a section, split further on top-level numbered clauses
     (``1.``, ``2.`` ...); a clause's lettered sub-items, nested lists, and
     other trailing prose stay attached to that clause and are never split
     across chunks.
  3. Adjacent clauses (or, in sections with no numbered clauses, adjacent
     paragraphs) are greedily packed together up to a target chunk size.
  4. Content with no header of its own (the preamble before the first
     header, or a section too short to stand alone) is folded into an
     adjacent section rather than left as an orphan, metadata-less chunk.

Token counts are estimated as ``len(text) // 4`` (roughly chars-per-token
for English) — good enough for sizing decisions, no tokenizer required.
"""

import re

import yaml

TARGET_MIN_TOKENS = 100
TARGET_MAX_TOKENS = 400
HARD_CEILING_TOKENS = 550
FLOOR_TOKENS = 20

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_HEADER_RE = re.compile(r"^(#{2,3})[ \t]+(.+?)\s*$", re.MULTILINE)
_NUMBERED_CLAUSE_RE = re.compile(r"^\d+\.\s")
_HEADER_NUM_TITLE_RE = re.compile(r"^(?P<num>[IVXLCDM]+|[A-Z]|\d+)\.\s+(?P<title>.+)$")
_ANNEXURE_RE = re.compile(r"^annexure\b\s*[—:\-]*\s*(?P<title>.*)$", re.IGNORECASE)

# Signals that a clause is substantial/self-contained enough to deserve its
# own chunk even when it would otherwise be small enough to merge with its
# neighbors: a bolded inline label acting as a mini-header ("**Foo:**" right
# after the clause number), or its own lettered sub-items ("a) ...", "b) ...")
# — as opposed to a plain parenthetical enumeration like "(a) ...; (b) ..."
# inline in one sentence, which is excluded via the negative lookbehind.
_BOLD_LABEL_RE = re.compile(r"^\d+\.\s+\*\*(?P<label>.+?)\*\*")
_LETTER_SUBITEM_RE = re.compile(r"(?<!\()\b[a-h][.\)]\s")


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars / 4) used only for chunk-sizing decisions."""
    return max(1, len(text) // 4)


def parse_frontmatter(raw_text: str) -> tuple[dict, str]:
    """Split a source markdown file into its YAML frontmatter and body.

    Args:
        raw_text: The full contents of a source .md file, frontmatter included.

    Returns:
        A tuple of (frontmatter dict, body markdown text).
    """
    match = _FRONTMATTER_RE.match(raw_text)
    if not match:
        return {}, raw_text
    frontmatter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return frontmatter, body


def _parse_header(header_text: str) -> tuple[str | None, str]:
    """Derive (section_number, section_title) from a header's raw text."""
    m = _HEADER_NUM_TITLE_RE.match(header_text)
    if m:
        return m.group("num"), m.group("title").strip()
    m = _ANNEXURE_RE.match(header_text)
    if m:
        title = m.group("title").strip()
        return "Annexure", title or header_text
    return None, header_text


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]


def _split_sections(body: str) -> list[dict]:
    """Split body into ordered sections at each ##/### header.

    Returns a list of {"number", "title", "blocks"} dicts. Content before the
    first header (if any) is returned as a leading section with number/title
    set to None, so callers can fold it into the first real section.
    """
    headers = list(_HEADER_RE.finditer(body))
    sections = []

    preamble = body[: headers[0].start()] if headers else body
    if preamble.strip():
        sections.append({"number": None, "title": None, "blocks": _split_paragraphs(preamble)})

    for i, h in enumerate(headers):
        start = h.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(body)
        content = body[start:end]
        number, title = _parse_header(h.group(2))
        sections.append({"number": number, "title": title, "blocks": _split_paragraphs(content)})

    return sections


def _section_tokens(section: dict) -> int:
    return estimate_tokens("\n\n".join(section["blocks"]))


def _merge_thin_sections(sections: list[dict]) -> list[dict]:
    """Fold headerless preamble and undersized sections into a neighbor.

    A section with no header of its own can never carry valid metadata, so
    it always merges forward. A section that does have a header but is too
    short to be a useful standalone chunk merges into the next section
    (or the previous one, if it's last), keeping the neighbor's metadata.
    """
    # Forward pass: fold anything headerless or thin into the *next* section.
    result: list[dict] = []
    carry: list[str] = []
    for section in sections:
        is_headerless = section["number"] is None and section["title"] is None
        is_thin = _section_tokens(section) < FLOOR_TOKENS
        if (is_headerless or is_thin) and section is not sections[-1]:
            carry.extend(section["blocks"])
            continue
        blocks = carry + section["blocks"]
        carry = []
        result.append({"number": section["number"], "title": section["title"], "blocks": blocks})

    # If the very last section was itself headerless/thin (nothing after it
    # to fold forward into), fold it backward into the previous section.
    if carry:
        if result:
            result[-1]["blocks"] = result[-1]["blocks"] + carry
        else:
            result.append({"number": None, "title": None, "blocks": carry})

    return result


def _isolation_info(group: dict) -> tuple[bool, str | None]:
    """Whether a clause group is substantial enough to force its own chunk.

    Triggers on a bolded inline label acting as a mini-header, or on the
    clause having its own lettered sub-items (a), b), ... — signals that
    it's a distinct, individually-citable provision rather than filler
    that's fine to merge with its neighbors.

    Returns (isolate, title_override). A bolded label doubles as the
    chunk's section_title (e.g. "Schedule of Implementation"), since it's
    functioning as a mini-header the enclosing section's title can't
    capture. Lettered sub-items carry no such title, so the enclosing
    section's title is left as-is.
    """
    if group["number"] is None:
        return False, None
    m = _BOLD_LABEL_RE.match(group["blocks"][0])
    if m:
        return True, m.group("label").strip().rstrip(":").strip()
    text = "\n\n".join(group["blocks"])
    if len(_LETTER_SUBITEM_RE.findall(text)) >= 2:
        return True, None
    return False, None


def _group_by_clause(blocks: list[str]) -> list[dict]:
    """Group a section's paragraph blocks into atomic clause groups.

    Each top-level numbered clause (and any lettered sub-items / nested
    lists / trailing prose that follow it) forms one group. Blocks that
    precede the first numbered clause become a "None"-numbered group so
    they still get packed rather than dropped.

    If the section has no numbered clauses at all, each paragraph is its
    own atomic group instead, so plain prose can still be split across
    multiple appropriately-sized chunks by _pack_groups.
    """
    if not any(_NUMBERED_CLAUSE_RE.match(b) for b in blocks):
        return [{"number": None, "blocks": [b], "isolate": False, "title_override": None} for b in blocks]

    groups: list[dict] = []
    for block in blocks:
        m = _NUMBERED_CLAUSE_RE.match(block)
        if m:
            number = block.split(".", 1)[0]
            groups.append({"number": number, "blocks": [block]})
        elif groups:
            groups[-1]["blocks"].append(block)
        else:
            groups.append({"number": None, "blocks": [block]})

    for g in groups:
        g["isolate"], g["title_override"] = _isolation_info(g)
    return groups


def _merge_number_labels(a: str | None, b: str | None) -> str | None:
    if a is None:
        return b
    if b is None:
        return a
    if a == b:
        return a
    return f"{a}-{b}"


def _pack_groups(groups: list[dict]) -> list[dict]:
    """Greedily pack adjacent atomic groups into chunks near the target size.

    A group flagged "isolate" always gets flushed into a chunk of its own —
    it never merges with a preceding or following group, regardless of size.
    """
    chunks: list[dict] = []
    current_numbers: list[str | None] = []
    current_blocks: list[str] = []
    current_tokens = 0
    current_isolated = False
    current_title_override: str | None = None

    def flush(protected: bool = False, title_override: str | None = None):
        nonlocal current_numbers, current_blocks, current_tokens, current_isolated, current_title_override
        if not current_blocks:
            return
        number = None
        for n in current_numbers:
            number = _merge_number_labels(number, n)
        chunks.append(
            {
                "number": number,
                "content": "\n\n".join(current_blocks),
                "protected": protected,
                "title_override": title_override,
            }
        )
        current_numbers, current_blocks, current_tokens, current_isolated = [], [], 0, False
        current_title_override = None

    for group in groups:
        group_text = "\n\n".join(group["blocks"])
        group_tokens = estimate_tokens(group_text)
        is_isolate = group.get("isolate", False)
        if current_blocks and (current_tokens + group_tokens > TARGET_MAX_TOKENS or is_isolate or current_isolated):
            flush(protected=current_isolated, title_override=current_title_override)
        current_numbers.append(group["number"])
        current_blocks.extend(group["blocks"])
        current_tokens += group_tokens
        current_isolated = is_isolate
        current_title_override = group.get("title_override")
    flush(protected=current_isolated, title_override=current_title_override)
    return chunks


def _merge_floor_chunks(chunks: list[dict]) -> list[dict]:
    """Merge any chunk under FLOOR_TOKENS into a neighboring chunk.

    Chunks marked "protected" (forced into isolation by _pack_groups) are
    never dissolved this way, even if they happen to be small.
    """
    i = 0
    while len(chunks) > 1 and i < len(chunks):
        if chunks[i].get("protected") or estimate_tokens(chunks[i]["content"]) >= FLOOR_TOKENS:
            i += 1
            continue
        if i + 1 < len(chunks) and not chunks[i + 1].get("protected"):
            chunks[i + 1]["content"] = chunks[i]["content"] + "\n\n" + chunks[i + 1]["content"]
            chunks[i + 1]["number"] = _merge_number_labels(chunks[i]["number"], chunks[i + 1]["number"])
            del chunks[i]
        elif i > 0 and not chunks[i - 1].get("protected"):
            chunks[i - 1]["content"] = chunks[i - 1]["content"] + "\n\n" + chunks[i]["content"]
            chunks[i - 1]["number"] = _merge_number_labels(chunks[i - 1]["number"], chunks[i]["number"])
            del chunks[i]
            i -= 1
        else:
            i += 1
    return chunks


def chunk_document(markdown_text: str, doc_id: str) -> list[dict]:
    """Split a markdown document's body into chunks with section metadata.

    Args:
        markdown_text: Full markdown document body (frontmatter already stripped).
        doc_id: The document's doc_id, for traceability in returned chunks.

    Returns:
        A list of dicts with keys: section_number, section_title, content.
    """
    sections = _split_sections(markdown_text)
    sections = _merge_thin_sections(sections)

    chunks: list[dict] = []
    for section in sections:
        groups = _group_by_clause(section["blocks"])
        section_chunks = _pack_groups(groups)
        section_chunks = _merge_floor_chunks(section_chunks)

        # A section's numbered clauses are only genuinely *its* sub-items if
        # numbering restarts at "1" within the section (e.g. NSE Annexure
        # sections A-J each number their own items 1, 2, 3...). If the first
        # clause found continues the document's outer numbering instead
        # (e.g. clauses 6-10 spilling past doc 01's "V." header), those are
        # top-level clauses, not children of this header, so the header's
        # own letter/roman marker should not be glued onto them.
        first_clause_number = next((g["number"] for g in groups if g["number"] is not None), None)
        nested = first_clause_number == "1"

        for c in section_chunks:
            if section["number"] is None:
                section_number = c["number"]
            elif not nested:
                section_number = c["number"] if c["number"] is not None else section["number"]
            elif c["number"] is None or len(section_chunks) == 1:
                section_number = section["number"]
            else:
                section_number = f'{section["number"]}.{c["number"]}'
            section_title = c.get("title_override") or section["title"]
            chunks.append(
                {
                    "section_number": section_number,
                    "section_title": section_title,
                    "content": c["content"],
                }
            )
    return chunks
