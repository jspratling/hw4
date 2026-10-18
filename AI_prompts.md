# AI Prompts Log – Homework 4 (Campus Customs)

Evidence for this assignment is the running site, database writes, and screenshots. This file only logs the prompts I typed.

---

## Problem 1: Vibe coder prompts

**Prompt:**
> create ai prompts.md and keep it updated with my work.

**Follow-up prompt:**
> I need one section for each problem to include, the problem number and title, at least one prompt i typed and one follow-up prompt i f needed (and one sentence on what was lacking after the first). For this assignment all i need is my running site, database writes, and screenshots are the evidence. I do not need an extra proof essay beyond these points

**What was lacking after the first:** The first version had no set structure for each problem section and added result notes that weren't needed.

---

## Problem 2: Data Harness

**Prompt:**
> open data/campus_customs.db.  I need to read it and understand the fields on each table.

**Follow-up prompt:**
> start a file output/harness.md. I have to write down each table and its fields and I have to give one short line on why each field matters for the shop or chatbot.  Give me the fields one by one and I will write why the field matters in my own words

**What was lacking after the first:** The first prompt only explained the tables, and nothing was saved to the `output/harness.md` file the assignment needs.

**Follow-up prompt 2:**
> check my answers for completeness and make sure i am answering them correctly

**What was lacking after the second:** All the "why it matters" answers were filled in, but they hadn't been checked for accuracy or completeness.

**Follow-up prompt 3:**
> incorporate my first answer with the updates to complete the sentences for accuracy

**What was lacking after the third:** Three answers (`catalogue.product_id`, `catalogue.search_tags`, `inventory.id`) were still not fully accurate.

---

## Problem 3: Build the Campus Customs website

**Prompt:**
> on catalogue.product_id show product images taken from image_file_path with basic information from catalogue - name, price, short description

**Follow-up prompt:**
> make each product open on a single item page. large image on one side, full product text on the other side, description, size, stock, price when you have them. clicking a card on product should take the shopper there

**What was lacking after the first:** Products only showed as a grid of cards, with no way to open an item and see its full description, sizes and stock.

**Follow-up prompt 2:**
> add a chat interface at the bottom right of the site. start a fastapi app in backend/main.py to serve products and images then grow into the agent backend in problem 5

**What was lacking after the second:** The site had product pages but no chat interface for shoppers, and the backend had no chat endpoint to grow into the agent later.

**Follow-up prompt 3:**
> create a nav bar at the top of the page, it need to include home, products, about us, log in and create account. pull the information and link this to the appropriate addresses to get the correct information

**What was lacking after the third:** The site had no nav bar and no Home, About Us, Log in or Create account pages, so shoppers could only reach the product pages.

---

## Problem 4: Create account and login

**Prompt:**
> build a create-account/loginflow, the create account file needs to require the following: first name, last name, email address, password, confirm password. the password and confirm password must match. then build a log in tab.  this will include email address and password to sign in to get into their accoun.t  once the account is created, it should take them to the login page

**Follow-up prompt:**
> problem 4: store the user name and password. do not show the password.  put a "show password" icon in place that the customer can click on.  do not prefill or populate the password field. do not let the user name or password out of output/harness.md.  Prompt the customer to change the password after 3 failed attempts. send them a reset password link to their email account that is on file.

**What was lacking after the first:** Log-in used a different hash setting than the seeded users, so the seeded test user couldn't log in, there was no show-password icon or reset after failed tries, and `output/harness.md` didn't explain how auth works.

---

## Problem 5: PydanticAI agent backend

**Prompt:**
> build the shop chatbot as a pydanticai agent behind fastapi plug it into my front-end chat widget. put the api app in backend/main.py, keep the agent as these four files next to it backend/prompts/prompt.md, backend/agent.py, backend/tools.py, backend/models.py. In main.py create a chat message route when it comes in from the website to the chatbot.  It needs to returns a reply from the agent to let respond if the product is in stock, verify the price, colors and size. us the ai model api key for the agent

**Follow-up prompt:**
> put campus customs voice and safety basics in prompts/prompt.md. run update types in models.py for chat replies and product cards as needed

**What was lacking after the first:** The agent answered correctly but had no defined Campus Customs voice or safety rules, and the chat reply and product card types had no follow-up question or stock summary.

**Follow-up prompt 2:**
> in output/harness.md how does the frontend talk to fastapi. make sure the backend runs from backend/. show me how it runs

**What was lacking after the second:** There was no write-up of how the front end reaches FastAPI, and the backend was being started from the project root instead of from `backend/`.

---

## Problem 6: Tools: product info and stock

**Prompt:**
> create a test that runs after each customer interaction to make sure the program is given the exact information being asked for, run a test every after every purchase to make sure the inventory is up to date, test all the tools each hour to make sure they run without fail.

**Follow-up prompt:**
> add a purchase now feature and a cart which prompts the customer to checkout now or continue shopping

**What was lacking after the first:** The site had no way to buy anything, so there was no purchase for the inventory test to run after.

