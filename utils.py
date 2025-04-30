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
        if self.verify_element_by_xpath(xpath):
            try:
                return self.driver.find_element(By.XPATH, xpath).text
            except:
                return default
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
        """Safely click an element"""
        element = self.wait_for_element(xpath)
        if element:
            try:
                element.click()
                return True
            except Exception as e:
                print(f"Error clicking element: {e}")
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except:
                    return False
        return False
    
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