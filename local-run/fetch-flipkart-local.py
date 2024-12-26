import os
import time
import logging
import csv
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from playsound3 import playsound

# Import variables from variables.py
from variables import PIN_CODES, HEADLESS_MODE, URL_FILE_PATH, MAX_CYCLES, WAIT_TIME, CSV_FILE_PATH

class ProductChecker:
    def __init__(self, url, pincodes, headless=True):
        self.url = url
        self.pincodes = pincodes
        self.driver = self._setup_driver(headless)

    def _setup_driver(self, headless):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        return webdriver.Chrome(options=options)

    def fetch_product_details(self):
        self.driver.get(self.url)
        product_name = self._get_element_text(By.CLASS_NAME, 'VU-ZEz', "Product name not found")
        product_price = self._get_element_text(By.CLASS_NAME, 'Nx9bqj.CxhGGd', "Price not found")
        is_sold_out = self._is_sold_out()
        return product_name, product_price, is_sold_out

    def check_pincode_availability(self):
        _, _, is_sold_out = self.fetch_product_details()
        availability_results = {}

        if is_sold_out:
            availability_results = {pincode: "Sold out" for pincode in self.pincodes}
        else:
            for pincode in self.pincodes:
                status = self._check_single_pincode(pincode)
                availability_results[pincode] = status
                if status == "Available":
                    playsound('notification.wav')

        return availability_results

    def _check_single_pincode(self, pincode):
        try:
            pincode_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'pincodeInputId'))
            )
            pincode_input.clear()
            pincode_input.send_keys(pincode)
            check_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'i40dM4'))
            )
            check_button.click()
            time.sleep(5)

            if self._element_exists(By.CLASS_NAME, 'nyRpc8'):
                return "Out of stock"

            return "Available"
        except Exception as e:
            logger.error(f"Error checking pincode {pincode}: {e}")
            return "Could not check availability."

    def _get_element_text(self, by, identifier, default=""):
        try:
            return self.driver.find_element(by, identifier).text
        except:
            return default

    def _is_sold_out(self):
        return self._element_exists(By.CLASS_NAME, 'Z8JjpR')

    def _element_exists(self, by, identifier):
        try:
            return bool(self.driver.find_element(by, identifier))
        except:
            return False

    def close(self):
        self.driver.quit()

def configure_logging():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def print_header(pincodes):
    headers = ["Product", "Price"] + pincodes
    header_format = "| {:<50} | {:<10} " + "| {:<12} " * len(pincodes) + "|"
    header_row = header_format.format(*headers)
    separator_row = '-' * len(header_row)

    print(separator_row)
    print(header_row)
    print(separator_row)

def display_product(product_name, product_price, availability_results):
    data_format = "| {:<50} | {:>10} " + "| {:<12} " * len(availability_results) + "|"
    data = [
        product_name,
        product_price
    ] + [
        "Available" if status == "Available" else "Out of stock"
        for status in availability_results.values()
    ]

    data_row = data_format.format(*data)
    print(data_row)
    print('-' * len(data_row))

def write_results_to_csv(product_name, product_price, availability_results):
    file_exists = os.path.isfile(CSV_FILE_PATH)
    headers = ["Date and Time", "Product", "Price"] + list(availability_results.keys())

    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow([current_datetime, product_name, product_price] + list(availability_results.values()))

def main():
    logger = configure_logging()

    try:
        with open(URL_FILE_PATH, 'r') as file:
            urls = [url.strip() for url in file if url.strip()]

        for cycle in range(MAX_CYCLES):
            start_time = time.time()

            print_header(PIN_CODES)

            for url in urls:
                product_checker = ProductChecker(url, PIN_CODES, HEADLESS_MODE)
                try:
                    product_name, product_price, _ = product_checker.fetch_product_details()
                    availability_results = product_checker.check_pincode_availability()

                    display_product(product_name, product_price, availability_results)
                    write_results_to_csv(product_name, product_price, availability_results)
                finally:
                    product_checker.close()

            execution_time = time.time() - start_time
            logger.info(f"Fetch time: {execution_time:.2f} seconds")

            if cycle < MAX_CYCLES - 1:
                logger.info(f"Waiting for {WAIT_TIME} seconds before the next iteration...")
                time.sleep(WAIT_TIME)

    except Exception as e:
        logger.error(f"An error occurred in the main function: {e}")

if __name__ == "__main__":
    main()