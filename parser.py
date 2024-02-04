import logging
import time

import coloredlogs
from logging import handlers
import os
import numpy as np
import coloredlogs
from typing import Any

import pandas as pd
import asyncio
import aiohttp

from seleniumwire import webdriver as webdriver_wire
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import NoSuchElementException
from fake_useragent import UserAgent
import logging
from multiprocessing.pool import ThreadPool as Pool
from multiprocessing import Process
from multiprocessing import Semaphore
import re
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException

from queue import Queue

logger = logging.getLogger('seleniumwire')
logger.setLevel(logging.ERROR)
# logger.setLevel(logging.INFO)

coloredlogs.install(level='INFO')
main_data = pd.read_excel('Main_data_spb.xlsx')
missed_urls = list()
numbers_list = list()


# @classmethod
def get_logger(name=None, level=logging.DEBUG):
    logger = logging.getLogger(name)
    name = 'root' if name is None else name
    if not os.path.exists(os.getcwd() + '/logs'):
        os.makedirs(os.getcwd() + '/logs')
    logger.setLevel(level)
    logger.propagate = True
    logger_Handler = handlers.TimedRotatingFileHandler(filename=f"{os.getcwd() + '/logs'}/{name}.log")
    logger_Formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    logger_Handler.setFormatter(logger_Formatter)
    logger.addHandler(logger_Handler)
    return logger


module_logger = get_logger("parse_catalog_lot")


# @classmethod
def get_webdriver() -> Any:
    """
        Create webdriver object with options and proxy secure

    :return: webdriver object.
    """
    useragent = UserAgent().random
    options = webdriver_wire.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument('--disable-logging')
    options.add_argument('--headless=new')  # turn off opening browser window
    options.add_argument(f"user-agent={useragent}")
    return webdriver_wire.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)


class ParseLot:
    def __init__(self, filename: str = None):
        # self.main_data = pd.read_excel(filename)
        self.module_logger = get_logger("seleniumwire")
        # self.module_logger = get_logger("parse_catalog_lot")
        self.module_logger.setLevel(logging.INFO)
        # self.module_logger.setLevel(logging.ERROR)
        self.missed_urls = list()

    def parse_description(self, driver, description):
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

    def parse_lot(self, url: str = None):
        driver = get_webdriver()
        try:
            driver.get(url)
            # driver.maximize_window()

            area, number, purpose, floor, entrance = None, None, None, None, None
            description = driver.find_elements(By.CLASS_NAME, "ty-product__full-description")[-1].text

            if 'имущество должников' in driver.find_element(By.CLASS_NAME, "product-rows").find_elements(
                    By.TAG_NAME, "dd")[0].text.lower():

                address = driver.find_element(By.CLASS_NAME, "product-rows").find_elements(By.TAG_NAME, "dd")[5].text
                area, number, floor, entrance, purpose = self.parse_description(driver, description)
                if 'использование' in description:
                    purpose = \
                        description.lower().split("использование")[1].replace(": ", "").replace(",", ".").split(".")[
                            0].strip()
                if not area:
                    try:
                        area = "".join(re.findall('([0-9][,|.]{0,1})',
                                                  description.lower().split("площадь")[1].replace(": ", "").split("м")[0]))
                    except IndexError:
                        pass
                if not number:
                    number = ', '.join(
                        re.findall('([0-9]{2}[:]{1}[0-9]{2}[:][0-9]{6,7}[:][0-9]{3,4})', description.lower()))
            else:
                try:
                    address = driver.find_element(By.CLASS_NAME, "product-rows").find_elements(By.TAG_NAME, "dd")[7].text
                except IndexError:
                    try:
                        address = [item.find_element(By.TAG_NAME, 'dd').text for item in
                                   driver.find_element(By.CLASS_NAME, "product-rows").find_elements(By.TAG_NAME, "div") if
                                   'Адрес' in item.text][0]
                    except:
                        address = None
                area, number, floor, entrance, purpose = self.parse_description(driver, description)
                if not area:
                    try:
                        area = ''.join(
                            re.findall('[\d,|.]\d', description.lower().split("площадь")[1].replace(": ", "").split()[0]))
                    except IndexError:
                        pass
                if not number:
                    number = ', '.join(
                        re.findall('([0-9]{2}[:]{1}[0-9]{2}[:][0-9]{6,7}[:][0-9]{3,4})', description.lower()))
            try:
                state = driver.find_element(By.ID, "bidding_result").text
            except NoSuchElementException:
                try:
                    state = driver.find_element(By.ID, "lot_status").text
                except:
                    state = None

            try:
                participants = len(
                    driver.find_elements(By.ID, "rejected_participants")[0].find_elements(By.TAG_NAME, "tr"))
            except (NoSuchElementException, IndexError):
                participants = 0
                pass
            new_data = [address, area, number, floor, entrance, purpose, participants, state]
            # driver.close()
            # driver.quit()
            return new_data
        except Exception as exc:
            module_logger.error(f"Was exception {str(exc)} \n While parsed link {url} ")
            with open(r'missed_links_data.txt', 'a') as fp:
                fp.write("%s\n" % url)
        finally:
            driver.close()
            driver.quit()


def parse_page(*params):
    parser = ParseLot(filename="Main_data_spb.xlsx")
    index, url = params
    module_logger.info(f'Running parse page {index}. {url}')
    new_data = parser.parse_lot(url)
    main_data.loc[index, ["Адрес", "Площадь", "Кадастровый номер", "Этаж", "Входы", "Назначение",
                          "Отклоненные участники", "Состояние"]] = new_data
    main_data.to_excel("Main_data_spb.xlsx", index=False)


def run_threads(max_concurrent_requests=1):
    # urls = main_data.drop_duplicates(subset='Название лота', keep='first').loc[:, 'Ссылка на лот'].to_list()
    urls = main_data.loc[np.isnan(main_data.loc[:, 'Отклоненные участники']), 'Ссылка на лот'].to_list()  #
    module_logger.info(f"Amount of parse urls is {str(len(urls))}.")
    args = [(main_data.loc[main_data['Ссылка на лот'] == url].index[0], url) for url in urls]
    with Pool(processes=max_concurrent_requests) as pool:
        pool.starmap(parse_page, args, chunksize=40)


if __name__ == '__main__':
    # parser = ParseLot('catalog_2023.xlsx')
    # asyncio.run(parser.process_links(max_concurrent_requests=3))
    run_threads(max_concurrent_requests=8)
