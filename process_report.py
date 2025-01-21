import streamlit as st
import json
import re
import os
from datetime import datetime

from utils.auth import init_openai_client, get_assistant_instructions
from rating_calculator import calculate_rating

def process_report(client, get_assistant_instructions):
    """Process QME reports for ratings and summaries"""
    
    # Mode selection
    mode = st.radio(
        "Select Processing Mode",
        ["Calculate WPI Ratings", "Generate Medical Summary"],
        key="processing_mode"
    )
    
    # File upload
    uploaded_file = st.file_uploader("Upload QME Report PDF", type=["pdf"])
    
    if uploaded_file:
        st.write("Processing uploaded report...")
        
        try:
            # Save uploaded file temporarily
            with open("temp_file.pdf", "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Create OpenAI file
            openai_file = client.files.create(
                file=open("temp_file.pdf", "rb"),
                purpose="assistants"
            )
            st.info("File uploaded successfully")
            
            # Create vector store for file search
            vector_store = client.beta.vector_stores.create(
                name="QME Report Store"
            )
            st.info("Vector store created")
            
            # Add file to vector store and wait for processing
            file_batch = client.beta.vector_stores.file_batches.create_and_poll(
                vector_store_id=vector_store.id,
                file_ids=[openai_file.id]
            )
            
            if file_batch.status != "completed":
                st.error(f"File processing failed with status: {file_batch.status}")
                st.stop()
            
            st.success("File processed successfully")
            
            # Create assistant with file search enabled
            assistant = client.beta.assistants.create(
                name="QME Assistant",
                instructions=get_assistant_instructions(mode),
                tools=[{"type": "file_search"}],
                model=config.openai_model,
                tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
            )
            st.info("Assistant created")
            
            # Create thread and message
            thread = client.beta.threads.create()
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content="Please analyze this medical report according to the instructions provided."
            )
            
            # Run assistant
            with st.spinner("Analyzing report..."):
                run = client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id,
                    assistant_id=assistant.id
                )
            
            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                response_text = messages.data[0].content[0].text.value
                
                if mode == "Calculate WPI Ratings":
                    try:
                        # Parse JSON from response
                        extracted_data = json.loads(response_text)
                        st.write("### Extracted Data")
                        st.json(extracted_data)
                        
                        # Calculate rating using the updated function
                        result = calculate_rating(
                            occupation=extracted_data.get("occupation"),
                            bodypart=extracted_data.get("bodypart"),
                            age_injury=extracted_data.get("age_injury"),
                            wpi=extracted_data.get("wpi"),
                            pain=extracted_data.get("pain", 0)
                        )
                        
                        if result['status'] == 'success':
                            st.write("\n### Rating Breakdown")
                            for detail in result['details']:
                                st.write(f"{detail['body_part']}: {detail['final_value']}% WPI")
                            st.success(f"**Final Combined Rating:** {result['final_value']}%")
                        else:
                            st.error(f"Error: {result['message']}")
                            
                    except json.JSONDecodeError:
                        st.error("Invalid JSON format in the assistant's response.")
                        st.text("Response text:")
                        st.code(response_text)
                        
                else:
                    # Display medical summary
                    st.markdown("## Medical Report Summary")
                    st.markdown(response_text)
                    
                    # Add download button for the summary
                    st.download_button(
                        "Download Summary",
                        response_text,
                        file_name="medical_summary.txt",
                        mime="text/plain"
                    )
            else:
                st.error(f"Run failed with status: {run.status}")
                if hasattr(run, 'last_error'):
                    st.error(f"Error: {run.last_error}")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
        
        finally:
            # Clean up
            try:
                os.remove("temp_file.pdf")
                if 'assistant' in locals():
                    client.beta.assistants.delete(assistant_id=assistant.id)
                if 'vector_store' in locals():
                    client.beta.vector_stores.delete(vector_store_id=vector_store.id)
            except Exception as e:
                st.error(f"Cleanup error: {e}")
