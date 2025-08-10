from bs4 import BeautifulSoup           ## Python library to parse HTML and extract data
import requests                          ## Used to make HTTP requests to fetch the HTML of the news page.
from readability import Document         ##  Part of the readability-lxml package, isolates the main readable content of a webpage (removes sidebars, ads, etc.).

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

article_text = soup.get_text(separator="\n", strip=True)   ## Puts each block of text on a new line.
print(article_text)