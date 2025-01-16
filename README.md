# Workers' Compensation Rating Calculator

This application processes workers' compensation permanent disability ratings by analyzing medical reports and calculating benefits using the California PDRS (Permanent Disability Rating Schedule) system.

## Application Flow

### 1. File Upload and Initial Processing

1. User uploads a medical report PDF through the Streamlit interface
2. The file is temporarily saved and uploaded to OpenAI using the Assistants API
3. A vector store is created for enhanced document search capabilities:
   - Creates a new vector store instance named "Medical Report Store"
   - Processes the PDF file to create embeddings for semantic search
   - Waits for the file batch processing to complete

### 2. OpenAI Assistant Integration

1. Creates a specialized medical report assistant with:
   - Custom instructions for extracting key information
   - File search capabilities enabled
   - GPT-4 Turbo (gpt-4-1106-preview) as the base model
   - Access to the vector store for semantic search

2. The assistant extracts key information including:
   - Patient age
   - Occupation
   - Body parts injured
   - WPI (Whole Person Impairment) ratings
   - Pain add-on percentages

3. Returns a structured JSON response containing:
```json
{
    "age": int,
    "occupation": string,
    "impairments": [
        {
            "body_part": string,
            "wpi": float
        }
    ],
    "pain_addon": float (optional)
}
```

### 3. Vector Store Search Process

1. The assistant uses the vector store to perform semantic search across the medical report
2. This enables:
   - Context-aware information extraction
   - Accurate identification of medical terms and ratings
   - Better handling of various report formats

### 4. SQL-Based Calculations

The application performs a series of calculations using multiple SQL tables:

#### A. Occupation Group Determination
1. Queries the `occupations` table to map job titles to occupation groups
2. Handles special cases (e.g., stockers/sorters mapped to packer group)
3. Returns a numeric group code used in subsequent calculations

#### B. Body Part Code Mapping
1. Maps described body parts to standardized impairment codes
2. Uses pattern matching for various body regions:
   - Spine and nervous system
   - Upper extremities
   - Lower extremities
   - Other systems

#### C. Variant Determination
1. Uses either `variants` or `variants_2` table based on occupation group
2. Maps specific body parts to general categories
3. Determines the appropriate variant label (c-j) for the occupation/impairment combination

#### D. WPI Adjustments
The application applies several adjustments to the initial WPI rating:

1. Pain Add-on:
   - Caps pain add-on at 3%
   - Adds to base WPI

2. Occupational Adjustment:
   - Queries `occupational_adjustments` table
   - Finds closest rating percentage
   - Applies adjustment based on occupation group and variant

3. Age Adjustment:
   - Queries `age_adjustment` table
   - Determines age bracket
   - Applies final age-based adjustment to WPI

### 5. Final Calculations

1. Combines multiple impairment ratings:
   - Groups by body region (upper extremities, lower extremities, spine, other)
   - Applies combination formula for multiple impairments
   - Calculates final combined rating

2. Determines payment details:
   - Calculates weeks of payment based on PD percentage ranges
   - Applies weekly rate ($290.00)
   - Computes total payout

### 6. Result Display

Presents detailed results including:
- Individual impairment calculations
- Combination steps (if multiple impairments)
- Final calculations showing:
  - Combined rating percentage
  - Pain add-ons
  - Total weeks of PD
  - Age at date of injury
  - Weekly rate
  - Total payout amount

## Database Schema

The application uses SQLite with the following key tables:

1. `occupational_adjustments`: Rating percentages and adjustment factors
2. `occupations`: Job titles and group numbers
3. `variants` & `variants_2`: Body part and impairment code mappings
4. `age_adjustment`: Age-based adjustment factors

## Environment Setup

Required environment variables:
- `OPENAI_API_KEY`: OpenAI API key
- `DATABASE_PATH`: Path to SQLite database (default: "data/local.db")
- `ASSISTANT_ID`: OpenAI Assistant ID
- `VECTOR_STORE`: Vector store identifier

## Dependencies

- OpenAI API (gpt-4-1106-preview model)
- Streamlit for the web interface
- SQLite for data storage
- Python standard library components
