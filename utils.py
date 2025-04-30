from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import os
import time
import requests
import re

class SociollaUtils:
    def __init__(self, driver, wait_time=10):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, wait_time)
        
    def setup_directories(self):
        """Create necessary directories for output"""
        os.makedirs('output/product_images', exist_ok=True)
        
    def scroll_page(self, limit=10):
        """Scroll down the page gradually"""
        for i in range(1, limit+1):
            scroll_value = 300 * i 
            self.driver.execute_script(f"window.scrollTo(0, {scroll_value})")
            print(f"Scrolling increment {i}/{limit}")
            time.sleep(0.5)
    
    def verify_element_by_xpath(self, xpath, timeout=5):
        """Check if element exists by xpath"""
        try:
            self.driver.implicitly_wait(timeout)
            self.driver.find_element(By.XPATH, xpath)
            return True
        except NoSuchElementException:
            return False
        
    def get_text_if_exists(self, xpath, default=""):
        """Get text of element if it exists, otherwise return default value"""
        try:
            if self.verify_element_by_xpath(xpath):
                element = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)  # Short pause after scrolling
                return element.text
        except Exception as e:
            print(f"Error getting text from {xpath}: {e}")
        return default
    
    def wait_for_element(self, xpath, timeout=10):
        """Wait for element to be clickable"""
        try:
            element = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            return element
        except TimeoutException:
            print(f"Timeout waiting for element: {xpath}")
            return None
    
    def safe_click(self, xpath):
        """Safely click an element with multiple strategies"""
        try:
            if not self.verify_element_by_xpath(xpath):
                print(f"Element not found: {xpath}")
                return False
                
            element = self.driver.find_element(By.XPATH, xpath)
            
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)  # Wait after scrolling
            
            # Try direct click
            try:
                element.click()
                time.sleep(1)  # Wait after clicking
                return True
            except Exception as e:
                print(f"Direct click failed: {e}")
                
            # Try JavaScript click
            try:
                self.driver.execute_script("arguments[0].click();", element)
                time.sleep(1)  # Wait after clicking
                return True
            except Exception as e:
                print(f"JavaScript click failed: {e}")
                
            return False
        except Exception as e:
            print(f"Safe click error on {xpath}: {e}")
            return False
    
    def get_element_by_data_attr(self, attribute_prefix, element_type=None, class_name=None):
        """Find element by data-v-* attribute with optional filtering by element type and class"""
        xpath_parts = []
        
        # Start with element type or any element
        if element_type:
            xpath_parts.append(f"//{element_type}")
        else:
            xpath_parts.append("//*")
        
        # Add data attribute condition 
        xpath_parts.append(f"[starts-with(@data-v, '{attribute_prefix}')]")
        
        # Add class condition if specified
        if class_name:
            xpath_parts.append(f"[contains(@class, '{class_name}')]")
        
        # Combine into a complete XPath
        xpath = ''.join(xpath_parts)
        
        # Look for the element
        if self.verify_element_by_xpath(xpath):
            return self.driver.find_element(By.XPATH, xpath)
        return None

    def get_text_by_data_attr(self, attribute_prefix, element_type=None, class_name=None, default=""):
        """Get text from element found by data-v-* attribute"""
        element = self.get_element_by_data_attr(attribute_prefix, element_type, class_name)
        if element:
            return element.text.strip()
        return default
    
    def clean_filename(self, filename):
        """Clean a string to make it suitable as a filename"""
        # Replace spaces and special characters
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        # Limit length to avoid very long filenames
        return filename[:100].lower()
    
    def download_image(self, url, product_name, folder="output/product_images"):
        """Download an image and save it to disk"""
        if not url:
            return None
        
        try:
            # Create a clean filename from product name
            filename = self.clean_filename(product_name) + ".jpg"
            filepath = os.path.join(folder, filename)
            
            # Download the image
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return filepath
            else:
                print(f"Failed to download image, status code: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None
    
    def close_popups(self):
        """Close common popups on Sociolla"""
        # Close notification popup if present
        if self.verify_element_by_xpath("//button[@class='ng-binding']"):
            self.safe_click("//button[@class='ng-binding']")
        
        # Close chat popup if present
        if (self.verify_element_by_xpath("//p[text()='Chat with Us ']") and 
            self.verify_element_by_xpath("//button[@class='button-quick-tour']")):
            self.safe_click("//button[@class='button-quick-tour']")