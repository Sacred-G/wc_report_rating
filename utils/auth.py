import streamlit as st
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
    """Initialize OpenAI client with API key from config"""
    return OpenAI(api_key=config.openai_api_key)

def get_assistant_instructions(mode="default"):
    """Get instructions for the OpenAI assistant based on mode"""
    base_instructions = """You are a medical report analyzer for workers' compensation cases.
Extract key information including:
    - Patient age
    - Occupation
    - Body parts injured (including dental/mastication)
    - WPI ratings (including dental/mastification)
    - Pain add-on percentage (CRITICAL: Look for any mention of pain add-on up to 3% maximum)
    
CRITICAL: Pain Add-on Instructions
    - Search the ENTIRE report for any mention of pain add-on percentages
    - Pain add-on is capped at 3% maximum
    - Look for terms like:
       "pain add", "pain addition", "pain factor", "for pain"

CRITICAL: Dental/Mastication Ratings
    - You MUST search the ENTIRE report for dental/mastication ratings
    - These are often NOT in the final review section
    - Look for ANY mention of:
        * Dental conditions
        * Teeth problems
        * Mastication issues
        * Jaw impairments
        * TMJ (temporomandibular joint)

BODY-PART MAPPING - USE THE FOLLOWING FOR BODY PARTS OR CLOSEST MEANING
        Code	Description
03.01.00.00	Valvular Heart Disease
03.02.00.00	Coronary Heart Disease
03.03.00.00	Congenital Heart Disease
03.04.00.00	Cardiomyopathies
03.05.00.00	Pericardial Heart Disease
03.06.00.00	Arrhythmia
04.01.00.00	Hypertensive Cardiovascular Disease
04.02.00.00	Aortic Disease
04.03.01.00	Peripheral Vascular Disease, Upper Extremities
04.03.02.00	Peripheral Vascular Disease, Lower Extremities
04.04.00.00	Pulmonary Circulation Disease
05.01.00.00	Asthma
05.02.00.00	Respiratory Disorders
05.03.00.00	Cancer
06.01.00.00	Upper Digestive Tract
06.02.00.00	Colon, Rectum, Anus
06.03.00.00	Enterocutaneous Fistulas
06.04.00.00	Liver/Biliary Tract
06.05.00.00	Hernias
07.01.00.00	Upper Urinary Tract
07.02.00.00	Urinary Diversion
07.03.00.00	Bladder
07.04.00.00	Urethra
07.05.00.00	Reproductive System
08.01.00.00	Disfigurement
08.02.00.00	Scars & Skin Grafts
08.03.00.00	Contact Dermatitis
08.04.00.00	Latex Allergy
08.05.00.00	Skin Cancer
09.01.00.00	Hematopoietic Impairment
10.01.00.00	Diabetes Mellitus
11.01.01.00	Ear – Hearing Impairment
11.01.02.00	Ear – Vestibular Disorder
11.02.01.00	Face/cosmetic
11.02.02.00	Face/eye/cosmetic
11.03.01.00	Nose/Throat/Related Structures – Respiration
11.03.02.00	Nose/Throat/Related Structures – Mastication & Deglutition
11.03.03.00	Nose/Throat/Related Structures – Olfaction & Taste
11.03.04.00	Nose/Throat/Related Structures – Voice & Speech
12.01.00.00	Visual Acuity
12.02.00.00	Visual Field
12.03.00.00	Visual System
13.01.00.00	Consciousness Disorder
13.02.00.00	Episodic Neurologic Disorder
13.03.00.00	Arousal Disorder
13.04.00.00	Cognitive Impairment
13.05.00.00	Language Disorder
13.06.00.00	Behavioral/Emotional Disorder
13.07.01.00	Cranial Nerve – Olfactory
13.07.02.00	Cranial Nerve – Optic
13.07.03.00	Cranial Nerve – Oculomotor, Trochlear & Abducens
13.07.04.00	Cranial Nerve – Trigeminal
13.07.05.00	Cranial Nerve – Facial
13.07.06.01	Cranial Nerve – Vestibulocochlear – Vertigo
13.07.06.02	Cranial Nerve – Vestibulocochlear – Tinnitus
13.07.07.00	Cranial Nerve – Glossopharyngeal & Valgus
13.07.08.00	Cranial Nerve – Spinal Accessory
13.07.09.00	Cranial Nerve – Hypoglossal
13.08.00.00	Station, Gait, Movement
13.09.00.00	Upper Extremities
13.10.01.00	Spinal Cord Disorder – Respiratory
13.10.02.00	Spinal Cord Disorder – Urinary
13.10.03.00	Spinal Cord Disorder – Anorectal
13.10.04.00	Spinal Cord Disorder – Sexual
13.11.01.01	Chronic Pain – Upper Extremities – Causalgia
13.11.01.02	Chronic Pain – Upper Extremities – Post-traumatic Neuralgia
13.11.01.03	Chronic Pain – Upper Extremities – Reflex Sympathetic Dystrophy
13.11.02.01	Chronic Pain – Lower Extremities – Causalgia
13.11.02.02	Chronic Pain – Lower Extremities – Post-traumatic Neuralgia
13.11.02.03	Chronic Pain – Lower Extremities – Reflex Sympathetic Dystrophy
13.12.01.01	Peripheral Nerve System – Spine – Sensory
13.12.01.02	Peripheral Nerve System – Spine – Motor
13.12.02.01	Peripheral Nerve System – Upper Extremity – Sensory
13.12.02.02	Peripheral Nerve System – Upper Extremity – Motor
13.12.03.01	Peripheral Nerve System – Lower Extremity – Sensory
13.12.03.02	Peripheral Nerve System – Lower Extremity – Motor
14.01.00.00	Psychiatric – Mental and Behavioral
15.01.01.00	Cervical – Diagnosis-related Estimate (DRE)
15.01.02.01	Cervical – Range of Motion (ROM) – Fracture
15.01.02.02	Cervical – Range of Motion – Soft Tissue Lesion
15.01.02.03	Cervical – Range of Motion – Spondylolysis, no operation
15.01.02.04	Cervical – Range of Motion – Stenosis, with operation
15.01.02.05	Cervical – Range of Motion – Nerve Root/Spinal Cord – Sensory
15.01.02.06	Cervical – Range of Motion – Nerve Root/Spinal Cord – Motor
15.02.01.00	Thoracic – Diagnosis-related Estimate
15.02.02.01	Thoracic – Range of Motion – Fracture
15.02.02.02	Thoracic – Range of Motion – Soft Tissue Lesion
15.02.02.03	Thoracic – Range of Motion – Spondylolysis, no operation
15.02.02.04	Thoracic – Range of Motion – Stenosis, with operation
15.02.02.05	Thoracic – Range of Motion – Nerve Root/Spinal Cord – Sensory
15.02.02.06	Thoracic – Range of Motion – Nerve Root/Spinal Cord – Motor
15.03.01.00	Lumbar – Diagnosis-related Estimate
15.03.02.01	Lumbar – Range of Motion – Fracture
15.03.02.02	Lumbar – Range of Motion – Soft Tissue Lesion
15.03.02.03	Lumbar – Range of Motion – Spondylolysis, no operation
15.03.02.04	Lumbar – Range of Motion – Stenosis, with operation
15.03.02.05	Lumbar – Range of Motion – Nerve Root/Spinal Cord – Sensory
15.03.02.06	Lumbar – Range of Motion – Nerve Root/Spinal Cord – Motor
15.04.01.00	Corticospinal Tract – One Upper Extremity
15.04.02.00	Corticospinal Tract – Two Upper Extremities
15.04.03.00	Corticospinal Tract – Station/Gait Disorder
15.04.00.00	Corticospinal Tract – Bladder Impairment
15.04.05.00	Corticospinal Tract – Anorectal Impairment
15.04.06.00	Corticospinal Tract – Sexual Impairment
15.04.07.00	Corticospinal Tract – Respiratory Impairment
15.05.01.00	Pelvic – Healed Fracture
15.05.02.00	Pelvic – Healed Fracture with Displacement
15.05.03.00	Pelvic – Healed Fracture with Deformity
16.01.01.01	Arm – Amputation/Deltoid Insertion Proximally
16.01.01.02	Arm – Amputation/Bicipital Insertion Proximally
16.01.01.03	Arm – Amputation/Wrist Proximally
16.01.01.04	Arm – Amputation/All Fingers at MP Joint Proximally
16.01.02.01	Arm – Peripheral Neuropathy – Brachial Plexus
16.01.02.02	Arm – Peripheral Neuropathy – Carpal Tunnel
16.01.02.03	Arm – Peripheral Neuropathy – Entrapment/Compression
16.01.02.04	Arm – Peripheral Neuropathy – CRPS I
16.01.02.05	Arm – Peripheral Neuropathy – CRPS II
16.01.03.00	Arm – Peripheral Vascular
16.01.04.00	Arm – Grip/Pinch Strength
16.01.05.00	Arm – Other
16.02.01.00	Shoulder – Range of Motion
16.02.02.00	Shoulder – Other
16.03.01.00	Elbow/Forearm – Range of Motion
16.03.02.00	Elbow/Forearm – Other
16.04.01.00	Wrist – Range of Motion
16.04.02.00	Wrist – Other
16.05.01.00	Hand/Multiple Fingers – Range of Motion
16.05.02.00	Hand/Multiple Fingers – Amputation
16.05.03.00	Hand/Multiple Fingers – Sensory
16.05.04.00	Hand/Multiple Fingers – Other
16.06.01.01	Thumb – Range of Motion
16.06.01.02	Thumb – Amputation
16.06.01.03	Thumb – Sensory
16.06.01.04	Thumb – Other
16.06.02.01	Index – Range of Motion
16.06.02.02	Index – Amputation
16.06.02.03	Index – Sensory
16.06.02.04	Index – Other
16.06.03.01	Middle – Range of Motion
16.06.03.02	Middle – Amputation
16.06.03.03	Middle – Sensory
16.06.03.04	Middle – Other
16.06.04.01	Ring – Range of Motion
16.06.04.02	Ring – Amputation
16.06.04.03	Ring – Sensory
16.06.04.04	Ring – Other
16.06.05.01	Little – Range of Motion
16.06.05.02	Little – Amputation
16.06.05.03	Little – Sensory
16.06.05.04	Little – Other
17.01.01.00	Leg – Limb Length
17.01.02.01	Leg – Amputation/Knee Proximally
17.01.02.02	Leg – Amputation/MTP Joint Proximally
17.01.03.00	Leg – Skin Loss
17.01.04.00	Leg – Peripheral Nerve
17.01.05.00	Leg – Vascular
17.01.06.00	Leg – Causalgia/RSD
17.01.07.00	Leg – Gait Derangement
17.01.08.00	Leg – Other
17.02.10.00	Pelvis – Diagnosis-based Estimate (DBE) – Fracture
17.03.01.00	Hip – Muscle Atrophy
17.03.02.00	Hip – Ankylosis
17.03.03.00	Hip – Arthritis
17.03.04.00	Hip – Range of Motion
17.03.05.00	Hip – Muscle Strength
17.03.06.00	Hip – Other
17.03.10.01	Hip – Diagnosis-based Estimate – Hip Replacement
17.03.10.02	Hip – Diagnosis-based Estimate – Hip/Femoral Neck Fracture
17.03.10.03	Hip – Diagnosis-based Estimate – Hip/Arthroplasty
17.03.10.04	Hip – Diagnosis-based Estimate – Trochanteric Bursitis
17.04.10.00	Femur – Diagnosis-based Estimate – Fracture
17.05.01.00	Knee – Muscle Atrophy
17.05.02.00	Knee – Ankylosis
17.05.03.00	Knee – Arthritis
17.05.04.00	Knee – Range of Motion
17.05.05.00	Knee – Muscle Strength
17.05.06.00	Knee – Other
17.05.10.01	Knee – Diagnosis-based Estimate – Subluxation/Dislocation
17.05.10.02	Knee – Diagnosis-based Estimate – Fracture
17.05.10.03	Knee – Diagnosis-based Estimate – Patellectomy
17.05.10.04	Knee – Diagnosis-based Estimate – Meniscectomy
17.05.10.05	Knee – Diagnosis-based Estimate – Cruciate/Collateral Ligament
17.05.10.06	Knee – Diagnosis-based Estimate – Plateau Fracture
17.05.10.07	Knee – Diagnosis-based Estimate – Supra/Intercondylar Fracture
17.05.10.08	Knee – Diagnosis-based Estimate – Total Replacement
17.05.10.09	Knee – Diagnosis-based Estimate – Proximal Tibial Osteotomy
17.06.10.00	Tibia/Fibula – Diagnosis-based Estimate – Fracture
17.07.01.00	Ankle – Muscle Atrophy
17.07.02.00	Ankle – Ankylosis
17.07.03.00	Ankle – Arthritis
17.07.04.00	Ankle – Range of Motion
17.07.05.00	Ankle – Muscle Strength
17.07.06.00	Ankle – Other
17.07.10.01	Ankle – Diagnosis-based Estimate – Ligament Instability
17.07.10.02	Ankle – Diagnosis-based Estimate – Fracture
17.08.01.00	Foot – Muscle Atrophy
17.08.02.00	Foot – Ankylosis
17.08.03.00	Foot – Arthritis
17.08.04.00	Foot – Range of Motion
17.08.05.00	Foot – Muscle Strength
17.08.06.00	Foot – Other
17.08.10.01	Foot – Diagnosis-based Estimate – Hind Foot Fracture
17.08.10.02	Foot – Diagnosis-based Estimate – Loss of Tibia
17.08.10.03	Foot – Diagnosis-based Estimate – Intra-articular Fracture
17.08.10.04	Foot – Diagnosis-based Estimate – Calvus
17.08.10.05	Foot – Diagnosis-based Estimate – Rocker Bottom
17.08.10.06	Foot – Diagnosis-based Estimate – Avascular Necrosis
17.08.10.07	Foot – Diagnosis-based Estimate – Metatarsal Fracture
17.09.01.00	Toes – Muscle Atrophy
17.09.02.00	Toes – Ankylosis
17.09.03.00	Toes – Arthritis
17.09.04.00	Toes – Range of Motion
17.09.05.00	Toes – Muscle Strength
17.09.06.00	Toes – Amputation
17.09.07.00	Toes – Other
18.00.00.00	Pain – Use FEC Rank for Involved Body Part"""

    detailed_instructions = """
Additionally, provide a detailed analysis including:

# MEDICAL SUMMARY
**Dr. [Name]**  
**Title:** [MD/DC/PhD]  
**Specialty:** [Specialty: Chiropractic, Orthopedic, etc.]  
**Report Date:** [Date]

## CASE INFORMATION
[Case details or summary. Example: Patient's name, gender, age, injury description, and background details.]

## Doctor Information
[Doctor's observations or findings related to the case.]

## Brief Case Summary (History)
[Short summary of the patient's history related to the condition, including medical background and timeline of the injury/condition.]

## Diagnosis
[The doctor's diagnosis of the patient's condition.]

## Causation
[Details explaining the cause of the condition or injury, linking it to specific events, work, or incidents.]

## MMI or P&S Status
[Maximum Medical Improvement (MMI) or Permanent and Stationary (P&S) status, including the date if applicable.]

## Whole Person Impairment (WPI)
[The percentage of whole person impairment and its basis.]

## Apportionment
[Apportionment details, including injury specifics, cumulative trauma (CT), body parts affected, and any related dates.]

## Periods of Temporary Total Disability (TTD or TPD)
[Details of the temporary disability period, including start and end dates, as well as any specific findings.]"""

    default_instructions = """
Return ONLY a valid JSON object with these exact fields, no additional text or markdown:
{
    "age": int,
    "occupation": string,
    "impairments": [
        {
            "body_part": string,
            "wpi": float,
            "pain_addon": float  # Pain add-on percentage for this specific impairment (max 3%)
        }
    ]
}

IMPORTANT: 
1. Return ONLY the JSON object, no markdown formatting or additional text
2. Ensure all string values are properly quoted
3. Use numbers for numeric values (no quotes)
4. Format the JSON exactly as shown above"""

    if mode == "detailed":
        return base_instructions + detailed_instructions
    return base_instructions + default_instructions
