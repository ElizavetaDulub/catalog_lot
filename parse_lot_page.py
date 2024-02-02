import logging
from os import path, getcwd
import json
import random
from typing import Dict, Any, Tuple, Optional
import time
import base64
import re

from seleniumwire import webdriver as webdriver_wire
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException

from fake_useragent import UserAgent


class ParsePage:

    def get_webdriver(cls, user_agent: str = None) -> Any:
        """
            Create webdriver object with options and proxy secure

        :param host: proxy host name;
        :param port: proxy port;
        :param usr: user name;
        :param pwd: proxy password;
        :param user_agent: user_agent for webdriver;
        :return: webdriver object.
        """
        if not user_agent:
            useragent = UserAgent().random
        else:
            useragent = user_agent

        options = webdriver_wire.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        # if usr and pwd:
        #     seleniumwire_options = {
        #         'proxy': {
        #             'http': f'http://{usr}:{pwd}@{host}:{port}',
        #             'verify_ssl': False,
        #         },
        #     }
        # else:
        seleniumwire_options = {}
            # options.add_argument(f"--proxy-server=https://{usr}:{pwd}@{host}:{port}")
        # options.add_argument(f"--proxy-server=https://{host}:{port}")
        # options.add_argument('--headless=new')  # turn off opening browser window
        options.add_argument(f"user-agent={useragent}")
        options.set_capability("goog:loggingPrefs", {'browser': 'ALL'})

        return webdriver_wire.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options,
                                     seleniumwire_options=seleniumwire_options), useragent

    def parse_description(self, driver, description) -> Tuple:
        area, number, purpose, floor, entrance = None, None, None, None, None
        if 'назначение' in description:
            purpose = description.lower().split("назначение")[1].replace(": ", "").replace(",", ".").split(".")[
                0].strip()
        elif 'этаж' in description:
            floor = description.lower().split("этаж")[1].replace(": ", "").replace(",", ".").split(".")[
                0].strip()
        elif 'входы' in description:
            entrance = description.lower().split("входы:")[1].split(".")[0]
        try:
            driver.find_element(By.ID, "ui-id-1").click()

            for item in driver.find_element(By.CLASS_NAME, "ui-accordion-content").find_elements(
                    By.CLASS_NAME, "product-list-field"):
                if item.find_element(By.CLASS_NAME, "ty-control-group__label").text == 'Кадастровый номер':
                    number = item.find_element(By.CLASS_NAME, "ty-control-group__item").text
                elif item.find_element(By.CLASS_NAME, "ty-control-group__label").text == 'Общая площадь':
                    area = item.find_element(By.CLASS_NAME, "ty-control-group__item").text
        except (ElementNotInteractableException, NoSuchElementException):
            pass

        return area, number, floor, entrance, purpose

    def parse_page(self, parse_url) -> Dict:
        driver, user_agent = self.get_webdriver()
        try:
            driver.get(parse_url)
            # driver.maximize_window()

            area, number, purpose, floor, entrance = None, None, None, None, None
            description = driver.find_elements(By.CLASS_NAME, "ty-product__full-description")[-1].text

            if 'имущество должников' in driver.find_element(By.CLASS_NAME, "product-rows").find_elements(
                    By.TAG_NAME, "dd")[0].text.lower():

                address = driver.find_element(By.CLASS_NAME, "product-rows").find_elements(By.TAG_NAME, "dd")[5].text
                area, number, floor, entrance, purpose = self.parse_description(driver, description)
                if 'использование' in description:
                    purpose = description.lower().split("использование")[1].replace(": ", "").replace(",", ".").split(".")[0].strip()
                if not area:
                    area = "".join(re.findall('([0-9][,|.]{0,1})', description.lower().split("площадь")[1].replace(": ", "").split("м")[0]))
                if not number:
                    number = ', '.join(re.findall('([0-9]{2}[:]{1}[0-9]{2}[:][0-9]{6,7}[:][0-9]{3,4})', description.lower()))
            else:
                address = driver.find_element(By.CLASS_NAME, "product-rows").find_elements(By.TAG_NAME, "dd")[7].text
                area, number, floor, entrance, purpose = self.parse_description(driver, description)
                if not area:
                    # area = description.lower().split("площадь")[1].split()[1]
                    area = ''.join(re.findall('[\d,|.]\d', description.lower().split("площадь")[1].replace(": ", "").split()[0]))
                if not number:
                    number = ', '.join(re.findall('([0-9]{2}[:]{1}[0-9]{2}[:][0-9]{6,7}[:][0-9]{3,4})', description.lower()))

            try:
                participants = len(driver.find_elements(By.ID, "rejected_participants")[0].find_elements(By.TAG_NAME, "tr"))
            except (NoSuchElementException, IndexError):
                participants = 0
                pass

            return {'address': address, 'area': area, 'number': number, 'floor': floor, 'entrance': entrance,
                    'purpose': purpose, 'participants': participants}

        except Exception as exc:
            logging.error(str(exc))

        finally:
            driver.close()
            driver.quit()


test = ParsePage()
print(test.parse_page("https://catalog.lot-online.ru/index.php?dispatch=products.view&product_id=770998"))
