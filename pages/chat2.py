import streamlit as st
from openai import OpenAI
import os

def chat_interface(client):
    """Chat interface with file management"""
    st.title("Chat Interface")
    
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
    
    # Create layout
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.header("Document Management")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Upload Documents",
            type=["pdf", "txt", "doc", "docx"],
            accept_multiple_files=True
        )
        
        # Process uploaded files
        if uploaded_files:
            for file in uploaded_files:
                if file.name not in [f.name for f in st.session_state.files]:
                    try:
                        # Save file temporarily
                        with open(f"temp_{file.name}", "wb") as f:
                            f.write(file.getvalue())
                        
                        # Create OpenAI file
                        openai_file = client.files.create(
                            file=open(f"temp_{file.name}", "rb"),
                            purpose="assistants"
                        )
                        
                        # Create vector store if not exists
                        if not st.session_state.vector_store:
                            st.session_state.vector_store = client.beta.vector_stores.create(
                                name="Chat Documents Store"
                            )
                        
                        # Add file to vector store
                        file_batch = client.beta.vector_stores.file_batches.create_and_poll(
                            vector_store_id=st.session_state.vector_store.id,
                            file_ids=[openai_file.id]
                        )
                        
                        if file_batch.status == "completed":
                            st.session_state.files.append(file)
                            st.success(f"File uploaded: {file.name}")
                        else:
                            st.error(f"File processing failed: {file.name}")
                        
                        # Cleanup temp file
                        os.remove(f"temp_{file.name}")
                        
                    except Exception as e:
                        st.error(f"Error processing file {file.name}: {str(e)}")
        
        # Display uploaded files
        if st.session_state.files:
            st.subheader("Uploaded Documents")
            with st.container(height=400):
                for file in st.session_state.files:
                    st.write(f"📄 {file.name}")
        
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
        # Chat interface
        st.header("Chat")
        
        # Display chat messages
        chat_container = st.container(height=500)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
        
        # Chat input
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
                        instructions="""You are a helpful assistant that can answer questions about uploaded documents.
                        Use the file_search tool to find relevant information in the documents.
                        Always cite the source document and location when providing information.""",
                        tools=[{"type": "file_search"}],
                        model="gpt-4o-mini",
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
