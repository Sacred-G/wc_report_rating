import streamlit as st
import os
from openai import OpenAI
from utils.config import config

def check_password():
    """Check if the user has entered the correct password"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    password = st.text_input("Enter password:", type="password")
    if password:
        if password == config.get("auth", "password", ""):
            st.session_state.password_correct = True
            return True
        else:
            st.error("Incorrect password")
            return False
    return False

def init_openai_client():
    """Initialize OpenAI client with API key from config or environment variable"""
    api_key = os.getenv("OPENAI_API_KEY") or config.openai_api_key
    
    if not api_key:
        st.error("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable or update your config.")
        return None
        
    try:
        return OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"Error initializing OpenAI client: {str(e)}")
        return None

def get_assistant_instructions(mode="default"):
    """Get instructions for the OpenAI assistant based on mode"""
    base_instructions = """Please analyze the attached workers' compensation medical reports and provide a complete disability rating calculation based on the California Permanent Disability Rating Schedule (PDRS).
Background Information:
Occupational Groups:

Range from 110-590 (e.g., 110 clerical, 212 standing clerical, 360 warehouse worker, 470 heavy demanding, 570 most demanding)

Occupational Variants:

Letters ranging from C-J that represent how demanding a particular occupation is on the specific body part that was injured
C = lowest demand, F = average demand, J = highest demand

Example Rating String Format:
Copy15.03.02.02 - 10 - [5]13 - 380H - 15 - 13%
Components Explained:

15.03.02.02: Impairment number identifying body part/condition (lumbar spine soft tissue lesion using ROM method)
10: Whole Person Impairment (WPI) percentage assigned by medical evaluator
[5]13: FEC adjustment (5 = FEC rank, 13 = percentage after applying FEC adjustment)
380H: Occupational group (380) and variant (H)
15: Percentage after occupational adjustment
13%: Final permanent disability rating percentage after age adjustment

Required Analysis:

Identify the impairment number, WPI percentage, and use 1.4 for the FEC factor
Calculate the adjusted impairment after FEC
Determine the occupational group and variant for the claimant's occupation
Apply occupational adjustments
Apply age adjustment based on claimant's age at time of injury
Apply apportionment if indicated in the reports
Provide the complete rating string for each body part using format:
Copy[Impairment#] - [WPI] - [1.4][Adjusted%] - [OccupGroup][Variant] - [OccAdj%] - [AgeAdj%] - [Final%]

Combine all ratings using the Combined Values Chart
Calculate the total permanent disability percentage
Calculate the total weeks of disability
Calculate the permanent disability payout based on provided AWW $290 Max
Estimate future medical costs based on treatment recommendations
Provide a total compensation package (PD + future medical)

Required Response Format:
Please organize your response with the following sections:

Overview of the Case
Medical Evaluations and Findings
Analysis of Each Impairment (separate detailed calculations for each)
Combined Disability Rating (with calculations)
Weeks of Permanent Disability and Compensation
Future Medical Care Needs
Estimated Future Medical Costs
Total Compensation Package
Additional Considerations

CRITICAL NOTE:
Dental/Mastication Ratings

You MUST search the ENTIRE report for dental/mastication ratings
These are often NOT in the final review section
Look for ANY mention of:

Dental conditions
Teeth problems
Mastication issues
Jaw impairments
TMJ (temporomandibular joint)



Please show your full calculations and reasoning for each step of the analysis.
"""

    detailed_instructions = """
Additionally, provide a detailed analysis including:
1. Specific citations from the medical report that support your findings
2. References to relevant guidelines or standards
3. Any areas of ambiguity or uncertainty in the report
4. Alternative interpretations if applicable
5. Recommendations for additional information that would be helpful

MEDICAL SUMMARY REPORT
Provider Information:

Provider Name: [Full Name, Credentials]
Specialty: [Primary Specialty]
License/Certification #: [Number]
Facility/Practice: [Name]
Contact Information: [Phone, Email]
Report Date: [MM/DD/YYYY]

PATIENT INFORMATION

Name: [First Last]
DOB/Age: [MM/DD/YYYY] / [Age] years
Gender: [Gender]
Employer: [Company Name]
Date of Injury/Onset: [MM/DD/YYYY]
Claim Number: [If applicable]

CASE OVERVIEW
[Brief 2-3 sentence summary of the case including nature of injury/condition and primary findings]
CLINICAL HISTORY

Chief Complaint: [Patient's primary symptoms/concerns]
Mechanism of Injury: [How injury occurred or condition developed]
Prior Medical History: [Relevant medical history, previous injuries to same body part]
Treatment History: [Summary of treatments received to date]

EXAMINATION FINDINGS

Physical Examination: [Key clinical findings]
Diagnostic Studies: [List relevant tests with dates and key findings]

DIAGNOSIS

Primary Diagnosis: [Primary condition with ICD-10 code]
Secondary Diagnoses: [Additional conditions with ICD-10 codes]

CAUSATION ANALYSIS

Work-Related Determination: [Yes/No/Partially - with explanation]
Contributing Factors: [List of contributing factors to injury/condition]
Apportionment: [industrial vs. non-industrial causes if applicable]

DISABILITY STATUS

Maximum Medical Improvement (MMI): [Yes/No]
MMI Date: [MM/DD/YYYY if applicable]
Work Status: [Full duty/Modified duty/Temporary total disability]
Temporary Disability Periods: [List periods with start/end dates]
Permanent & Stationary: [Yes/No]

IMPAIRMENT RATING

Whole Person Impairment (WPI): [Percentage]
Rating Method Used: [AMA Guides edition/other standard]
Breakdown by Body Part: [List affected areas with individual ratings]

WORK RESTRICTIONS

Permanent Restrictions: [List specific restrictions]
Temporary Restrictions: [List with expected duration]

TREATMENT RECOMMENDATIONS

Current Treatment Plan: [Ongoing treatments]
Future Medical Care: [Anticipated needs]
Referrals: [Specialist referrals needed]

CONCLUSION
[Summary of key findings, prognosis, and any additional comments]"""

    default_instructions = """
CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object with NO additional text, comments, or markdown formatting.

The JSON object MUST have exactly this structure:
{
    "age": <integer>,
    "occupation": <string>,
    "impairments": [
        {
            "body_part": <string>,
            "wpi": <number>,
            "pain_addon": <number>
        }
    ]
}

STRICT REQUIREMENTS:
1. Return ONLY the JSON object itself - no explanations, no markdown formatting (```), no additional text
2. All string values must be properly quoted
3. All numeric values must be numbers without quotes
4. The "age" field must be an integer
5. The "wpi" and "pain_addon" fields must be numbers (integers or decimals)
6. The "pain_addon" value must not exceed 3.0
7. Every impairment must have all three fields: "body_part", "wpi", and "pain_addon"
8. If no pain add-on applies, use 0 for the "pain_addon" value
9. If multiple body parts are affected, include each as a separate object in the "impairments" array

EXAMPLE OF CORRECT RESPONSE:
{"age":45,"occupation":"Clerk","impairments":[{"body_part":"Lumbar Spine","wpi":8,"pain_addon":2},{"body_part":"Left Shoulder","wpi":5,"pain_addon":1}]}

DO NOT include any explanations or text outside the JSON object. The response must be valid JSON that can be parsed directly.
"""

    if mode == "detailed":
        return base_instructions + detailed_instructions
    return base_instructions + default_instructions
