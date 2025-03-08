import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

st.title("Environment Variables Check")

# Check for critical environment variables
st.write("### Critical Environment Variables")
st.write(f"OPENAI_API_KEY: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Not set'}")
st.write(f"ASSISTANT_ID: {'✓ Set' if os.getenv('ASSISTANT_ID') else '✗ Not set'}")
st.write(f"VECTOR_STORE: {'✓ Set' if os.getenv('VECTOR_STORE') else '✗ Not set'}")
st.write(f"SUPABASE_URL: {'✓ Set' if os.getenv('SUPABASE_URL') else '✗ Not set'}")
st.write(f"SUPABASE_KEY: {'✓ Set' if os.getenv('SUPABASE_KEY') else '✗ Not set'}")
st.write(f"DATABASE_PATH: {'✓ Set' if os.getenv('DATABASE_PATH') else '✗ Not set'}")

# Check if the database directory exists
db_path = os.getenv('DATABASE_PATH', 'data/local.db')
db_dir = os.path.dirname(db_path)
st.write(f"Database directory ({db_dir}): {'✓ Exists' if os.path.exists(db_dir) else '✗ Does not exist'}")

# Check OpenAI connection
st.write("### OpenAI Connection Test")
if os.getenv('OPENAI_API_KEY'):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        st.success("OpenAI client successfully initialized")
        
        # Test a simple API call
        try:
            models = client.models.list()
            st.success(f"Successfully connected to OpenAI API. Available models: {len(models.data)}")
        except Exception as e:
            st.error(f"Error connecting to OpenAI API: {str(e)}")
    except Exception as e:
        st.error(f"Error initializing OpenAI client: {str(e)}")
else:
    st.error("Cannot test OpenAI connection: API key not set")

# Add a section to manually set environment variables
st.write("### Set Environment Variables")
st.write("You can set these values temporarily for testing. They won't be saved to your .env file.")

openai_api_key = st.text_input("OPENAI_API_KEY", type="password")
if openai_api_key:
    os.environ["OPENAI_API_KEY"] = openai_api_key
    st.success("OPENAI_API_KEY set for this session")

assistant_id = st.text_input("ASSISTANT_ID")
if assistant_id:
    os.environ["ASSISTANT_ID"] = assistant_id
    st.success("ASSISTANT_ID set for this session")

# Add a button to test the connection with the new values
if st.button("Test OpenAI Connection"):
    if os.getenv('OPENAI_API_KEY'):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            models = client.models.list()
            st.success(f"Successfully connected to OpenAI API with the provided key. Available models: {len(models.data)}")
        except Exception as e:
            st.error(f"Error connecting to OpenAI API: {str(e)}")
    else:
        st.error("Cannot test OpenAI connection: API key not set")

# Instructions for fixing the environment
st.write("### How to Fix Environment Issues")
st.write("""
1. Create or edit your `.env` file in the project root directory
2. Add the following lines (replace with your actual values):
```
OPENAI_API_KEY=your_openai_api_key_here
ASSISTANT_ID=your_assistant_id_here
VECTOR_STORE=your_vector_store_id_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
DATABASE_PATH=data/local.db
```
3. Save the file and restart your Streamlit app
""")
