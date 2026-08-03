import json
import os
import smtplib
import urllib.request
import urllib.error

from collections import OrderedDict
from datetime import datetime, timezone
from email.mime.text import MIMEText

from flask import Flask, request, jsonify
from google.oauth2.service_account import Credentials
import gspread


app = Flask(__name__)


SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")

# --- Groq API config -----------------------------------------------------
# Add GROQ_API_KEY to your environment variables (Vercel project
# settings, etc). Get a free key at https://console.groq.com/keys
# If it's missing, or the API call fails for any reason, submissions
# still succeed and the email falls back to a plain question/answer
# listing instead of a narrative summary.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# openai/gpt-oss-120b is Groq's current recommended replacement for the
# retired llama-3.3-70b-versatile model. Override with GROQ_MODEL if
# you'd rather use something else (e.g. "llama-3.1-8b-instant" for max
# speed, or check console.groq.com/docs/models for the current list).
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


CAMPAIGNS = {

    "recruitment": {
        "sheet": "Recruitment Readiness",
        "email": "promise.nabaasa@welcometoebc.com",
        "title": "Recruitment Readiness Assessment"
    },

    "revenue": {
        "sheet": "Revenue Growth",
        "email": "makishe@welcometoebc.com",
        "title": "Revenue Growth Assessment"
    },

    "workplace": {
        "sheet": "Workplace Performance",
        "email": "christian@welcometoebc.com",
        "title": "Workplace Performance Assessment"
    },

    "mens": {
        "sheet": "Men's Wellbeing",
        "email": "johnguest@welcometoebc.com",
        "title": "Men's Workplace Wellbeing Assessment"
    },

    "executive": {
        "sheet": "Year-End Organizational",
        "email": "mercy.kemirembe@welcometoebc.com",
        "title": "Year-End Organizational Assessment"
    }

}


# --- Question text, per campaign ---------------------------------------
# Maps the raw form field name to the actual question wording, so the
# email (and the AI summary prompt) can refer to what was really asked
# instead of a snake_case field key. Order is preserved so the "Full
# Responses" section in the email reads in the same order as the form.

