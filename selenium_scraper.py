import pandas as pd
import os
import csv
import re
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc  # This is a key difference - using undetected_chromedriver

class AmazonUndetectedScraper:
    def __init__(self):
        """Initialize scraper with undetected-chromedriver to bypass anti-bot measures"""
        self.setup_driver()
        
        # Create output directory
        self.output_dir = "amazon_reviews"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create master CSV file
        self.all_reviews_file = f"{self.output_dir}/all_reviews.csv"
        with open(self.all_reviews_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['product_id', 'review_text'])
    
    def setup_driver(self):
        """Set up undetected-chromedriver which bypasses anti-bot detection"""
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        
        # Added user agent to appear more like a real browser
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        self.driver = uc.Chrome(options=options)
        self.driver.set_page_load_timeout(30)
    
    def extract_product_id(self, url):
        """Extract Amazon product ID (ASIN) from URL"""
        pattern = r'/dp/([A-Z0-9]{10})'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None
    
    def random_delay(self, min_sec=2, max_sec=5):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_sec, max_sec)
        print(f"  Waiting for {delay:.1f} seconds...")
        time.sleep(delay)
    
    def get_reviews_for_product(self, product_url, max_reviews=500):
        """Get reviews for a product using undetected-chromedriver"""
        product_id = self.extract_product_id(product_url) or "unknown"
        print(f"Scraping reviews for product: {product_url}")
        print(f"Product ID: {product_id}")
        
        reviews = []
        
        try:
            # Directly go to the reviews page using the URL format that works for Amazon India
            reviews_url = f"https://www.amazon.in/product-reviews/{product_id}/ref=cm_cr_arp_d_viewopt_srt?sortBy=recent&pageNumber=1"
            print(f"  Loading reviews page: {reviews_url}")
            self.driver.get(reviews_url)
            
            # Wait longer to ensure page loads completely
            self.random_delay(5, 8)
            
            # Check if we're on a reviews page
            try:
                # Take screenshot for debugging (optional)
                self.driver.save_screenshot(f"{self.output_dir}/page_screenshot.png")
                print("  Saved screenshot for debugging")
                
                # Wait for reviews to load and check if they exist
                review_containers = self.driver.find_elements(By.CSS_SELECTOR, "[data-hook='review']")
                
                # If no reviews found with primary selector, try alternates
                if not review_containers:
                    review_containers = self.driver.find_elements(By.CSS_SELECTOR, ".a-section.review")
                
                if not review_containers:
                    review_containers = self.driver.find_elements(By.CSS_SELECTOR, "[data-cel-widget*='customer_review']")
                
                if not review_containers:
                    print("  No reviews found using standard selectors. Checking page source...")
                    
                    # Check if there's a message about no reviews
                    page_source = self.driver.page_source.lower()
                    if "there are no customer reviews yet" in page_source or "be the first to review this item" in page_source:
                        print("  This product has no reviews")
                        return []
                    
                    # If page doesn't indicate no reviews, try advanced approach
                    print("  Using advanced review extraction from page source...")
                    soup_text = self.driver.page_source
                    
                    # Look for review text in the raw HTML using regex patterns
                    # This is a backup approach when selectors fail
                    review_patterns = [
                        r'<span data-hook="review-body"[^>]*>(.*?)</span>',
                        r'<div class="a-row a-spacing-small review-data">(.*?)</div>',
                        r'<span class="a-size-base review-text">(.*?)</span>'
                    ]
                    
                    for pattern in review_patterns:
                        matches = re.findall(pattern, soup_text, re.DOTALL)
                        if matches:
                            for match in matches:
                                # Clean up the HTML and extract just the text
                                clean_text = re.sub(r'<[^>]+>', ' ', match).strip()
                                clean_text = re.sub(r'\s+', ' ', clean_text)
                                if len(clean_text) > 20:  # Only take reviews of reasonable length
                                    reviews.append(clean_text)
                            
                            print(f"  Found {len(reviews)} reviews using regex pattern")
                            break
                    
                    if not reviews:
                        print("  Could not extract reviews - site structure may have changed")
                        return []
                
                else:
                    print(f"  Found {len(review_containers)} reviews on first page")
                    
                    # Process reviews on this page
                    self.process_review_containers(review_containers, reviews, product_id)
                    
                    # Navigate through additional pages if needed
                    page = 1
                    while len(reviews) < max_reviews:
                        page += 1
                        
                        # Check for next page button
                        next_button = None
                        next_selectors = [
                            ".a-pagination .a-last a",
                            "li.a-last a",
                            "[data-hook='pagination-next']"
                        ]
                        
                        for selector in next_selectors:
                            try:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                if elements:
                                    next_button = elements[0]
                                    break
                            except:
                                continue
                        
                        if next_button:
                            # Check if the "Next" button is disabled
                            parent_element = self.driver.execute_script(
                                "return arguments[0].parentNode;", next_button
                            )
                            parent_class = parent_element.get_attribute("class")
                            
                            if parent_class and "a-disabled" in parent_class:
                                print("  Next button is disabled - reached last page")
                                break
                            
                            print(f"  Navigating to page {page}...")
                            
                            # Scroll to the next button
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                            self.random_delay(1, 2)
                            
                            # Click to go to next page
                            next_button.click()
                            self.random_delay(3, 6)
                            
                            # Get and process reviews on the new page
                            review_containers = self.driver.find_elements(By.CSS_SELECTOR, "[data-hook='review']")
                            if not review_containers:
                                review_containers = self.driver.find_elements(By.CSS_SELECTOR, ".a-section.review")
                            if not review_containers:
                                review_containers = self.driver.find_elements(By.CSS_SELECTOR, "[data-cel-widget*='customer_review']")
                            
                            print(f"  Found {len(review_containers)} reviews on page {page}")
                            self.process_review_containers(review_containers, reviews, product_id)
                        else:
                            print("  No next button found - reached last page")
                            break
                
            except Exception as e:
                print(f"  Error processing reviews: {str(e)}")
            
            print(f"  Successfully scraped {len(reviews)} reviews for product {product_id}")
            
            # Save reviews to product-specific file
            product_file = f"{self.output_dir}/reviews_{product_id}.csv"
            with open(product_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['review_text'])
                for review in reviews:
                    writer.writerow([review])
            
            print(f"  Saved reviews to {product_file}")
            
        except Exception as e:
            print(f"Error scraping product {product_url}: {str(e)}")
        
        return reviews
    
    def process_review_containers(self, containers, reviews_list, product_id):
        """Process review containers and extract review text"""
        for container in containers:
            try:
                # Try multiple selectors for review text
                review_text_element = None
                selectors = [
                    "[data-hook='review-body'] span",
                    ".review-text-content span",
                    ".review-text",
                    ".a-expander-content"
                ]
                
                for selector in selectors:
                    try:
                        elements = container.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            review_text_element = elements[0]
                            break
                    except:
                        continue
                
                if review_text_element:
                    review_text = review_text_element.text.strip()
                    if review_text:
                        reviews_list.append(review_text)
                        
                        # Write to CSV file as we go
                        with open(self.all_reviews_file, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow([product_id, review_text])
            except Exception as e:
                print(f"  Error extracting review text: {str(e)}")
    
    def scrape_from_csv(self, csv_file, max_reviews_per_product=500):
        """Scrape reviews for all products in a CSV file"""
        try:
            # Read the CSV file
            df = pd.read_csv(csv_file)
            
            # Determine URL column
            if 'product_links' in df.columns:
                url_column = 'product_links'
            else:
                url_column = df.columns[0]
            
            print(f"Found {len(df)} products in CSV file in column '{url_column}'")
            
            total_reviews = 0
            successful_products = 0
            
            # Process each product URL
            for i, row in df.iterrows():
                try:
                    url = str(row[url_column]).strip()
                    
                    # Skip empty or invalid URLs
                    if not url or not isinstance(url, str):
                        print(f"Skipping invalid URL in row {i+1}")
                        continue
                    
                    # Add https:// if missing
                    if not url.startswith('http'):
                        url = 'https://' + url
                    
                    print(f"\nProcessing product {i+1}/{len(df)}: {url}")
                    
                    # Scrape reviews for this product
                    reviews = self.get_reviews_for_product(url, max_reviews=max_reviews_per_product)
                    
                    if reviews:
                        total_reviews += len(reviews)
                        successful_products += 1
                    
                    # Add longer delay between products
                    self.random_delay(8, 15)
                    
                except Exception as e:
                    print(f"Error processing product at row {i+1}: {str(e)}")
            
            print("\nScraping completed!")
            print(f"Products processed: {len(df)}")
            print(f"Products with reviews: {successful_products}")
            print(f"Total reviews collected: {total_reviews}")
            print(f"All reviews saved to: {self.all_reviews_file}")
            
            return self.all_reviews_file
            
        except Exception as e:
            print(f"Error processing CSV file: {str(e)}")
            return None
        
        finally:
            # Always close the WebDriver
            if hasattr(self, 'driver'):
                self.driver.quit()
                print("WebDriver closed")

# Main execution
if __name__ == "__main__":
    scraper = AmazonUndetectedScraper()
    try:
        scraper.scrape_from_csv("amazon_products1.csv", max_reviews_per_product=500)
    finally:
        # Make sure driver is closed
        if hasattr(scraper, 'driver'):
            scraper.driver.quit()


