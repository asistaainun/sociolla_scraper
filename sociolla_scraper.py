from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import time
# Add these imports at the top of your file if not already present
from bs4 import BeautifulSoup
import pandas as pd
import random
import json
import pickle
import os
from utils import SociollaUtils
import re
import datetime

# Add this function at the top of your file, before main()
def save_checkpoint(current_page, total_pages, products_data, filename='output/checkpoint.json'):
    """Save current scraping progress to a checkpoint file"""
    import json
    
    # Create a checkpoint object
    checkpoint = {
        'current_page': current_page,
        'total_pages': total_pages,
        'products_count': len(products_data),
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Save checkpoint info to a JSON file
    try:
        with open(filename, 'w') as f:
            json.dump(checkpoint, f)
        
        # Also save the current products data
        if products_data:
            df = pd.DataFrame(products_data)
            df.to_csv('output/checkpoint_data.csv', index=False)
            
        print(f"Checkpoint saved: Page {current_page}/{total_pages}, {len(products_data)} products collected")
    except Exception as e:
        print(f"Error saving checkpoint: {e}")

def load_checkpoint(filename='output/checkpoint.json'):
    """Load the last checkpoint if it exists"""
    import json
    import os
    
    if not os.path.exists(filename):
        return None, []
    
    try:
        # Load checkpoint info
        with open(filename, 'r') as f:
            checkpoint = json.load(f)
        
        # Load saved products data if it exists
        products_data = []
        if os.path.exists('output/checkpoint_data.csv'):
            df = pd.read_csv('output/checkpoint_data.csv')
            products_data = df.to_dict('records')
            
        print(f"Loaded checkpoint: Page {checkpoint['current_page']}/{checkpoint['total_pages']}, {len(products_data)} products")
        return checkpoint, products_data
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
        return None, []
    
def check_for_pause():
    """Check if pause.txt exists and return True if it does"""
    if os.path.exists("pause.txt"):
        print("Pause file detected. Saving checkpoint and exiting...")
        return True
    return False


def main():
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Initialize WebDriver
    service = Service(executable_path="drivers/chromedriver_win64/chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Initialize utils
    utils = SociollaUtils(driver=driver)
    utils.setup_directories()
    
    # Product data storage
    # all_products = []
    # Check for existing checkpoint
    checkpoint, all_products = load_checkpoint()
    
    # Define base URL and number of pages to scrape
    base_url = "https://www.sociolla.com/140-skin-care?sort=-created_at&page="
    num_pages = 145  # Change this to the number of pages you want to scrape

    # Create a counter for total products processed
    # total_products_processed = 0

    # Set starting page from checkpoint if available
    start_page = 1
    if checkpoint:
        start_page = checkpoint['current_page']
        print(f"Resuming from page {start_page}")

    # Create a counter for total products processed
    total_products_processed = len(all_products)
    print(f"Starting with {total_products_processed} products already collected")

    try:
        # Loop through pages
        for page in range(start_page, num_pages + 1):
            print(f"\n--- Scraping Page {page}/{num_pages} ---\n")
            
            # Save checkpoint every 5 pages
            if page % 5 == 0 and page > start_page:
                save_checkpoint(page, num_pages, all_products)

            # Navigate to page
            try:
                page_url = f"{base_url}{page}"
                driver.get(page_url)
                
                # Wait for page load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)
                # Save current progress to checkpoint file
                # save_checkpoint(page, num_pages, all_products)

            except Exception as e:
                print(f"Error loading page {page}: {e}")
                continue
            
            # Close popups that might interfere with scraping
            utils.close_popups()
            
            # Scroll down to load all products
            utils.scroll_page(limit=5)
            
            # Get product links
            product_urls = []
            
            # Try different selectors to find product links
            link_selectors = [
                "//a[@class='product__name']",
                "//div[contains(@class, 'product-item')]//a[contains(@class, 'product-name')]",
                "//div[contains(@class, 'product-thumb')]//a",
                "//h3[contains(@class, 'product-name')]/a"
            ]
            
            for selector in link_selectors:
                try:
                    links = driver.find_elements(By.XPATH, selector)
                    for link in links:
                        try:
                            url = link.get_attribute('href')
                            if url and "sociolla.com" in url and url not in product_urls:
                                product_urls.append(url)
                        except:
                            continue
                except:
                    continue
            
            print(f"Found {len(product_urls)} product URLs on page {page}")
            
            # Process each product (taking only the first 3 for testing if needed)
            for idx, product_url in enumerate(product_urls):
                try:
                    print(f"\nProcessing product {idx+1}/{len(product_urls)} on page {page}")
                    print(f"URL: {product_url}")
                    
                    # Use a new tab for each product to avoid stale elements
                    driver.execute_script("window.open('');")
                    driver.switch_to.window(driver.window_handles[1])
                    
                    # Navigate to product page
                    driver.get(product_url)
                    
                    # Wait for page to load
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    time.sleep(2)
                    
                    # Close any popups
                    utils.close_popups()
                    
                    # Extract product data
                    product_data = extract_product_data(driver, utils, product_url)
                    
                    # Add to our collection
                    all_products.append(product_data)
                    total_products_processed += 1

                    # Print progress
                    print(f"Total products collected so far: {total_products_processed}")
                    
                    # Close tab and switch back to main tab
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    
                    # Random delay
                    time.sleep(1 + random.random() * 2)
                    
                except Exception as e:
                    print(f"Error processing product: {e}")
                    # Make sure we get back to the main window
                    try:
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                    except:
                        pass
                    continue

                # Check for manual pause (create a file called "pause.txt" to pause)
                if os.path.exists('pause.txt'):
                    print("\n*** Scraping paused manually ***")
                    print("Delete 'pause.txt' file and run the script again to resume")
                    save_checkpoint(page, num_pages, all_products)
                    return
                
    except KeyboardInterrupt:
        print("\n*** Scraping paused by user (Ctrl+C) ***")
        save_checkpoint(page, num_pages, all_products)
        print("Run the script again to resume from this point")
                
    
    except Exception as e:
        print(f"Error during scraping: {e}")
        save_checkpoint(page, num_pages, all_products)
    
    finally:
        # Save data to CSV with error handling
        if all_products:
            # Create DataFrame
            df = pd.DataFrame(all_products)

            # Save to CSV with timestamp to avoid overwriting
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'output/product_data_full_{timestamp}.csv'

            try:
                # Try to save to the original file
                df.to_csv('output/product_data.csv', index=False)
                print(f"Saved data for {len(all_products)} products to output/product_data.csv")

                # Also save a timestamped backup
                df.to_csv(filename, index=False)
                print(f"Also saved backup to {filename}")
                
            except PermissionError:
                # If permission error, try saving to a new file with timestamp
                # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                # new_filename = f'output/product_data_{timestamp}.csv'
                try:
                    # df.to_csv(new_filename, index=False)
                    # print(f"Permission error on original file. Saved data to {new_filename} instead.")
                    df.to_csv(filename, index=False)
                    print(f"Permission error on original file. Saved data to {filename} instead.")
                except Exception as e:
                    print(f"Error saving data: {e}")
                    # Last resort - save to user's home directory
                    home_dir = os.path.expanduser("~")
                    home_file = os.path.join(home_dir, f'sociolla_product_data_{timestamp}.csv')
                    df.to_csv(home_file, index=False)
                    print(f"Saved data to {home_file}")

        # Close browser
        driver.quit()

def extract_product_data(driver, utils, product_url):
    """Extract product data targeting specific elements based on the latest screenshots"""
    product_data = {}
    
    # Basic product info
    product_data['URL_Product'] = product_url
    
    # Wait for page to load
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)
    except:
        print("Timeout waiting for page load, proceeding anyway...")
    
    # Product name
    product_name = utils.get_text_if_exists("//h1[contains(@class, 'title')]")
    if product_name:
        product_data['product_name'] = product_name
    
    # Brand name
    brand = utils.get_text_if_exists("//p[contains(@class, 'brand')]/a")
    if brand:
        product_data['brand'] = brand
    
    # Product type
    product_data['product_type'] = "Skin Care"

    # ── PRICE ────────────────────────────────────────────────────────────
    # Based on screenshot 4 - price display
    try:
        # Look for the price display ul element
        price_selectors = [
            "//ul[contains(@class, 'price-display-top')]",
            "//ul[contains(@class, 'clearfix') and contains(@class, 'price-display-top')]"
        ]
        
        for selector in price_selectors:
            if utils.verify_element_by_xpath(selector):
                price_ul = driver.find_element(By.XPATH, selector)
                
                # Get sale price
                try:
                    sale_price_selectors = [
                        ".//span[contains(@class, 'after-no-save')]",
                        ".//span[contains(@class, 'after-save')]"
                    ]
                    
                    for sale_selector in sale_price_selectors:
                        try:
                            sale_price = price_ul.find_element(By.XPATH, sale_selector).text.strip()
                            if sale_price:
                                product_data['sale_price'] = sale_price
                                break
                        except:
                            continue
                except:
                    product_data['sale_price'] = ""
                
                # Get regular price
                try:
                    regular_price_selectors = [
                        ".//li[contains(@class, 'pricing-hasdiscount')]",
                        ".//span[contains(@class, 'before-discount')]"
                    ]
                    
                    for regular_selector in regular_price_selectors:
                        try:
                            regular_price = price_ul.find_element(By.XPATH, regular_selector).text.strip()
                            if regular_price:
                                product_data['regular_price'] = regular_price
                                break
                        except:
                            continue
                except:
                    product_data['regular_price'] = ""
                
                break
    except Exception as e:
        print(f"Error getting price: {e}")
        product_data['sale_price'] = ""
        product_data['regular_price'] = ""

    # ── RATING & REVIEW COUNT ───────────────────────────────────────────
    # Based on screenshot 2 - rating and reviews
    try:
        # Look for the info list
        info_selectors = [
            "//ul[contains(@class, 'info') and not(contains(@class, 'info-mobile'))]",
            "//ul[contains(@class, 'info') and contains(@class, 'clearfix')]"
        ]
        
        for selector in info_selectors:
            if utils.verify_element_by_xpath(selector):
                info_ul = driver.find_element(By.XPATH, selector)
                
                # Get rating
                try:
                    rating_selectors = [
                        ".//li[contains(@class, 'rating')]",
                        ".//li[contains(@class, 'rate')]"
                    ]
                    
                    for rating_selector in rating_selectors:
                        try:
                            rating = info_ul.find_element(By.XPATH, rating_selector).text.strip()
                            if rating:
                                product_data['rating'] = rating
                                break
                        except:
                            continue
                except:
                    product_data['rating'] = ""
                
                # Get review count
                try:
                    review_selectors = [
                        ".//li[contains(@class, 'total-review')]",
                        ".//li[contains(@class, 'review')]"
                    ]
                    
                    for review_selector in review_selectors:
                        try:
                            review_text = info_ul.find_element(By.XPATH, review_selector).text.strip()
                            if review_text:
                                # Extract just the number from the review count (e.g., "(2)" -> "2")
                                review_count = re.search(r'\((\d+)\)', review_text)
                                if review_count:
                                    product_data['review_count'] = review_count.group(1)
                                else:
                                    product_data['review_count'] = review_text
                                break
                        except:
                            continue
                except:
                    product_data['review_count'] = "0"
                
                break
    except Exception as e:
        print(f"Error getting rating and reviews: {e}")
        product_data['rating'] = ""
        product_data['review_count'] = "0"

    # ── BPOM NUMBER ───────────────────────────────────────────────────────
    # Based on screenshot 3 - BPOM number
    try:
        bpom_selectors = [
            "//div[contains(@class, 'info') and contains(text(), 'Izin Edar BPOM')]",
            "//div[contains(text(), 'BPOM')]"
        ]
        
        for selector in bpom_selectors:
            if utils.verify_element_by_xpath(selector):
                bpom_element = driver.find_element(By.XPATH, selector)
                bpom_text = bpom_element.text.strip()
                
                # Extract just the BPOM number
                bpom_match = re.search(r'No\s+(\w+)', bpom_text)
                if bpom_match:
                    product_data['bpom_number'] = bpom_match.group(1)
                else:
                    product_data['bpom_number'] = bpom_text
                break
    except Exception as e:
        print(f"Error getting BPOM number: {e}")
        product_data['bpom_number'] = ""
    
    
    # Get tab navigation elements - EXACTLY as shown in screenshots
    tab_selectors = [
        "//ul[@data-v-6f64a6b4]//li//a[@data-v-6f64a6b4][@title]"
    ]
    
    tab_elements = []
    for selector in tab_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                tab_elements = elements
                break
        except Exception as e:
            print(f"Error finding tab elements: {e}")
    
    # Process each tab
    if tab_elements:
        # Create a dictionary to store tabs by title
        tabs_by_title = {}
        
        # Identify all tabs
        for tab in tab_elements:
            try:
                title = tab.get_attribute("title")
                if title:
                    tabs_by_title[title.upper()] = tab
            except Exception as e:
                print(f"Error getting tab title: {e}")
        
        print(f"Found tabs: {list(tabs_by_title.keys())}")
        
        # Click on Description tab
        if "DESCRIPTION" in tabs_by_title:
            try:
                # Click the tab
                driver.execute_script("arguments[0].click();", tabs_by_title["DESCRIPTION"])
                time.sleep(1)
                
                # Based on Image 4 - get content from product-descriptions div
                description = utils.get_text_if_exists(
                    "//div[@id='product-descriptions' and @data-v-6f64a6b4]//p"
                )
                
                if description:
                    product_data['description'] = description
                else:
                    # Try alternative selector
                    description = utils.get_text_if_exists(
                        "//div[contains(@class, 'tabs-content')]//div[@id='product-descriptions']//p"
                    )
                    if description:
                        product_data['description'] = description
            except Exception as e:
                print(f"Error extracting description: {e}")
        
        # Click on How To Use tab
        if "HOW TO USE" in tabs_by_title:

            try:
                # Click the tab
                driver.execute_script("arguments[0].click();", tabs_by_title["HOW TO USE"])
                # Wait longer for content to load
                time.sleep(2)

                # Get the HTML content of the tab
                try:
                    # First try to get the specific element with id="brand-descriptions"
                    brand_desc_element = driver.find_element(By.XPATH, "//div[@id='brand-descriptions']")
                    html_content = brand_desc_element.get_attribute('innerHTML')

                    # If that fails, try getting the entire tab content
                    if not html_content:
                        tab_content = driver.find_element(By.XPATH, "//div[contains(@class, 'tabs-content')]//div[contains(@class, 'tabs-item') and @data-v-6f64a6b4]")
                        html_content = tab_content.get_attribute('innerHTML')
                except:
                    # Fallback to JavaScript
                    html_content = driver.execute_script("""
                        var brandDesc = document.getElementById('brand-descriptions');
                        return brandDesc ? brandDesc.innerHTML : '';
                    """)
                
                # Parse the HTML with BeautifulSoup
                if html_content:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract all text from paragraphs, preserving structure
                    paragraphs = soup.find_all('p')
                    if paragraphs:
                        # Join all paragraph texts with newlines to preserve structure
                        how_to_use = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                        if how_to_use:
                            product_data['how_to_use'] = how_to_use
                            print(f"Found How To Use with BeautifulSoup: {how_to_use[:50]}...")
                    else:
                        # If no paragraphs found, get all text from the div
                        how_to_use = soup.get_text(strip=True)
                        if how_to_use:
                            product_data['how_to_use'] = how_to_use
                            print(f"Found How To Use with BeautifulSoup (text only): {how_to_use[:50]}...")
                
                # If BeautifulSoup approach didn't work, try the original methods
                if 'how_to_use' not in product_data or not product_data['how_to_use']:
                # Based on the screenshot, try these specific selectors
                    how_to_use_selectors = [
                        # Most specific selector based on your screenshot
                        "//div[@data-v-6f64a6b4 and @id='brand-descriptions']//p",
                        "//div[@data-v-6f64a6b4 and @class='tabs-item']//div[@id='brand-descriptions']//p",
                        "//div[@class='tabs-content']//div[@id='brand-descriptions']//p",
                        # More generic fallbacks
                        "//div[@id='brand-descriptions']//p",
                        "//div[contains(@class, 'tabs-content')]//div[contains(@class, 'tabs-item')]//p"
                    ]
                    
                    how_to_use = ""
                    for selector in how_to_use_selectors:
                        text = utils.get_text_if_exists(selector)
                        if text:
                            how_to_use = text
                            print(f"Found How To Use with selector: {selector}")
                            print(f"Content: {how_to_use[:50]}...")
                            break
                
                    # If still not found, try getting all paragraphs in the tab content
                    if not how_to_use:
                        try:
                            # Get all paragraphs in the tab content area
                            paragraphs = driver.find_elements(By.XPATH, "//div[contains(@class, 'tabs-content')]//p")
                            if paragraphs:
                                how_to_use = "\n".join([p.text for p in paragraphs if p.text.strip()])
                                print(f"Found How To Use with multiple paragraphs: {how_to_use[:50]}...")
                        except Exception as e:
                            print(f"Error getting How To Use with paragraphs method: {e}")
                    
                    # If still not found, try direct JavaScript extraction
                    if not how_to_use:
                        try:
                            # Use JavaScript to get the content
                            how_to_use = driver.execute_script("""
                                var brandDesc = document.getElementById('brand-descriptions');
                                return brandDesc ? brandDesc.textContent.trim() : '';
                            """)
                            if how_to_use:
                                print(f"Found How To Use with JavaScript: {how_to_use[:50]}...")
                        except Exception as e:
                            print(f"Error getting How To Use with JavaScript: {e}")
                
                    # Save the content if found
                    if how_to_use:
                        product_data['how_to_use'] = how_to_use
                    else:
                        print("Could not find How To Use content")
                        product_data['how_to_use'] = ""
                    
            except Exception as e:
                print(f"Error extracting how to use: {e}")
                product_data['how_to_use'] = ""
        
        # Click on Ingredients tab
        if "INGREDIENTS" in tabs_by_title:
            try:
                # Click the tab
                driver.execute_script("arguments[0].click();", tabs_by_title["INGREDIENTS"])
                time.sleep(1)
                
                # Get the HTML content of the tab
                try:
                    # First try to get the specific element with id="ingredients"
                    ingredients_element = driver.find_element(By.XPATH, "//div[@id='ingredients']")
                    html_content = ingredients_element.get_attribute('innerHTML')
                    
                    # If that fails, try getting the entire tab content
                    if not html_content:
                        tab_content = driver.find_element(By.XPATH, "//div[contains(@class, 'tabs-content')]//div[contains(@class, 'tabs-item') and @data-v-6f64a6b4]")
                        html_content = tab_content.get_attribute('innerHTML')
                except:
                    # Fallback to JavaScript
                    html_content = driver.execute_script("""
                        var ingredientsDiv = document.getElementById('ingredients');
                        return ingredientsDiv ? ingredientsDiv.innerHTML : '';
                    """)

                # Parse the HTML with BeautifulSoup
                if html_content:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract all text from paragraphs, preserving structure
                    paragraphs = soup.find_all('p')
                    if paragraphs:
                        # Join all paragraph texts with newlines to preserve structure
                        ingredients = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                        if ingredients:
                            product_data['ingredients'] = ingredients
                            print(f"Found Ingredients with BeautifulSoup: {ingredients[:50]}...")
                    else:
                        # If no paragraphs found, get all text from the div
                        ingredients = soup.get_text(strip=True)
                        if ingredients:
                            product_data['ingredients'] = ingredients
                            print(f"Found Ingredients with BeautifulSoup (text only): {ingredients[:50]}...")
                
                # If BeautifulSoup approach didn't work, try the original method
                if 'ingredients' not in product_data or not product_data['ingredients']:

                    # Based on Image 2 - get content from ingredients div
                    ingredients = utils.get_text_if_exists(
                        "//div[@id='ingredients' and @data-v-6f64a6b4]//p"
                    )
                    
                    if ingredients:
                        product_data['ingredients'] = ingredients
            except Exception as e:
                print(f"Error extracting ingredients: {e}")
    else:
        print("No tab elements found")
    
    # If we still don't have the data, try alternative methods
    # Direct tab content extraction without clicking
    if 'description' not in product_data or not product_data['description']:
        # Try different selectors for description
        description_selectors = [
            "//div[@id='product-descriptions']//p",
            "//div[contains(@class, 'tabs-content')]//div[contains(@id, 'product-descriptions')]//p",
            "//div[contains(@class, 'description')]//p"
        ]
        
        for selector in description_selectors:
            description = utils.get_text_if_exists(selector)
            if description:
                product_data['description'] = description
                break
    
    if 'how_to_use' not in product_data or not product_data['how_to_use']:
        # Try different selectors for how to use
        how_to_use_selectors = [
            "//div[@id='brand-descriptions']//p",
            "//div[contains(@class, 'tabs-content')]//div[contains(@id, 'brand-descriptions')]//p",
            "//div[contains(@id, 'how_to_use')]//p"
        ]
        
        for selector in how_to_use_selectors:
            how_to_use = utils.get_text_if_exists(selector)
            if how_to_use:
                product_data['how_to_use'] = how_to_use
                break
    
    if 'ingredients' not in product_data or not product_data['ingredients']:
        # Try different selectors for ingredients
        ingredients_selectors = [
            "//div[@id='ingredients']//p",
            "//div[contains(@class, 'tabs-content')]//div[contains(@id, 'ingredients')]//p"
        ]
        
        for selector in ingredients_selectors:
            ingredients = utils.get_text_if_exists(selector)
            if ingredients:
                product_data['ingredients'] = ingredients
                break
    
    # Image URL extraction - Exactly as in Image 1
    try:
        # Target the specific image element based on the screenshot
        img_selectors = [
            # Primary selector matching the screenshot exactly
            "//img[contains(@class, 'lazy-img') and @data-v-188df2f8]",
            # Alternative selectors based on the screenshot structure
            "//figure[contains(@class, 'gallery-preview')]//img[contains(@class, 'lazy-img')]",
            "//img[contains(@class, 'lazy-img') and @data-src]",
            "//div[contains(@class, 'gallery-preview')]//img",
            # More generic fallbacks
            "//figure//img[contains(@src, 'sociolla.com')]"
        ]
        
        image_url = None
        for selector in img_selectors:
            if utils.verify_element_by_xpath(selector):
                img_element = driver.find_element(By.XPATH, selector)
                
                # Try to get the URL from data-src first (as shown in screenshot)
                data_src = img_element.get_attribute('data-src')
                if data_src and 'sociolla.com' in data_src:
                    image_url = data_src
                    print(f"Found image URL from data-src: {image_url[:50]}...")
                    break
                
                # If data-src is not available, try src
                src = img_element.get_attribute('src')
                if src and 'sociolla.com' in src and not src.endswith('blank.gif'):
                    image_url = src
                    print(f"Found image URL from src: {image_url[:50]}...")
                    break
        
        # If we found an image URL
        if image_url:
            product_data['image_url'] = image_url
            
            # Create a filename for the image
            filename = f"{product_data.get('brand', 'unknown')}_{product_data.get('product_name', 'product')}".replace(' ', '_')
            
            # Download image
            local_path = utils.download_image(image_url, filename)
            product_data['local_image_path'] = local_path
        else:
            # Try JavaScript approach as last resort
            try:
                image_url = driver.execute_script("""
                    var img = document.querySelector('img.lazy-img');
                    return img ? (img.dataset.src || img.src) : '';
                """)
                
                if image_url and 'sociolla.com' in image_url:
                    product_data['image_url'] = image_url
                    
                    # Create a filename for the image
                    filename = f"{product_data.get('brand', 'unknown')}_{product_data.get('product_name', 'product')}".replace(' ', '_')
                    
                    # Download image
                    local_path = utils.download_image(image_url, filename)
                    product_data['local_image_path'] = local_path
            except Exception as e:
                print(f"Error getting image with JavaScript: {e}")
    except Exception as e:
        print(f"Error getting image: {e}")
        product_data['image_url'] = ""
        product_data['local_image_path'] = ""
    # Ensure all fields have values
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
    if product_data.get('description'):
        print(f"Description: {product_data['description'][:50]}...")
    if product_data.get('ingredients'):
        print(f"Ingredients: {product_data['ingredients'][:50]}...")
    if product_data.get('how_to_use'):
        print(f"How to use: {product_data['how_to_use'][:50]}...")
    if product_data.get('image_url'):
        print(f"Image URL: {product_data['image_url']}")
    
    return product_data

if __name__ == "__main__":
    main()