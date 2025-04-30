from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import pandas as pd
import os
from utils import SociollaUtils
import re

def main():
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    
    # Initialize WebDriver
    service = Service(executable_path="drivers/chromedriver_win64/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Initialize utils
    utils = SociollaUtils(driver=driver)
    utils.setup_directories()
    
    # Product data storage
    all_products = []
    
    # Define base URL and number of pages to scrape
    base_url = "https://www.sociolla.com/140-skin-care?sort=-created_at&page="
    num_pages = 5  # Change this to the number of pages you want to scrape
    
    try:
        # Loop through pages
        for page in range(1, num_pages + 1):
            print(f"\n--- Scraping Page {page}/{num_pages} ---\n")
            
            # Navigate to page
            page_url = f"{base_url}{page}"
            driver.get(page_url)
            time.sleep(3)
            
            # Close popups that might interfere with scraping
            utils.close_popups()
            
            # Scroll down to load all products
            utils.scroll_page(limit=10)
            
            # Get product links on current page
            product_links = driver.find_elements(By.XPATH, "//a[@class='product__name']")
            product_urls = [link.get_attribute('href') for link in product_links]
            
            print(f"Found {len(product_urls)} products on page {page}")
            
            # Process each product on the page
            for idx, product_url in enumerate(product_urls):
                try:
                    print(f"Processing product {idx+1}/{len(product_urls)} on page {page}")
                    
                    # Navigate to product page
                    driver.get(product_url)
                    time.sleep(3)
                    
                    # Close any popups
                    utils.close_popups()
                    
                    # Extract product data
                    product_data = extract_product_data(driver, utils, product_url)
                    
                    # Add to our collection
                    all_products.append(product_data)
                    
                    print(f"Successfully scraped: {product_data['product_name']}")
                    
                except Exception as e:
                    print(f"Error processing product: {e}")
                    continue
    
    except Exception as e:
        print(f"Error during scraping: {e}")
    
    finally:
        # Save data to CSV
        if all_products:
            df = pd.DataFrame(all_products)
            df.to_csv('output/product_data.csv', index=False)
            print(f"Saved data for {len(all_products)} products to output/product_data.csv")
        
        # Close browser
        driver.quit()

def extract_product_data(driver, utils, product_url):
    """Extract all required data from a product page based on the specific structure of Sociolla"""
    product_data = {}
    
    # Basic product info
    product_data['URL_Product'] = product_url
    
    # Wait for page to load properly - adjust timeout as needed
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1[class*='title']"))
        )
    except:
        print("Page load timeout, proceeding anyway...")
    
    # Product name - Target the h1 element with title class using data-v-* attribute
    product_name_selectors = [
        "//h1[contains(@class, 'title')]",
        "//h1[starts-with(@data-v, 'data-v-')]", 
        "//h1[contains(@class, 'product-name')]"
    ]
    
    for selector in product_name_selectors:
        product_name = utils.get_text_if_exists(selector)
        if product_name:
            product_data['product_name'] = product_name.strip()
            break
    
    # Brand name - From p.brand element containing an a tag
    brand_selectors = [
        "//p[contains(@class, 'brand')]/a",
        "//p[starts-with(@data-v, 'data-v-')][contains(@class, 'brand')]/a",
        "//div[contains(@class, 'brand')]/a"
    ]
    
    for selector in brand_selectors:
        brand = utils.get_text_if_exists(selector)
        if brand:
            product_data['brand'] = brand.strip()
            break
    
    # Product type
    product_data['product_type'] = "Skin Care"
    
    # Price information - Look for elements containing pricing info
    price_selectors = [
        "//span[contains(@class, 'product_info-sale-percentage')]",
        "//span[contains(@class, 'price-sales')]",
        "//div[contains(@class, 'price')]//span",
        "//span[contains(@class, 'product-price')]"
    ]
    
    # Get sale percentage if available
    sale_percentage = None
    for selector in price_selectors:
        percentage_text = utils.get_text_if_exists(selector)
        if percentage_text and '%' in percentage_text:
            sale_percentage = percentage_text
            break
    
    # Get regular and sale prices
    regular_price_selectors = [
        "//span[contains(@class, 'price-normal')]",
        "//span[contains(@class, 'original-price')]",
        "//span[contains(@class, 'regular-price')]",
        "//div[contains(@class, 'price')]//span[1]"
    ]
    
    sale_price_selectors = [
        "//span[contains(@class, 'price-sales')]",
        "//span[contains(@class, 'sale-price')]",
        "//div[contains(@class, 'price')]//span[2]"
    ]
    
    # Try to get regular price
    for selector in regular_price_selectors:
        regular_price = utils.get_text_if_exists(selector)
        if regular_price:
            product_data['regular_price'] = regular_price.strip()
            break
    
    # Try to get sale price if there's a sale percentage
    if sale_percentage:
        for selector in sale_price_selectors:
            sale_price = utils.get_text_if_exists(selector)
            if sale_price:
                product_data['sale_price'] = sale_price.strip()
                break
    
    # Rating and review count
    rating_selectors = [
        "//div[contains(@class, 'rating')]//span",
        "//span[contains(@class, 'rating')]"
    ]
    
    for selector in rating_selectors:
        rating = utils.get_text_if_exists(selector)
        if rating:
            try:
                # Extract numeric value
                match = re.search(r'([0-9.]+)', rating)
                if match:
                    product_data['rating'] = match.group(1)
                else:
                    product_data['rating'] = rating
                break
            except:
                product_data['rating'] = rating
                break
    
    # If no rating was found, set default
    if 'rating' not in product_data:
        product_data['rating'] = "0"
    
    # Review count
    review_count_selectors = [
        "//span[contains(@class, 'review')]",
        "//div[contains(@class, 'review-count')]"
    ]
    
    for selector in review_count_selectors:
        review_count_text = utils.get_text_if_exists(selector)
        if review_count_text:
            try:
                match = re.search(r'\d+', review_count_text)
                product_data['review_count'] = match.group(0) if match else "0"
                break
            except:
                product_data['review_count'] = "0"
                break
    
    if 'review_count' not in product_data:
        product_data['review_count'] = "0"
    
    # Improved tab content extraction based on your screenshots
    # First, find all tab elements
    tabs_found = False
    
    # Look for tab navigation elements
    tab_selectors = [
        "//li[starts-with(@data-v, 'data-v-')]//a[@title='DESCRIPTION' or @title='HOW TO USE' or @title='INGREDIENTS']",
        "//ul[contains(@class, 'nav-tabs')]//a",
        "//div[contains(@class, 'tabs')]//a"
    ]
    
    # Try each selector to find tabs
    for tab_selector in tab_selectors:
        tab_elements = driver.find_elements(By.XPATH, tab_selector)
        if tab_elements and len(tab_elements) > 0:
            tabs_found = True
            
            # Loop through each tab and extract its content
            for tab in tab_elements:
                try:
                    tab_title = tab.get_attribute("title")
                    if not tab_title:
                        tab_title = tab.text.strip().upper()
                    
                    # Click on the tab
                    driver.execute_script("arguments[0].click();", tab)
                    time.sleep(1)  # Wait for content to load
                    
                    # Extract content based on tab type
                    if "DESCRIPTION" in tab_title:
                        # Look for description content
                        description_content_selectors = [
                            "//div[@id='description']",
                            "//div[contains(@class, 'tabs-content')]//div[contains(@id, 'description')]",
                            "//div[contains(@class, 'tab-pane')][contains(@id, 'description')]"
                        ]
                        
                        for selector in description_content_selectors:
                            content = utils.get_text_if_exists(selector)
                            if content:
                                product_data['description'] = content.strip()
                                break
                    
                    elif "HOW TO USE" in tab_title:
                        # Look for how to use content
                        how_to_use_content_selectors = [
                            "//div[@id='how_to_use']",
                            "//div[contains(@class, 'tabs-content')]//div[contains(@id, 'how_to_use')]",
                            "//div[contains(@class, 'tab-pane')][contains(@id, 'how_to_use')]"
                        ]
                        
                        for selector in how_to_use_content_selectors:
                            content = utils.get_text_if_exists(selector)
                            if content:
                                product_data['how_to_use'] = content.strip()
                                break
                    
                    elif "INGREDIENTS" in tab_title:
                        # Look for ingredients content
                        ingredients_content_selectors = [
                            "//div[@id='ingredients']",
                            "//div[contains(@class, 'tabs-content')]//div[contains(@id, 'ingredients')]",
                            "//div[contains(@class, 'tab-pane')][contains(@id, 'ingredients')]"
                        ]
                        
                        for selector in ingredients_content_selectors:
                            content = utils.get_text_if_exists(selector)
                            if content:
                                product_data['ingredients'] = content.strip()
                                break
                
                except Exception as e:
                    print(f"Error processing tab {tab_title if 'tab_title' in locals() else 'unknown'}: {e}")
            
            # If we found and processed tabs, break out of the selector loop
            break
    
    # If no tabs were found or content wasn't extracted, try direct content extraction
    if not tabs_found or 'description' not in product_data:
        # Try to directly find content without tab clicking
        description = utils.get_text_if_exists("//div[contains(@class, 'product-description')]")
        if description:
            product_data['description'] = description.strip()
    
    # Direct extraction for ingredients if not found via tabs
    if 'ingredients' not in product_data:
        ingredients = utils.get_text_if_exists("//div[contains(@id, 'ingredients')]")
        if ingredients:
            product_data['ingredients'] = ingredients.strip()
    
    # Direct extraction for how to use if not found via tabs
    if 'how_to_use' not in product_data:
        how_to_use = utils.get_text_if_exists("//div[contains(@id, 'how_to_use')]")
        if how_to_use:
            product_data['how_to_use'] = how_to_use.strip()
    
    # BPOM Number extraction from description
    if 'description' in product_data and product_data['description']:
        bpom_patterns = [
            r'BPOM\s*:?\s*([A-Z0-9]+)',
            r'BPOM\s*No[.:]\s*([A-Z0-9]+)',
            r'No\.\s*BPOM\s*:?\s*([A-Z0-9]+)'
        ]
        
        for pattern in bpom_patterns:
            bpom_match = re.search(pattern, product_data['description'])
            if bpom_match:
                product_data['bpom_number'] = bpom_match.group(1)
                break
    
    # Image URL - Based on your screenshot showing an img.lazy-img element
    image_selectors = [
        "//img[contains(@class, 'lazy-img')]",
        "//figure[contains(@class, 'gallery-preview')]//img",
        "//div[contains(@class, 'gallery-product')]//img",
        "//div[contains(@class, 'product-image')]//img"
    ]
    
    for selector in image_selectors:
        if utils.verify_element_by_xpath(selector):
            try:
                image_element = driver.find_element(By.XPATH, selector)
                # Try multiple attributes for image URL
                for attr in ['src', 'data-src', 'data-lazy-src']:
                    image_url = image_element.get_attribute(attr)
                    if image_url and not image_url.endswith('blank.gif') and not image_url.endswith('placeholder.png'):
                        product_data['image_url'] = image_url
                        
                        # Create a filename for the image
                        filename = f"{product_data.get('brand', 'unknown')}_{product_data.get('product_name', 'product')}".replace(' ', '_')
                        
                        # Download image
                        local_path = utils.download_image(image_url, filename)
                        product_data['local_image_path'] = local_path
                        break
                
                if 'image_url' in product_data:
                    break
            except Exception as e:
                print(f"Error getting image: {e}")
                continue
    
    # Ensure we have values for all fields, even if empty
    ensure_fields = [
        'product_name', 'brand', 'product_type', 'regular_price', 'sale_price',
        'rating', 'review_count', 'description', 'how_to_use', 'ingredients',
        'bpom_number', 'image_url', 'local_image_path'
    ]
    
    for field in ensure_fields:
        if field not in product_data:
            product_data[field] = ""
    
    # Print what we found for debugging
    print(f"Extracted data for: {product_data.get('product_name', 'Unknown Product')}")
    print(f"Brand: {product_data.get('brand', 'Unknown')}")
    print(f"Description: {product_data.get('description', '')[:30]}..." if product_data.get('description') else "No description found")
    print(f"Ingredients: {product_data.get('ingredients', '')[:30]}..." if product_data.get('ingredients') else "No ingredients found")
    print(f"Image URL: {product_data.get('image_url', 'No image URL')}")
    
    return product_data

if __name__ == "__main__":
    main()