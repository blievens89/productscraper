"""
Shopping Feed Attribute Scraper - Streamlit App
Extracts product attributes from URLs in a Google Shopping XML feed
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
import pandas as pd
import time
from typing import Dict, List, Optional
from io import BytesIO, StringIO
import traceback


class FeedAttributeScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def extract_products_from_xml(self, xml_content: bytes) -> List[Dict[str, str]]:
        """Extract product data (ID, title, URL) from Google Shopping XML feed"""
        products = []
        try:
            root = ET.fromstring(xml_content)
            
            # Handle namespace - Google Shopping feeds typically use 'g:' namespace
            namespaces = {'g': 'http://base.google.com/ns/1.0'}
            
            # Find all items
            items = root.findall('.//item')
            
            for item in items:
                product = {}
                
                # Extract ID
                id_elem = item.find('g:id', namespaces)
                if id_elem is None:
                    id_elem = item.find('id')
                if id_elem is not None and id_elem.text:
                    product['id'] = id_elem.text.strip()
                
                # Extract title
                title_elem = item.find('g:title', namespaces)
                if title_elem is None:
                    title_elem = item.find('title')
                if title_elem is not None and title_elem.text:
                    product['title'] = title_elem.text.strip()
                
                # Extract link
                link_elem = item.find('g:link', namespaces)
                if link_elem is None:
                    link_elem = item.find('link')
                if link_elem is not None and link_elem.text:
                    url = link_elem.text.strip()
                    if url.startswith('http'):
                        product['url'] = url
                
                # Only add if we have at least a URL
                if 'url' in product:
                    products.append(product)
            
            return products
            
        except Exception as e:
            st.error(f"Error parsing XML: {e}")
            return []
    
    def scrape_product_attributes(self, product_data: Dict[str, str]) -> Dict[str, str]:
        """Scrape product attributes from a single product page"""
        # Start with existing product data (id, title, url)
        attributes = product_data.copy()
        url = attributes.get('url', '')
        
        if not url:
            attributes['error'] = 'No URL provided'
            return attributes
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract all text content for pattern matching
            page_text = soup.get_text()
            title = attributes.get('title', '')
            
            # Extract dimensions (for product_detail or custom use)
            dimensions = self.extract_dimensions(page_text, title)
            if dimensions:
                attributes['size_dimensions'] = dimensions
            
            # Extract weight (for shipping_weight attribute)
            weight = self.extract_weight(page_text)
            if weight:
                attributes['weight'] = weight
            
            # Extract colour (REQUIRED for apparel)
            colour = self.extract_colour(page_text, soup, title)
            if colour:
                attributes['color'] = colour
            
            # Extract material (REQUIRED for apparel)
            material = self.extract_material(page_text)
            if material:
                attributes['material'] = material
            
            # Extract pattern
            pattern = self.extract_pattern(page_text)
            if pattern:
                attributes['pattern'] = pattern
            
            # Extract size (for apparel size attribute)
            size = self.extract_size(page_text, title)
            if size:
                attributes['size'] = size
            
            # Extract table data if available
            table_data = self.extract_table_data(soup)
            attributes.update(table_data)
            
            return attributes
            
        except requests.exceptions.RequestException as e:
            attributes['error'] = f"Request error: {str(e)}"
            return attributes
        except Exception as e:
            attributes['error'] = f"Processing error: {str(e)}"
            return attributes
    
    def extract_dimensions(self, text: str, title: str = "") -> Optional[str]:
        """Extract product dimensions in various formats"""
        # Combine text sources
        search_text = f"{title} {text}"
        
        patterns = [
            # Metric with labels (152cm (L) x 76cm (W) x 80cm (H))
            r'(\d+(?:\.\d+)?)\s*(?:cm|mm|m)\s*\(L\)\s*x\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|m)\s*\(W\)\s*x\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|m)\s*\(H\)',
            # Metric dimensions (2.72 x 11m, 152 x 76 x 80cm)
            r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(?:x\s*(\d+(?:\.\d+)?))?\s*(?:cm|mm|m)\b',
            # Imperial dimensions (107" x 36ft)
            r'(\d+(?:\.\d+)?)\s*(?:"|\'|inch|inches|in)\s*x\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|\')',
            # With "x" or "×" (152 x 76 x 80 cm)
            r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:[xX×]\s*(\d+(?:\.\d+)?))?\s*(?:cm|mm|m|inches?|ft)\b',
            # Dimensions: or Size: prefix
            r'(?:Dimensions?|Size|Measurements?):\s*(\d+(?:\.\d+)?)\s*(?:x|×)\s*(\d+(?:\.\d+)?)\s*(?:(?:x|×)\s*(\d+(?:\.\d+)?))?\s*(?:cm|mm|m|inches?|ft)?',
            # Table size format
            r'(?:Table size|Product size|Paper size):\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|m)\s*(?:\(L\))?\s*x\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|m)',
            # Width x Height x Depth
            r'(?:Width|W):\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|m|").*?(?:Height|H):\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|m|").*?(?:Depth|D):\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|m|")',
            # Single dimension formats
            r'(\d+(?:\.\d+)?)\s*(?:cm|mm|m)\s*(?:wide|width|height|tall|long|length)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                dims = [g for g in match.groups() if g]
                if dims:
                    # Try to extract unit
                    unit_match = re.search(r'(cm|mm|m|inches?|in|ft|feet)', match.group(0), re.IGNORECASE)
                    unit = unit_match.group(1) if unit_match else 'cm'
                    return ' x '.join(dims) + f' {unit}'
        
        return None
    
    def extract_weight(self, text: str) -> Optional[str]:
        """Extract product weight"""
        patterns = [
            r'(?:Net Weight|Weight|Net):\s*(\d+(?:\.\d+)?)\s*(?:kg|g|lbs)',
            r'(\d+(?:\.\d+)?)\s*(?:kg|kgs)(?:\s|$|,)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return None
    
    def extract_colour(self, text: str, soup: BeautifulSoup, title: str = "") -> Optional[str]:
        """Extract product colour"""
        # Combine sources
        search_text = f"{title} {text}"
        
        # Expanded colour list
        colours = [
            'black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 
            'purple', 'pink', 'brown', 'grey', 'gray', 'silver', 'gold',
            'navy', 'beige', 'cream', 'multicolour', 'multi-colour', 'turquoise',
            'cyan', 'magenta', 'maroon', 'olive', 'teal', 'lime', 'indigo',
            'violet', 'coral', 'salmon', 'khaki', 'burgundy', 'champagne',
            'bronze', 'copper', 'rose', 'mint', 'lavender', 'peach', 'cherry',
            'ivory', 'pearl', 'charcoal', 'slate', 'emerald', 'sapphire', 'ruby'
        ]
        
        # Look for explicit colour mentions with patterns
        colour_patterns = [
            r'(?:Colour|Color):\s*([A-Za-z\s\-]+)',
            r'(?:Available in|Finish|Shade):\s*([A-Za-z\s\-]+)',
            r'([A-Za-z]+)\s+(?:Seamless|Background|Paper|Fabric|Material)',
        ]
        
        for pattern in colour_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                colour_text = match.group(1).strip().lower()
                for colour in colours:
                    if colour in colour_text:
                        return colour.capitalize()
        
        # Look for RGB values
        rgb_pattern = r'RGB\s*Values?:\s*\((\d+),\s*(\d+),\s*(\d+)\)'
        rgb_match = re.search(rgb_pattern, text, re.IGNORECASE)
        if rgb_match:
            # Try to find a colour name near the RGB value
            context = text[max(0, rgb_match.start()-100):rgb_match.end()+50]
            for colour in colours:
                if re.search(rf'\b{colour}\b', context, re.IGNORECASE):
                    return colour.capitalize()
        
        # Look for colour names in title or general text
        text_lower = search_text.lower()
        for colour in colours:
            if re.search(rf'\b{colour}\b', text_lower):
                return colour.capitalize()
        
        return None
    
    def extract_material(self, text: str) -> Optional[str]:
        """Extract product material"""
        materials = [
            'MDF', 'wood', 'metal', 'steel', 'aluminium', 'aluminum', 
            'plastic', 'PVC', 'fabric', 'leather', 'foam', 'rubber',
            'glass', 'ceramic', 'carbon', 'composite', 'nylon', 'polyester',
            'paper', 'cardboard', 'cotton', 'wool', 'silk', 'linen',
            'vinyl', 'acrylic', 'resin', 'bamboo', 'oak', 'pine', 'mahogany',
            'stainless steel', 'brass', 'chrome', 'titanium', 'fiberglass'
        ]
        
        # Look for explicit material mentions
        material_patterns = [
            r'(?:Construction|Material|Made from|Manufactured from):\s*([A-Za-z\s\-/]+)',
            r'(?:^|\s)(\d+%\s*recycled\s+[a-z]+)',
            r'(?:high quality|premium)\s+([a-z]+\s+paper)',
        ]
        
        for pattern in material_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Look for material keywords
        text_lower = text.lower()
        found_materials = []
        for material in materials:
            if re.search(rf'\b{material.lower()}\b', text_lower):
                found_materials.append(material)
        
        if found_materials:
            return ', '.join(found_materials[:3])
        
        return None
    
    def extract_pattern(self, text: str) -> Optional[str]:
        """Extract product pattern"""
        patterns_list = [
            'striped', 'stripes', 'polka dot', 'floral', 'paisley', 'plaid',
            'checkered', 'checked', 'chevron', 'geometric', 'animal print',
            'leopard', 'zebra', 'camouflage', 'camo', 'solid', 'plain'
        ]
        
        # Look for explicit pattern mentions
        pattern_pattern = r'(?:Pattern):\s*([A-Za-z\s\-]+)'
        match = re.search(pattern_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Look for pattern keywords
        text_lower = text.lower()
        for pattern_name in patterns_list:
            if re.search(rf'\b{pattern_name}\b', text_lower):
                return pattern_name.capitalize()
        
        return None
    
    def extract_size(self, text: str, title: str = "") -> Optional[str]:
        """Extract apparel/product size (S/M/L, numerical sizes, etc)"""
        search_text = f"{title} {text}"
        
        # Apparel sizes
        apparel_patterns = [
            r'\b((?:XX?|[23X])?[SML](?:arge|edium|mall)?)\b',  # XS, S, M, L, XL, XXL, etc
            r'\bsize:?\s*([A-Z0-9\-/]+)\b',
            r'\b(\d+(?:\.\d+)?)\s*(?:UK|US|EU)\b',  # UK 10, US 8, EU 42
            r'\bone size\b',
            r'\bOSFA\b',  # One Size Fits All
        ]
        
        for pattern in apparel_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def extract_gsm(self, text: str) -> Optional[str]:
        """Extract GSM (paper weight/density)"""
        pattern = r'(\d+)\s*GSM'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} GSM"
        return None
    
    def extract_gtin(self, text: str, soup: BeautifulSoup) -> Optional[str]:
        """Extract GTIN/EAN/UPC/Barcode"""
        patterns = [
            r'(?:GTIN|EAN|UPC|Barcode):\s*(\d{8,14})',
            r'(?:Product Code|Item Code|SKU):\s*([A-Z0-9\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Look for structured data
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'gtin' in data:
                        return data['gtin']
                    if 'gtin13' in data:
                        return data['gtin13']
                    if 'sku' in data:
                        return data['sku']
            except:
                pass
        
        return None
    
    def extract_motor_info(self, text: str) -> Optional[str]:
        """Extract motor/power information"""
        pattern = r'(\d+W?\s*(?:motor|watt|power)|\d+W)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
        return None
    
    def extract_warranty(self, text: str) -> Optional[str]:
        """Extract warranty information"""
        pattern = r'(\d+\s*(?:month|year|yr)\s*(?:warranty|guarantee))'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
        return None
    
    def extract_brand(self, text: str, soup: BeautifulSoup) -> Optional[str]:
        """Extract brand information"""
        pattern = r'(?:Brand|Manufacturer):\s*([A-Za-z0-9\s\-&]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def extract_table_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract structured data from tables if present"""
        data = {}
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text().strip().lower()
                    value = cells[1].get_text().strip()
                    
                    if 'dimension' in key or 'size' in key:
                        data['size'] = value
                    elif 'weight' in key:
                        data['weight'] = value
                    elif 'colour' in key or 'color' in key:
                        data['colour'] = value
                    elif 'material' in key:
                        data['material'] = value
        
        return data


