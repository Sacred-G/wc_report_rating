import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    st.set_page_config(page_title="Chat Interface", page_icon="💬", layout="wide")
    
    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    except Exception as e:
        st.error("Error initializing OpenAI client. Please check your API key.")
        return
        
    # Add navigation title
    st.sidebar.markdown("### Navigation")
    
    # Custom styling
    st.markdown("""
        <style>
        /* Style sidebar nav */
        .stDeployButton {display:none !important;}
        section[data-testid="stSidebar"] .stMarkdown h3 {
            color: white;
            margin-bottom: 1rem;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
            background-color: rgba(255, 255, 255, 0.1);
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul {
            gap: 0.5rem;
            padding: 0.5rem;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] span {
            font-size: 0.9rem;
            color: white !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            color: white !important;
            opacity: 0.8;
            transition: opacity 0.2s;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
            background-color: rgba(255, 255, 255, 0.2);
            opacity: 1;
        }
        
        /* Improve file uploader appearance */
        .stFileUploader {
            border: 2px dashed #4a4a4a;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            background-color: rgba(255, 255, 255, 0.05);
            transition: all 0.3s ease;
        }
        .stFileUploader:hover {
            border-color: #2196F3;
            background-color: rgba(33, 150, 243, 0.05);
        }
        
        /* Adjust spacing and layout */
        .main .block-container {
            padding-top: 4rem;
            padding-bottom: 5rem;
            max-width: 95rem;
        }
        
        /* Adjust top spacing */
        [data-testid="stAppViewContainer"] > .main {
            padding-top: 1rem;
        }
        
        /* Style the chat container */
        .stChatMessage {
            background-color: rgba(240, 242, 246, 0.7);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* Chat container background */
        [data-testid="stChatMessageContent"] {
            background-color: white !important;
            border-radius: 8px;
            padding: 8px 12px;
        }
        
        /* Chat input styling */
        .stChatInputContainer {
            padding: 1rem 0;
            background: transparent !important;
        }
        
        /* Style the chat input */
        .stChatInput {
            border: 1px solid #ddd !important;
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border-radius: 8px;
        }
        
        /* Style chat input placeholder */
        .stChatInput::placeholder {
            color: rgba(255, 255, 255, 0.7) !important;
        }
        
        /* Remove extra padding */
        .css-1544g2n {
            padding-top: 0 !important;
        }
        
        /* Improve chat message alignment */
        .stChatMessage [data-testid="chatAvatarIcon-user"],
        .stChatMessage [data-testid="chatAvatarIcon-assistant"] {
            top: 0.5rem;
        }
        
        /* Compact headers */
        .stMarkdown h3 {
            margin-bottom: 0.5rem;
        }
        
        /* Custom file list */
        .file-list {
            background-color: rgba(240, 242, 246, 0.7);
            border-radius: 8px;
            padding: 12px;
            margin-top: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* Hide streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Adjust sidebar padding */
        section[data-testid="stSidebar"] {
            padding-top: 3rem;
        }
        
        /* Adjust sidebar content */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
        }
        
        /* Make chat interface fill available height */
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column"] > [data-testid="stVerticalBlock"] {
            min-height: calc(100vh - 3rem);
        }
        
        /* Style the Clear All Documents button */
        .stButton button {
            width: 100%;
            margin-top: 1rem;
            background-color: #f44336;
            color: white;
        }
        .stButton button:hover {
            background-color: #d32f2f;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Initialize session state for chat
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'assistant' not in st.session_state:
        st.session_state.assistant = None
    if 'thread' not in st.session_state:
        st.session_state.thread = None
    if 'vector_store' not in st.session_state:
        st.session_state.vector_store = None
    if 'files' not in st.session_state:
        st.session_state.files = []
    
    # Create layout with more emphasis on chat
    col1, col2 = st.columns([4, 1])
    
    with col2:
        st.markdown('<h3 style="margin-bottom: 1.5rem;">Document Management</h3>', unsafe_allow_html=True)
        
        # File uploader with custom styling and message
        st.markdown("""
            <style>
            .uploadedFile {display: none}
            .stFileUploader div:first-child {
                width: 100%;
                padding: 0;
            }
            .upload-text {
                text-align: center;
                color: #666;
                margin-bottom: 10px;
            }
            .file-types {
                text-align: center;
                color: #888;
                font-size: 0.8em;
                margin-top: 5px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<p class="upload-text">📄 Drag and drop files here</p>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "",  # Empty label since we're using custom text
            type=["pdf", "txt", "doc", "docx"],
            accept_multiple_files=True,
            key="file_uploader"
        )
        st.markdown('<p class="file-types">Supported: PDF, TXT, DOC, DOCX</p>', unsafe_allow_html=True)
        
        # Process uploaded files
        if uploaded_files:
            for file in uploaded_files:
                if file.name not in [f.name for f in st.session_state.files]:
                    try:
                        # Save file temporarily
                        with open(f"temp_{file.name}", "wb") as f:
                            f.write(file.getvalue())
                        
                        # Store file information temporarily
                        st.session_state.temp_files = getattr(st.session_state, 'temp_files', [])
                        st.session_state.temp_files.append({
                            'file': file,
                            'temp_path': f"temp_{file.name}"
                        })
                        
                        # Create OpenAI file
                        openai_file = client.files.create(
                            file=open(f"temp_{file.name}", "rb"),
                            purpose="assistants"
                        )
                        st.session_state.temp_files[-1]['openai_id'] = openai_file.id
                        
                    except Exception as e:
                        st.error(f"Error processing file {file.name}: {str(e)}")
                        continue
            
            # Process all files in a single batch if we have temporary files
            if hasattr(st.session_state, 'temp_files') and st.session_state.temp_files:
                try:
                    # Create vector store if not exists
                    if not st.session_state.vector_store:
                        st.session_state.vector_store = client.beta.vector_stores.create(
                            name="Chat Documents Store"
                        )
                    
                    # Collect all file IDs
                    file_ids = [temp_file['openai_id'] for temp_file in st.session_state.temp_files]
                    
                    # Create a single batch for all files
                    with st.spinner('Processing files...'):
                        file_batch = client.beta.vector_stores.file_batches.create_and_poll(
                            vector_store_id=st.session_state.vector_store.id,
                            file_ids=file_ids
                        )
                    
                    if file_batch.status == "completed":
                        # Add all successfully processed files
                        for temp_file in st.session_state.temp_files:
                            st.session_state.files.append(temp_file['file'])
                            st.success(f"File uploaded: {temp_file['file'].name}")
                    else:
                        st.error(f"Batch processing failed with status: {file_batch.status}")
                        if hasattr(file_batch, 'file_counts'):
                            st.error(f"File counts: {file_batch.file_counts}")
                
                except Exception as e:
                    st.error(f"Error in batch processing: {str(e)}")
                
                finally:
                    # Cleanup temp files
                    for temp_file in st.session_state.temp_files:
                        try:
                            os.remove(temp_file['temp_path'])
                        except Exception:
                            pass
                    
                    # Clear temporary storage
                    st.session_state.temp_files = []
        
        # Display uploaded files
        if st.session_state.files:
            st.markdown("#### Uploaded Documents")
            with st.container(height=400):
                st.markdown('<div class="file-list">', unsafe_allow_html=True)
                for file in st.session_state.files:
                    st.markdown(f"📄 {file.name}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Clear files button
        if st.button("Clear All Documents"):
            try:
                if st.session_state.vector_store:
                    client.beta.vector_stores.delete(vector_store_id=st.session_state.vector_store.id)
                st.session_state.vector_store = None
                st.session_state.files = []
                st.session_state.messages = []
                st.session_state.assistant = None
                st.session_state.thread = None
                st.success("All documents cleared")
            except Exception as e:
                st.error(f"Error clearing documents: {str(e)}")
    
    with col1:
        # Chat interface with minimal spacing
        st.markdown('<h3 style="margin: 0 0 0.5rem;">💬 Document Chat</h3>', unsafe_allow_html=True)
        
        # Display chat messages in reverse order
        for message in reversed(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Chat input at bottom
        if prompt := st.chat_input("Ask a question about your documents..."):
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            try:
                # Create assistant and thread if not exists
                if not st.session_state.assistant:
                    st.session_state.assistant = client.beta.assistants.create(
                        name="Document Assistant",
                        instructions="""Please analyze the attached workers' compensation medical reports and provide a complete disability rating calculation based on the California Permanent Disability Rating Schedule (PDRS).
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
Calculate the permanent disability payout based on provided AWW
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



Please show your full calculations and reasoning for each step of the analysis.""",
                        tools=[{"type": "file_search"}],
                        model="o3-mini",
                        tool_resources={"file_search": {"vector_store_ids": [st.session_state.vector_store.id]}}
                    )
                
                if not st.session_state.thread:
                    st.session_state.thread = client.beta.threads.create()
                
                # Add message to thread
                client.beta.threads.messages.create(
                    thread_id=st.session_state.thread.id,
                    role="user",
                    content=prompt
                )
                
                # Run assistant
                run = client.beta.threads.runs.create_and_poll(
                    thread_id=st.session_state.thread.id,
                    assistant_id=st.session_state.assistant.id
                )
                
                if run.status == "completed":
                    # Get assistant's response
                    messages = client.beta.threads.messages.list(
                        thread_id=st.session_state.thread.id
                    )
                    assistant_message = messages.data[0].content[0].text.value
                    
                    # Add assistant message to chat
                    st.session_state.messages.append({"role": "assistant", "content": assistant_message})
                    with st.chat_message("assistant"):
                        st.write(assistant_message)
                else:
                    st.error(f"Assistant run failed with status: {run.status}")
                    
            except Exception as e:
                st.error(f"Error processing chat: {str(e)}")

if __name__ == "__main__":
    main()
