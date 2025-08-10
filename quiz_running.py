# --------------------------------------------------------------------------------
# Block 1: gettin all the libraries we need
# --------------------------------------------------------------------------------
# ok so we need all this stuff to make the app work.
# streamlit: this is for the web app itself, the user interface part.
import streamlit as st
# langchain_groq: this lets us use the super fast LLM from Groq.
from langchain_groq import ChatGroq
# langchain.prompts: we use this to build a template, basically a set of instructions for the LLM.
from langchain.prompts import PromptTemplate
# dotenv: this is just to load our API key from the .env file so we dont have to write it directly in the code.
from dotenv import load_dotenv
# langchain_core.output_parsers: these help get the output from the LLM into a format we can actually use, like a simple string or JSON.
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
# bs4 (BeautifulSoup): this helps clean up the messy HTML code from a website and pull out the text.
from bs4 import BeautifulSoup
# requests: this is for grabbing data from a URL, like the HTML of a webpage.
import requests
# readability: this library is really good at finding the main article content on a page and getting rid of junk like ads and menus.
from readability import Document
# json: the LLM will give us data in JSON format, so we need this to work with it in Python.
import json
# re (Regular Expressions): for finding the clean JSON inside the LLM's response, which can sometimes be a bit messy. its a pattern matching tool.
import re




# --------------------------------------------------------------------------------
# Block 2: loading up the API keys and getting set up
# --------------------------------------------------------------------------------
# alright, lets load the environment variables.
# this line will look for a .env file and load any keys inside it.
load_dotenv()




# --------------------------------------------------------------------------------
# Block 3: getting the LLM (the "brain") and the Prompt ready
# --------------------------------------------------------------------------------
# here we're setting up the LLM we're gonna use.
# we're using Groq's "llama-3.1-8b-instant" model cause its really fast.
model = ChatGroq(model_name="llama-3.1-8b-instant")