QUESTIONS = {

    "recruitment": OrderedDict([
        ("recruitment_process_description", "When an employee resigns, how would you describe the recruitment process that usually follows?"),
        ("vacancy_duration_frequency", "How often do vacancies remain open longer than originally expected?"),
        ("management_time_impact", "Does recruitment take more management time than it should?"),
        ("hr_strategic_distraction", "Do recruitment activities ever take the HR team away from higher-value strategic work?"),
        ("wrong_fit_hiring_frequency", "Have they ever hired someone who looked perfect in interviews but turned out to be the wrong fit?"),
        ("candidate_attraction_confidence", "How confident are they that they're consistently attracting the best candidates?"),
        ("volume_application_struggle", "How often do they receive hundreds of applications but still struggle to identify the right candidate?"),
        ("repeat_recruitment_frequency", "Have they ever had to repeat recruitment because the first hire didn't work out?"),
        ("operational_impact_of_delays", "Have recruitment delays ever affected business operations or sales performance?"),
        ("value_of_faster_recruitment", "Would cutting recruitment time by 50% create value for them?"),
        ("know_replacement_cost", "Do they know the true cost of replacing one employee?"),
        ("growth_expectations", "Is the organization expecting growth over the next 12 months?"),
        ("preparedness_for_resignation", "If a critical employee resigned tomorrow, how prepared would the organization be?"),
        ("talent_pipeline_status", "Do they currently have a ready talent pipeline for key positions?"),
        ("pre_qualified_candidates_value", "How valuable would pre-qualified candidates (ready before a vacancy occurs) be to them?"),
        ("impact_of_improved_process", "If recruitment became faster and more predictable, what impact would that have on the organization?"),
        ("interest_in_pipeline_model", "Are they interested in exploring a model where recruitment begins before vacancies happen?"),
    ]),

    "revenue": OrderedDict([
        ("q1_sales_performance", "Is sales performance consistently meeting or exceeding revenue targets?"),
        ("q2_sales_training", "After sales training, does the team quickly return to old habits?"),
        ("q3_sales_motivation", "Is the sales team highly motivated and bringing positive energy to the business?"),
        ("q4_sales_isolation", "Has sales become isolated from the rest of the organization instead of working as one commercial team?"),
        ("q5_market_difficult", "When sales decline, is 'the market is difficult' the most common explanation?"),
        ("q6_lower_prices", "Does the sales team frequently ask for lower prices to remain competitive?"),
        ("q7_accountability", "Is there a sales culture where accountability is stronger than excuses?"),
        ("q8_revenue_predictability", "Is revenue predictable enough that leadership can confidently forecast future performance?"),
        ("q9_sales_managers", "Do sales managers spend more time coaching than chasing numbers?"),
        ("q10_high_performers", "Does winning or losing business depend too heavily on a few high-performing individuals?"),
        ("q11_sales_process", "Is the sales process consistent, regardless of who is speaking to the customer?"),
        ("q12_revenue_responsibility", "Do people believe revenue growth is everyone's responsibility, not just sales'?"),
        ("q13_execution", "Do they lose more opportunities to poor execution than to competitors?"),
        ("q14_salesperson_dependency", "If their best salesperson resigned tomorrow, would the business keep growing without major disruption?"),
        ("q15_revenue_opportunity", "Which single thing would have the greatest impact on revenue over the next 12 months?"),
    ]),

    "workplace": OrderedDict([
        ("q1_office_environment", "Does the current office environment support the way teams work today?"),
        ("q2_collaboration", "Does the office encourage collaboration between departments?"),
        ("q3_culture_brand", "Does the workplace reflect the organization's culture and brand?"),
        ("q4_employee_experience", "Do employees enjoy coming to the office?"),
        ("q5_workplace_design", "Do they believe workplace design has a direct impact on employee performance?"),
        ("q6_office_layout", "Does the office layout support productivity rather than creating distractions?"),
        ("q7_workplace_review", "Do they regularly review whether the workplace still meets business needs?"),
        ("q8_meeting_spaces", "Do meeting spaces support effective collaboration and decision-making?"),
        ("q9_workplace_improvement", "If they could improve one thing about the workplace today, what would it be?"),
        ("q10_repairs_maintenance", "Does the office currently require any repairs or maintenance?"),
        ("q11_refurbishment_areas", "Are there areas of the office they'd like to refurbish or redesign?"),
        ("q12_last_renovation", "How long since the office was last renovated or significantly upgraded?"),
        ("q13_planned_improvements", "Are they planning any workplace improvements in the next 12 months?"),
        ("q14_improvement_barrier", "What's currently preventing those improvements?"),
        ("q15_site_visit", "Would they like a complimentary Workplace Performance Site Visit from an EBC designer?"),
    ]),

    "mens": OrderedDict([
        ("q1_leadership_invests", "Does the organization intentionally invest in the wellbeing and development of male employees?"),
        ("q2_wellbeing_influences_performance", "Do they believe men's wellbeing directly influences organizational performance?"),
        ("q3_supporting_men_in_strategy", "Is supporting men included in the employee wellbeing strategy?"),
        ("q4_senior_leadership_support", "Does senior leadership actively support initiatives focused on men's wellbeing?"),
        ("q5_comfort_seeking_support", "Do male employees feel comfortable seeking support when facing personal challenges?"),
        ("q6_healthy_conversations", "Does the workplace encourage healthy conversations around mental and emotional wellbeing?"),
        ("q7_positive_role_models", "Is there a culture that promotes positive male role models and mentorship?"),
        ("q8_develops_beyond_technical", "Does the organization intentionally develop men beyond technical or professional skills?"),
        ("q9_current_initiatives", "Which initiatives currently exist within the organization?"),
        ("q10_initiative_frequency", "How often does the organization run employee wellbeing or team development initiatives?"),
        ("q11_dedicated_mens_initiative", "Do they currently have a dedicated Men's Wellness or Men's Development initiative?"),
        ("q12_challenges", "Which challenges are currently affecting the male workforce?"),
        ("q13_desired_outcomes", "Which outcomes would they most like to improve?"),
        ("q14_biggest_challenge", "In their own words, what's currently the biggest challenge facing the men in the organization?"),
        ("q15_partnership_interest", "Would they consider an Annual Men's Development & Workplace Wellbeing Partnership?"),
        ("q16_services_of_interest", "Which services would be of greatest interest?"),
        ("q17_strategy_session", "Would they like a complimentary Organizational Men's Wellbeing Strategy Session?"),
    ]),

    "executive": OrderedDict([
        ("q1_review_scheduled", "Has leadership scheduled time to formally review this year's organizational performance?"),
        ("q2_measured_performance", "Have they measured performance against the goals set at the start of the year?"),
        ("q3_aligned_priorities", "Is leadership aligned on the organization's priorities for next year?"),
        ("q4_key_lessons", "Have they identified the key lessons from this year's successes and challenges?"),
        ("q5_priorities_discussed", "Have next year's strategic priorities already been discussed?"),
        ("q6_performance_description", "How would they describe the organization's performance this year?"),
        ("q7_focus_areas", "Which business areas would they most like leadership to focus on during an Executive Strategy Retreat?"),
        ("q8_employees_understand_direction", "Do employees clearly understand the organization's direction for next year?"),
        ("q9_recognize_achievements", "Do they intentionally recognize and celebrate employee achievements?"),
        ("q10_employee_morale", "Does employee morale remain positive approaching year end?"),
        ("q11_teams_engaged", "Do teams remain engaged and motivated?"),
        ("q12_departments_collaborate", "Do departments collaborate effectively across the organization?"),
        ("q13_desired_outcomes", "Which outcomes would they like an End-of-Year Team Experience to achieve?"),
        ("q14_strategy_retreat_planned", "Has the organization already planned an Executive Strategy Retreat?"),
        ("q15_team_experience_planned", "Has the organization planned an End-of-Year Team Experience?"),
        ("q16_preferred_month", "Approximately when would they like to hold these activities?"),
        ("q17_executive_count", "Approximately how many employees would participate?"),
        ("q18_duration_preference", "Preferred format for these activities?"),
        ("q19_venue_preference", "Preferred venue?"),
        ("q20_strategy_session", "Would they like a complimentary Organizational Strategy Session with an EBC consultant?"),
        ("q21_biggest_opportunity", "What's the biggest opportunity they'd like the organization to capitalize on before year end?"),
        ("q22_additional_info", "Anything else they'd like EBC to know about the organization or its objectives?"),
    ]),

}


