# Campus Customs – Usability Improvements (Problem 9)

Two front-end improvements make the shop easier to browse, and two agent/backend improvements
make what the site and the chat assistant say more current and more personal.

---

## Front end 1: Faceted search and clear category navigation

**What I added**

- A filter panel on the **Products** page with:
  - **Category**: Hoodies, Crewnecks & sweatshirts, T-shirts, Quarter-zips, Jackets & fleece, Long sleeves
  - **Price**: Under $40, $40 to $70, Over $70
  - **Size in stock**: XS, S, M, L, XL, XXL. Only items that have that size in stock are shown.
  - **Color**: grouped into simple colors (Navy, Gray, White, Red, and so on)
  - **Brand**: Campus Customs, Champion, Brooks Brothers, Under Armour, District, Hype and Vice
- Category buttons across the top of the Products page for one-click browsing.
- Each option shows how many items match, and options that would return nothing are greyed out.
- A search box, sorting (featured, price low to high, price high to low), a "Clear all" button,
  and a running count such as "14 items".
- The filters are saved in the page address, so a filtered view can be bookmarked, shared or
  reopened with the Back button.

**Why it helps**

A shopper looking for "a navy hoodie in medium under $70" can get there in three clicks instead
of scrolling through 102 products. Showing only sizes that are in stock means they never fall
for an item they can't buy. For the business, faster finding means more completed purchases and
fewer shoppers leaving the site.

---

## Front end 2: Casual / Formal style toggle and dynamic product images

**What I added**

- A **style toggle** (All styles · Casual · Formal) on the Home page and the Products page. Home
  shows a "Shop by style" row that switches instantly when the toggle changes.
- The toggle is driven by **backend metadata tags**. Every product is tagged Casual or Formal
  (for example, quarter-zips, fleece jackets, the bomber jacket and premium crewnecks are
  Formal; tees, hoodies and sports crewnecks are Casual). See Backend 1.
- **Dynamic images**: product photos zoom in smoothly on hover on every product card. On the
  single-item page the photo magnifies wherever the mouse points, so shoppers can inspect
  lettering, crests and fabric.
- Each card shows small labels from the tags (brand, "Formal", "Game day", "Sold out").

**Why it helps**

Many shoppers are buying for an occasion, such as an interview, a campus event or a gift for a
parent, rather than hunting for a garment type. One click narrows the shop to the right look.
Zooming in on the photo answers "what does the crest look like?" without a trip to the store.
That builds confidence to buy and reduces returns. (No product videos exist in the catalogue
yet, so there are no video previews.)

---

## Backend 1: Up-to-the-minute stock, seasonal updates and pricing

**What I added**

- **Product tagging** (`backend/tagging.py`): each time the backend starts, every product is
  tagged in a new `product_tags` table with its category, brand, style (Casual or Formal),
  simple color groups and seasons. New products are tagged automatically.
- **Live stock and prices**: product, price and stock responses are sent with
  `Cache-Control: no-store`, so the browser never shows an old copy. A new
  `GET /api/products/{id}/stock` route returns current stock and price with the time it was
  checked. The item page and the item popup re-check it every 30 seconds, and again when the
  shopper comes back to the tab. They show "Live stock and price · checked just now", and they update the sizes
  you can pick if something sells out while you're looking.
- **Seasonal updates**: each product carries season tags (Fall & winter, Spring & summer,
  Game day). The backend works out what is **in season now** from today's date: in October and
  November that is fall-and-winter items plus Harvard–Yale game-day items. The site shows an
  "In season now" filter and a Home page row, both updating automatically when the season turns.
- **New agent tool `browse_catalogue`**: the chat assistant can filter by category, brand,
  style, color, size, price and "in season now", so questions like "something formal for an
  interview under $80" or "what's in season?" get exact matches from the database.

**Why it helps**

Shoppers see the stock and price that are true right now, not when the page was opened, so they
don't try to buy a size that has just sold out. The business can change a price or restock in the
database and every page and the chat assistant reflect it immediately. Seasonal picks keep the
shop looking current without anyone editing the website by hand.

---

## Backend 2: Customer profile, order history and tailored recommendations

**What I added**

- A **customer profile** built by the backend (`backend/customer_profile.py`) from what the shop already
  knows about a logged-in shopper:
  - order history (`orders`, `order_items`): what they bought and in which sizes
  - products they opened (`product_views`, from Problem 8)
  - products the chat showed them (`chat_messages`)

  From these it works out their **usual size**, favorite **colors**, **categories**, **styles**
  and **brands**.
- `GET /api/me/profile` returns the profile and order history, and
  `GET /api/me/recommendations` returns up to 8 tailored picks with a reason for each (for
  example, "Because you like Formal styles · in your size M"). Picks are in stock in their
  usual size and exclude things they already bought.
- A **"Recommended for you"** row on the Home page for logged-in shoppers.
- A new agent tool **`recommend_for_me`** so the chat can answer "what would you recommend for
  me?" with the same picks, in the shopper's size.
- The profile is built so an outside CRM or distributor system could be added as another data
  source later. None exists for Campus Customs today, so none is connected.

**Why it helps**

Returning shoppers see items that match their taste and are available in their size, instead of
the same featured list everyone gets. That shortens the path to a purchase and encourages repeat
orders. For the business, it puts the data it already collects (orders, views and chats) to work
without asking shoppers to fill in a preferences form.

---

## Where to see each improvement in the running app

| Improvement | Where to look |
|---|---|
| Faceted search and categories | **Products** page: filter panel on the left, category buttons on top |
| Style toggle and dynamic images | **Home** "Shop by style" row and **Products** toggle; hover any card; hover the photo on an item page |
| Live stock and seasonal updates | Item page and popup: "Live stock and price · checked just now"; "In season now" row on Home and filter on Products; ask the chat "what's in season?" |
| Profile and recommendations | Log in, then **Home** "Recommended for you"; ask the chat "what would you recommend for me?" |
