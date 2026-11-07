"""Build docs/StrayWatch-Solution-Ideation.pdf."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "StrayWatch-Solution-Ideation.pdf"
pdfmetrics.registerFont(TTFont("Segoe", "C:/Windows/Fonts/segoeui.ttf"))
pdfmetrics.registerFont(TTFont("SegoeB", "C:/Windows/Fonts/segoeuib.ttf"))

TEAL = colors.HexColor("#2a8f97")
INK = colors.HexColor("#1b2430")
GREY = colors.HexColor("#5b6773")
LIGHT = colors.HexColor("#eef4f5")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="SegoeB", fontSize=28, leading=34, textColor=INK, spaceAfter=6)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontName="Segoe", fontSize=13, textColor=TEAL, alignment=TA_CENTER, leading=17)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="SegoeB", fontSize=15, textColor=TEAL, spaceBefore=12, spaceAfter=5)
P = ParagraphStyle("P", parent=ss["Normal"], fontName="Segoe", fontSize=10.5, leading=15, textColor=INK, spaceAfter=5)
SMALL = ParagraphStyle("S", parent=P, fontSize=9, textColor=GREY)
CELL = ParagraphStyle("C", parent=P, fontSize=9.5, leading=13, spaceAfter=0)
CELLB = ParagraphStyle("CB", parent=CELL, fontName="SegoeB")


def bullets(items):
    return ListFlowable([ListItem(Paragraph(t, P), leftIndent=12) for t in items], bulletType="bullet",
                        start="•", leftIndent=12, bulletFontName="Segoe")


def table(rows, widths, header=True):
    data = [[Paragraph(c, CELLB if (header and i == 0) else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3da")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), LIGHT))
    t.setStyle(TableStyle(style))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Segoe", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(18 * mm, 10 * mm, "StrayWatch · Solution Ideation · Flip the Switch Hackathon 2026")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Meenakshi Satpathy, BIT Mesra · page {doc.page}")
    canvas.restoreState()


s = []
s.append(Image(str(ROOT / "docs" / "cover.png"), width=150 * mm, height=150 * mm * 720 / 1280))
s.append(Spacer(1, 8))
s.append(Paragraph("StrayWatch: Solution Ideation", H1))
s.append(Paragraph("Rescue dispatch for stray animals on Indian roads, run by AI agents and people in one team chat", SUB))
s.append(Spacer(1, 10))
s.append(table([
    ["Hackathon", "Flip the Switch (WeMakeDevs × DevTools Academy × Switch AI), Nov 4–7, 2026"],
    ["Track", "Track 01: Best Business Workflow"],
    ["Builder", "Meenakshi Satpathy, BIT Mesra, Ranchi (solo)"],
    ["Code", "github.com/meenakshisatpathy20-del/SWITCH-AI"],
], [32 * mm, 142 * mm], header=False))

s.append(Paragraph("1. The theme", H2))
s.append(Paragraph(
    "The challenge: <b>turn your solo agent into a teammate</b>. Build a workflow where an AI agent and the people "
    "in a team chat get a real task done together, connected by <b>Switch</b>: open-source infrastructure that "
    "turns every chat channel into a <i>room</i> that agents join like any other teammate.", P))

s.append(Paragraph("2. Why I chose this problem", H2))
s.append(Paragraph(
    "On my way to college in Ranchi, I saw an injured dog lying on the road while vehicles kept passing it. "
    "Nobody called anyone, because nobody knew who to call. That moment is why I started StrayWatch.", P))

s.append(Paragraph("3. The problem", H2))
s.append(Paragraph(
    "Stray cattle and dogs on busy roads block traffic, cause accidents and are themselves injured or killed. "
    "In 2024, Odisha recorded <b>437 deaths from 903 animal–vehicle collisions</b>; Haryana has seen "
    "<b>900+ deaths in five years</b> from stray-cattle accidents; in Bengaluru a biker died after being chased by "
    "stray dogs.", P))
s.append(Paragraph(
    "Police, municipal teams, NGOs and volunteers all exist. The real problem is that <b>help arrives too late and "
    "works blind</b>:", P))
s.append(bullets([
    "Reports arrive as scattered calls and WhatsApp forwards, often with no exact location",
    "The same animal is reported again and again by different people",
    "Nobody knows who is handling a case, so cases get lost in the scroll",
    "Nobody records where and when it happens, so the same road is dangerous again tomorrow at 6 PM",
]))
s.append(Paragraph(
    "This is a <b>team coordination problem inside a chat app</b>, which is exactly what Switch is built for.", P))

s.append(Paragraph("4. The idea", H2))
s.append(Paragraph(
    "<b>StrayWatch is ambulance dispatch for animals on roads.</b> One Telegram group becomes a Switch room. "
    "Citizens and responders are in it as people; three AI agents are in it as teammates. A citizen only posts "
    "what they see. The agents and responders do the rest, in the open, until the case is closed with proof.", P))
s.append(table([
    ["Step", "Who", "What happens"],
    ["1. Triage", "sw-triage (agent)", "Reads the report (text/photo, Hindi or English), asks for the location if missing, files a case, sets urgency HIGH / CHECK / LOW, catches duplicates"],
    ["2. Dispatch", "sw-dispatch (agent)", "Tags the right responder: traffic police for blocked lanes, municipal team for cattle, NGO for injuries, ABC team for aggressive dogs"],
    ["3. Accept", "Responder (person)", "Replies \"accept SW-0046\", so everyone sees who owns the case"],
    ["4. Escalate", "sw-watch (custom agent)", "If nobody accepts within 10 minutes, the duty coordinator is tagged"],
    ["5. Close with proof", "Responder + sw-dispatch", "The responder posts a photo; dispatch looks at it and closes the case only if the animal is helped and the road is clear"],
    ["6. Prevent", "sw-hotspot (agent)", "Turns the case history into action: \"Ratu Road, 6–7 PM, cattle: send the cattle team at 5 PM, before the rush\""],
], [28 * mm, 38 * mm, 108 * mm]))

s.append(Paragraph("5. Why Switch is central", H2))
s.append(Paragraph("Remove Switch and StrayWatch stops working. The Switch room <i>is</i> the dispatch system:", P))
s.append(bullets([
    "<b>Messaging bridge</b>: people report and respond from Telegram, the app they already use; nobody installs anything",
    "<b>Agents as teammates</b>: three agents with distinct jobs post in the same conversation as humans",
    "<b>Agent-to-agent handoff in the open</b>: triage hands cases to dispatch by name, so people can see and correct every step",
    "<b>Main agent + \"anyone\" addressing</b>: citizens don't need agent names or a Switch account",
    "<b>Attachments reach agents</b>: this is what makes \"close only with photo proof\" possible",
    "<b>Agent protocol</b>: a custom Python agent (sw-watch) keeps the clock, because Switch has no scheduler",
    "<b>Templates</b>: the whole workflow is one YAML file another city can reuse",
]))

s.append(Paragraph("6. Design principles", H2))
s.append(bullets([
    "<b>Code decides urgency, AI extracts facts.</b> Rules live in a tested script, so the same report always gets the same urgency",
    "<b>No invented data.</b> Agents never guess a location, a case id or a handle, and refuse to recreate a missing case from memory",
    "<b>Animal welfare first.</b> Aggressive dogs go to ABC (sterilisation &amp; vaccination) teams, never \"removal\"; reporters are told not to approach injured animals",
    "<b>Honest data.</b> Demo history is clearly labelled as simulated, and kept separate from live cases",
]))

s.append(Paragraph("7. Who uses it", H2))
s.append(table([
    ["User", "Pain today", "Why they use StrayWatch"],
    ["NGOs, vets, rescuers", "Cases arrive scattered, without a location", "One clean, located, urgency-sorted queue"],
    ["Feeders, caring citizens", "They post, but nothing happens", "Their report reaches a responder and they see the result"],
    ["Traffic control", "Hears late, from jams and complaints", "Only real, high-impact alerts"],
    ["Municipal teams", "No data on where or when", "Weekly hotspot list of roads and times"],
], [40 * mm, 62 * mm, 72 * mm]))

s.append(Paragraph("8. What is built (working prototype)", H2))
s.append(bullets([
    "Three Switch agents (Claude Code) working in a live Telegram room; sw-watch, a custom escalation agent built on the Switch agent protocol, is included (dispatch also runs the same escalation check whenever it is addressed)",
    "Case ledger with deterministic urgency, routing, duplicate merge, accept / close-with-proof and escalation",
    "Hotspot report with recommended actions, on 45 simulated cases on real Ranchi roads",
    "8 automated tests, MIT licence, step-by-step setup in the README, and a demo video",
]))

s.append(Paragraph("9. Impact we would measure in a pilot", H2))
s.append(bullets([
    "Time from report to a responder accepting, and to the road being cleared",
    "Share of injured-animal cases closed with photo proof",
    "Fewer repeat cases on hotspot roads after teams act before the rush",
]))

s.append(Paragraph("10. Roadmap", H2))
s.append(bullets([
    "<b>Camera agent</b>: YOLOv8 on existing traffic cameras flags animals that stay inside a lane or lie still, and posts them into the room like any citizen report",
    "Separate public <i>Reports</i> and private <i>Responders</i> rooms, linked in Switch, so exact locations go only to verified responders",
    "WhatsApp intake and Hindi / Kannada voice notes",
    "Pilot in Ranchi, then scale to Bengaluru through municipal and Smart City road-safety programmes",
]))
s.append(Spacer(1, 14))
s.append(Paragraph("<b>Help the animal, clear the road.</b>", ParagraphStyle("end", parent=P, alignment=TA_CENTER, fontSize=13, textColor=TEAL)))
s.append(Paragraph("Sources for statistics: The Statesman (Odisha 2024 data), PTI / Business Standard (Haryana), India TV and Deccan Herald (Bengaluru).", SMALL))

SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=18 * mm, title="StrayWatch: Solution Ideation", author="Meenakshi Satpathy").build(
    s, onFirstPage=footer, onLaterPages=footer)
print(OUT)
