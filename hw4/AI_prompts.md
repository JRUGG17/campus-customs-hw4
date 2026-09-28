# AI Prompt Log
## Problem 1 — Vibe Coder Prompts

### Prompt 1

```
start AI_prompts.md and keep it updatred as we work pls. going to have a problem name and title for each problem. need at least one prompt i typed maybe a follow up prompt if i needed it (and a sentence on what was lacking after first)

i need running site, database writes, and screenshots as evidence

Problem 1: vibe coder prompts
goal is to build campus customs areal customer webside with a helpful chatbot. were doingi a react +vite typescrpte front end and a python fastAPI backend whose brain is a pydanticai agent. shoppers should be able to browse products, creare an account, chat about merch , see matching items appear on page, and get honest answers about price and stock from a local db 

have a zip with campus_customs.db with tables for stuff. gotta research yalebulldogs.com to learn the syyle of the campus customs page and info fot the agent prompt 

have put data zip in hw4. 

questions?
```

### Follow-up prompt 1

The first prompt didn't lay out the full scope of the assignment or settle whether the site should be serious or ironic.

```
1. we need to take it one problem at a time, but at a high level we;re going to be analyzing the db, buidling a campus customs website, creating an account and logging in, doing the pydanticAI agent backend, doing some tools- product info and stock, char search that updates the page, customer memory, usability improvements, styling the site, testing the sit, an audit trail, safetey and final touches on harness, and then push to github and submit the url

2. lets play it straight. can i take that ironic element out of my agent in general please actually.
```

## Problem 2 — Analyze the Database

### Prompt 1

```
Problem 2: Analyze the database

i need to look at campus_customs.db and try to understand catalogue, inventory and users but the text looks cursed af. whats going on there

also need to start output/harness.md where we're gonna wirte down each table and its fields, and one short line on why each field matters for the shop or chatbot.

we're gonna keep adding to this harness file in later problems too
```

## Problem 3 — Build the Campus Customs Website

### Prompt 1

```
Problem 3: build the campus customs website

we're scafolding a react + vite+ typescript front end for campus customs. put a nav bar up top that links to the main pages:
home
products
about us
log in 
create account

we're gonna pull campus customs style wording from the yalebulldogs site for home and about us but should write this in own voice and not copy it from the site.

on the products page, show product images from catalogue (use image paths in db) with bsic produc info (price, name, short description)

each product opens a singe-item page (large image on one side, ful product text on the other- descroption, price, sizes/stock when have the,. clinking a card on products should take shopper there

add a chat interfce in the bottom right of the site (floatig chat panel fine) it does not need to talk to an agent yet, a stub that will call backend later is enough for now 

gona need small API soon to read the database, fine to start a simple FastAPI app in backend/main.py to serve products and images then grow it into the agent backend in problem 5

good?
```

## Problem 4 — Create an Account and Log In

### Prompt 1

```
Problem 4: create an account and login

build a normal create-account/login flow

create account: first name, last name, email , password (confirm password maybe too) 

log in: email and password

new accounts go into the users table. store passwords securely so hackers cant get em

seed db has a test user test@campuscustoms.yale.edu that i can try to test with

but also going to be creating new account 

gotta update output/harness.md with how auth works (what store for user and how passwords are secured)

questions?
```

## Problem 5 — PydanticAI Agent Backend

### Prompt 1

```
Problem 5: PydanticAI agent backend

build the shop chatbot as a PydanticAi agent behind fastAPI plugged into frontend widget. put API app in backend/main.py (file we run with Uvicorn). Keep the agent as these four files next to it (same idea as hw3)
1. backend/prompts/prompt.md- system prompt (grow this file l8r)
2. backend/agent.py- agent entry/wiring
3. backend/tools.py- tools agent can call
4. backend/model/py- pydantic / pydanticAI structrued types

in main.py, expose a chat route so message from site returns as reply from agent (and whatver else you need for products/auth). Will need AI model API key for agent

Put campus vustoms voice anmd safety basics into prompts/prompt.md (will expand tools and saftey later)

Start or update types in models.py for chat replies / prodct card as needed

in output/harness.md, note how front end talks to FastAPI and how agent is loaded (prompt file +model)

make sure backend runs from backend/ folder like below:
uvicorn main:app --reload --port 8000

questions?
```

## Problem 6 — Tools: Product Info and Stock

### Prompt 1

```
Problem 6: Tools: product info and stock

give agent tools that look ip real information from campus_customs.db

product decription, price, how many in stock (by size when customer asks)

agent must use database, should not invent prices or quantities. if size out of stock, say it clearly

expand prompts/prompt.md so agent knows to call these tools for price and stock questions. 

add/update return types in models.py

in output/harness.md list each tool and explain which fields you chose for lookup results and why

good?
```

## Problem 7 — Chat Search That Updates the Page

### Prompt 1

```
Problem 7: chat search that updates the page

add feature to site so when customer asks about a type of item agent should seatch the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info)

this is an api contract; agent returns structured produict matches then the front end renders them on the site

after dyanmic product cards loaded by new feature, make sure same single-item page behavior built in prob 3 still works. each product card- including ones chat just put on the page- should still open that detai view (large image+ full info) when clicked. 

update prompts/prompt.md and output/harness.md so its clear how search results reach page

good?
```

## Problem 8 — Customer Memory

### Prompt 1

```
Problem 8: customer memory

when a shopper is logged in, save chat history in db in appropriate table and reload it when they return. agent should know who is chatting (name,email) ; put in agent deps (or equivilant clear pattern) and/or tools that agent can call.

also pass enough page context that if someon is on prodcut page and asks do "you have this in pink" agent knows which items they mean. Hint- you can put code into the agent context

guests can still chat but history only needs to persist for loggedin users

document in output/harness.md how user chat history is stored, what customer fields agent sees, and how page context is passed 

good?
```