# Various forms use different field names for the same kind of contact
# info. This maps each alias to a friendly display label.
CONTACT_FIELD_LABELS = OrderedDict([
    ("full_name", "Name"),
    ("respondent_name", "Name"),
    ("position", "Position"),
    ("department", "Department"),
    ("organization", "Organization"),
    ("industry", "Industry"),
    ("number_of_employees", "Number of Employees"),
    ("male_employees", "Approx. Male Employees"),
    ("office_locations", "Office Location(s)"),
    ("location", "Location"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("phone_number", "Phone"),
    ("telephone", "Phone"),
])


def get_cors_headers():

    return {

        "Access-Control-Allow-Origin": "*",

        "Access-Control-Allow-Methods": "POST, OPTIONS",

        "Access-Control-Allow-Headers": "Content-Type, Accept",

    }


def get_sheets_client():

    if not GOOGLE_CREDENTIALS:

        raise ValueError(
            "GOOGLE_CREDENTIALS environment variable is not set."
        )

    creds_info = json.loads(
        GOOGLE_CREDENTIALS
    )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets"
    ]

    credentials = Credentials.from_service_account_info(
        creds_info,
        scopes=scopes
    )

    return gspread.authorize(credentials)


def parse_form_data():

    data = {}

    for key in request.form.keys():

        values = request.form.getlist(key)

        if len(values) > 1:

            data[key] = ", ".join(values)

        else:

            data[key] = values[0] if values else ""

    return data


