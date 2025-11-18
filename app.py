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
import json
from typing import Dict, List, Optional, Any
from io import BytesIO, StringIO
import traceback
from urllib.parse import urljoin


class FeedAttributeScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def extract_structured_data(self, soup: BeautifulSoup, url: str = "") -> Dict[str, Any]:
        """Extract structured data from JSON-LD, microdata, and meta tags"""
        data = {}

        # 1. Extract JSON-LD structured data (most comprehensive)
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                if script.string:
                    json_data = json.loads(script.string)

                    # Handle both single objects and arrays
                    json_items = json_data if isinstance(json_data, list) else [json_data]

                    for item in json_items:
                        if not isinstance(item, dict):
                            continue

                        # Check for Product schema
                        schema_type = item.get('@type', '')
                        if 'Product' in schema_type or schema_type == 'Product':
                            # Extract common product fields
                            if 'name' in item and not data.get('title'):
                                data['title'] = item['name']
                            if 'description' in item and not data.get('description'):
                                data['description'] = item['description']
                            if 'brand' in item:
                                brand = item['brand']
                                if isinstance(brand, dict):
                                    data['brand'] = brand.get('name', '')
                                else:
                                    data['brand'] = str(brand)
                            if 'sku' in item:
                                data['sku'] = item['sku']
                            if 'gtin' in item:
                                data['gtin'] = item['gtin']
                            if 'gtin13' in item:
                                data['gtin'] = item['gtin13']
                            if 'gtin12' in item and not data.get('gtin'):
                                data['gtin'] = item['gtin12']
                            if 'mpn' in item:
                                data['mpn'] = item['mpn']
                            if 'color' in item:
                                data['color'] = item['color']
                            if 'material' in item:
                                data['material'] = item['material']
                            if 'size' in item:
                                data['size'] = item['size']

                            # Extract offers data (price, availability)
                            if 'offers' in item:
                                offers = item['offers']
                                if isinstance(offers, dict):
                                    if 'price' in offers:
                                        data['price'] = str(offers['price'])
                                    if 'priceCurrency' in offers:
                                        data['currency'] = offers['priceCurrency']
                                    if 'availability' in offers:
                                        data['availability'] = offers['availability']
                                elif isinstance(offers, list) and offers:
                                    # Take first offer
                                    first_offer = offers[0]
                                    if 'price' in first_offer:
                                        data['price'] = str(first_offer['price'])
                                    if 'priceCurrency' in first_offer:
                                        data['currency'] = first_offer['priceCurrency']

                            # Extract image
                            if 'image' in item:
                                image = item['image']
                                if isinstance(image, str):
                                    data['image_url'] = urljoin(url, image)
                                elif isinstance(image, list) and image:
                                    data['image_url'] = urljoin(url, image[0])
                                elif isinstance(image, dict) and 'url' in image:
                                    data['image_url'] = urljoin(url, image['url'])

                            # Extract additional product properties
                            if 'additionalProperty' in item:
                                props = item['additionalProperty']
                                if isinstance(props, list):
                                    for prop in props:
                                        if isinstance(prop, dict) and 'name' in prop and 'value' in prop:
                                            prop_name = prop['name'].lower()
                                            if 'weight' in prop_name and not data.get('weight'):
                                                data['weight'] = prop['value']
                                            elif 'dimension' in prop_name and not data.get('size_dimensions'):
                                                data['size_dimensions'] = prop['value']
                                            elif 'warranty' in prop_name and not data.get('warranty'):
                                                data['warranty'] = prop['value']
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue

        # 2. Extract Open Graph meta tags
        og_tags = {
            'og:title': 'title',
            'og:description': 'description',
            'og:image': 'image_url',
            'og:price:amount': 'price',
            'og:price:currency': 'currency',
            'product:brand': 'brand',
            'product:color': 'color',
            'product:material': 'material',
        }

        for og_property, data_key in og_tags.items():
            if data.get(data_key):
                continue  # Skip if already found
            tag = soup.find('meta', property=og_property)
            if tag and tag.get('content'):
                value = tag['content'].strip()
                if data_key == 'image_url':
                    data[data_key] = urljoin(url, value)
                else:
                    data[data_key] = value

        # 3. Extract standard meta tags
        meta_tags = {
            'description': 'description',
            'keywords': 'keywords',
        }

        for meta_name, data_key in meta_tags.items():
            if data.get(data_key):
                continue
            tag = soup.find('meta', attrs={'name': meta_name})
            if tag and tag.get('content'):
                data[data_key] = tag['content'].strip()

        # 4. Extract Twitter Card meta tags (fallback)
        if not data.get('image_url'):
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                data['image_url'] = urljoin(url, twitter_image['content'])

        # 5. Extract microdata (fallback for older sites)
        if not data.get('price'):
            price_span = soup.find(attrs={'itemprop': 'price'})
            if price_span:
                data['price'] = price_span.get('content', price_span.get_text()).strip()

        if not data.get('brand'):
            brand_span = soup.find(attrs={'itemprop': 'brand'})
            if brand_span:
                brand_name = brand_span.find(attrs={'itemprop': 'name'})
                if brand_name:
                    data['brand'] = brand_name.get_text().strip()
                else:
                    data['brand'] = brand_span.get_text().strip()

        return data

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
    
    def extract_price_from_html(self, soup: BeautifulSoup, page_text: str) -> Optional[str]:
        """Extract price using common CSS selectors and patterns"""
        # Common price CSS selectors
        price_selectors = [
            {'itemprop': 'price'},
            {'class': re.compile(r'price|product-price|current-price|sale-price|offer-price', re.I)},
            {'id': re.compile(r'price|product-price', re.I)},
            {'data-price': True},
        ]

        for selector in price_selectors:
            elements = soup.find_all(attrs=selector)
            for elem in elements:
                # Check data attributes first
                price = elem.get('content') or elem.get('data-price')
                if price:
                    return str(price).strip()
                # Check text content
                text = elem.get_text().strip()
                # Match price patterns like $19.99, £50, €25.00, 19.99
                price_match = re.search(r'[$£€]?\s*(\d+[,\.]?\d*\.?\d+)', text)
                if price_match:
                    return price_match.group(0).strip()

        # Regex fallback on page text
        price_patterns = [
            r'(?:Price|Sale Price|Our Price):\s*[$£€]\s*(\d+[,\.]?\d*\.?\d+)',
            r'[$£€]\s*(\d+[,\.]?\d*\.?\d+)',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, page_text)
            if match:
                return match.group(0).strip()

        return None

    def extract_image_from_html(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract main product image using common patterns"""
        # Try common image selectors
        image_selectors = [
            {'itemprop': 'image'},
            {'class': re.compile(r'product-image|main-image|primary-image|product-photo', re.I)},
            {'id': re.compile(r'product-image|main-image|primary-image', re.I)},
        ]

        for selector in image_selectors:
            img = soup.find('img', attrs=selector)
            if img:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy')
                if src:
                    return urljoin(url, src)

        # Fallback: first large image in content area
        images = soup.find_all('img')
        for img in images:
            src = img.get('src') or img.get('data-src')
            if src and not any(skip in src.lower() for skip in ['logo', 'icon', 'sprite', 'banner']):
                # Check if image is reasonably large (basic heuristic)
                width = img.get('width', '0')
                height = img.get('height', '0')
                try:
                    if (width and int(width) > 200) or (height and int(height) > 200):
                        return urljoin(url, src)
                except ValueError:
                    pass
                # If no size info, assume first content image is product image
                if not img.find_parent('header') and not img.find_parent('nav'):
                    return urljoin(url, src)

        return None

    def extract_description_from_html(self, soup: BeautifulSoup, page_text: str) -> Optional[str]:
        """Extract product description"""
        # Try meta description first (often good summary)
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()

        # Try common description containers
        desc_selectors = [
            {'itemprop': 'description'},
            {'class': re.compile(r'product-description|product-details|description|product-info', re.I)},
            {'id': re.compile(r'description|product-description|product-details', re.I)},
        ]

        for selector in desc_selectors:
            elem = soup.find(attrs=selector)
            if elem:
                # Get text but limit length
                text = elem.get_text(separator=' ', strip=True)
                if text and len(text) > 20:
                    # Limit to reasonable length (e.g., 500 chars)
                    return text[:500] if len(text) > 500 else text

        return None

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

            # STEP 1: Extract structured data first (JSON-LD, microdata, meta tags)
            structured_data = self.extract_structured_data(soup, url)

            # Merge structured data (don't overwrite existing title/id from XML)
            for key, value in structured_data.items():
                if key not in ['title', 'id'] and value:  # Preserve XML title/id
                    attributes[key] = value

            # Extract all text content for pattern matching (fallback)
            page_text = soup.get_text()
            title = attributes.get('title', '')

            # STEP 2: Extract data using CSS selectors and HTML structure

            # Price (if not found in structured data)
            if not attributes.get('price'):
                price = self.extract_price_from_html(soup, page_text)
                if price:
                    attributes['price'] = price

            # Image (if not found in structured data)
            if not attributes.get('image_url'):
                image = self.extract_image_from_html(soup, url)
                if image:
                    attributes['image_url'] = image

            # Description (if not found in structured data)
            if not attributes.get('description'):
                description = self.extract_description_from_html(soup, page_text)
                if description:
                    attributes['description'] = description

            # STEP 3: Extract specific attributes using pattern matching (fallback)

            # Dimensions (for product_detail or custom use)
            if not attributes.get('size_dimensions'):
                dimensions = self.extract_dimensions(page_text, title)
                if dimensions:
                    attributes['size_dimensions'] = dimensions

            # Weight (for shipping_weight attribute)
            if not attributes.get('weight'):
                weight = self.extract_weight(page_text)
                if weight:
                    attributes['weight'] = weight

            # Colour (REQUIRED for apparel)
            if not attributes.get('color'):
                colour = self.extract_colour(page_text, soup, title)
                if colour:
                    attributes['color'] = colour

            # Material (REQUIRED for apparel)
            if not attributes.get('material'):
                material = self.extract_material(page_text)
                if material:
                    attributes['material'] = material

            # Pattern
            if not attributes.get('pattern'):
                pattern = self.extract_pattern(page_text)
                if pattern:
                    attributes['pattern'] = pattern

            # Size (for apparel size attribute)
            if not attributes.get('size'):
                size = self.extract_size(page_text, title)
                if size:
                    attributes['size'] = size

            # Brand (if not from structured data)
            if not attributes.get('brand'):
                brand = self.extract_brand(page_text, soup)
                if brand:
                    attributes['brand'] = brand

            # GTIN/SKU (if not from structured data)
            if not attributes.get('gtin') and not attributes.get('sku'):
                gtin = self.extract_gtin(page_text, soup)
                if gtin:
                    attributes['gtin'] = gtin

            # Additional attributes
            if not attributes.get('warranty'):
                warranty = self.extract_warranty(page_text)
                if warranty:
                    attributes['warranty'] = warranty

            # GSM for paper products
            gsm = self.extract_gsm(page_text)
            if gsm:
                attributes['gsm'] = gsm

            # Motor info for appliances
            motor = self.extract_motor_info(page_text)
            if motor:
                attributes['motor'] = motor

            # STEP 4: Extract table data if available (can override pattern matches)
            table_data = self.extract_table_data(soup)
            for key, value in table_data.items():
                if not attributes.get(key):  # Only add if not already found
                    attributes[key] = value

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

        # Find all tables, prioritize those with product/specification classes
        tables = soup.find_all('table')
        priority_tables = [t for t in tables if t.get('class') and any(
            keyword in ' '.join(t['class']).lower()
            for keyword in ['product', 'spec', 'detail', 'attribute', 'info']
        )]

        # Process priority tables first, then others
        all_tables = priority_tables + [t for t in tables if t not in priority_tables]

        for table in all_tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text().strip().lower()
                    value = cells[1].get_text().strip()

                    # Skip empty values
                    if not value or len(value) < 2:
                        continue

                    # Map table keys to our attribute names
                    if any(kw in key for kw in ['dimension', 'measurements']) and 'size_dimensions' not in data:
                        data['size_dimensions'] = value
                    elif 'size' in key and 'apparel' in key.lower() and 'size' not in data:
                        data['size'] = value
                    elif 'weight' in key and 'weight' not in data:
                        data['weight'] = value
                    elif any(kw in key for kw in ['colour', 'color']) and 'color' not in data:
                        data['color'] = value
                    elif 'material' in key and 'material' not in data:
                        data['material'] = value
                    elif 'brand' in key and 'brand' not in data:
                        data['brand'] = value
                    elif any(kw in key for kw in ['sku', 'product code', 'item code']) and 'sku' not in data:
                        data['sku'] = value
                    elif any(kw in key for kw in ['gtin', 'ean', 'upc', 'barcode']) and 'gtin' not in data:
                        data['gtin'] = value
                    elif 'warranty' in key and 'warranty' not in data:
                        data['warranty'] = value
                    elif 'pattern' in key and 'pattern' not in data:
                        data['pattern'] = value
                    elif 'price' in key and 'price' not in data:
                        data['price'] = value

        # Also check for definition lists (dl/dt/dd) - common for product specs
        dls = soup.find_all('dl')
        for dl in dls:
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                key = dt.get_text().strip().lower()
                value = dd.get_text().strip()

                if not value or len(value) < 2:
                    continue

                if any(kw in key for kw in ['dimension', 'measurements']) and 'size_dimensions' not in data:
                    data['size_dimensions'] = value
                elif 'weight' in key and 'weight' not in data:
                    data['weight'] = value
                elif any(kw in key for kw in ['colour', 'color']) and 'color' not in data:
                    data['color'] = value
                elif 'material' in key and 'material' not in data:
                    data['material'] = value
                elif 'brand' in key and 'brand' not in data:
                    data['brand'] = value

        return data


def main():
    st.set_page_config(
        page_title="Feed Attribute Scraper",
        page_icon="🛍️",
        layout="wide"
    )
    
    st.title("🛍️ Shopping Feed Attribute Scraper")
    st.markdown("""
    Upload your Google Shopping XML feed to extract comprehensive product attributes from any e-commerce website.

    **Intelligent multi-source extraction:**
    - 🎯 Structured data (JSON-LD schema)
    - 🏷️ Meta tags (Open Graph, Twitter Cards)
    - 🔍 Smart HTML parsing with CSS selectors
    - 📊 Product specification tables
    - 📝 Pattern-based text extraction (fallback)

    Works across different e-commerce platforms automatically!
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
        ### Attributes extracted:

        **Core Product Data:**
        - ✅ **title** - Product name
        - ✅ **description** - Product description
        - ✅ **price** - Product price
        - ✅ **image_url** - Main product image
        - ✅ **brand** - Brand name
        - ✅ **sku** / **gtin** - Product codes

        **Google Shopping (Apparel):**
        - ✅ **color** (required)
        - ✅ **size** (required)
        - ✅ **material** (required)
        - ✅ **pattern** (optional)

        **Physical Attributes:**
        - ✅ **size_dimensions** - Product dimensions
        - ✅ **weight** - Shipping weight

        **Additional:**
        - ✅ **warranty** - Warranty info
        - ✅ **availability** - Stock status

        *Uses structured data (JSON-LD), meta tags, and intelligent HTML parsing*
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