**Follow-up prompt 2:**
> I need a tool that looks up a description price and stock by size from the database.  the bot will respond if the item is sold out. prompt.md will tell the agent to use those tools for price and stock quantity questions. models.py will return the right types.  Test this to make sure the prompt works properly. output/harness.md should list each tool and its fields. you can draft the explanation and i can amend it if needed.

**What was lacking after the second:** The tools existed, but the prompt didn't clearly map price and stock questions to tools, the return types didn't spell out sold-out sizes, there was no test of the prompt itself, and `output/harness.md` didn't list the tools and their fields.

---

## Problem 7: Chat search that updates the page

**Prompt:**
> Once a shopper goes into the chat to ask a question about a product, i want the product matches to display on the main page and not just in the chat window

**Follow-up prompt:**
> it should return the item, price and short description of the item

**What was lacking after the first:** The matches showed on the main page, but the cards showed a stock line and the full description instead of just the item, price and a short description.

**Follow-up prompt 2:**
> when a shopper clicks on a card, the price, item description and sizes available should pop up with option to add to shopping cart and to to go checkout.  update prompts/prompt.md and output/harness.md. once the customer types the item in the chat giving the path it took to get to the item searched for.  I need the path logged on how the search reached the page

**What was lacking after the second:** Clicking a card left the page instead of showing the price, description and sizes with Add to cart and checkout in a popup, `prompt.md` and `harness.md` didn't explain how search results reach the page, and nothing logged the path a search took.

---

## Problem 8: Customer memory

**Prompt:**
> I need to store all chat information on each customer that logs in with their name and email address.  once they log in the past chat history needs to populate the chat so they can see where they left off.  it should land them on the last product they looked at landing page. prompt them to ask if they would like to see more styles like their last search or make similar suggestions.

**Follow-up prompt:**
> save logged in chats in output/harness.md. when an customer logs in, the chatbot reads the item that was searched for and recalls it. the bot needs to read the price, description, sizes, if it is in stock.

**What was lacking after the first:** Chats were saved and reloaded, but the welcome back only named the last item without its price, description, sizes or stock, and `output/harness.md` didn't explain how logged-in chats are stored, what customer fields the agent sees, or how page context is passed.

---

## Problem 9: Usability improvements

**Prompt:**
> on the frontend implement faceted search  and clear category navigation (price, size, color,brand), so shoppers can quickly find items. add interactive style toggles (casual, formal) and dynamic images and video previews supported by backend metadata tagging to make the products more engaging and personalized. use plain language navigation labels that match user goals. for the backend ensure that it delivers up to the minute stock levels, seasonal updates and pricing changes. integrate crm and distributor management systems so the backend can feed user profiles, order history, and preferences into the frontend for tailored recommendations

**Follow-up prompt:**
> take my first two suggestions from each and only implement them

**What was lacking after the first:** The first prompt asked for more than the two front-end and two backend improvements the problem calls for, so it had to be narrowed to faceted search, the style toggle with dynamic images, live stock and seasonal pricing, and profile-based recommendations.

---

## Problem 10: Style the website

**Prompt:**
> I want the site to have an old world but clean look and feel.  I want a traditional ivy league look.  I want a college campus in the background with traditional buildings. cozy modern and vintage with yale colors and happy college students wearing the apparel. Use all the yale colors.  display sports themes when someone is searching for a specific sport apparel.  display images of a specific profession when someone searches for a particular major. example, if someone is look for school of management attire, business profession type images need to be displayed.  use college style font, motion cards that rise in a ticker of new arrivals and a chat that feels like you are talking to someone in that particular field or sport or field of study.  I want a dynamic, engaging page that tells a story and makes people want to purchase.  I want to promote school spirit. save this in output/design.md. This will help customers buy because it will make them feel apart of the school. also display "Go Yale! Beat Harvard!" on each page

---

## Problem 11: Site testing (app check)

**Prompt:**
> For problem 11 i need you to make it easy for the grader. Make a heading for each check, screenshot and one sentence of what each proves and what each screen shot shows.  put the screenshots in output/app_check_images/and link them from app_check.html/ with relative paths for each. example app_check_images/inventory.png

---

## Problem 12: Audit trail, safety, finish harness

**Prompt:**
> Add safety rules under prompts/prompt.md. do not make up prices. only use the actual price for each item that is in the system. do not make up stock levels. only use actual stock levels. do not share customer information. do not place orders without the shopper confirming. stay on topic with what the customer is requesting. for panel b finish output/harness.md so it clearly explains how the system works. the fields in models.py, the tools and what the assistant can do with the guardrails the specs, loop limit of 3 loops, cap results to 5, which ai models are used and how to run the frontend and backend

**Follow-up prompt:**
> Add the audit trail under output/audit_trail.json

**What was lacking after the first:** The first prompt covered the safety rules and Panel B (`output/harness.md`) but not Panel A's audit trail, so nothing recorded the agent loop's activity (time, tool, short inputs and results, why it stopped) in `output/audit_trail.json`.

---

## Problem 13: Push to GitHub and submit the URL

**Prompt:**
> Put the code in hw4. and push it to public github repository. on canvas submit to repo url