def get_or_create_worksheet(spreadsheet, title):

    try:

        return spreadsheet.worksheet(title)

    except gspread.WorksheetNotFound:

        return spreadsheet.add_worksheet(
            title=title,
            rows=1000,
            cols=60
        )


def append_row_with_headers(worksheet, data):

    headers = worksheet.row_values(1)

    if not headers:

        headers = list(data.keys())

        worksheet.append_row(headers)

    row = [
        data.get(header, "")
        for header in headers
    ]

    worksheet.append_row(row)


def extract_contact_info(data):
    """Pull out name/org/email/etc, using whichever field names this
    particular form happened to use, and return an ordered dict of
    friendly-label -> value (skipping anything blank)."""

    contact = OrderedDict()

    for field, label in CONTACT_FIELD_LABELS.items():

        value = data.get(field, "").strip()

        if value and label not in contact:

            contact[label] = value

    return contact


def extract_qa_pairs(campaign, data):
    """Return a list of (question_text, answer) for every question this
    campaign's form actually asked and the respondent actually answered."""

    questions = QUESTIONS.get(campaign, OrderedDict())

    pairs = []

    for field, question_text in questions.items():

        value = data.get(field, "").strip()

        if value:

            pairs.append((question_text, value))

    return pairs


def call_groq(prompt, max_tokens=700):

    if not GROQ_API_KEY:

        raise RuntimeError("GROQ_API_KEY is not set")

    payload = json.dumps({

        "model": GROQ_MODEL,

        "max_tokens": max_tokens,

        "messages": [
            {"role": "user", "content": prompt}
        ]

    }).encode("utf-8")

    req = urllib.request.Request(

        GROQ_API_URL,

        data=payload,

        headers={

            "Content-Type": "application/json",

            "Authorization": f"Bearer {GROQ_API_KEY}",

        },

        method="POST"

    )

    with urllib.request.urlopen(req, timeout=30) as response:

        result = json.loads(response.read().decode("utf-8"))

    choices = result.get("choices", [])

    if not choices:

        raise RuntimeError(f"Groq returned no choices: {result}")

    return choices[0].get("message", {}).get("content", "").strip()


def generate_narrative_summary(campaign_info, contact, qa_pairs):
    """Ask Claude to turn the raw Q&A into a short narrative paragraph
    describing how the respondent sees their organization, written for
    a salesperson who wasn't the one filling out the form."""

    if not qa_pairs:

        return None

    contact_lines = "\n".join(
        f"{label}: {value}" for label, value in contact.items()
    ) or "(no contact details provided)"

    qa_lines = "\n".join(
        f"Q: {question}\nA: {answer}" for question, answer in qa_pairs
    )

    prompt = f"""You are helping a sales team at EBC quickly understand a
prospect who just completed the "{campaign_info['title']}" self-assessment
on their website. Someone else on the team will read your summary before
following up, so write it as if briefing a colleague — not as a report to
the prospect.

Contact details:
{contact_lines}

Their answers:
{qa_lines}

Write a short narrative summary (roughly 120-200 words) in the third
person that:
- Uses their name and organization naturally where it reads well
- Describes, in plain language, how they seem to feel about this topic
  based on their answers (their strengths, pain points, and any specific
  numbers or comments they gave)
- Notes anything relevant to their willingness to move forward (e.g. if
  they asked for a site visit, strategy session, or expressed interest
  in a new model/partnership)
- Ends with a one-line "Suggested next step:" for the sales rep

Only use what's actually in the answers above — don't invent details.
Write plain prose paragraphs (no headers, no bullet list except the final
"Suggested next step:" line). Do not include a preamble like "Here is a
summary" — start directly with the narrative."""

    return call_groq(prompt)


def build_qa_appendix(qa_pairs):

    if not qa_pairs:

        return ""

    lines = ["Full Responses", "-" * 40]

    for question, answer in qa_pairs:

        lines.append(f"Q: {question}")
        lines.append(f"A: {answer}")
        lines.append("")

    return "\n".join(lines)


