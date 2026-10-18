# Campus Customs – Design (Problem 10)

**Goal:** an old-world but clean, traditional Ivy League storefront that tells a story, promotes
school spirit and makes shoppers feel part of the school, so they stay longer and buy.

## What I changed and why it helps customers buy

| Change | What it is | Why it helps customers stick around and buy |
|---|---|---|
| **"Go Yale! Beat Harvard!" on every page** | A spirit bar above the menu and a spirit strip in the footer of every page, plus a big spirit band at the end of Home | Turns shopping into belonging. Every page reminds the shopper which team they're on, and the rivalry is the strongest emotional reason to buy Yale gear. |
| **Full Yale palette** | Yale Blue `#00356B`, medium blue `#286DC0`, light blue `#63AAFF`, dark and mid grays `#222222` `#4A4A4A`, warm gray `#978D85`, light gray `#DDDDDD`, off-white `#F9F9F9`, Yale green `#5F712D` and Yale orange `#BD5319` | The colors shoppers already associate with Yale make the shop feel official and trustworthy. Green marks fields of study and orange marks game day and sports, so color also helps people find their way. |
| **Collegiate type** | Libre Caslon (classic book serif) for headings, product names and prices; Graduate (varsity lettering) only for spirit moments (the spirit bar, ticker prices, pennants); Source Sans for easy reading | Caslon gives the old-world, library-and-ivy feel; varsity letters feel like a team jacket. Keeping varsity type to spirit moments keeps the page clean. |
| **Campus at dusk hero** | An original illustration of Gothic towers, lit windows, ivy and three happy students in Campus Customs hoodies (one waving a GO YALE pennant), with the line "Wear the story of New Haven." The students rise in once when the page opens. | Shoppers picture themselves, or their son or daughter, on campus in the gear. Showing the clothes being worn by happy students sells the feeling, not just the shirt. |
| **New arrivals ticker** | A slow scrolling strip of in-season and game-day items with prices under the hero; it pauses when you point at it, and every name is a link | Creates gentle urgency ("what's new") and puts real products and prices in front of shoppers within seconds of arriving. |
| **Shop by tradition pennants** | Four pennant-shaped links: Game day, On the ice, In the boardroom, In the studio | Shoppers think in moments and identities ("I'm going to The Game", "I'm at SOM"), not garment types. One click takes them to matching items with the matching theme. |
| **Cards that rise in** | Product rows rise into place, slightly staggered, the first time they scroll into view; cards have a limestone photo backdrop, a Yale Blue rule and Caslon names | Draws the eye down the page to keep people browsing, and the clean card style lets the product photos stand out. |
| **Sports themes** | Searching a sport (chat or Products search, e.g. "hockey") shows a banner with that sport's playing surface: a rink, a field with goalposts, a court, a diamond, water with a racing shell, a track and more | The shopper sees their sport, not just a list. The page feels made for them, which makes the item feel like part of their team identity. |
| **Profession themes for schools and majors** | Searching a school or major (e.g. "School of Management") shows professionals at work in that field: businesspeople with a briefcase against a skyline for SOM, a courthouse for Law, a clinic for Medicine, a blueprint arch for Architecture, and more | Shoppers picture where the degree takes them ("from the classroom to the boardroom"), so the purchase feels like an investment in their future self. |
| **Chat that talks like someone in that field** | The chat becomes a persona that fits the search: a hockey coach ("let's get you game-ready"), an SOM alum and consultant, a doctor, an architect and so on. The persona's name, role and medallion appear in the chat header, and it greets the shopper in character. Facts still come only from the database tools. | Talking to "Coach Casey" or "Morgan from SOM" feels like advice from someone who belongs, which builds trust and makes the recommendation more persuasive. |
| **Original crest and footer** | An original Campus Customs crest (shield, chevron, open book and "CC") in the menu and footer, plus a short story of the shop | Gives the store a heritage feel without copying Yale's trademarked shield or logo. |

## How the themes work

- `backend/themes.py` lists 16 sports and 11 schools and fields of study, each with keywords, a
  banner line and a chat persona. The longest matching keyword wins, so "field hockey" beats
  "hockey". If the question has no theme words, the theme comes from what most of the shown
  products have in common.
- `POST /api/chat` returns `theme` with the reply, and the website keeps the theme for follow-up
  questions. `GET /api/themes/detect?q=` does the same for the Products search box.
- The agent gets the persona through its instructions (`agent.py`, "Persona for this
  conversation"), and `prompts/prompt.md` has a "Sport and field-of-study personas" section.
  The safety rules are unchanged.
- Tests: `backend/tests/test_design.py`.

## Accessibility and polish

All motion (ticker, rise-in cards, students) stops for shoppers who set "reduce motion". Text
stays readable over the hero thanks to a soft blue shade behind it. The layout works down to
phone width, and keyboard focus is clearly outlined in light blue.

## Notes

The campus, students, sports and profession scenes are original vector illustrations drawn for
this site, so there are no stock-photo or trademark issues. Real photos of students wearing
Campus Customs gear can replace the illustrations later.
