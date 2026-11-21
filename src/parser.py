"""文档解析器：把 DOCX 解析成带条款号的结构化段落。

输出统一 schema（后续抽取、检索、判定都消费这个结构）：
    {
        "id": int,          # 段落在文档中的序号
        "page": int,        # 近似页码（DOCX 无真页码，靠显式分页符估算）
        "text": str,        # 原始文本
        "clause_no": str,   # 条款号，如 "第十二条" / "一、" / "1.1"；无则为 ""
        "heading": str,     # 条款标题（条款号后面的部分）
        "source": str,      # 来源："paragraph" 或 "table-N"
    }

设计说明：
- 条款号识别用正则，顺序很重要（第X条/第X章 → 一、 → （一） → 1.1.1）。
- 表格里也常藏条款（老式合同），所以一并解析，并按单元格去重（合并单元格会重复返回）。
"""

from __future__ import annotations

import re
from pathlib import Path

import docx

# ---- 条款号识别（顺序很重要）----
_CLAUSE_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十百零0-9]+[章条]"),  # 第X条 / 第X章
    re.compile(r"^[一二三四五六七八九十]+、"),                # 一、二、三
    re.compile(r"^[（(][一二三四五六七八九十]+[)）]"),         # （一）（二）
    re.compile(r"^\d+(?:\.\d+)+"),                            # 1.1 / 1.1.1
    re.compile(r"^\d+[\.、]"),                                # 2. / 3、（老式合同数字编号）
]

# 句末标点后紧跟新条款号 → 说明一个段落里塞了多条
_SPLIT_RE = re.compile(
    r"[。；！？\n][ \t　]*(?=(?:第[一二三四五六七八九十百零0-9]+[章条]"
    r"|[一二三四五六七八九十]+、"
    r"|[（(][一二三四五六七八九十]+[)）]"
    r"|\d+(?:\.\d+)+))"
)


def split_clauses(text: str) -> list[str]:
    """把一段文字按「句末标点 + 新条款号」切成多段。

    老式合同常把多条塞进一个段落，例如：
        "二、广告发布媒介为 。三、单位广告规格为 。四、……"
    这里会切成 ["二、广告发布媒介为 。", "三、单位广告规格为 。", "四、……"]。
    """
    text = text.strip()
    if not text:
        return []
    starts = [0]
    for m in _SPLIT_RE.finditer(text):
        starts.append(m.end())
    starts.append(len(text))
    segs = [text[starts[i]:starts[i + 1]].strip() for i in range(len(starts) - 1)]
    return [s for s in segs if s]


def extract_clause(text: str) -> tuple[str, str]:
    """从一段文字里拆出 (条款号, 标题)。无条款号时返回 ("", "")。"""
    for pat in _CLAUSE_PATTERNS:
        m = pat.match(text)
        if m:
            clause_no = m.group()
            heading = text[len(clause_no):].strip("　 　：:.、 ")
            return clause_no, heading
    return "", ""


def _has_page_break(p) -> bool:
    """判断段落是否触发分页（显式分页符 / Word 渲染分页标记）。"""
    xml = p._p.xml
    return 'w:type="page"' in xml or "lastRenderedPageBreak" in xml


def parse_docx(path: str | Path) -> list[dict]:
    """解析一个 DOCX，返回结构化段落列表。"""
    doc = docx.Document(str(path))

    out: list[dict] = []
    page = 1
    pid = 0

    def add(text: str, source: str) -> None:
        nonlocal page, pid
        text = text.strip()
        if not text:
            return
        # 一个段落里可能塞了多条（二、…三、…四、…），先拆再逐条入库
        for seg in split_clauses(text):
            clause_no, heading = extract_clause(seg)
            out.append({
                "id": pid,
                "page": page,
                "text": seg,
                "clause_no": clause_no,
                "heading": heading,
                "source": source,
            })
            pid += 1

    # 1) 正文段落
    for p in doc.paragraphs:
        if _has_page_break(p):
            page += 1
        add(p.text, "paragraph")

    # 2) 表格（老式合同条款常藏在表格里）
    for t_idx, table in enumerate(doc.tables):
        seen_texts = set()
        # 用 _cells 拿全部底层单元格；合并单元格会在多个网格位置重复同一文本，按文本去重
        for cell in table._cells:
            text = cell.text.strip()
            if text and text not in seen_texts:
                seen_texts.add(text)
                add(text, f"table-{t_idx}")

    return out


def parse(path: str | Path) -> list[dict]:
    """按扩展名分派解析器。目前支持 .docx，PDF 待补。"""
    path = Path(path)
    if path.suffix.lower() == ".docx":
        return parse_docx(path)
    raise ValueError(f"暂不支持该格式: {path.suffix}")


def to_text(paragraphs: list[dict]) -> str:
    """把结构化段落拼回纯文本（给抽取层做全文兜底）。"""
    return "\n".join(p["text"] for p in paragraphs)


def clause_headings(paragraphs: list[dict]) -> list[dict]:
    """只保留有条款号的段落（条款标题列表），便于快速浏览合同骨架。"""
    return [p for p in paragraphs if p["clause_no"]]


def parse_blocks(path: str | Path) -> list[dict]:
    """按文档顺序解析成「段落 + 表格」块，保留表格行列结构（用于预览）。

    与 parse() 的区别：parse() 把表格单元格拍平成段落（便于条款抽取）；
    这里保留表格结构，预览时能按原样渲染成表格。
    """
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = docx.Document(str(path))
    blocks: list[dict] = []
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            p = Paragraph(child, doc)
            text = p.text.strip()
            if text:
                clause_no, _ = extract_clause(text)
                blocks.append({"type": "paragraph", "clause_no": clause_no, "text": text})
        elif child.tag.endswith("}tbl"):
            t = Table(child, doc)
            rows = []
            for row in t.rows:
                cells = []
                seen = set()
                for cell in row.cells:
                    txt = cell.text.strip()
                    if txt and txt not in seen:
                        seen.add(txt)
                        cells.append(txt)
                if cells:
                    rows.append(cells)
            if rows:
                blocks.append({"type": "table", "rows": rows})
    return blocks
