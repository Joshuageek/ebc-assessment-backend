import json
import os
import smtplib

from collections import OrderedDict
from datetime import datetime, timezone
from email.mime.text import MIMEText

from flask import Flask, request, jsonify
from google.oauth2.service_account import Credentials
import gspread


app = Flask(__name__)


SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")


CAMPAIGNS = {

    "recruitment": {
        "sheet": "Recruitment Readiness",
        "email": [
            "promise.nabaasa@welcometoebc.com",
            "chrislenana@gmail.com"
        ],
        "title": "Recruitment Readiness Assessment"
    },

    "revenue": {
        "sheet": "Revenue Growth",
        "email": [
            "makishe@welcometoebc.com",
            "chrislenana@gmail.com"
        ],
        "title": "Revenue Growth Assessment"
    },

    "workplace": {
        "sheet": "Workplace Performance",
        "email": [
            "christian@welcometoebc.com",
            "chrislenana@gmail.com"
        ],
        "title": "Workplace Performance Assessment"
    },

    "mens": {
        "sheet": "Men's Wellbeing",
        "email": [
            "johnguest@welcometoebc.com",
            "chrislenana@gmail.com"
        ],
        "title": "Men's Workplace Wellbeing Assessment"
    },

    "executive": {
        "sheet": "Year-End Organizational",
        "email": [
            "mercy.kemirembe@welcometoebc.com",
            "chrislenana@gmail.com"
        ],
        "title": "Year-End Organizational Assessment"
    },

    "brave_men": {
        "sheet": "Brave Men Support Check-In",
        "email": [
            "christian@welcometoebc.com",
            "chrislenana@gmail.com"
        ],
        "title": "Brave Men Support Check-In"
    },

    "agile": {
        "sheet": "AGILE Project Readiness",
        "email": [
            "christian@weareagileconstructions.com",
            "operations@weareagileconstructions.com",
            "chrislenana@gmail.com"
        ],
        "title": "AGILE Project Readiness and Client Alignment Questionnaire"
    },

    "christian_lenana": {
        "sheet": "Christian Lenana Connect",
        "email": [
            "christian@welcometoebc.com",
            "chrislenana@gmail.com"
        ],
        "title": "Connect with Christian Lenana"
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

    "brave_men": OrderedDict([
        ("privacy_understood", "Has the respondent read and understood the privacy statement?"),
        ("purpose_understood", "Does the respondent understand this form is for support and professional matching, not emergency assistance or a medical diagnosis?"),
        ("age_18_or_older", "Is the respondent 18 years of age or older?"),
        ("preferred_name", "Name the respondent prefers to be called"),
        ("age_range", "Age range"),
        ("location_country_city", "Country and town/city where the respondent currently lives"),
        ("nationality", "Nationality"),
        ("relationship_status", "Current relationship status"),
        ("work_situation", "Current work situation"),
        ("referral_source", "How did they hear about Brave Men Series?"),
        ("referral_source_detail", "If through a video or post, what was its subject or message?"),
        ("support_areas", "Which areas would they like help with?"),
        ("primary_support_area", "Which ONE area needs attention first?"),
        ("duration_affected", "How long has this been affecting them?"),
        ("impact_severity", "How strongly is this affecting their daily life today? (1-10)"),
        ("situation_description", "In their own words, what is happening and what would they like help with?"),
        ("impact_areas", "What impact is this having?"),
        ("previous_attempts", "What have they already tried? What helped, even a little?"),
        ("previous_professional_help", "Have they previously received professional help for this matter?"),
        ("current_help_additional_support", "If currently receiving help, what additional support are they seeking from Brave Men Series?"),
        ("relevant_background_info", "Any diagnosed conditions, medications, physical limitations, legal proceedings or other facts a matched professional should know?"),
        ("desired_outcome_30_90_days", "If this support works well, what would be different in their life in the next 30-90 days?"),
        ("support_type_preference", "What kind of support do they believe would help most?"),
        ("readiness_to_act", "How ready are they to take action?"),
        ("immediate_danger", "Is anyone in immediate physical danger right now?"),
        ("self_harm_thoughts", "During the past two weeks, have they had thoughts of harming themselves, ending their life or harming another person?"),
        ("urgent_safety_concern", "Are they currently experiencing abuse, violence, threats, severe withdrawal, a medical emergency or another urgent safety concern?"),
        ("currently_safe", "Are they in a safe place at this moment?"),
        ("professional_preference", "Who would they be most comfortable speaking with?"),
        ("support_format_preference", "Preferred support format"),
        ("preferred_languages", "Preferred language(s)"),
        ("availability", "When are they generally available?"),
        ("contact_timeframe", "How soon would they like to be contacted?"),
        ("safest_contact_method", "What is the safest way to contact them?"),
        ("contact_avoid_times", "Are there times or methods to avoid for privacy or safety?"),
        ("fee_capability", "Which statement best describes their ability to pay for professional support?"),
        ("cultural_accessibility_notes", "Anything important about culture, faith, disability, accessibility needs or personal preferences that should guide the match?"),
        ("consent_to_contact", "May an authorised Brave Men Series team member contact them about this request?"),
        ("consent_to_marketing", "May Brave Men Series send them support information, videos, event updates and resources?"),
        ("referral_handling_preference", "If a suitable professional is identified, how would they like the referral handled?"),
        ("consent_share_information", "Consent to share relevant information (only after their approval)"),
        ("signature_full_name", "Typed name confirming the information is accurate and consent is given"),
        ("signature_date", "Date"),
        ("additional_comments", "Is there anything else they would like Brave Men Series to know?"),
    ]),
    "agile": OrderedDict([
        ("client_organization", "Please provide the client or organisation name"),
        ("contact_person", "Please provide the contact person full name"),
        ("position", "Kindly state your position or role in the organisation"),
        ("telephone", "Please provide your telephone number"),
        ("email", "Please provide your email address"),
        ("formal_communication_method", "Which method would you prefer us to use for formal project communication?"),
        ("introduction_source", "How were you introduced to AGILE Constructions?"),
        ("referrer", "If you were referred, kindly provide the name of the person or organisation that referred you"),
        ("agile_attractions", "Which aspects of AGILE Constructions attracted your interest?"),
        ("project_type", "Which type of project would you like us to consider?"),
        ("project_name", "Please provide the project name, where applicable"),
        ("project_location", "Please provide the project location"),
        ("within_kampala", "Please indicate whether the project is located within Kampala"),
        ("space_size", "If known, kindly indicate the approximate size of the space"),
        ("space_condition", "Which description best represents the current condition of the space?"),
        ("project_stage", "Which stage has the project currently reached?"),
        ("deliverables", "Please briefly describe what you would like AGILE Constructions to deliver"),
        ("three_outcomes", "Please share the three most important outcomes you expect from the project"),
        ("space_challenges", "Which challenges would you like the new space to address?"),
        ("operational_date", "Please indicate when you would like the completed space to become operational"),
        ("completion_flexibility", "Please let us know whether the requested completion date is flexible"),
        ("property_relationship", "Which option best describes your relationship to the property?"),
        ("landlord_approval", "If the property is rented, please indicate the status of the landlord approval for the proposed alterations"),
        ("approval_responsibility", "Please indicate who will be responsible for landlord approvals statutory permits and building management clearances"),
        ("site_restrictions", "Kindly outline any restrictions concerning working hours noise access loading parking or use of lifts"),
        ("uninterrupted_access", "Please indicate whether AGILE will have uninterrupted access to the site during the approved construction programme"),
        ("decision_role", "Please let us know your role in appointing AGILE Constructions and approving project expenditure"),
        ("final_authority", "Please identify the person who will have final authority to approve the design BOQ variations and handover"),
        ("approval_count", "Please indicate how many people will be involved in approving the project"),
        ("approval_period", "Please indicate your organisation normal approval period"),
        ("authorised_project_lead", "Please identify the authorised client project lead"),
        ("budget_status", "Please indicate the current status of the project budget"),
        ("investment_range", "Which anticipated project investment range best applies?"),
        ("selection_factors", "Please rank the factors that will matter most when appointing a construction partner"),
        ("purchasing_approach", "Which statement best represents your purchasing approach?"),
        ("quality_value_ack", "I understand that AGILE Constructions is a quality and value led company and may not be the lowest-priced provider"),
        ("site_assessment_fee", "To proceed with a site assessment, please confirm your understanding of the UGX 380,000 professional site-assessment fee"),
        ("site_fee_credit_ack", "Please confirm your understanding that the site-assessment fee will be credited against the AGILE project invoice if the project proceeds"),
        ("site_fee_payment_timing", "If the project qualifies, please indicate when you would be ready to pay the site-assessment fee"),
        ("preferred_site_visits", "Kindly provide three preferred site-visit dates and times"),
        ("design_fee", "To proceed with design development, please confirm your understanding of the UGX 4,200,000 design and visualisation fee"),
        ("design_fee_credit_ack", "Please confirm your understanding that this fee will be credited against the invoice if AGILE is appointed to implement the project"),
        ("design_ip_ack", "Please acknowledge that the design remains the intellectual property of AGILE Constructions"),
        ("design_use_ack", "We kindly require your confirmation that the design will only be used for the named project and approved location"),
        ("design_license_ack", "Please acknowledge that appointing another contractor to implement an AGILE design requires a separate design-licensing agreement and fee"),
        ("design_if_not_appointed", "If AGILE is not appointed to implement the project, please indicate how you intend to use the design"),
        ("implementation_fee", "To confirm commercial alignment, please acknowledge that AGILE professional and implementation fee is 35% of the approved gross BOQ value"),
        ("two_edits_ack", "Please confirm your understanding that the standard design allowance includes a maximum of two edit rounds"),
        ("additional_design_changes_ack", "Please acknowledge that additional design changes may be charged separately"),
        ("five_reviews_ack", "Please confirm your understanding that the engagement provides for a maximum of five scheduled project-review meetings or site visits after appointment"),
        ("additional_meetings_ack", "Please acknowledge that additional or unplanned meetings may attract a separate professional fee"),
        ("programme_fit", "Please indicate whether the proposed programme can accommodate a properly planned 14-working-day active-site implementation period"),
        ("delay_ack", "Please acknowledge that delays in approvals payments access or client decisions may extend the completion date"),
        ("phased_implementation", "Please indicate whether you would prefer the project to be implemented in phases"),
        ("phase_funding", "Please indicate whether your organisation will be able to fund each approved phase before work begins"),
        ("work_before_funding", "Please let us know whether your organisation requires AGILE to execute any portion of the work before receiving the corresponding funds"),
        ("financing_fee_ack", "If funding is required, please confirm your understanding that the unfunded work will attract a 15% project-financing fee"),
        ("payment_approver", "Please identify the person responsible for approving and releasing project payments"),
        ("formal_change_control_ack", "To maintain clear project records, we kindly require your confirmation that formal written communication will be used for instructions affecting scope design cost materials or timelines"),
        ("whatsapp_change_ack", "Please acknowledge that WhatsApp instructions will not authorise design changes variations or additional work"),
        ("change_documentation_ack", "We kindly require all approved changes to be documented and authorised before implementation. Please confirm your acceptance of this process"),
        ("site_authority_ack", "To maintain clear site authority, we kindly require all project instructions to be communicated through the AGILE project manager or site supervisor"),
        ("no_direct_technician_instructions_ack", "Please confirm that instructions will not be issued directly to AGILE technicians or subcontractors"),
        ("technical_adjustment_ack", "Please acknowledge that technical adjustments must be reviewed during a formal site meeting and approved in writing"),
        ("client_project_lead", "Please identify the person who will serve as the client authorised project lead"),
        ("site_security", "Please indicate how security will be provided at the site throughout the project"),
        ("premises_security_ack", "Please acknowledge that the client remains responsible for the general security of the premises"),
        ("damage_charge_ack", "Please acknowledge that damage caused by client employees visitors or unrelated contractors will be assessed and charged to the client"),
        ("maintenance_arrangement", "Please indicate whether you would like the one-year maintenance arrangement included in the commercial proposal"),
        ("maintenance_terms_ack", "Please confirm your understanding that the first six months are complimentary and the additional six months are separately charged"),
        ("support_needed", "Which statement best represents the professional support you are looking for?"),
        ("process_willingness", "To proceed, we kindly require your willingness to follow AGILE design approval communication and project-control processes"),
        ("concerns", "Please share any concerns or questions you would like AGILE to address before the site assessment"),
        ("additional_information", "Please share any additional information that may help us understand the proposed project"),
        ("declaration_name", "Please provide your full name"),
        ("declaration_position", "Please provide your position"),
        ("electronic_confirmation", "I confirm that entering my name and submitting this form constitutes my acknowledgement of the information provided above"),
        ("declaration_date", "Please provide the date"),
        ("declaration_accuracy", "I confirm that the information provided in this form is accurate to the best of my knowledge."),
        ("declaration_quality", "I understand that AGILE Constructions is a value-led and quality-led company and is not positioned as the cheapest provider."),
        ("declaration_site_fee", "I understand the UGX 380,000 professional site-assessment fee."),
        ("declaration_design_fee", "I understand the UGX 4,200,000 design and visualisation fee."),
        ("declaration_credits", "I understand that the site-assessment and design fees are credited against the project invoice when AGILE receives the implementation assignment."),
        ("declaration_ip", "I understand AGILE design-ownership and limited-use conditions."),
        ("declaration_license", "I understand that implementing an AGILE design through another provider requires a separate design-licensing agreement and fee."),
        ("declaration_implementation_fee", "I understand that AGILE professional and implementation fee is 35% of the approved gross BOQ value."),
        ("declaration_two_edits", "I understand the limit of two design-edit rounds."),
        ("declaration_change_control", "I understand the formal communication and change-control requirements."),
        ("declaration_site_authority", "I understand that project instructions must go through the project manager or site supervisor."),
        ("declaration_financing", "I understand that unfunded or deferred work attracts a 15% project-financing fee."),
        ("declaration_programme", "I understand the standard 14-working-day active-site programme and its dependencies."),
        ("declaration_no_appointment", "I understand that completing this form does not appoint AGILE or authorise work to commence."),
        ("consent_contact", "I consent to AGILE contacting me regarding this project."),
    ]),

    "christian_lenana": OrderedDict([
        ("full_name", "Full name"),
        ("email", "Email address"),
        ("phone", "WhatsApp/telephone number"),
        ("location", "City and country"),
        ("referral_source", "How did you hear about me?"),
        ("inquiry_type", "Are you making this inquiry for yourself, a project, or an organisation?"),
        ("about_description", "Tell us briefly about yourself, the project, or the organisation"),
        ("service_type", "What are you looking for?"),
        ("long_term_program", "Which long-term developmental program interests you?"),
        ("one_day_engagement", "Which one-day engagement do you require?"),
        ("speaking_engagement_details", "What type of speaking engagement are you planning?"),
        ("phu_donation", "I/We want to donate"),
        ("phu_consulting", "I/We need CSR consulting"),
        ("donation_details", "What would you like to donate and where is it located?"),
        ("csr_consulting_type", "Is this CSR consulting for you personally, a business/project, or an organisation?"),
        ("result_challenge", "What result or challenge would you like me to help you address?"),
        ("participants", "Who will participate or benefit?"),
        ("delivery_format", "What timing and delivery format do you prefer?"),
        ("timing_details", "Preferred date/timeframe and location"),
        ("budget", "Budget range (optional)"),
        ("decision_timeline", "Decision timeline"),
        ("supporting_link", "Supporting link or document (optional)"),
        ("fee_acknowledgement", "Consultation fee acknowledgement"),
    ]),

}


# Various forms use different field names for the same kind of contact
# info. This maps each alias to a friendly display label.
CONTACT_FIELD_LABELS = OrderedDict([
    ("full_name", "Name"),
    ("respondent_name", "Name"),
    ("preferred_name", "Preferred Name"),
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
    ("client_organization", "Organization"),
    ("contact_person", "Name"),
    ("project_name", "Project Name"),
    ("project_location", "Project Location"),
    ("declaration_name", "Declaration Name"),
    ("declaration_position", "Declaration Position"),
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

    appendix = build_qa_appendix(qa_pairs)

    return f"{header}\n{appendix}"


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

        recipients = campaign_info["email"]
        if isinstance(recipients, str):
            recipients = [recipients]

        for recipient in recipients:
            send_notification_email(
                recipient=recipient,
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

        }

    }), 200


if __name__ == "__main__":

    app.run(debug=True)