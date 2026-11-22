# Data-driven medicine ordering storefront 

A static, mobile-friendly catalogue with category-first browsing, fast quantity entry, dynamic category/company filters, medicine information and a browser-only order preview.

## Repository contents

- `index.html`, `css/styles.css`, `js/app.js`: storefront code. These normally remain unchanged during daily product updates.
- `user.json`: distributor/store name, email, mobile, logo and markup percentage.
- `data/catalogue.json`: compact product index used for search, filters and prices.
- `data/details.json`: medicine descriptions loaded when a product detail is opened.
- `tools/build_data.py`: converts the daily CSV export to JSON.
- `tools/mappings.json`: editable vendor aliases and category corrections.
- `UPDATE_PRODUCTS.bat`: Windows shortcut to rebuild the data.

## First setup / daily update

1. Put the latest Shopify CSV export in the repository root and name it `All Products.csv` (or `All Products(1).csv`). Keep the expected columns: `Title`, `Body (HTML)`, `Vendor`, `Tags`, `Variant Price`, `Variant Compare At Price`, `Image Src`. The script also accepts `Product Category` and `Type` as category fallbacks.
2. Double-click `UPDATE_PRODUCTS.bat` on Windows. Python 3 must be installed and available as `py -3`.
3. Review `data/build-report.json`.
4. Upload only `data/catalogue.json`, `data/details.json` and `data/build-report.json` to GitHub for a normal product-data update. Do not upload the daily CSV unless you want it in the repository.
5. If you change distributor details or markup, edit and upload `user.json` too.

The original CSV is never modified. Category and vendor normalisation is controlled by `tools/mappings.json`; if you change mappings, rerun the BAT file and upload the regenerated JSON. The website discovers companies and categories from the generated data; they are not hardcoded in the frontend.

The storefront presents every category in a paged, four-row carousel. Page size adjusts to the screen (four columns on desktop, three on tablet, and two on mobile); categories with more catalogue products appear first. This ordering is based on product count, not sales popularity or live stock. Products appear after a category or company is selected, or a search is entered; the full catalogue and ordering behavior remain available.

## Distributor configuration

Edit `user.json`:

```json
{
  "store_name": "Ishwar Pharma",
  "email": "orders@ishwarpharma.com",
  "mobile": "9876543210",
  "logo": "",
  "markup_percent": 10,
  "currency": "INR",
  "show_mrp": true
}
```

Markup is applied to the original `Variant Price` once. Rounding uses the nearest increment: under ₹5 = ₹0.05; ₹5–<₹10 = ₹0.10; ₹10–<₹20 = ₹0.25; ₹20–<₹50 = ₹0.50; ₹50–<₹100 = ₹1; ₹100–<₹200 = ₹5; ₹200+ = ₹10. Products with zero price are not orderable. If the calculated price exceeds MRP, the product is flagged as “Price under review” and cannot be added to cart.

## Preview locally

Browsers generally block `fetch()` from `file://`. From this folder run:

```bash
py -3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Important order limitation

Checkout is currently a **local preview only**. It stores test orders in the visitor's browser and does not email the distributor or save orders centrally. Do not use this as a live order-acceptance system until a secure backend/order endpoint is connected. There is no payment gateway.

## Data notes

- Current build source: `All Products(1).csv` renamed to `All Products.csv` for this package.
- Vendor aliases currently merge Alkem1 → Alkem, Aristo1 → Aristo, Cadila1 → Cadila, and Romson 1 → Romson. Miracalus and Naprod remain separate. Original vendor is retained in each catalogue record as `vendorOriginal`.
- Compound tag pairs are mapped in `tools/mappings.json`; other comma-separated tags are treated as separate categories. `others` is displayed as “Other Medicines”.
- Product title and original `Type` are retained. Composition is not guessed from brand names.
- Medicine descriptions are shown from the CSV `Body (HTML)` field. Eleven records in the current CSV have no description; they are listed in `data/build-report.json`.


## Order email setup (Cloudflare Pages + Resend)

The repository includes `functions/api/order.js`. Cloudflare Pages automatically detects the root-level `functions/` directory when deploying from Git integration. The checkout sends only product IDs and quantities; the Function reads the deployed `user.json` and `data/catalogue.json`, recalculates prices using the configured markup and fair rounding, checks MRP, and emails the order to the distributor address in `user.json`. The Resend API key is never exposed to browser code.

After pushing this update to the connected GitHub repository:

1. Wait for the Cloudflare Pages deployment to finish successfully.
2. In Cloudflare Dashboard, open **Workers & Pages → ujs → Settings → Variables and secrets**. The project will now support runtime variables because it has a Pages Function.
3. Add a **Secret** named `RESEND_API_KEY` and paste the API key from Resend. Do not put the key in GitHub, this README, or `user.json`.
4. Add a **Text** variable named `RESEND_FROM_EMAIL` with value `UJS Pharma Orders <orders@ujspharma.com>`. This sender address must belong to the verified Resend domain.
5. Save the variables and trigger a new deployment if Cloudflare asks you to.
6. Test with a small order and confirm it arrives at the email address in `user.json`.

The Function uses the public `user.json` email as the recipient, so changing the distributor email in that file changes the order recipient on the next deployment. For a different distributor/domain, set `RESEND_FROM_EMAIL` to a sender address on that distributor's verified Resend domain as well.

**Important:** This sends order requests by email; it does not create a central order database, guarantee stock availability, or collect payment. Protect the endpoint against abuse before wider public promotion (for example, add Cloudflare rate limiting/Turnstile).
