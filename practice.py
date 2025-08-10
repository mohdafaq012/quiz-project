import streamlit as st
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from bs4 import BeautifulSoup
import requests
from readability import Document
import json
import re

# ----------------------
# 1. Setup
# ----------------------
# Load environment variables from a .env file (for API keys)
load_dotenv()

# ----------------------
# 2. Setup LLM & Parser
# ----------------------
# Initialize the Groq model for fast inference
model = ChatGroq(model_name="llama-3.1-8b-instant")

# Define the prompt template for the quiz generator
# This structures the input to the LLM
quiz_from_text_prompt = PromptTemplate(
    # These are the variables the prompt expects
    input_variables=["num_questions", "article_text"],
    # We use LangChain's JSON parser to get formatting instructions
    # This helps the LLM know exactly what JSON structure to output
    partial_variables={"format_instructions": JsonOutputParser().get_format_instructions()},
    template="""
You are a quiz generator that must follow the rules strictly.

Rules:
1. Use ONLY the provided text.
2. Create {num_questions} MCQs with 4 options (A–D).
3. You MUST include the "correct_answer" key for every question. This is mandatory.
4. Do not invent facts.
5. Keep each question under 25 words.
6. Output must be valid JSON that adheres to the schema below. Do not add any text before or after the JSON.

{format_instructions}

Text passage (max 1500 words):
\"\"\"{article_text}\"\"\"

Generate the quiz now:
"""
)

# Create the processing chain using LangChain Expression Language (LCEL)
# 1. quiz_from_text_prompt: Formats the user input into a full prompt.
# 2. model: Sends the prompt to the LLM.
# 3. StrOutputParser: Extracts the string content from the LLM's response.
chain = quiz_from_text_prompt | model | StrOutputParser()

# ----------------------
# 3. Streamlit UI
# ----------------------
# Configure the page title and layout
st.set_page_config(page_title="AI Quiz Generator", layout="wide")
st.title("📚 Quiz Generator from News Article")

# Initialize session state variables to hold data across reruns
# 'quiz_data' stores the generated questions and answers
if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
# 'submitted' tracks whether the user has submitted their answers
if 'submitted' not in st.session_state:
    st.session_state.submitted = False

# Create a sidebar for user inputs
with st.sidebar:
    st.header("Article")
    url = st.text_input("Enter News Article URL", "https://www.ndtv.com/world-news/india-endorses-us-russia-summit-in-alaska-cites-pm-modis-remark-9053353")
    num_questions = st.slider("Number of questions", 1, 10, 5)

    # Button to trigger the quiz generation
    if st.button("Generate Quiz"):
        if not url:
            st.error("Please enter a URL.")
        else:
            # Show a spinner while processing
            with st.spinner("Fetching article and generating quiz..."):
                try:
                    # Clean the URL to prevent errors
                    cleaned_url = url.strip()
                    if not cleaned_url:
                        st.error("URL is empty. Please enter a valid URL.")
                        st.stop()
                    
                    # Scrape and parse the article text
                    html = requests.get(cleaned_url).text
                    doc = Document(html)
                    clean_html = doc.summary()
                    soup = BeautifulSoup(clean_html, "html.parser")
                    text = " ".join(soup.get_text(separator="\n", strip=True).split())

                    # Invoke the LLM chain to get the raw string output
                    raw_output = chain.invoke({
                        "article_text": text,
                        "num_questions": num_questions
                    })

                    # Use regex to find and extract the JSON list from the raw output
                    match = re.search(r"\[.*\]", raw_output, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                        result = json.loads(json_str)
                        
                        # Validate that the LLM returned a complete dataset
                        is_valid = True
                        for q_item in result:
                            if not all(key in q_item for key in ["question", "options", "correct_answer"]):
                                is_valid = False
                                st.error("The LLM returned incomplete data (missing keys). Please try generating again.")
                                break
                        
                        # If data is valid, store it in the session state
                        if is_valid:
                            st.session_state.quiz_data = result
                            st.session_state.submitted = False # Reset submission status
                            st.success("✅ Quiz Generated!")
                    else:
                        st.error("⚠️ Could not find valid JSON in the LLM response. Please try again.")
                
                # Handle potential errors during the process
                except json.JSONDecodeError:
                    st.error("⚠️ Failed to parse LLM output. The format was invalid.")
                except Exception as e:
                    st.error(f"⚠️ An error occurred: {str(e)}")

# This section runs only if quiz data exists in the session state
if st.session_state.quiz_data:
    quiz_data = st.session_state.quiz_data
    
    # Use a form to group the quiz questions and the submit button
    with st.form("quiz_form"):
        # Loop through each question in the quiz data
        for idx, q in enumerate(quiz_data, start=1):
            # Display the question number and text safely using .get()
            st.markdown(f"**Q{idx}. {q.get('question', 'Error: Question not found')}**")
            
            # Create radio buttons for the options
            user_choice = st.radio(
                label="Options",
                # Get the option keys (A, B, C, D)
                options=list(q.get("options", {}).keys()),
                # Format the display to show "A: Option text"
                format_func=lambda opt: f"{opt}: {q.get('options', {}).get(opt, '')}",
                key=f"q_{idx}",
                label_visibility="collapsed",
                # Disable the buttons after submission
                disabled=st.session_state.submitted,
                # --- KEY FIX: Set index=None to have no default selection ---
                index=None
            )
        
        # The submit button for the form
        submitted = st.form_submit_button("Submit Answers")
        if submitted:
            st.session_state.submitted = True
            # Rerun the script to update the UI (disable buttons and show score)
            st.rerun()

# This section runs only after the user has submitted their answers
if st.session_state.submitted and st.session_state.quiz_data:
    score = 0
    # Calculate the score by comparing user answers with correct answers
    for idx, q in enumerate(st.session_state.quiz_data, start=1):
        # Retrieve the user's answer from session state using the widget's key
        user_choice = st.session_state[f'q_{idx}']
        correct_answer = q.get('correct_answer')
        
        if user_choice == correct_answer:
            score += 1

    # Display the final score
    st.write(f"### 🎯 Your Score: {score} / {len(st.session_state.quiz_data)}")
    st.info("The correct answers are marked in green below.")

    # Display a detailed breakdown of the results
    for idx, q in enumerate(st.session_state.quiz_data, start=1):
        st.markdown(f"**Q{idx}. {q.get('question', 'Error: Question not found')}**")
        user_choice = st.session_state[f'q_{idx}']
        correct_answer = q.get('correct_answer')

        # Loop through options to display them with color-coding
        for opt_key, opt_val in q.get("options", {}).items():
            if correct_answer and opt_key == correct_answer:
                st.success(f"{opt_key}: {opt_val} (Correct Answer)")
            elif user_choice and opt_key == user_choice:
                st.error(f"{opt_key}: {opt_val} (Your Answer)")
            else:
                st.write(f"{opt_key}: {opt_val}")
        st.divider()