def main():
    st.set_page_config(
        page_title="Feed Attribute Scraper",
        page_icon="🛍️",
        layout="wide"
    )
    
    st.title("🛍️ Shopping Feed Attribute Scraper")
    st.markdown("""
    Upload your Google Shopping XML feed to extract product attributes (size, colour, weight, material, etc.) 
    and create a supplemental feed for enhanced product data.
    """)
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Settings")
        
        delay = st.slider(
            "Delay between requests (seconds)",
            min_value=0.5,
            max_value=5.0,
            value=1.0,
            step=0.5,
            help="Delay between each product page request to avoid rate limiting"
        )
        
        max_urls = st.number_input(
            "Limit number of URLs (0 = all)",
            min_value=0,
            max_value=1000,
            value=0,
            step=10,
            help="Process only first N URLs (useful for testing)"
        )
        
        st.markdown("---")
        st.markdown("""
        ### Google Shopping attributes extracted:
        - ✅ **color** (required for apparel)
        - ✅ **size** (required for apparel)
        - ✅ **material** (required for apparel)
        - ✅ **pattern** (optional variant)
        - ✅ **size_dimensions** (for product_detail)
        - ✅ **weight** (for shipping_weight)
        
        *Apparel = required in US, UK, DE, FR, JP, BR*
        """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload your XML feed file",
        type=['xml'],
        help="Upload your Google Shopping feed XML file"
    )
    
    if uploaded_file is not None:
        # Read XML content
        xml_content = uploaded_file.read()
        
        # Initialize scraper
        scraper = FeedAttributeScraper()
        
        # Extract products with ID, title, and URL
        with st.spinner("Extracting products from feed..."):
            products = scraper.extract_products_from_xml(xml_content)
        
        if not products:
            st.error("❌ No products found in the XML feed. Please check your file format.")
            st.info("Expected format: `<item>` tags with `<g:id>`, `<g:title>`, and `<g:link>` elements")
            return
        
        st.success(f"✅ Found {len(products)} products in feed")
        
        # Apply limit if set
        if max_urls > 0 and max_urls < len(products):
            products = products[:max_urls]
            st.info(f"ℹ️ Processing first {max_urls} products only (as per settings)")
        
        # Preview products
        with st.expander("📋 Preview products to be scraped"):
            preview_df = pd.DataFrame(products[:10])
            st.dataframe(preview_df, use_container_width=True)
            if len(products) > 10:
                st.text(f"... and {len(products) - 10} more")
        
        # Start scraping button
        if st.button("🚀 Start Scraping", type="primary"):
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Results container
            results_container = st.container()
            
            all_attributes = []
            
            # Process each product
            for i, product in enumerate(products):
                url = product.get('url', 'Unknown URL')
                product_id = product.get('id', 'No ID')
                status_text.text(f"Processing {i+1}/{len(products)}: {product_id} - {url[:50]}...")
                
                attributes = scraper.scrape_product_attributes(product)
                all_attributes.append(attributes)
                
                # Update progress
                progress_bar.progress((i + 1) / len(products))
                
                # Rate limiting
                if i < len(products) - 1:
                    time.sleep(delay)
            
            status_text.text("✅ Scraping complete!")
            
            # Create DataFrame
            df = pd.DataFrame(all_attributes)
            
            # Reorder columns - ID and title first, then URL, then attributes
            priority_cols = ['id', 'title', 'url']
            other_cols = [col for col in df.columns if col not in priority_cols and col != 'error']
            if 'error' in df.columns:
                column_order = priority_cols + other_cols + ['error']
            else:
                column_order = priority_cols + other_cols
            
            # Only include columns that exist
            column_order = [col for col in column_order if col in df.columns]
            df = df[column_order]
            
            # Calculate statistics
            total_urls = len(df)
            urls_with_attributes = len(df[df.apply(lambda x: len([v for v in x if pd.notna(v) and v != '']) > 1, axis=1)])
            success_rate = (urls_with_attributes / total_urls) * 100 if total_urls > 0 else 0
            
            # Display statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total URLs", total_urls)
            with col2:
                st.metric("Successful Extractions", urls_with_attributes)
            with col3:
                st.metric("Success Rate", f"{success_rate:.1f}%")
            
            # Display attribute coverage
            st.subheader("📊 Attribute Coverage")
            attribute_cols = [col for col in df.columns if col not in ['id', 'title', 'url', 'error']]
            coverage_data = []
            
            for col in attribute_cols:
                count = df[col].notna().sum()
                percentage = (count / total_urls) * 100
                coverage_data.append({
                    'Attribute': col,
                    'Found': count,
                    'Coverage': f"{percentage:.1f}%"
                })
            
            if coverage_data:
                coverage_df = pd.DataFrame(coverage_data)
                st.dataframe(coverage_df, use_container_width=True)
            
            # Display results table
            st.subheader("📋 Extracted Data")
            st.dataframe(df, use_container_width=True)
            
            # Download buttons
            st.subheader("💾 Download Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV download
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()
                
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv_data,
                    file_name="supplemental_feed.csv",
                    mime="text/csv",
                    help="Download the supplemental feed as CSV for upload to Google Merchant Center"
                )
            
            with col2:
                # Excel download
                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False, engine='openpyxl')
                excel_data = excel_buffer.getvalue()
                
                st.download_button(
                    label="📥 Download as Excel",
                    data=excel_data,
                    file_name="supplemental_feed.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download as Excel file for analysis"
                )
            
            # Show errors if any
            if 'error' in df.columns:
                errors_df = df[df['error'].notna()]
                if len(errors_df) > 0:
                    with st.expander(f"⚠️ Errors ({len(errors_df)} URLs)"):
                        st.dataframe(errors_df[['url', 'error']], use_container_width=True)


if __name__ == "__main__":
    main()
