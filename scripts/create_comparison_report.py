"""Build a presentation report from the verified browser workflow evidence."""
from pathlib import Path
import json
from xml.sax.saxutils import escape
from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Flowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs' / 'browser-workflow'
OUT = ROOT / 'output' / 'pdf'
OUT.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('ReportArial', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ReportArialBold', 'C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFontFamily('ReportArial', normal='ReportArial', bold='ReportArialBold', italic='ReportArial', boldItalic='ReportArialBold')
high = json.loads((EVIDENCE / 'high-risk-C003.json').read_text(encoding='utf-8'))
buyer = json.loads((EVIDENCE / 'agent-results.json').read_text(encoding='utf-8'))
assert high['customer_id'] == 'C003' and buyer['customer_id'] == 'DEMO-IMPORT-001'
assert all(r['status'] == 'completed' and len(r['outputs']) == 9 for r in [high, buyer])
for r in [high, buyer]:
    assert len(r['outputs']['tracking']['events']) == 4

W, H = A4
WIDTH = W - 96
NAVY = colors.HexColor('#243449')
TEAL = colors.HexColor('#0C9278')
AMBER = colors.HexColor('#BD7D26')
MUTED = colors.HexColor('#5B6573')
LINE = colors.HexColor('#D9D9D9')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle', fontName='ReportArialBold', fontSize=25, leading=30, spaceAfter=12, textColor=colors.black))
styles.add(ParagraphStyle(name='ReportH1', fontName='ReportArialBold', fontSize=18, leading=23, spaceAfter=12, textColor=colors.black))
styles.add(ParagraphStyle(name='ReportH2', fontName='ReportArialBold', fontSize=12, leading=16, spaceBefore=14, spaceAfter=7, textColor=colors.black))
styles.add(ParagraphStyle(name='BodyTextReport', fontName='ReportArial', fontSize=10, leading=14.5, spaceAfter=9, textColor=colors.HexColor('#26313D')))
styles.add(ParagraphStyle(name='SmallReport', fontName='ReportArial', fontSize=8.4, leading=11.5, spaceAfter=7, textColor=MUTED))
styles.add(ParagraphStyle(name='CellReport', fontName='ReportArial', fontSize=9, leading=12, textColor=colors.HexColor('#26313D')))
styles.add(ParagraphStyle(name='CellHeader', fontName='ReportArialBold', fontSize=9, leading=12, textColor=colors.white))
styles.add(ParagraphStyle(name='CaptionReport', fontName='ReportArial', fontSize=8, leading=11, textColor=MUTED, spaceBefore=6, spaceAfter=9))

def p(text, style='BodyTextReport'):
    return Paragraph(text, styles[style])

def heading(text, first=False):
    return p(text, 'ReportH1' if first else 'ReportH2')

def table(headers, rows, widths, size=9):
    data = [[p(escape(str(c)), 'CellHeader') for c in headers]]
    data += [[p(escape(str(c)), 'CellReport') for c in row] for row in rows]
    result = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    result.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F5F8')]),
        ('GRID', (0, 0), (-1, -1), .5, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return result

class ScoreComparison(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = WIDTH, 122

    def draw(self):
        c = self.canv
        label_width, bar_width = 162, WIDTH - 218
        c.setFont('ReportArial', 8)
        for x, text, col in [(0, 'C003', AMBER), (86, 'DEMO-IMPORT-001', TEAL)]:
            c.setFillColor(col)
            c.rect(x, 109, 7, 7, fill=1, stroke=0)
            c.setFillColor(MUTED)
            c.drawString(x+12, 109, text)
        for label, vals, y in [('30 day inactivity score', [99.8, 38.37], 83), ('30 day purchase score', [2.23, 60.96], 34)]:
            c.setFont('ReportArialBold', 9)
            c.setFillColor(colors.black)
            c.drawString(0, y, label)
            for j, (value, col) in enumerate(zip(vals, [AMBER, TEAL])):
                yy = y - j*16
                c.setFillColor(colors.HexColor('#EDF0F3'))
                c.rect(label_width, yy-2, bar_width, 9, fill=1, stroke=0)
                c.setFillColor(col)
                c.rect(label_width, yy-2, bar_width*value/100, 9, fill=1, stroke=0)
                c.setFont('ReportArialBold', 9)
                c.drawRightString(WIDTH, yy-1, f'{value:.2f}%')

def screenshot(path, max_width, max_height):
    width, height = PILImage.open(path).size
    scale = min(max_width/width, max_height/height)
    return Image(str(path), width=width*scale, height=height*scale, hAlign='CENTER')

story = []
story += [p('Customer journey and risk comparison', 'ReportTitle'),
          p('JourneyGraph AI | C003 and DEMO-IMPORT-001 | 5 November 2026', 'SmallReport'),
          p('<b>C003 needs a re-engagement review; DEMO-IMPORT-001 merits a relevant product follow-up.</b> Both customers have four recorded interactions, but C003 stopped after browsing and has no purchase. The imported customer recently completed a $149 purchase. This case study demonstrates how temporal evidence supports different model scores and actions.'),
          p('All records are synthetic demonstration data. Prediction percentages are uncalibrated model scores, not verified real-world probabilities.', 'SmallReport'),
          table(['Comparison', 'C003', 'DEMO-IMPORT-001'], [
              ['Segment', 'Inactive', 'New buyers'],
              ['Recorded interactions', '4', '4'],
              ['Channels and transitions', 'Social; 0 transitions', 'Website and mobile; 1 transition'],
              ['Purchase history', '0 purchases; $0', '1 purchase; $149'],
              ['Days since latest activity', '161 completed days', '3 completed days'],
              ['Inactivity score and band', '99.80% | High', '38.37% | Low'],
              ['Purchase score and band', '2.23% | Low', '60.96% | Medium'],
              ['Recommended review', 'Re-engagement opportunity', 'Relevant product follow-up'],
              ['Priority', 'High', 'Normal'],
          ], [155, 163, WIDTH-318]),
          p('Recency is measured against the latest dataset event, 4 November 2026 at 19:20 UTC, rather than the report creation time.', 'CaptionReport'),
          heading('Prediction score comparison'), ScoreComparison(),
          p('Presentation takeaway: total activity counts can look similar while event sequence, recency, and purchase evidence point to very different engagement states.', 'SmallReport'), PageBreak()]

story += [heading('Recorded customer journeys', True),
          p('The following timelines use UTC event time. They reconstruct observed behavior; they do not establish the customer\'s intention or the cause of disengagement.'),
          heading('C003 browsing without a recorded purchase'),
          table(['Event time UTC', 'Interaction', 'Product', 'Channel'], [
              ['24 May 2026 11:43', 'Website visit', 'P005 Desk lamp', 'social'],
              ['24 May 2026 11:47', 'Product view', 'P005 Desk lamp', 'social'],
              ['26 May 2026 20:11', 'Website visit', 'P004 Everyday sneakers', 'social'],
              ['26 May 2026 20:15', 'Product view', 'P004 Everyday sneakers', 'social'],
          ], [123, 105, 170, WIDTH-398]),
          p('Evidence IDs EVT000107 to EVT000110. The two browsing visits span 2.36 days. There are no cart or purchase events, and no events in the final 30-day feature window.', 'CaptionReport'),
          p('<b>Interpretation.</b> C003 disengaged after browsing. Calling this cart abandonment would be unsupported because no cart was recorded. The event channel is social even though the interaction type is website_visit; the report preserves the stored fields.'),
          heading('DEMO IMPORT 001 a completed purchase journey'),
          table(['Event time UTC', 'Interaction', 'Product', 'Channel'], [
              ['1 Nov 2026 10:00', 'Website visit', 'P001 Studio headphones', 'website'],
              ['1 Nov 2026 10:04', 'Product view', 'P001 Studio headphones', 'website'],
              ['1 Nov 2026 10:08', 'Add to cart', 'P001 Studio headphones', 'mobile'],
              ['1 Nov 2026 10:12', 'Purchase $149', 'P001 Studio headphones', 'mobile'],
          ], [123, 105, 170, WIDTH-398]),
          p('Evidence IDs DEMO-IMPORT-E01 to DEMO-IMPORT-E04. The sequence lasts 12 minutes and contains one website-to-mobile transition.', 'CaptionReport'),
          p('<b>Interpretation.</b> The recorded cart was followed by a purchase. P001 appears in both the product view and purchase evidence, making it a relevant subject for a human-reviewed follow-up.'),
          heading('Temporal graph verification'),
          p('For DEMO-IMPORT-001, the browser showed 5 entities and 8 relationships: one entity fact and one channel fact for each event. A valid-at query before the journey returned zero facts. A known-at query before import also returned zero facts, demonstrating the separate event-time and transaction-time filters.'),
          p('Each purchase fact retains the source event ID, valid-from timestamp, server-recorded timestamp, channel, and synthetic-demo provenance. An open-ended event fact remains in the cumulative graph; it does not mean the activity continues indefinitely.', 'SmallReport'), PageBreak()]

story += [heading('Predictions and recommended actions', True),
          p('Both customers were scored by the same model family and evaluated population history. Inactivity means no tracked events in the next 30 days. Conversion means a purchase in the next 30 days, including a possible repeat purchase for the imported customer.'),
          heading('Why the scores differ'),
          p('<b>C003.</b> About 162 days of recency and zero events, purchases, carts, support events, or active channels in the final 30-day feature window. Recency is the largest positive contribution to the inactivity model and the largest negative contribution to the purchase model.'),
          p('<b>DEMO-IMPORT-001.</b> About 3.38 days of recency, four recent events, one purchase, one cart event, and two active channels. This produces a lower inactivity score and a higher purchase score. Feature contributions explain the fitted model, not causal effects.'),
          table(['Evaluated target', 'ROC AUC', 'Balanced accuracy', 'Brier score'], [
              ['30 day inactivity', '0.8550', '77.60%', '0.1557'],
              ['30 day purchase', '0.7796', '75.56%', '0.1813'],
          ], [185, 90, 125, WIDTH-400]),
          p('Evaluation: 120 training customers and 120 holdout customers. Training features end 5 September 2026; their 30-day labels end 5 October. Holdout features end 5 October; outcomes end 4 November. The exact cutoffs are 19:20 UTC. Both models use StandardScaler and balanced logistic regression.', 'CaptionReport'),
          p('ROC AUC measures ranking separation; balanced accuracy averages sensitivity across the two classes; lower Brier scores indicate smaller squared probability errors. These metrics assess a single synthetic temporal holdout, not production validity.', 'SmallReport'),
          heading('C003 recommendation'),
          p('<b>Review re-engagement opportunity | High priority.</b> The rule triggers because recency exceeds 30 days. The proposal cites EVT000107 to EVT000110 and the observed products P005 and P004. The 99.80% inactivity score supports the risk comparison, but it does not directly choose this action.'),
          heading('DEMO IMPORT 001 recommendation'),
          p('<b>Review relevant product follow-up | Normal priority.</b> The customer is recently active and the latest cart has a subsequent purchase. The follow-up rule therefore applies instead of inactivity re-engagement or cart assistance. The proposal cites DEMO-IMPORT-E01 to DEMO-IMPORT-E04 and product P001.'),
          heading('Human review and limits'),
          p('Both actions remain pending_human_review. No message or intervention was sent, and expected uplift was not estimated. Scores are uncalibrated and have no uncertainty intervals. Customers can appear in both time windows; missing tracking can resemble churn. C003 never purchased, so high inactivity should not be described as confirmed loss of a paying customer.', 'SmallReport'), PageBreak()]

story += [heading('Browser evidence and execution trace', True),
          p('Matching screenshot excerpts show the final recorded actions for each customer. The browser displays local India time; the chronology tables on page 2 use UTC. Screenshots preserve the original application display.'),
          table(['C003 final browsing events', 'DEMO-IMPORT-001 final purchase events'], [], [WIDTH/2, WIDTH/2]), Spacer(1,8)]
left = screenshot(EVIDENCE/'journey-C003-end.jpg', WIDTH/2-12, 235)
right = screenshot(EVIDENCE/'journey-DEMO-IMPORT-001-end.jpg', WIDTH/2-12, 235)
image_table = Table([[left, right]], colWidths=[WIDTH/2, WIDTH/2], hAlign='LEFT')
image_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
story += [image_table,
          p('Figure 1 C003 ends at a product view without a recorded cart or purchase. Figure 2 DEMO-IMPORT-001 ends with add to cart and purchase. The full four-event timelines are reproduced on page 2.', 'CaptionReport'),
          heading('Verified agent executions'),
          p('All nine agents completed in both runs: profiling, tracking, temporal graph, behavior, segmentation, prediction, recommendation, insight generation, and orchestration. Insight generation used the labeled local evidence summary; no external LLM was called.', 'SmallReport'),
          table(['Customer', 'Status', 'Completed agents', 'Execution time IST'], [['C003', 'Completed', '9 of 9', '09:54:07 to 09:54:10'], ['DEMO-IMPORT-001', 'Completed', '9 of 9', '09:48:26 to 09:48:29']], [145, 85, 105, WIDTH-335]), Spacer(1,10),
          p(f'C003 execution {high["id"]}<br/>DEMO-IMPORT-001 execution {buyer["id"]}', 'SmallReport'),
          p('Source evidence: docs/browser-workflow/high-risk-C003.json and agent-results.json; linked sample event files; product catalog in data/samples/products.csv. Screenshots captured from the running local application on 5 November 2026.', 'SmallReport')]

def furniture(c, doc):
    c.saveState()
    c.setFont('ReportArial', 8)
    c.setFillColor(MUTED)
    c.drawString(48, 27, 'JourneyGraph AI | Synthetic customer comparison | 5 November 2026')
    c.drawRightString(W-48, 27, str(doc.page))
    c.restoreState()

target = OUT/'JourneyGraph_C003_vs_DEMO_IMPORT_001.pdf'
doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=48, leftMargin=48, topMargin=43, bottomMargin=43, title='Customer journey and risk comparison', author='JourneyGraph AI', subject='Synthetic customer journey evidence and prediction comparison')
doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
print(target)