def build_email_body(campaign_info, contact, qa_pairs, data):

    contact_block = "\n".join(
        f"{label}: {value}" for label, value in contact.items()
    ) or "(no contact details provided)"

    header = (
        f"New EBC Business Assessment Submission\n\n"
        f"Assessment: {campaign_info['sheet']}\n"
        f"Submitted: {data.get('submission_timestamp', '')}\n\n"
        f"{contact_block}\n"
    )

    try:

        narrative = generate_narrative_summary(campaign_info, contact, qa_pairs)

    except Exception as e:

        narrative = None

        print(f"Groq summary generation failed: {e}")

    if narrative:

        summary_block = f"Summary\n{'-' * 40}\n{narrative}\n"

    else:

        summary_block = (
            "Summary\n" + "-" * 40 +
            "\n(AI summary unavailable — see full responses below.)\n"
        )

    appendix = build_qa_appendix(qa_pairs)

    return f"{header}\n{summary_block}\n{appendix}"


def send_notification_email(
    recipient,
    campaign_info,
    contact,
    qa_pairs,
    data
):

    sender = os.environ.get("SMTP_EMAIL")

    password = os.environ.get("SMTP_PASSWORD")

    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")

    smtp_port = int(os.environ.get("SMTP_PORT", 465))

    name = contact.get("Name", "")

    org = contact.get("Organization", "")

    who = f"{name} ({org})" if name and org else (name or org or "New submission")

    subject = f"{campaign_info['sheet']}: {who}"

    body = build_email_body(campaign_info, contact, qa_pairs, data)

    message = MIMEText(body)

    message["Subject"] = subject

    message["From"] = sender

    message["To"] = recipient

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:

        server.login(sender, password)

        server.send_message(message)


@app.route(
    "/api/submit",
    methods=["POST", "OPTIONS"]
)
def submit():

    if request.method == "OPTIONS":

        return "", 204, get_cors_headers()

    try:

        data = parse_form_data()

        campaign = data.get("campaign", "general")

        if campaign not in CAMPAIGNS:

            raise ValueError(f"Invalid campaign: {campaign}")

        campaign_info = CAMPAIGNS[campaign]

        data["submission_timestamp"] = (
            datetime.now(timezone.utc).isoformat()
        )

        client = get_sheets_client()

        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        worksheet = get_or_create_worksheet(
            spreadsheet,
            campaign_info["sheet"]
        )

        append_row_with_headers(worksheet, data)

        contact = extract_contact_info(data)

        qa_pairs = extract_qa_pairs(campaign, data)

        send_notification_email(
            recipient=campaign_info["email"],
            campaign_info=campaign_info,
            contact=contact,
            qa_pairs=qa_pairs,
            data=data
        )

        return (

            jsonify({
                "success": True,
                "message": "Assessment submitted successfully"
            }),

            200,

            get_cors_headers()

        )

    except Exception as e:

        return (

            jsonify({
                "success": False,
                "error": str(e)
            }),

            500,

            get_cors_headers()

        )


@app.route(
    "/api/health",
    methods=["GET"]
)
def health():

    return jsonify({"status": "healthy"}), 200


@app.route(
    "/api/debug",
    methods=["GET"]
)
def debug():

    routes = []

    for rule in app.url_map.iter_rules():

        routes.append({

            "rule": str(rule),

            "methods": sorted(
                m for m in rule.methods
                if m not in ("HEAD", "OPTIONS")
            )

        })

    return jsonify({

        "status": "debug ok",

        "registered_routes": routes,

        "env": {

            "SPREADSHEET_ID_set": bool(SPREADSHEET_ID),

            "GOOGLE_CREDENTIALS_set": bool(GOOGLE_CREDENTIALS),

            "SMTP_EMAIL_set": bool(os.environ.get("SMTP_EMAIL")),

            "SMTP_PASSWORD_set": bool(os.environ.get("SMTP_PASSWORD")),

            "GROQ_API_KEY_set": bool(GROQ_API_KEY),

        }

    }), 200


if __name__ == "__main__":

    app.run(debug=True)