## Problem 9 — Usability Improvements

### Prompt 1

```
Usability improvements 

we got the core stuff working, nice

now we gotta choose and implement 2 front-end usage usability improvements and 2 agent/backend usability improvements.

lets talk some ideas through before we run it i want to discuss

then after write output/usability.md before/as we build. for each improvement, say what we added and why it helps a campus customs shopper or the business

then we gotta make sure all improvements show up when running it. graders are gonna read write up and look for those features

so discuss?
```

### Follow-up prompt 1

The first prompt asked for ideas but didn't choose the improvements or say what I wanted from search and filters, so I narrowed it down and asked about the trade-offs.

```
yeah i was actually thinking we could use a search bar. could it have that dynamic thing we have with the chat? if a shopper knows what they want they can search, most people dont go instinctively to chat. helps business too make sales

breaking it down into categories too so its not 100 on a page. and also a filter thing? like filter by size, color, type if on the all products page anything else obvious?: from business side not overwhelming them with choice so might buyt somthing
life easier for shoppers


backend:
i like the smarter search filters
does turining it into one call make it more efficient? any trade offs?

Maybe find alternatives when a size is sold out or we dont have something that exacly matches what they want: keeps them in the game and might buy something

lets discuss the 2 for each were gonna do before diving in. and how each helps the business or shopper
```

### Follow-up prompt 2

The plan said the backend changes would be faster and save sales, but it didn't show how much better they'd make things or whether the trade-offs were worth it, so I pushed on that before building. The answer led to measuring before and after.

```
for b1 and b2 how does it make things better. and we're sure tradeoffs worth it?
```

### Follow-up prompt 3

After building, I tested it myself. The chat's results box stayed on top of the Products page when I used the search bar, so the search results were hidden until I closed the box, and the price filter only offered "under $X" instead of price ranges.

```
a follow up. I noticed that when the agent reccomoneds smethign and click on it, when i then type something in search it needs me to x out of the agent item before i can see it instead of showing it 

also for the frist filter can we do buckets like under x, x-y, y-z?
```

### Follow-up prompt 4

The filter buttons took up two rows and looked busy next to the sort dropdown, and four price ranges felt like more than shoppers need.

```
instead of buttons can we have the filters in drop downs like the sort currently? would that make it cleaner? also maybe 3 price buckets instead of 4?
```

## Problem 10 — Style the Website

### Prompt 1

```
Problem 10: Style the website

add creative design so the site feels like a real campus customs storefront - fonts, colors, heirarcchy, motion, product presentation, chat feel

more points for more imaginiative and innovative stuff

write output/design.md- what changed and why itll help customers stick around and buy. keep it short and concrete

lets discuss again before launching in: 
do we add little handsome dan bull dogs that pop up behind the home producsts, about us login, create acount when the mouse hovers over them? or too unprofessinal?

should the product cards have a more weighted premum feel. like when the mouse hovers over thme its like a heavier box. idk what that means but it makes sense to me lol

home page is boring, do we need pics? idk if thats allowed. i like the blue and white and grey colors though bc yale. 

what are your thoughts
```

### Follow-up prompt 1

The first prompt was a list of open questions. After the design proposal, this settled which ideas to build and limited Handsome Dan to two places.

```
perf, lets do all that. dan only in chat and pop up with create account, no other dan.
```

### Follow-up prompt 2

After the redesign, the full "Ask Dan" button sat on top of page content (like the "See everything" link and the edges of product cards), so I asked for a way to tuck it away until it's needed.

```
the ask dan thing gets in the way sometimes, there a way to minimize it or like only get it on screen when the mouse goes over to it slightly off screen if that makes sense?
```

## Problem 11 — Site Testing (App Check)

### Prompt 1

```
Problem 11: site testing (app check)

test live site and document in output/app_check.html (a page  i should be able todouble click open)

icnlude clear screenshots and short captions for :
1. chat checking the inventory level of an item (honest stock/price from the DB)
2. the dynamic search result cards appearing after a category question 
3/ one of the usability features added in problem 9 

good? im thinking we took too many screensjots along the way and this is where the screenshots are comoing in
```

### Follow-up prompt 1

The first version of app_check.html packed in a lot of extra material (safety tests, audit details, a fixes table) and embedded the images inside the file, so I asked for a simpler page a grader can scan quickly, with the images kept as separate files.

```
second part to problem 11:
make the html easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot provides. put screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory,png)
```

## Problem 12 — Audit Trail and Safety

### Prompt 1

This was typed at the end of the Problem 11 message by mistake. It's the start of Problem 12.

```
keep an append only output/audit_trail.json of agent-loop activity (time, tool names, short args/result, stop reason) and do not wipe it between runs

also think of some safety rules to give the agent and put them in prompts/prompt.md
```

### Follow-up prompt 1

The first part covered the audit trail and safety rules, but harness.md still read as a problem-by-problem build diary, with no single place explaining the models, tools, safety rules, and how to run the system.

```
Finish output/harness.md so its clear how the system works

model fields in models.py and why you chose them
tools and abilities
safety rules
specs (loop limits, result caps, models, how to run front+back)

also from part 1 do we have prompts/prompt.md where we added some safety rules for the agent?
```

## Problem 13 — Push to GitHub

### Prompt 1

```
Problem 13: put code in a folder named hw4 (think we did that) and push it to a public github repository. do not put real .env, campus_customs.db, or product images in github repo. use gitignore. include .env.example with placeholders only


the agent itsekf is four files under backend/ prompts/prompt.md, agent.py, tools.py and models.py

README.md should explain how to run the front end and back end after placing the data pack

questions?
```
