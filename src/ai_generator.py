import logging

from openai import OpenAI

from src.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

def generate_application_draft(category: str, job_description: str) -> tuple[str, str]:
    """
    Generate a professional German application draft using OpenAI GPT-4o.
    Returns a tuple of (subject, body).
    """
    if not OPENAI_API_KEY:
        raise ValueError("Missing OPENAI_API_KEY environment variable.")

    client = OpenAI(api_key=OPENAI_API_KEY)

    cv_profile = """
    Name: Leni Pazhayakariyil Iype
    Location: Graz, Austria
    Status: Master's student
    Experience: KFC kitchen work, catering service, supermarket/warehouse work
    Languages: English (fluent), German (A2, actively improving)
    Availability: flexible — mornings, afternoons, evenings, weekends
    """

    prompt = f"""
You are an AI assistant helping Leni Pazhayakariyil Iype write a professional job application email.
Here is Leni's profile:
{cv_profile}

Job Category: {category}
Job Description:
{job_description}

Please generate a professional job application email in German.
Follow these rules strictly:
1. Write in German ONLY. No English translation.
2. The email body must be short, professional, direct, and under 130 words.
3. Mention relevant experience (e.g. KFC kitchen, catering, supermarket/warehouse),
   language skills (German A2, actively improving, and fluent English),
   and flexibility (mornings, afternoons, evenings, weekends).
4. Do NOT mention any file names of attachments in the body.
5. Do NOT write a long cover letter. Keep it clean and concise as a direct application email.
6. Return your output EXACTLY in the following format. Do not add any conversational text
   before or after, and do not use markdown code blocks for the formatting.

SUBJECT:
<one-line German subject>

EMAIL:
<German email body>
"""

    logger.info("Requesting application draft generation from GPT-4o...")

    system_message = (
        "You are a professional recruiting assistant specialized in "
        "writing brief, impactful job applications in German."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content.strip()
    logger.info("Draft successfully generated.")
    return parse_draft(content)

def parse_draft(draft_text: str) -> tuple[str, str]:
    """Parse subject and email body from raw draft text with robust fallbacks."""
    subject = "Bewerbung um eine Stelle"
    body = ""

    # Standardize headers to simplify parsing
    normalized = draft_text
    normalized = normalized.replace("BETREFF:", "SUBJECT:")
    normalized = normalized.replace("EMAIL-TEXT:", "EMAIL:")
    normalized = normalized.replace("E-MAIL:", "EMAIL:")
    normalized = normalized.replace("EMAIL BODY:", "EMAIL:")

    if "SUBJECT:" in normalized and "EMAIL:" in normalized:
        parts = normalized.split("SUBJECT:", 1)
        sub_parts = parts[1].split("EMAIL:", 1)
        subject = sub_parts[0].strip()
        body = sub_parts[1].strip()
    else:
        # Fallback if headings got completely omitted
        lines = [line.strip() for line in normalized.split("\n") if line.strip()]
        if lines:
            if lines[0].upper().startswith("SUBJECT:"):
                subject = lines[0][8:].strip()
                if not subject and len(lines) > 1:
                    # If SUBJECT: was on its own line, take the next line as subject
                    subject = lines[1]
                    body = "\n".join(lines[2:])
                else:
                    body = "\n".join(lines[1:])
            else:
                subject = lines[0]
                body = "\n".join(lines[1:])

            # Clean EMAIL: header prefix in the body if it got mixed in
            if body.upper().startswith("EMAIL:"):
                body = body[6:].strip()
            elif body.upper().startswith("TEXT:"):
                body = body[5:].strip()

    return subject, body