# now we're making a script for the LLM to follow.
# its a PromptTemplate, like a form that we fill out to tell the LLM what to do.
quiz_from_text_prompt = PromptTemplate(
    # these are the variables in the template that we'll fill in later.
    # in this case, 'num_questions' and 'article_text'.
    input_variables=["num_questions", "article_text"],
    # partial_variables means a part of the template is already pre-filled.
    # here we're telling the LLM the exact JSON format to use so it doesnt mess up.
    partial_variables={"format_instructions": JsonOutputParser().get_format_instructions()},
    # and this is the main script we're giving the LLM. all the rules are here.
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

# here we're creating a processing pipeline, they call it a "chain".
# it just defines the sequence of steps for our data.
# 1. first, user input goes into the 'quiz_from_text_prompt' to build the full prompt.
# 2. then, that prompt goes to the 'model' (our LLM).
# 3. finally, whatever the LLM gives back, 'StrOutputParser' cleans it up into a simple string.
chain = quiz_from_text_prompt | model | StrOutputParser()




# --------------------------------------------------------------------------------
# Block 4: The Streamlit App's User Interface (UI)
# --------------------------------------------------------------------------------
# setting the page title and making the layout wide to use the whole screen.
st.set_page_config(page_title="AI Quiz Generator", layout="wide")
# this is the main title you see on the page.
st.title("AI Quiz Generator from News Article")

# -- The Magic of Session State --
# in streamlit, the whole script reruns from top to bottom every time you click a button.
# so, to remember stuff, we need to use session state. its like the app's short-term memory.
# here we're just making sure 'quiz_data' exists in the memory, if not, we create it as empty (None).
if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
# same thing for 'submitted'. this will remember if the user has submitted the quiz.
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
# and for 'article_text'. this is where we'll store the text we get from the website.
if 'article_text' not in st.session_state:
    st.session_state.article_text = ""

# now we make the sidebar on the left of the screen.
with st.sidebar:
    st.header("Configuration")
    # a text input box for the user to paste the article URL.
    url = st.text_input("Enter News Article URL", "https://www.ndtv.com/world-news/india-endorses-us-russia-summit-in-alaska-cites-pm-modis-remark-9053353")
    
    # this is the first button. its job is just to grab the article and show it.
    if st.button("Fetch & Preview Article"):
        # whenever we get a new article, we should clear out any old quiz.
        st.session_state.quiz_data = None
        st.session_state.submitted = False
        # if the user clicks the button without a URL, show an error.
        if not url:
            st.error("Please enter a URL.")
            st.session_state.article_text = ""
        else:
            # this spinner tells the user "hey, i'm working on it...".
            with st.spinner("Fetching article..."):
                # we use a try...except block so the app doesnt crash if something goes wrong, like the website is down.
                try:
                    cleaned_url = url.strip() # get rid of any accidental spaces around the url.
                    # now 'requests' grabs the whole HTML content from that URL.
                    html = requests.get(cleaned_url).text
                    # 'readability' takes that HTML and pulls out just the main article content.
                    doc = Document(html)
                    clean_html = doc.summary()
                    # 'BeautifulSoup' takes that clean HTML and strips out all the tags to give us plain text.
                    soup = BeautifulSoup(clean_html, "html.parser")
                    # just cleaning up the text a bit more, getting rid of extra lines and spaces.
                    text = " ".join(soup.get_text(separator="\n", strip=True).split())
                    # and finally, save our clean text into the session state memory.
                    st.session_state.article_text = text
                except Exception as e:
                    # if any error happens in the 'try' block, we'll tell the user what happened.
                    st.error(f"An error occurred while fetching the article: {str(e)}")
                    st.session_state.article_text = ""

    # this whole section will only show up after the article text has been fetched.
    if st.session_state.article_text:
        st.markdown("---")
        st.subheader("Quiz Settings")
        # a slider so the user can pick how many questions they want.
        num_questions = st.slider("Number of questions", 1, 10, 5)

        # this is the second button. this is where the main action happens.
        if st.button("Generate Quiz"):
            with st.spinner("Generating quiz..."):
                try:
                    # grab the article text that we already have stored in the session state.
                    article_text_for_quiz = st.session_state.article_text
                    
                    # now we call our LLM chain.
                    # we give it the article text and the number of questions the user wants.
                    raw_output = chain.invoke({
                        "article_text": article_text_for_quiz,
                        "num_questions": num_questions
                    })

                    # sometimes the LLM likes to add extra text around the JSON.
                    # this regex just pulls out the part that starts with '[' and ends with ']', which is our JSON data.
                    match = re.search(r"\[.*\]", raw_output, re.DOTALL)
                    if match:
                        # if we found the JSON, convert it from a string to a Python list/dictionary.
                        json_str = match.group(0)
                        result = json.loads(json_str)
                        
                        # now we double-check if the LLM gave us good data.
                        is_valid = True
                        for q_item in result:
                            # every question has to have a 'question', 'options', and 'correct_answer'.
                            if not all(key in q_item for key in ["question", "options", "correct_answer"]):
                                is_valid = False
                                st.error("The LLM returned incomplete data. Please try again.")
                                break
                        
                        # if everything looks good, save the quiz data to the session state.
                        if is_valid:
                            st.session_state.quiz_data = result
                            st.session_state.submitted = False
                            # *** THIS IS THE KEY STEP FOR THIS FEATURE ***
                            # after the quiz is made, we clear the article text from the session state.
                            # this makes it disappear from the screen. gives it that exam feel.
                            st.session_state.article_text = "" 
                            st.success("Quiz Generated! Good luck!")
                    else:
                        st.error("Could not find valid JSON. Please try again.")
                
                except json.JSONDecodeError:
                    st.error("Failed to parse LLM output. The format was invalid.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")




# --------------------------------------------------------------------------------
# Block 5: showing stuff on the main screen
# --------------------------------------------------------------------------------
# this part will only show the article text IF we have it in our session state memory,
# AND the quiz has not been generated yet.
if st.session_state.article_text:
    st.subheader("Article to be Quizzed On")
    st.info("Review the text below. When you are ready, click 'Generate Quiz' in the sidebar.")
    # st.markdown with ">" makes a blockquote, which just makes the text look a bit different.
    st.markdown(f"> {st.session_state.article_text}")
    st.divider()

# this part only runs when the quiz data exists in our session state.
if st.session_state.quiz_data:
    quiz_data = st.session_state.quiz_data
    
    st.subheader("Quiz Time!")
    # we use st.form so the user can answer all the questions before hitting 'Submit'.
    # this stops the page from reloading every time they click a radio button.
    with st.form("quiz_form"):
        # now we loop through each question in our quiz_data.
        for idx, q in enumerate(quiz_data, start=1):
            st.markdown(f"**Q{idx}. {q.get('question', 'Error: Question not found')}**")
            
            # create the radio buttons (options) for each question.
            user_choice = st.radio(
                label="Options",
                options=list(q.get("options", {}).keys()), # the options will be 'A', 'B', 'C', 'D'
                # format_func is just to make the options look nice, like "A: Option text".
                format_func=lambda opt: f"{opt}: {q.get('options', {}).get(opt, '')}",
                key=f"q_{idx}", # every radio button needs a unique key.
                label_visibility="collapsed", # hide the "Options" label, its not needed.
                disabled=st.session_state.submitted, # if the quiz is submitted, disable the options.
                index=None # so that no option is selected by default.
            )
        
        # the submit button for the form.
        submitted = st.form_submit_button("Submit Answers")
        if submitted:
            # if the user clicks submit, we set 'submitted' to True in our memory.
            st.session_state.submitted = True
            # st.rerun() just reloads the page immediately to show the results.
            st.rerun()

# this final section runs only after the quiz has been submitted.
if st.session_state.submitted and st.session_state.quiz_data:
    score = 0
    # loop through the questions again to calculate the score.
    for idx, q in enumerate(st.session_state.quiz_data, start=1):
        # get the user's selected answer from the session state.
        user_choice = st.session_state[f'q_{idx}']
        # get the correct answer.
        correct_answer = q.get('correct_answer')
        
        # compare them.
        if user_choice == correct_answer:
            score += 1

    # display the final score.
    st.write(f"### Your Score: {score} / {len(st.session_state.quiz_data)}")
    st.info("The correct answers are marked in green below.")

    # now show a detailed breakdown of the results.
    for idx, q in enumerate(st.session_state.quiz_data, start=1):
        st.markdown(f"**Q{idx}. {q.get('question', 'Error: Question not found')}**")
        user_choice = st.session_state[f'q_{idx}']
        correct_answer = q.get('correct_answer')

        # loop through each option and show it with color-coding.
        for opt_key, opt_val in q.get("options", {}).items():
            # if the option is the correct answer, show it in a green success box.
            if correct_answer and opt_key == correct_answer:
                st.success(f"{opt_key}: {opt_val} (Correct Answer)")
            # if the user picked this option and it was wrong, show it in a red error box.
            elif user_choice and opt_key == user_choice:
                st.error(f"{opt_key}: {opt_val} (Your Answer)")
            # just show all the other options normally.
            else:
                st.write(f"{opt_key}: {opt_val}")
        st.divider() # put a line after each question to separate them.