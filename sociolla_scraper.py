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
    """Extract all required data from a product page"""
    product_data = {}
    
    # Basic product info
    product_data['URL_Product'] = product_url
    
    # Wait for page to load properly
    time.sleep(5)
    
    # Product name - Try multiple selectors
    product_data['product_name'] = utils.get_text_if_exists("//h1[@class='product-name']")
    if not product_data['product_name']:
        product_data['product_name'] = utils.get_text_if_exists("//h1[@itemprop='name']")
    
    # Brand name - Try multiple approaches
    product_data['brand'] = utils.get_text_if_exists("//a[@class='product-brand']")
    if not product_data['brand']:
        product_data['brand'] = utils.get_text_if_exists("//div[contains(@class,'product-brand')]/a")
    
    # Product type
    product_data['product_type'] = "Skin Care"  # From the category URL
    
    # Regular price and sale price
    if utils.verify_element_by_xpath("//li[contains(@class,'pricing')]"):
        if utils.verify_element_by_xpath("//li[contains(@class,'pricing hasdiscount')]"):
            product_data['regular_price'] = utils.get_text_if_exists("//li[contains(@class,'pricing hasdiscount')]/span[@class='ori']")
            product_data['sale_price'] = utils.get_text_if_exists("//li[contains(@class,'pricing hasdiscount')]/span[@class='after']")
        else:
            price = utils.get_text_if_exists("//li[contains(@class,'pricing')]/span")
            product_data['regular_price'] = price
            product_data['sale_price'] = price
    
    # Rating and review count
    product_data['rating'] = utils.get_text_if_exists("//li[@class='rating']")
    review_count_text = utils.get_text_if_exists("//span[@class='review-counter']")
    if review_count_text:
        match = re.search(r'\d+', review_count_text)
        product_data['review_count'] = match.group(0) if match else "0"
    else:
        product_data['review_count'] = "0"
    
    # DESCRIPTION TAB - Improved tab clicking and content extraction
    utils.scroll_page(3)  # Scroll down to make tabs visible
    time.sleep(1)
    
    # Try different approaches for tab clicking
    description_tab_found = False
    
    # First try the original selector
    if utils.verify_element_by_xpath("//a[@title='DESCRIPTION']"):
        if utils.safe_click("//a[@title='DESCRIPTION']"):
            description_tab_found = True
            time.sleep(2)
    
    # Try alternative selectors if first one failed
    if not description_tab_found:
        if utils.verify_element_by_xpath("//li/a[contains(text(),'DESCRIPTION')]"):
            if utils.safe_click("//li/a[contains(text(),'DESCRIPTION')]"):
                description_tab_found = True
                time.sleep(2)
    
    # Extract description with multiple approaches
    product_data['description'] = utils.get_text_if_exists("//div[@id='description']")
    if not product_data['description']:
        product_data['description'] = utils.get_text_if_exists("//div[contains(@class,'tab-pane')][contains(@id,'description')]")
    
    # HOW TO USE TAB
    how_to_use_tab_found = False
    
    # First try the original selector
    if utils.verify_element_by_xpath("//a[@title='HOW TO USE']"):
        if utils.safe_click("//a[@title='HOW TO USE']"):
            how_to_use_tab_found = True
            time.sleep(2)
    
    # Try alternative selectors if first one failed
    if not how_to_use_tab_found:
        if utils.verify_element_by_xpath("//li/a[contains(text(),'HOW TO USE')]"):
            if utils.safe_click("//li/a[contains(text(),'HOW TO USE')]"):
                how_to_use_tab_found = True
                time.sleep(2)
    
    # Extract how to use with multiple approaches
    product_data['how_to_use'] = utils.get_text_if_exists("//div[@id='how_to_use']")
    if not product_data['how_to_use']:
        product_data['how_to_use'] = utils.get_text_if_exists("//div[contains(@class,'tab-pane')][contains(@id,'how_to_use')]")
    
    # INGREDIENTS TAB
    ingredients_tab_found = False
    
    # First try the original selector
    if utils.verify_element_by_xpath("//a[@title='INGREDIENTS']"):
        if utils.safe_click("//a[@title='INGREDIENTS']"):
            ingredients_tab_found = True
            time.sleep(2)
    
    # Try alternative selectors if first one failed
    if not ingredients_tab_found:
        if utils.verify_element_by_xpath("//li/a[contains(text(),'INGREDIENTS')]"):
            if utils.safe_click("//li/a[contains(text(),'INGREDIENTS')]"):
                ingredients_tab_found = True
                time.sleep(2)
    
    # Extract ingredients with multiple approaches
    product_data['ingredients'] = utils.get_text_if_exists("//div[@id='ingredients']")
    if not product_data['ingredients']:
        product_data['ingredients'] = utils.get_text_if_exists("//div[contains(@class,'tab-pane')][contains(@id,'ingredients')]")
    
    # BPOM Number (might be in description or other tabs)
    bpom_pattern = r'BPOM\s*:?\s*([A-Z0-9]+)'
    description = product_data.get('description', '')
    bpom_match = re.search(bpom_pattern, description)
    if bpom_match:
        product_data['bpom_number'] = bpom_match.group(1)
    else:
        product_data['bpom_number'] = ""
    
    # Image URL
    image_element = None
    if utils.verify_element_by_xpath("//img[@id='product-featured-image']"):
        image_element = driver.find_element(By.XPATH, "//img[@id='product-featured-image']")
    elif utils.verify_element_by_xpath("//div[contains(@class,'product-image')]//img"):
        image_element = driver.find_element(By.XPATH, "//div[contains(@class,'product-image')]//img")
    
    if image_element:
        product_data['image_url'] = image_element.get_attribute('src')
        
        # Create a filename for the image
        filename = f"{product_data.get('brand', 'unknown')}_{product_data.get('product_name', 'product')}"
        
        # Download image
        local_path = utils.download_image(
            product_data['image_url'], 
            filename
        )
        product_data['local_image_path'] = local_path
    else:
        product_data['image_url'] = ""
        product_data['local_image_path'] = ""
    
    # Print all extracted fields for debugging
    print(f"Extracted data for product: {product_data.get('product_name', 'unknown')}")
    print(f"- Brand: {product_data.get('brand', 'unknown')}")
    print(f"- Description: {product_data.get('description', '')[:30]}...")
    print(f"- Ingredients: {product_data.get('ingredients', '')[:30]}...")
    
    return product_data

if __name__ == "__main__":
    main()