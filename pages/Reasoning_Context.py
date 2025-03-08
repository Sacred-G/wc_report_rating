import os
import streamlit as st
import PyPDF2
import json
from openai import OpenAI
from dotenv import load_dotenv
from utils.auth import check_password, init_openai_client
from utils.styling import get_card_css

# Load environment variables
load_dotenv()

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    try:
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from each page
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
            
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def count_tokens(text):
    """Estimate the number of tokens in the text."""
    # A rough estimate: 1 token is approximately 4 characters for English text
    return len(text) // 4

def process_with_reasoning_model(client, text, model="o1-mini", prompt=""):
    """Process the extracted text with a reasoning model."""
    try:
        # Create a completion with the reasoning model
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nContext:\n{text}"
                }
            ],
            max_completion_tokens=65000  # Limit for o1-mini
        )
        
        # Extract the response content
        result = response.choices[0].message.content
        
        # Get token usage details
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        
        # Get reasoning tokens if available
        if hasattr(response.usage, "completion_tokens_details"):
            token_usage["reasoning_tokens"] = response.usage.completion_tokens_details.reasoning_tokens
        
        return result, token_usage
    except Exception as e:
        st.error(f"Error processing with reasoning model: {str(e)}")
        return str(e), {"error": str(e)}

def main():
    st.set_page_config(page_title="Reasoning Context", page_icon="🧠", layout="wide")
    st.markdown(get_card_css(), unsafe_allow_html=True)
    st.title("Reasoning Context Processor")
    
    # Check password before proceeding
    if not check_password():
        st.stop()
    
    st.write("Upload a PDF document to extract text and process it with a reasoning model.")
    st.write("The reasoning model has a context window of up to 200,000 tokens.")
    
    # Create two columns for layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # File upload section
        uploaded_file = st.file_uploader("Upload PDF Document", type=["pdf"])
        
        # Model selection
        model_options = {
            "o1-mini": "o1-mini (Faster, 128K context window)",
            "o1": "o1 (More powerful, 200K context window)"
        }
        selected_model = st.selectbox(
            "Select Reasoning Model",
            options=list(model_options.keys()),
            format_func=lambda x: model_options[x],
            index=0
        )
        
        # Custom prompt input
        st.subheader("Custom Prompt")
        prompt = st.text_area(
            "Enter your prompt for the reasoning model",
            value="Please analyze the following document and provide a detailed summary. Identify key points, important facts, and any conclusions that can be drawn from the text.",
            height=150
        )
        
        # Process button
        process_button = st.button("Process Document")
        
        if uploaded_file and process_button:
            with st.spinner("Extracting text from PDF..."):
                # Extract text from PDF
                extracted_text = extract_text_from_pdf(uploaded_file)
                
                if extracted_text:
                    # Count tokens
                    estimated_tokens = count_tokens(extracted_text)
                    st.info(f"Extracted approximately {estimated_tokens:,} tokens from the PDF.")
                    
                    # Check if the text is too large
                    max_tokens = 190000 if selected_model == "o1" else 120000
                    if estimated_tokens > max_tokens:
                        st.warning(f"The extracted text may exceed the model's context window ({max_tokens:,} tokens). The model will process as much as it can, but some content may be truncated.")
                    
                    # Initialize OpenAI client
                    client = init_openai_client()
                    if not client:
                        st.error("Failed to initialize OpenAI client. Check your API key.")
                        st.stop()
                    
                    # Process with reasoning model
                    with st.spinner(f"Processing with {selected_model}... This may take several minutes for large documents."):
                        result, token_usage = process_with_reasoning_model(
                            client, 
                            extracted_text, 
                            model=selected_model,
                            prompt=prompt
                        )
                        
                        # Store results in session state
                        st.session_state.reasoning_result = result
                        st.session_state.token_usage = token_usage
                        st.session_state.extracted_text = extracted_text
                        st.session_state.estimated_tokens = estimated_tokens
                        
                        # Rerun to display results
                        st.rerun()
                else:
                    st.error("Failed to extract text from the PDF. Please try another file.")
    
    with col2:
        # Results section
        if 'reasoning_result' in st.session_state:
            st.subheader("Processing Results")
            
            # Display token usage
            if 'token_usage' in st.session_state:
                usage = st.session_state.token_usage
                
                # Create a formatted display of token usage
                token_cols = st.columns(3)
                with token_cols[0]:
                    st.metric("Prompt Tokens", f"{usage.get('prompt_tokens', 0):,}")
                with token_cols[1]:
                    st.metric("Completion Tokens", f"{usage.get('completion_tokens', 0):,}")
                with token_cols[2]:
                    st.metric("Total Tokens", f"{usage.get('total_tokens', 0):,}")
                
                # Display reasoning tokens if available
                if 'reasoning_tokens' in usage:
                    st.metric("Reasoning Tokens", f"{usage.get('reasoning_tokens', 0):,}")
                    
                    # Calculate visible vs. reasoning tokens ratio
                    visible_tokens = usage.get('completion_tokens', 0) - usage.get('reasoning_tokens', 0)
                    if usage.get('reasoning_tokens', 0) > 0:
                        ratio = visible_tokens / usage.get('reasoning_tokens', 1)
                        st.info(f"Visible tokens to reasoning tokens ratio: 1:{ratio:.2f}")
            
            # Display the result
            st.subheader("Model Response")
            st.markdown(st.session_state.reasoning_result)
            
            # Option to download the result
            result_str = st.session_state.reasoning_result
            st.download_button(
                label="Download Result",
                data=result_str,
                file_name="reasoning_result.txt",
                mime="text/plain"
            )
            
            # Option to view extracted text
            with st.expander("View Extracted Text", expanded=False):
                st.text_area(
                    "Extracted Text",
                    value=st.session_state.extracted_text,
                    height=400,
                    disabled=True
                )
                
                # Download extracted text
                st.download_button(
                    label="Download Extracted Text",
                    data=st.session_state.extracted_text,
                    file_name="extracted_text.txt",
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()
