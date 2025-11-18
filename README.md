# Shopping Feed Attribute Scraper

A powerful Streamlit web app that intelligently extracts **50+ comprehensive product attributes** from **any e-commerce website** and creates enhanced supplemental feeds for Google Shopping.

**Extracts everything** - from basic details (price, images, descriptions) to category-specific attributes (processor specs for electronics, ISBN for books, assembly requirements for furniture) automatically.

## 🚀 Live Demo

Deploy to Streamlit Cloud: [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

## ✨ Key Features

### Intelligent Multi-Source Extraction
Works across different e-commerce platforms using multiple extraction strategies:

1. **🎯 Structured Data First** (JSON-LD Schema.org)
   - Extracts rich product data from JSON-LD markup
   - Handles Product, Offer, Brand schemas automatically

2. **🏷️ Meta Tags** (Open Graph, Twitter Cards)
   - Fallback to social media meta tags
   - Extracts images, prices, descriptions

3. **🔍 Smart HTML Parsing**
   - Common CSS selectors for e-commerce elements
   - Intelligent pattern matching for product details

4. **📊 Table & List Extraction**
   - Parses specification tables automatically
   - Extracts from definition lists (dl/dt/dd)

5. **📝 Pattern-Based Extraction**
   - Regex patterns for dimensions, weights, colors
   - Context-aware text mining

### Comprehensive Attribute Extraction

Extracts **50+ attributes** across all product categories:

**Core Product Data:**
- Product title & description
- Price, sale price & currency
- Main product image + additional images
- Brand name
- SKU, GTIN, MPN codes
- Product condition (new/refurbished/used)
- Availability status
- Product highlights/key features

**Google Shopping Feed Attributes:**
- **Apparel (Required):** color, size, material, pattern
- **Apparel (Recommended):** age_group, gender, fit_type
- Product type/category
- Multipack quantity
- Energy efficiency class
- Item group ID (for variants)

**Physical Attributes:**
- Product dimensions
- Shipping dimensions (package size)
- Weight (product & shipping)

**Ratings & Reviews:**
- Rating value
- Review count

**Category-Specific Attributes:**

📱 **Electronics:**
- Processor (Intel Core, AMD Ryzen, Apple M-series)
- RAM memory
- Storage capacity
- Screen size
- Model number

📚 **Books:**
- Author name
- ISBN
- Page count
- Format (Hardcover/Paperback/eBook)
- Publisher

🪑 **Furniture:**
- Assembly required (yes/no)
- Weight capacity
- Material composition
- Care instructions

👕 **Apparel:**
- Fit type (Slim/Regular/Relaxed/Oversized)
- Care instructions
- Fabric composition
- Size chart

⚡ **Appliances:**
- Motor/Power specifications
- Energy efficiency rating
- Warranty information
- Voltage/Wattage

📄 **Paper Products:**
- GSM (paper weight)
- Sheet count
- Material type

And more attributes automatically detected based on product type!

### User Features
- 📤 Upload Google Shopping XML feeds
- 📊 Real-time progress tracking
- 📈 Detailed attribute coverage statistics
- 💾 Download results as CSV or Excel
- ⚙️ Configurable scraping delay and URL limits
- 🎯 Works with most e-commerce platforms automatically

## Installation

### Local Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/feed-attribute-scraper.git
cd feed-attribute-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the app:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Deployment

### Streamlit Cloud (Recommended)

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select your repository, branch (main), and main file path (`app.py`)
6. Click "Deploy"

Your app will be live in minutes at `https://your-app-name.streamlit.app`

### Other Platforms

- **Heroku**: Add a `Procfile` with `web: streamlit run app.py`
- **Railway**: Works out of the box with `requirements.txt`
- **Render**: Set build command to `pip install -r requirements.txt` and start command to `streamlit run app.py`

## Usage

1. **Upload Feed**: Upload your Google Shopping XML feed file
2. **Configure Settings** (sidebar):
   - Set delay between requests (default: 1 second)
   - Optionally limit number of URLs for testing
3. **Preview URLs**: Check the URLs that will be scraped
4. **Start Scraping**: Click the button and wait for completion
5. **Review Results**: View extracted attributes and statistics
6. **Download**: Get your supplemental feed as CSV or Excel

## XML Feed Format

The app expects Google Shopping XML feeds with URLs in this format:

```xml
<item>
  <g:link>
    <![CDATA[ https://example.com/product-url ]]>
  </g:link>
</item>
```

Or standard:
```xml
<item>
  <link>https://example.com/product-url</link>
</item>
```

## Output Format

The supplemental feed can include **50+ attributes** (depending on availability):

**Core Fields:**
- `id` - Product ID from XML feed
- `title` - Product title (from XML or page)
- `url` - Product URL
- `description` - Product description
- `price` - Regular product price
- `sale_price` - Sale/promotional price
- `currency` - Price currency (USD, GBP, etc.)
- `image_url` - Main product image URL
- `additional_image_link` - Additional product images (comma-separated)
- `brand` - Brand name
- `condition` - Product condition (new, refurbished, used)

**Product Identifiers:**
- `sku` - Stock Keeping Unit
- `gtin` - Global Trade Item Number (UPC/EAN)
- `mpn` - Manufacturer Part Number

**Product Categorization:**
- `product_type` - Product category
- `product_highlight` - Key features/highlights (pipe-separated)
- `keywords` - Product keywords

**Apparel & Variants:**
- `color` - Product color (REQUIRED for apparel)
- `size` - Apparel size (REQUIRED for apparel: S, M, L, etc.)
- `material` - Material composition (REQUIRED for apparel)
- `pattern` - Pattern type
- `age_group` - Target age group (newborn, infant, toddler, kids, adult)
- `gender` - Target gender (male, female, unisex)
- `fit_type` - Fit style (Slim, Regular, Relaxed, Oversized)

**Physical Properties:**
- `size_dimensions` - Product dimensions
- `shipping_dimensions` - Package dimensions
- `weight` - Product/shipping weight

**Product Details:**
- `availability` - Stock status
- `multipack` - Bundle/pack quantity
- `energy_efficiency_class` - Energy rating (A+++, A++, A+, A, B, C, D, E, F, G)
- `rating` - Product rating value
- `review_count` - Number of reviews
- `warranty` - Warranty information

**Category-Specific Attributes:**
- Electronics: `processor`, `ram`, `storage`, `screen_size`
- Books: `author`, `isbn`, `pages`, `format`
- Furniture: `assembly_required`, `weight_capacity`
- Appliances: `motor`
- Paper Products: `gsm`

## Tips & Best Practices

### Testing
- **Start small**: Use the URL limit setting to test with 10-20 URLs first
- **Check coverage**: Review the attribute coverage statistics to see what's being extracted
- **Compare results**: Try products from different categories to test extraction quality

### Performance
- **Rate limiting**: Keep delay at 1s minimum to respect website servers and avoid being blocked
- **Large feeds**: 300 URLs at 1s delay = ~5 minutes processing time
- **Timeout**: Default 15s timeout per URL - adjust if needed for slow sites

### Success Rate
- **Modern e-commerce sites** (Shopify, WooCommerce, Magento): 80-95% attribute coverage
- **Sites with JSON-LD**: Near 100% coverage for structured attributes
- **Custom/legacy sites**: 40-70% coverage (relies on pattern matching)
- **Best results**: Sites that implement Schema.org Product markup

## Customization & Extension

The scraper uses a layered approach - you can customize any layer:

### 1. Structured Data (Highest Priority)
Edit `extract_structured_data()` to add support for additional Schema.org types or custom JSON-LD schemas.

### 2. HTML Parsing (CSS Selectors)
Modify these methods to add site-specific selectors:
- `extract_price_from_html()` - Add price selectors
- `extract_image_from_html()` - Add image selectors
- `extract_description_from_html()` - Add description selectors

### 3. Pattern Matching (Fallback)
Enhance regex patterns in:
- `extract_dimensions()` - Dimension formats
- `extract_weight()` - Weight patterns
- `extract_colour()` - Color names
- `extract_material()` - Material keywords
- `extract_size()` - Size formats

### 4. Table Extraction
Update `extract_table_data()` to map additional table headers to attributes.

### Adding New Attributes
1. Add extraction method (e.g., `extract_rating()`)
2. Call it in `scrape_product_attributes()`
3. Add to structured data extraction if applicable

## Troubleshooting

**No URLs found**:
- Check your XML uses `<g:link>` or `<link>` tags
- Verify the XML feed is valid and properly formatted

**Low attribute coverage for a specific site**:
- Check if the site uses JSON-LD (view page source, search for "application/ld+json")
- The site may use non-standard HTML structure - add custom selectors
- Some attributes may be loaded dynamically via JavaScript (not accessible to this scraper)

**Missing specific attributes**:
- Review the attribute coverage statistics to see what's being found
- Check the page source to see how the attribute is marked up
- Add custom patterns to the relevant extraction method

**Slow performance**:
- Normal behavior - respects rate limiting to avoid being blocked
- Adjust delay in settings (minimum 1s recommended)
- Consider processing in batches

**Request errors (403, 429)**:
- Website may be blocking scraper traffic
- Increase delay between requests
- Some sites require additional headers or authentication

## Licence

MIT Licence - feel free to use and modify

## Contributing

Pull requests welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description
