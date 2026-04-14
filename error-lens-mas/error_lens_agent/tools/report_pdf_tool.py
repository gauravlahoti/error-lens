"""PDF diagnostic report generator — saves as an ADK session artifact.

Design: Google Material Design pastel palette, consulting-grade typography.
"""

import json
import os
import re
from datetime import datetime
from google.adk.tools import ToolContext
from google.genai import types
from fpdf import FPDF

# ── Google Material Palette ───────────────────────────────────────────────────
# Primary brand
G_BLUE       = (66,  133, 244)   # #4285F4
G_DARK_BLUE  = (26,  115, 232)   # #1A73E8  — header background
G_RED        = (234,  67,  53)   # #EA4335
G_YELLOW     = (251, 188,   4)   # #FBBC04
G_GREEN      = (52,  168,  83)   # #34A853

# Pastel backgrounds (Material 50-level)
P_BLUE   = (232, 240, 254)       # #E8F0FE
P_RED    = (252, 232, 230)       # #FCE8E6
P_GREEN  = (230, 244, 234)       # #E6F4EA
P_YELLOW = (254, 247, 224)       # #FEF7E0
P_GREY   = (248, 249, 250)       # #F8F9FA
P_GREY2  = (241, 243, 244)       # #F1F3F4

# Neutrals
C_WHITE  = (255, 255, 255)
C_TEXT   = (32,   33,  36)       # #202124  primary text
C_MUTED  = (95,   99, 104)       # #5F6368  secondary text
C_BORDER = (218, 220, 224)       # #DADCE0  dividers
C_CODE   = (32,   33,  50)       # dark code bg

# Severity map
_SEV_FG = {
    "critical": G_RED,
    "high":     (230,  81,   0),
    "medium":   (230, 140,   0),
    "low":      G_GREEN,
}
_SEV_BG = {
    "critical": P_RED,
    "high":     (255, 237, 213),
    "medium":   P_YELLOW,
    "low":      P_GREEN,
}

# Rank accent colours (blue family)
_RANK_CLR = [(26, 115, 232), (66, 133, 244), (138, 180, 248)]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _s(v) -> str:
    """Encode to latin-1 safely; replace unmappable chars."""
    if not isinstance(v, str):
        v = str(v)
    return v.encode("latin-1", errors="replace").decode("latin-1")


def _pct(v) -> str:
    try:
        return f"{float(v) * 100:.0f}%"
    except Exception:
        return str(v)


def _conf_fg(v):
    try:
        f = float(v)
        return G_GREEN if f >= 0.80 else (G_YELLOW if f >= 0.60 else G_RED)
    except Exception:
        return G_BLUE


def _clean_md(text: str) -> str:
    """Strip markdown formatting for plain PDF rendering."""
    text = str(text)
    text = re.sub(r'\*\*[a-zA-Z]\.\*\*\s*', '', text)    # step labels **a.**
    text = re.sub(r'\*\*([^*\n]+)\*\*', r'\1', text)      # bold
    text = re.sub(r'\*([^*\n]+)\*', r'\1', text)           # italic
    text = re.sub(r'`([^`\n]+)`', r'\1', text)             # inline code
    text = re.sub(r'```\w*\n?', '', text)                  # fenced block open
    text = re.sub(r'```', '', text)                        # fenced block close
    return text.strip()


_CMD_RE = re.compile(
    r'^\s*(gcloud\s|kubectl\s|export\s+\w+=|set\s+\w+=|\$\s|helm\s|bq\s|gsutil\s|docker\s)'
)


def _is_cmd(line: str) -> bool:
    """Return True if the line looks like a shell command."""
    return bool(_CMD_RE.match(line))


# ── PDF class ─────────────────────────────────────────────────────────────────

