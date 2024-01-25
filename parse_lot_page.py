import logging
from os import path, getcwd
import json
import random
from typing import Dict, Any
import time
import base64

from seleniumwire import webdriver as webdriver_wire
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

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

    def parse_page(self, parse_url) -> Dict:
        driver, user_agent = self.get_webdriver()
        try:
            driver.get(parse_url)
            driver.maximize_window()

            area, number = None, None
            address = driver.find_element(By.CLASS_NAME, "product-rows").find_elements(By.TAG_NAME, "dd")[7].text
            description = driver.find_elements(By.CLASS_NAME, "ty-product__full-description")[1].text
            purpose = description.lower().split("назначение")[1].replace(": ", "").replace(",", ".").split(".")[0].strip()
            floor = description.lower().split("этаж")[1].replace(": ", "").replace(",", ".").split(".")[0].strip()
            entrance = description.lower().split("входы:")[1].split(".")[0]

            driver.find_element(By.ID, "ui-id-1").click()

            for item in driver.find_element(By.CLASS_NAME, "ui-accordion-content").find_elements(
                    By.CLASS_NAME, "product-list-field"):
                if item.find_element(By.CLASS_NAME, "ty-control-group__label").text == 'Кадастровый номер':
                    number = item.find_element(By.CLASS_NAME, "ty-control-group__item").text
                elif item.find_element(By.CLASS_NAME, "ty-control-group__label").text == 'Общая площадь':
                    area = item.find_element(By.CLASS_NAME, "ty-control-group__item").text

            if not area:
                area = description.lower().split("площад")[1].split()[1]
            if not number:
                number = description.lower().split("кадастровый номер").split()[-1].split(".")[0]

            try:
                participants = len(driver.find_elements(By.ID, "rejected_participants")[0].find_elements(By.TAG_NAME, "tr"))
            except NoSuchElementException:
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
print(test.parse_page("https://catalog.lot-online.ru/index.php?dispatch=products.view&product_id=698458"))
