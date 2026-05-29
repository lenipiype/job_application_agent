from src.ai_generator import parse_draft


def test_parse_draft_perfect_format():
    """Verify that perfect formatting is correctly parsed into subject and body."""
    draft = """SUBJECT:
Bewerbung als Küchenhilfe - Leni Pazhayakariyil Iype

EMAIL:
Sehr geehrte Damen und Herren,

hiermit bewerbe ich mich...
Mit freundlichen Grüßen,
Leni"""

    subject, body = parse_draft(draft)
    assert subject == "Bewerbung als Küchenhilfe - Leni Pazhayakariyil Iype"
    assert body.startswith("Sehr geehrte Damen und Herren,")
    assert body.endswith("Leni")

def test_parse_draft_german_headings():
    """Verify that German variant headings (e.g. BETREFF:) are correctly caught."""
    draft = """BETREFF:
Bewerbung als Servicekraft

EMAIL:
Sehr geehrtes Team,
ich interessiere mich für die Stelle..."""

    subject, body = parse_draft(draft)
    assert subject == "Bewerbung als Servicekraft"
    assert body == "Sehr geehrtes Team,\nich interessiere mich für die Stelle..."

def test_parse_draft_no_headings():
    """Verify that text lacking headings falls back to taking line 1 as subject
    and the rest as body.
    """
    draft = """Bewerbung als Allround-Hilfe
Sehr geehrte Damen und Herren,
ich bin Student in Graz..."""

    subject, body = parse_draft(draft)
    assert subject == "Bewerbung als Allround-Hilfe"
    assert body == "Sehr geehrte Damen und Herren,\nich bin Student in Graz..."

def test_parse_draft_inline_prefixes():
    """Verify robust parsing of inline layouts with embedded prefix markers."""
    draft = """SUBJECT: Bewerbung als Lagerhelfer
EMAIL: Sehr geehrter Herr...,
ich möchte mich gerne bewerben."""

    subject, body = parse_draft(draft)
    assert subject == "Bewerbung als Lagerhelfer"
    assert body == "Sehr geehrter Herr...,\nich möchte mich gerne bewerben."
