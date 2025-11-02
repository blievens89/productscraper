# Shopping Feed Attribute Scraper

A Streamlit web app that extracts product attributes (size, colour, weight, material, etc.) from product pages and creates supplemental feeds for Google Shopping.

## 🚀 Live Demo

Deploy to Streamlit Cloud: [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

## Features

- 📤 Upload Google Shopping XML feeds
- 🔍 Automatically extracts product attributes:
  - Size/Dimensions
  - Weight
  - Colour
  - Material
  - Motor/Power specifications
  - Warranty information
  - Brand
- 📊 Real-time progress tracking
- 📈 Attribute coverage statistics
- 💾 Download results as CSV or Excel
- ⚙️ Configurable scraping delay and URL limits

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

The supplemental feed includes:
- `url` - Original product URL
- `size` - Product dimensions
- `weight` - Product weight
- `colour` - Product colour
- `material` - Construction material
- `motor` - Power/motor specifications
- `warranty` - Warranty period
- `brand` - Brand name

## Tips

- **Test first**: Use the URL limit setting to process 10-20 URLs initially
- **Rate limiting**: Keep delay at 1s minimum to respect website servers
- **Large feeds**: 300 URLs at 1s delay = ~5 minutes processing time
- **Success rate**: Depends on how consistently the site structures product data

## Customisation

To add more attribute extraction patterns, edit the extraction methods in `app.py`:
- `extract_dimensions()`
- `extract_weight()`
- `extract_colour()`
- `extract_material()`

## Troubleshooting

**No URLs found**: Check your XML uses `<g:link>` or `<link>` tags

**Low success rate**: The site may structure data differently - customise regex patterns

**Slow performance**: Normal - respects rate limiting to avoid server issues

## Licence

MIT Licence - feel free to use and modify

## Contributing

Pull requests welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description
