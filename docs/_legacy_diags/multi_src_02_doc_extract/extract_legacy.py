"""Extract legacy .doc / .docx text from Multi1D++Portable20241128 into .workbuddy/tmp/legacy/ .

Strategy per file (first success wins):
  1. win32com Word.Application (uses the real Word, most faithful)
  2. docx (for .docx)
  3. raw OLE WordDocument stream decode (utf-16-be swap aware)
"""
import io
import os
import sys

SRC = r"src\Multi1D++Portable20241128"
OUT = r".workbuddy\tmp\legacy"

TARGETS = [
    r"doc\Atomic(LEDCOP)说明.doc",
    r"doc\Hyades 数据格式说明.doc",
    r"doc\Restart.doc",
    r"doc\GUI,IO相关.docx",
    r"doc\MULTI使用的SESAME数据文件格式.docx",
    r"doc\QuietStart.docx",
    r"doc\多群辐射源(FDS).docx",
    r"doc\反弹冲击波的撞击壳的时刻.docx",
    r"matter++\ATOMIC\Atomic(LEDCOP)不透明度格式说明.docx",
    r"matter++\hyades\Hyades 数据格式说明.doc",
]


def norm(s):
    return s.replace("\r\n", "\n").replace("\r", "\n")


def cnt_cjk(t):
    return sum(1 for c in t if "\u4e00" <= c <= "\u9fff")


def try_word(path):
    """Use installed MS Word via COM."""
    try:
        import win32com.client  # noqa
        import pythoncom
    except Exception:
        return None
    try:
        pythoncom.CoInitialize()
        app = win32com.client.Dispatch("Word.Application")
        app.Visible = False
        app.DisplayAlerts = 0
        doc = app.Documents.Open(os.path.abspath(path), ReadOnly=True,
                                 ConfirmConversions=False, AddToRecentFiles=False)
        txt = doc.Content.Text
        # tables often hold the format specs - grab them too
        parts = [txt]
        try:
            for t in doc.Tables:
                rows = []
                for r in t.Rows:
                    cells = []
                    for c in r.Cells:
                        cells.append(c.Range.Text.replace("\r\x07", "").strip())
                    rows.append(" | ".join(cells))
                if rows:
                    parts.append("\n[TABLE]\n" + "\n".join(rows) + "\n[/TABLE]\n")
        except Exception as e:
            parts.append("\n[table extract failed: %r]\n" % (e,))
        doc.Close(False)
        app.Quit()
        return norm("\n".join(parts))
    except Exception as e:
        print("      word path failed: %r" % (e,))
        return None


def try_docx(path):
    try:
        import docx
    except Exception:
        return None
    try:
        d = docx.Document(path)
        out = []
        for p in d.paragraphs:
            out.append(p.text)
        for ti, t in enumerate(d.tables):
            out.append("\n[TABLE %d]\n" % (ti + 1))
            for r in t.rows:
                out.append(" | ".join(c.text.strip() for c in r.cells))
            out.append("[/TABLE]\n")
        return norm("\n".join(out))
    except Exception as e:
        print("      docx path failed: %r" % (e,))
        return None


def try_ole(path):
    """Last resort: byte-swap aware scrape."""
    try:
        raw = io.open(path, "rb").read()
    except Exception:
        return None
    best = ""
    # try utf-16-le / be on the whole payload
    for enc in ("utf-16-le", "utf-16-be"):
        try:
            s = raw.decode(enc, "ignore")
        except Exception:
            continue
        keep = []
        for ch in s:
            o = ord(ch)
            if ch in "\n\t" or 32 <= o < 127 or 0x4E00 <= o <= 0x9FFF or 0x3000 <= o <= 0x303F \
               or 0xFF00 <= o <= 0xFFEF or 0x2000 <= o <= 0x206F:
                keep.append(ch)
            else:
                keep.append(" ")
        t = "".join(keep)
        score = cnt_cjk(t) + sum(1 for c in t if c.isalpha())
        if score > 200:
            # collapse runs of spaces
            lines = []
            for ln in t.split("\n"):
                ln = " ".join(ln.split())
                if ln:
                    lines.append(ln)
            cand = norm("\n".join(lines))
            if len(cand) > len(best):
                best = cand
    return best or None


def main():
    os.makedirs(OUT, exist_ok=True)
    report = []
    for rel in TARGETS:
        path = os.path.join(SRC, rel)
        print("=" * 78)
        print("FILE:", rel, "exists:", os.path.exists(path))
        if not os.path.exists(path):
            report.append((rel, 0, 0, "MISSING"))
            continue
        size = os.path.getsize(path)
        text = None
        how = ""
        if rel.lower().endswith(".doc"):
            text = try_word(path)
            if text:
                how = "win32com/Word"
            if not text:
                text = try_ole(path)
                if text:
                    how = "raw-OLE"
        else:
            text = try_docx(path)
            if text:
                how = "python-docx"
            if not text:
                text = try_word(path)
                if text:
                    how = "win32com/Word"
        if not text:
            report.append((rel, size, 0, "FAILED"))
            print("  -> FAILED")
            continue
        base = os.path.splitext(os.path.basename(rel))[0]
        op = os.path.join(OUT, base + ".txt")
        io.open(op, "w", encoding="utf-8", newline="\n").write(text)
        cjk = cnt_cjk(text)
        report.append((rel, size, cjk, "%s -> %s" % (how, os.path.basename(op))))
        print("  -> %s | chars=%d cjk=%d" % (how, len(text), cjk))

    print()
    print("=" * 78)
    print("%-58s %10s %8s  %s" % ("source", "bytes", "CJK", "method"))
    print("-" * 78)
    for rel, size, cjk, how in report:
        print("%-58s %10d %8d  %s" % (rel[:58], size, cjk, how))


if __name__ == "__main__":
    sys.exit(main())