class PDF(FPDF):

    def __init__(self):
        super().__init__()
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(True, margin=22)
        self.add_page()

    # ── low-level drawing helpers ─────────────────────────────────────────

    def _rect(self, x, y, w, h, fill, border_clr=None, lw=0.2):
        self.set_fill_color(*fill)
        if border_clr:
            self.set_draw_color(*border_clr)
            self.set_line_width(lw)
            self.rect(x, y, w, h, style="FD")
        else:
            self.rect(x, y, w, h, style="F")

    def _hrule(self, color=C_BORDER, lw=0.3):
        self.set_draw_color(*color)
        self.set_line_width(lw)
        self.line(self.l_margin, self.get_y(),
                  self.l_margin + self.epw, self.get_y())

    def _txt(self, color, size=10, style=""):
        self.set_font("Helvetica", style=style, size=size)
        self.set_text_color(*color)

    # ── page header ───────────────────────────────────────────────────────

    def make_header(self, service, severity, case_ref, generated_at):
        """Blue banner with branding on left, metadata on right."""
        bh = 46
        self._rect(0, 0, self.w, bh, G_DARK_BLUE)

        # Left — product name + tagline
        self._txt(C_WHITE, size=22, style="B")
        self.set_xy(18, 10)
        self.cell(90, 10, "ErrorLens", new_x="LMARGIN", new_y="NEXT")
        self._txt((180, 210, 255), size=8)
        self.set_xy(18, 23)
        self.cell(90, 5, "Diagnostic Report  |  Powered by Google ADK",
                  new_x="LMARGIN", new_y="NEXT")

        # Right column — date / case / severity
        rx = self.w - 82
        self._txt((180, 210, 255), size=8)
        self.set_xy(rx, 10)
        self.cell(64, 5, _s(generated_at), align="R",
                  new_x="LMARGIN", new_y="NEXT")

        # Always show case ref — "Case: Pending" when not yet assigned
        case_label = (
            case_ref
            if case_ref and case_ref not in ("RECORDING_PENDING", "")
            else "Pending"
        )
        self._txt(C_WHITE, size=8, style="B")
        self.set_xy(rx, 18)
        self.cell(64, 5, _s(f"Case: {case_label}"), align="R",
                  new_x="LMARGIN", new_y="NEXT")

        if severity:
            sc = _SEV_FG.get(severity.lower(), G_BLUE)
            sb = _SEV_BG.get(severity.lower(), P_BLUE)
            pill_w, pill_h = 52, 10
            px = self.w - 18 - pill_w
            self._rect(px, 28, pill_w, pill_h, sb, sc, lw=0.4)
            self._txt(sc, size=8, style="B")
            self.set_xy(px, 29)
            self.cell(pill_w, 8, _s(severity.upper() + "  SEVERITY"),
                      align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*C_TEXT)
        self.set_xy(18, bh + 5)

    # ── executive summary strip ───────────────────────────────────────────

    def exec_summary(self, service, severity, overall_conf, n_fixes, case_ref):
        """4-metric card row below header."""
        y = self.get_y()
        strip_h = 26
        self._rect(0, y, self.w, strip_h, P_GREY2)

        metrics = [
            ("GCP SERVICE",    _s(service) if service else "—"),
            ("SEVERITY",       _s(severity.upper()) if severity else "—"),
            ("CONFIDENCE",     _pct(overall_conf)),
            ("RANKED FIXES",   str(n_fixes)),
        ]

        card_w  = self.epw / len(metrics)
        for i, (label, value) in enumerate(metrics):
            cx = self.l_margin + i * card_w

            # subtle left divider between cards
            if i > 0:
                self.set_draw_color(*C_BORDER)
                self.set_line_width(0.3)
                self.line(cx, y + 4, cx, y + strip_h - 4)

            # label
            self._txt(C_MUTED, size=7, style="B")
            self.set_xy(cx + 4, y + 4)
            self.cell(card_w - 8, 5, label, new_x="LMARGIN", new_y="NEXT")

            # value — colour the confidence and severity
            if label == "CONFIDENCE":
                vc = _conf_fg(overall_conf)
            elif label == "SEVERITY":
                vc = _SEV_FG.get(severity.lower(), C_TEXT) if severity else C_TEXT
            else:
                vc = C_TEXT
            self._txt(vc, size=11, style="B")
            self.set_xy(cx + 4, y + 11)
            self.cell(card_w - 8, 7, _s(value), new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*C_TEXT)
        self.set_xy(18, y + strip_h + 6)

    # ── section heading ───────────────────────────────────────────────────

    def section(self, title, subtitle=""):
        """Blue accent bar + bold title, optional italic subtitle."""
        self.ln(3)
        y = self.get_y()

        # 4 px left accent stripe
        self._rect(self.l_margin, y, 4, 12 if not subtitle else 17, G_DARK_BLUE)

        self._txt(G_DARK_BLUE, size=13, style="B")
        self.set_xy(self.l_margin + 7, y + 1)
        self.cell(self.epw - 7, 7, _s(title), new_x="LMARGIN", new_y="NEXT")

        if subtitle:
            self._txt(C_MUTED, size=9, style="I")
            self.set_x(self.l_margin + 7)
            self.cell(self.epw - 7, 5, _s(subtitle),
                      new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*C_TEXT)
        self.ln(4)

    # ── callout block ─────────────────────────────────────────────────────

    def callout(self, text, bg=P_BLUE, stripe=G_DARK_BLUE, icon=""):
        """Highlighted info box with left colour stripe."""
        x, y, w = self.l_margin, self.get_y(), self.epw
        self.set_font("Helvetica", size=10)
        prefix = (icon + "  ") if icon else ""
        full   = prefix + text
        lines  = self.multi_cell(w - 14, 6, _s(full), split_only=True)
        h      = len(lines) * 6 + 12

        self._rect(x,     y, w,  h, bg,     C_BORDER, lw=0.2)
        self._rect(x,     y, 4,  h, stripe)

        self._txt(C_TEXT, size=10)
        self.set_xy(x + 10, y + 6)
        self.multi_cell(w - 14, 6, _s(full), new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    # ── code block ────────────────────────────────────────────────────────

    def code_block(self, text):
        """Monospace dark block — truncated at 480 chars."""
        x, y, w = self.l_margin, self.get_y(), self.epw
        display = text[:480] + (" [truncated]" if len(text) > 480 else "")
        self.set_font("Courier", size=8)
        lines = self.multi_cell(w - 12, 5, _s(display), split_only=True)
        h     = len(lines) * 5 + 10

        self._rect(x, y, w, h, C_CODE)
        self.set_text_color(144, 238, 144)   # light green on dark
        self.set_xy(x + 7, y + 5)
        self.multi_cell(w - 12, 5, _s(display), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*C_TEXT)
        self.ln(4)

    # ── fix card ──────────────────────────────────────────────────────────

    def fix_card(self, rank, title, why, steps, confidence, source):
        """White card with left rank accent, title, why, steps, meta row."""
        x, y, w = self.l_margin, self.get_y(), self.epw
        accent = _RANK_CLR[min(rank - 1, len(_RANK_CLR) - 1)]

        # — measure content height —
        inner_w = w - 20   # after 6px accent + 14px inner margin

        clean_why = _clean_md(str(why)) if why else ""
        self.set_font("Helvetica", size=9)
        why_lines = self.multi_cell(inner_w, 5.5, _s(clean_why),
                                    split_only=True) if clean_why else []

        # Build step segments: ("prose", text) or ("code", [lines])
        step_segments = []
        if isinstance(steps, list):
            for i, s in enumerate(steps):
                clean_step = _clean_md(str(s))
                prose_buf, code_buf = [], []
                for ln in clean_step.splitlines():
                    if _is_cmd(ln):
                        if prose_buf:
                            step_segments.append(("prose", f"  {i + 1}.  " + " ".join(prose_buf)))
                            prose_buf = []
                        code_buf.append(ln.strip())
                    else:
                        if code_buf:
                            step_segments.append(("code", code_buf))
                            code_buf = []
                        if ln.strip():
                            prose_buf.append(ln.strip())
                if prose_buf:
                    step_segments.append(("prose", f"  {i + 1}.  " + " ".join(prose_buf)))
                if code_buf:
                    step_segments.append(("code", code_buf))
        elif steps:
            step_segments.append(("prose", _clean_md(str(steps))))

        # Estimate total step height
        step_h_total = 0
        self.set_font("Helvetica", size=9)
        for seg_type, seg_data in step_segments:
            if seg_type == "prose":
                seg_lines = self.multi_cell(inner_w, 5.5, _s(seg_data), split_only=True)
                step_h_total += len(seg_lines) * 5.5 + 2
            else:
                step_h_total += len(seg_data) * 5 + 14

        title_h = 10
        why_h   = len(why_lines) * 5.5 + (5 if why_lines else 0)
        step_h  = step_h_total + (6 if step_segments else 0)
        meta_h  = 9
        card_h  = title_h + why_h + step_h + meta_h + 8

        if y + card_h > self.h - self.b_margin - 5:
            self.add_page()
            y = self.get_y()

        # — card shell —
        self._rect(x, y, w, card_h, C_WHITE, C_BORDER, lw=0.3)

        # — left accent stripe —
        self._rect(x, y, 6, card_h, accent)

        # — rank badge (circle overlay on stripe) —
        cx_badge = x + 3
        cy_badge = y + 5
        self.set_fill_color(*C_WHITE)
        self.ellipse(cx_badge - 4, cy_badge, 8, 8, style="F")
        self._txt(accent, size=8, style="B")
        self.set_xy(cx_badge - 4, cy_badge + 1)
        self.cell(8, 6, str(rank), align="C", new_x="LMARGIN", new_y="NEXT")

        # — title row —
        tx = x + 12
        self._txt(C_TEXT, size=11, style="B")
        self.set_xy(tx, y + 3)
        self.cell(w - 14, title_h - 2, _s(_clean_md(str(title))), new_x="LMARGIN", new_y="NEXT")

        # — "why recommended" in italic muted —
        if why_lines:
            self._txt(C_MUTED, size=9, style="I")
            self.set_x(tx)
            self.multi_cell(inner_w, 5.5, _s(clean_why),
                            new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        # — steps (prose segments + inline code blocks for shell commands) —
        for seg_type, seg_data in step_segments:
            if seg_type == "prose":
                self._txt(C_TEXT, size=9)
                self.set_x(tx)
                self.multi_cell(inner_w, 5.5, _s(seg_data),
                                new_x="LMARGIN", new_y="NEXT")
                self.ln(2)
            else:  # code block
                self.set_xy(tx, self.get_y())
                code_text = "\n".join(seg_data)
                display = code_text[:480] + (" [truncated]" if len(code_text) > 480 else "")
                self.set_font("Courier", size=8)
                cb_lines = self.multi_cell(inner_w, 5, _s(display), split_only=True)
                cb_h = len(cb_lines) * 5 + 10
                cx, cy = self.get_x(), self.get_y()
                self._rect(cx, cy, inner_w, cb_h, C_CODE)
                self.set_text_color(144, 238, 144)
                self.set_xy(cx + 4, cy + 5)
                self.multi_cell(inner_w - 8, 5, _s(display),
                                new_x="LMARGIN", new_y="NEXT")
                self.set_text_color(*C_TEXT)
                self.ln(4)

        # — meta divider + confidence + source —
        meta_y = max(y + card_h - meta_h, self.get_y() + 2)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.line(x + 6, meta_y, x + w, meta_y)

        self.set_xy(tx, meta_y + 2)
        if confidence:
            fc = _conf_fg(confidence)
            self._txt(fc, size=8, style="B")
            self.cell(50, 5, _s(f"Confidence:  {_pct(confidence)}"),
                      new_x="RIGHT", new_y="LAST")

        if source:
            self._txt(C_MUTED, size=8)
            src_label = _s(f"Source:  {source}")
            self.cell(0, 5, src_label, new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*C_TEXT)
        self.set_xy(x, max(y + card_h + 5, self.get_y() + 5))

    # ── confidence summary bar ────────────────────────────────────────────

    def conf_bar(self, label, score, bar_w=100):
        """Labelled horizontal progress bar."""
        try:
            v = float(score)
        except Exception:
            v = 0.0
        fc   = _conf_fg(v)
        y    = self.get_y()
        lbl_w = 52

        self._txt(C_MUTED, size=9)
        self.cell(lbl_w, 7, _s(label), new_x="RIGHT", new_y="LAST")

        bx = self.get_x() + 2
        # track
        self._rect(bx, y + 2.5, bar_w, 4, P_GREY2)
        # fill
        self._rect(bx, y + 2.5, bar_w * v, 4, fc)

        self.set_xy(bx + bar_w + 5, y)
        self._txt(fc, size=9, style="B")
        self.cell(20, 7, _pct(v), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*C_TEXT)

    # ── page footer ───────────────────────────────────────────────────────

    def footer(self):
        self.set_y(-14)
        self._rect(0, self.h - 12, self.w, 12, P_GREY2)

        self._hrule(C_BORDER)
        self._txt(C_MUTED, size=7)
        self.set_xy(18, self.h - 9)
        self.cell(
            self.epw * 0.7, 5,
            "ErrorLens Knowledge Bank  |  Powered by Google ADK  |  Confidential",
            new_x="RIGHT", new_y="LAST",
        )
        self.cell(
            self.epw * 0.3, 5,
            f"Page {self.page_no()}",
            align="R",
            new_x="LMARGIN", new_y="NEXT",
        )
        self.set_text_color(*C_TEXT)


# ── main tool function ────────────────────────────────────────────────────────

async def generate_pdf_report(tool_context: ToolContext) -> dict:
    """Generates a consulting-grade PDF diagnostic report and saves it as a session artifact."""

    # 1. Read ADK session state
    synthesis = tool_context.state.get("synthesis_result")
    if not synthesis:
        return {"error": "No diagnostic data yet. Run a full investigation first."}

    if isinstance(synthesis, str):
        synthesis = json.loads(synthesis)

    error_ctx = tool_context.state.get("error_triage_result") or {}
    if isinstance(error_ctx, str):
        error_ctx = json.loads(error_ctx)

    kb_result = tool_context.state.get("kb_record_result") or {}
    if isinstance(kb_result, str):
        kb_result = json.loads(kb_result)

    cost_summary = tool_context.state.get("_cost_summary", "")

    # 2. Extract fields (matches actual Pydantic model names)
    service       = error_ctx.get("primary_service", "")
    severity      = error_ctx.get("severity", "")
    error_message = error_ctx.get("error_message", "")
    case_ref      = kb_result.get("case_ref", "")
    root_cause    = synthesis.get("root_cause", "")
    ranked_fixes  = synthesis.get("ranked_fixes", [])
    overall_conf  = synthesis.get("overall_confidence", "")
    fallback      = synthesis.get("fallback_guidance", "")
    src_agreed    = synthesis.get("sources_agreed", False)
    src_contra    = synthesis.get("sources_contradicted", False)

    now          = datetime.now()
    generated_at = now.strftime("%d %b %Y  %H:%M UTC")
    timestamp    = now.strftime("%Y%m%d_%H%M%S")
    filename     = f"ErrorLens_Diagnostic_Report_{timestamp}.pdf"

    # 3. Build PDF
    pdf = PDF()
    W   = pdf.epw

    # ── Header ───────────────────────────────────────────────────────────
    pdf.make_header(service, severity, case_ref, generated_at)

    # ── Executive Summary strip ───────────────────────────────────────────
    pdf.exec_summary(service, severity, overall_conf, len(ranked_fixes), case_ref)

    # ── Error Message ─────────────────────────────────────────────────────
    if error_message:
        pdf.section("Error Message",
                    subtitle="Raw exception as reported by the application")
        pdf.code_block(error_message)

    # ── Root Cause Analysis ───────────────────────────────────────────────
    if root_cause:
        if src_agreed:
            rc_subtitle = "GCP docs and community sources are in agreement on the primary fix"
        elif src_contra:
            rc_subtitle = "Sources contain conflicting guidance — review all ranked fixes before applying"
        else:
            rc_subtitle = "Synthesised from GCP documentation and community sources"

        pdf.section("Root Cause Analysis", subtitle=rc_subtitle)
        pdf.callout(root_cause, bg=P_BLUE, stripe=G_DARK_BLUE)

    # ── Resolution Playbook ───────────────────────────────────────────────
    if ranked_fixes:
        pdf.section(
            "Resolution Playbook",
            subtitle=f"{len(ranked_fixes)} fixes ranked by confidence score — apply in order",
        )
        for i, fix in enumerate(ranked_fixes, start=1):
            pdf.fix_card(
                rank       = i,
                title      = fix.get("title", f"Fix {i}"),
                why        = fix.get("why_recommended", ""),
                steps      = fix.get("steps", []),
                confidence = fix.get("confidence", ""),
                source     = fix.get("source", ""),
            )

    # ── Confidence Summary ────────────────────────────────────────────────
    if overall_conf:
        # Needs ~40pt: section heading (20) + bar row (10) + padding (10)
        if pdf.get_y() > pdf.h - pdf.b_margin - 40:
            pdf.add_page()
        else:
            pdf.ln(1)
        pdf.section("Confidence Summary")
        pdf.conf_bar("Overall pipeline score", overall_conf)
        pdf.ln(5)

    # ── Escalation Path ───────────────────────────────────────────────────
    if fallback:
        pdf.section("Escalation Path",
                    subtitle="If none of the ranked fixes resolve the issue")
        pdf.callout(fallback, bg=P_YELLOW, stripe=G_YELLOW)

    # ── Case Tracking ─────────────────────────────────────────────────────
    pdf.section("Case Tracking",
                subtitle="Reference this case when confirming a fix to improve future auto-resolution")

    if case_ref and case_ref not in ("RECORDING_PENDING", ""):
        pdf.callout(
            f"Case Reference: {case_ref}\n\n"
            "Share this reference with your team.  Once a fix is confirmed, tell ErrorLens:\n"
            f'    "Case ref {case_ref}, fix #1 worked"\n\n'
            "ErrorLens will update the knowledge bank so future occurrences resolve instantly,\n"
            "without running the full research pipeline.",
            bg=P_GREEN, stripe=G_GREEN,
        )
    else:
        pdf.callout(
            "Case recording is in progress.  A reference will be assigned shortly.\n\n"
            "Once available, share the case reference with your team and use it to\n"
            "confirm the fix and contribute the resolution back to the knowledge bank.",
            bg=P_YELLOW, stripe=G_YELLOW,
        )

    # ── Session Usage ─────────────────────────────────────────────────────
    if cost_summary:
        pdf.ln(2)
        pdf._hrule(C_BORDER)
        pdf.ln(4)
        pdf._txt(C_MUTED, size=8, style="I")
        pdf.cell(W, 5, _s(f"Session usage:  {cost_summary}"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*C_TEXT)

    # 4. Serialise PDF bytes
    pdf_bytes = bytes(pdf.output())

    # 5. Upload directly to GCS for a stable public URL
    gcs_url = None
    bucket_name = os.environ.get("ARTIFACT_GCS_BUCKET")
    if bucket_name:
        from google.cloud import storage as gcs_storage
        _client = gcs_storage.Client()
        _blob = _client.bucket(bucket_name).blob(f"reports/{filename}")
        _blob.upload_from_string(data=pdf_bytes, content_type="application/pdf")
        gcs_url = f"https://storage.googleapis.com/{bucket_name}/reports/{filename}"

    # 6. Also save via ADK artifact system (populates the Artifacts panel in adk web UI)
    version = await tool_context.save_artifact(
        filename=filename,
        artifact=types.Part(
            inline_data=types.Blob(
                data=pdf_bytes,
                mime_type="application/pdf",
                display_name=filename,
            )
        ),
    )

    if gcs_url:
        message = f"PDF saved as '{filename}'. Download: {gcs_url}"
    else:
        message = f"PDF saved as '{filename}'. A download link has appeared in the chat."

    return {
        "filename": filename,
        "version":  version + 1,
        "gcs_url":  gcs_url,
        "message":  message,
    }
