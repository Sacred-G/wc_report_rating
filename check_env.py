import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables from .env file
load_dotenv()

# Check for critical environment variables
print("Checking environment variables...")
print(f"OPENAI_API_KEY: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Not set'}")
print(f"ASSISTANT_ID: {'✓ Set' if os.getenv('ASSISTANT_ID') else '✗ Not set'}")
print(f"VECTOR_STORE: {'✓ Set' if os.getenv('VECTOR_STORE') else '✗ Not set'}")
print(f"SUPABASE_URL: {'✓ Set' if os.getenv('SUPABASE_URL') else '✗ Not set'}")
print(f"SUPABASE_KEY: {'✓ Set' if os.getenv('SUPABASE_KEY') else '✗ Not set'}")
print(f"DATABASE_PATH: {'✓ Set' if os.getenv('DATABASE_PATH') else '✗ Not set'}")

# Check if the database directory exists
db_path = os.getenv('DATABASE_PATH', 'data/local.db')
db_dir = os.path.dirname(db_path)
print(f"Database directory ({db_dir}): {'✓ Exists' if os.path.exists(db_dir) else '✗ Does not exist'}")

# Check if OpenAI can be imported
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    print("OpenAI client: ✓ Successfully initialized")
except Exception as e:
    print(f"OpenAI client: ✗ Error initializing - {str(e)}")
