import streamlit as st
import json
import re
import os

def process_report(client, get_assistant_instructions, find_occupation_group, find_impairment_variant,
                  calculate_occupational_adjustment, calculate_age_adjustment, combine_ratings):
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
                model="gpt-4o-mini",
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
                        # Extract JSON data
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if not json_match:
                            st.error("Could not find JSON data in response")
                            st.stop()
                            
                        extracted_data = json.loads(json_match.group())
                        st.write("### Extracted Data")
                        st.json(extracted_data)
                        
                        # Process ratings
                        occupation = extracted_data.get("occupation")
                        if not occupation:
                            st.error("No occupation found in the report")
                            st.stop()
                            
                        age = extracted_data.get("age")
                        if not age:
                            st.error("No age found in the report")
                            st.stop()
                            
                        body_parts = extracted_data.get("body_parts", {})
                        if not body_parts:
                            st.error("No body parts with WPI ratings found in the report")
                            st.stop()
                        
                        dental_ratings = extracted_data.get("dental", {})
                        if not dental_ratings:
                            st.warning("No dental ratings found in the report")
                        
                        # Find occupation group
                        occupation_group = find_occupation_group(occupation)
                        if not occupation_group:
                            st.error(f"Could not find occupation group for '{occupation}'")
                            st.stop()
                        
                        st.success(f"Found occupation group: {occupation_group}")
                        
                        # Calculate ratings for each body part
                        final_ratings = []
                        rating_strings = []
                        
                        for body_part, ratings in body_parts.items():
                            st.write(f"\nProcessing {body_part}...")
                            
                            try:
                                # Get WPI and pain values
                                if isinstance(ratings, dict):
                                    wpi = ratings.get("wpi", 0)
                                    pain = min(max(ratings.get("pain", 0), 0), 3)  # Clamp pain between 0-3
                                else:
                                    wpi = float(ratings)
                                    pain = 0
                                
                                if not wpi and wpi != 0:
                                    rating_strings.append(f"{body_part}: No WPI value provided")
                                    continue
                                
                                # Add pain to WPI
                                total_wpi = wpi + pain
                                if pain > 0:
                                    st.write(f"Base WPI: {wpi}% + Pain: {pain}% = Total: {total_wpi}%")
                                
                                impairment_code, variant = find_impairment_variant(occupation_group, body_part)
                                if impairment_code and variant:
                                    st.write(f"Found variant: {variant}")
                                    
                                    occ_adj_total = calculate_occupational_adjustment(total_wpi, variant)
                                    st.write(f"After occupational adjustment: {occ_adj_total}%")
                                    
                                    age_adj_value = calculate_age_adjustment(occ_adj_total, age)
                                    st.write(f"After age adjustment: {age_adj_value}%")
                                    
                                    if age_adj_value is not None:
                                        final_ratings.append(float(age_adj_value))
                                        rating_strings.append(f"{body_part}: {age_adj_value}% WPI")
                                    else:
                                        rating_strings.append(f"{body_part}: Age adjustment failed")
                                else:
                                    rating_strings.append(f"{body_part}: Could not find variant")
                            except Exception as e:
                                rating_strings.append(f"{body_part}: Error - {str(e)}")
                                st.error(f"Error processing {body_part}: {str(e)}")
                        
                        # Calculate final combined rating
                        if final_ratings:
                            total_pd = combine_ratings(final_ratings)
                            
                            # Display results
                            st.write("\n### Rating Breakdown")
                            for rating in rating_strings:
                                st.write(rating)
                            st.success(f"**Final Combined Rating:** {total_pd}%")
                        else:
                            st.warning("No valid ratings to combine")
                        
                        # Process dental ratings
                        if dental_ratings:
                            dental_wpi = dental_ratings.get("wpi", 0)
                            dental_pain = dental_ratings.get("pain", 0)
                            st.write(f"\nDental Ratings: {dental_wpi}% WPI + {dental_pain}% Pain")
                    except Exception as e:
                        st.error(f"Error processing ratings: {str(e)}")
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
