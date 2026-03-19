import streamlit as st
import time
import PyPDF2
import docx
from openai import OpenAI

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Multi-Agent Business Bureau", page_icon="👔", layout="wide")
st.title("🤖 Multi-Agent Business Analysis Bureau")
st.markdown("Upload a business plan (TXT/PDF/DOCX) and watch the virtual consulting team deconstruct and analyze it step by step.")

# ==========================================
# 2. Engine Ignition
# ==========================================
# ⚠️ Using st.secrets to securely read the API key from the cloud environment
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"] 
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
MODEL_NAME = "deepseek-chat"

# ==========================================
# 3. Team Initialization (Agent Roles)
# ==========================================
agents = {
    "Researcher": {
        "name": "Chief Information Officer (Researcher)",
        "icon": "🕵️‍♂️",
        "role_desc": "You are the [Chief Information Officer]. Extract the core elements of the business model from the user's data: target audience, product/service, and revenue model. Output in a structured and concise format."
    },
    "Strategist": {
        "name": "Business Strategist (Strategist)",
        "icon": "🧠",
        "role_desc": "You are the [Business Strategist]. Based on the previous info, use frameworks like 'Porter's Five Forces' or 'SWOT Analysis' to deeply deconstruct the business logic, pointing out core competitiveness and market opportunities."
    },
    "Critic": {
        "name": "Critical Reviewer (Critic)",
        "icon": "🧐",
        "role_desc": "You are the [Critical Reviewer]. From a highly critical investor's perspective, identify fatal flaws, overly optimistic assumptions, and financial risks in this business model."
    },
    "Operations": {
        "name": "Operations Architect (Operations)",
        "icon": "🏗️",
        "role_desc": "You are the [Operations Architect]. Responsible for grounding the business ideas. You MUST use ASCII characters (like ├── and └──) to draw a clear [Organizational Chart Tree], showing what core departments need to be established. Then briefly explain how they collaborate in daily operations."
    },
    "Writer": {
        "name": "Chief Writer (Writer)",
        "icon": "✍️",
        "role_desc": "You are the [Chief Writer]. Summarize all the viewpoints of the above four experts (especially the Operations Architect's tree chart), and write a well-structured 'Business Model Analysis Executive Summary'. It MUST include: 1. Project Overview 2. Advantage Analysis 3. Risks 4. Organizational Structure Tree 5. Final Investment Recommendation."
    }
}

# ==========================================
# 4. File Parsing Core 
# ==========================================
def read_uploaded_file(uploaded_file):
    """Parse the content of the file uploaded from the frontend"""
    extracted_text = ""
    try:
        if uploaded_file.name.endswith(".txt"):
            extracted_text = uploaded_file.getvalue().decode("utf-8")
        elif uploaded_file.name.endswith(".pdf"):
            reader = PyPDF2.PdfReader(uploaded_file)
            extracted_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        elif uploaded_file.name.endswith(".docx"):
            doc = docx.Document(uploaded_file)
            extracted_text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
            
        # Truncation protection to prevent context overflow
        if len(extracted_text) > 30000:
            st.warning(f"The file is too long, truncated to the first 30,000 characters for analysis.")
            extracted_text = extracted_text[:30000]
            
        return extracted_text
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        return None

# ==========================================
# 5. UI Layout & Main Logic
# ==========================================
# Left Sidebar: File Upload
with st.sidebar:
    st.header("📂 Data Input")
    uploaded_file = st.file_uploader("Upload a business plan or report", type=["txt", "pdf", "docx"])
    start_btn = st.button("🚀 Start Multi-Agent Analysis", type="primary", use_container_width=True)

# Main Content Area: Agent Workflow
if start_btn:
    if not uploaded_file:
        st.warning("👈 Please upload a file on the left sidebar first!")
    else:
        # 1. Read the file
        with st.status("Parsing file content...", expanded=False) as status:
            business_context = read_uploaded_file(uploaded_file)
            if business_context:
                status.update(label=f"File parsed successfully! Total {len(business_context)} characters.", state="complete", expanded=False)
            else:
                status.update(label="File parsing failed", state="error")
                st.stop()

        # 2. Initialize global context
        shared_context = [
            {"role": "user", "content": f"Please read the following business project information and conduct a deep analysis:\n\n{business_context}"}
        ]
        
        st.divider()
        st.subheader("💬 Real-time Thinking and Discussion Process")

        # 3. Agent Relay Pipeline
        workflow_order = ["Researcher", "Strategist", "Critic", "Operations", "Writer"]
        
        for name in workflow_order:
            agent = agents[name]
            
            # Use Streamlit's chat message component
            with st.chat_message(name, avatar=agent["icon"]):
                st.markdown(f"**{agent['name']}** is thinking...")
                
                # Placeholder for the typewriter effect
                message_placeholder = st.empty()
                full_response = ""
                
                # Construct message history (Added English instruction)
                messages = [{"role": "system", "content": agent["role_desc"] + "\nPlease strictly adhere to your role and output your response entirely in English."}] + shared_context
                
                try:
                    # stream=True for typewriter effect
                    stream = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1500,
                        stream=True 
                    )
                    
                    # Render typewriter effect in real-time
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            full_response += chunk.choices[0].delta.content
                            # Add cursor ▌ for a realistic typing feel
                            message_placeholder.markdown(full_response + "▌") 
                            
                    # Remove cursor when finished
                    message_placeholder.markdown(full_response)
                    
                    # Append current Agent's output to the global context
                    shared_context.append({"role": "assistant", "name": name, "content": f"[Output from {name}]:\n{full_response}"})
                    
                except Exception as e:
                    st.error(f"API Request Error: {e}")
                    st.stop()
                    
                time.sleep(1) # Slight pause for visual transition

        # 4. Process complete, provide final report download
        st.success("🎉 All agents have finished their analysis! The final executive summary is ready.")
        
        # Use Writer's final output as the downloadable report
        final_report = shared_context[-1]["content"]
        st.download_button(
            label="📥 Download Full Analysis Report (TXT)",
            data=final_report,
            file_name=f"Report_{uploaded_file.name}.txt",
            mime="text/plain",
            type="primary"
        )