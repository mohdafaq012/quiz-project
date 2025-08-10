from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
import streamlit as st
from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser

# ----------------------
# 1. Setup
# ----------------------
load_dotenv()


# ----------------------
# 2. Load the article    ## using beutifulsoup
# ----------------------


from bs4 import BeautifulSoup     ## Python library to parse HTML and extract data
import requests               ## Used to make HTTP requests to fetch the HTML of the news page.
from readability import Document       ##  Part of the readability-lxml package, isolates the main readable content of a webpage (removes sidebars, ads, etc.).

url = "https://www.ndtv.com/world-news/india-endorses-us-russia-summit-in-alaska-cites-pm-modis-remark-9053353"
html = requests.get(url).text
## Sends an HTTP GET request to the URL.
## .text returns the HTML source code as a string.

doc = Document(html)   ##  Initializes Readability’s article parser on the HTML content.
clean_html = doc.summary()  # main article HTML only Returns only the main article HTML (removes headers, footers, menus, ads, etc.).
soup = BeautifulSoup(clean_html, "html.parser")  ##Creates a BeautifulSoup object to work with the article HTML.
# "html.parser" → Tells BeautifulSoup to use Python’s built-in HTML parser.

# Remove images
for img in soup.find_all("img"):   ## Finds every <img> tag in the article HTML.
    img.decompose()           ## Completely removes those tags from the parsed document.

text = soup.get_text(separator="\n", strip=True)   ## Puts each block of text on a new line.
print(text)


    
# ----------------------
# 3. Setup LLM 
# ----------------------
model = ChatGroq(model_name="llama-3.1-8b-instant")


quiz_from_text_prompt = PromptTemplate(
    input_variables=["num_questions", "article_text"],
    template="""
You are a quiz generator.

You will be given a text passage.
Your task:
1. Read and understand the text.
2. Create {num_questions} multiple-choice questions **only** from the information in the text.
3. Do not use any external knowledge.
4. Each question should have exactly 4 options: A, B, C, D.
5. Clearly mark the correct answer.
6. Output format must be JSON in this exact structure:
[
  {{
    "question": "Question text?",
    "options": {{
      "A": "Option 1",
      "B": "Option 2",
      "C": "Option 3",
      "D": "Option 4"
    }},
    "correct_answer": "A"
  }},
  ...
]

Text passage:
\"\"\"{article_text}\"\"\"

Generate the quiz now:
"""
)

parser = JsonOutputParser()


chain = quiz_from_text_prompt | model | parser
result = chain.invoke({
    "article_text": text,
    "num_questions": 5
})

print(result)

# print(f"Loaded {len(docs)} documents")

# # ----------------------
# # 4. Run the LLM on each article
# # ----------------------
# for doc in docs:
#     summary = chain.run(article_text=doc.page_content)
#     print("\n--- Summary ---\n")
    # print(summary)


  