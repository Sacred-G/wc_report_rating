from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

client = OpenAI()

# Create an assistant
assistant = client.beta.assistants.create(
    name="Workers Comp Assistant",
    instructions="""You are a workers' compensation assistant specialized in processing medical reports.
    Extract and analyze the following information from medical reports:
    1. Patient's age
    2. Patient's occupation
    3. List of impairments with body parts and WPI ratings
    4. Pain add-on percentage if mentioned
    
    Format responses as JSON objects with the following structure:
    {
        "age": int,
        "occupation": str,
        "impairments": [
            {
                "body_part": str,
                "wpi": float
            }
        ],
        "pain_addon": float
    }
    """,
    tools=[{"type": "code_interpreter"}, {"type": "file_search"}],
    model="gpt-4o-mini"
)

print(f"Created assistant with ID: {assistant.id}")
print("Please update your .env file with this assistant ID")
