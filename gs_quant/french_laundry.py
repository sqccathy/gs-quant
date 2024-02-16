import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from multiprocessing import Pool
import sys
import random

# options = Options()

# options.add_experimental_option("excludeSwitches", ["enable-automation"])
# options.add_experimental_option('useAutomationExtension', False)
# options.add_experimental_option('prefs', {
#     'credentials_enable_service': False,
#     'profile': {
#         'password_manager_enabled': False
#     }
# })
# s = Service('C:\\Users\\sqcca\\chromedriver-win32\\chromedriver-win32\\chromedriver.exe')
# driver = webdriver.Chrome(service=s, options=options)

# wait = WebDriverWait(driver, 30)

# stealth(driver,
#       languages=["en-US", "en"],
#       vendor="Google Inc.",
#       platform="Win32",
#       webgl_vendor="Intel Inc.",
#       renderer="Intel Iris OpenGL Engine",
#       fix_hairline=True,
# )


# #CLAIM RESERVATION
# name = "tfl"
# month = "03"
# day = "22"
# size = "4"
# timeorig = "20:30"
# picktime = timeorig.replace(":","%3A")

# url = "https://www.exploretock.com/" + name + "/search?date=2024-" + month + "-" + day + "&size=" + size + "&time=" + picktime

# driver.get(url)

# time.sleep(0.5)

# #change reservation name and time
# while True:
#     try: 
#         res = driver.find_element(By.XPATH, "//button[@class='Consumer-resultsListItem is-available']")
#         res.click()
#         sys.exit("Program stopped.")
#     except:
#         pass
#     time.sleep(0.5)
#     print("trying again")

def booking(date: str):
    options = Options()

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option('prefs', {
        'credentials_enable_service': False,
        'profile': {
            'password_manager_enabled': False
        }
    })
    s = Service('C:\\Users\\sqcca\\chromedriver-win32\\chromedriver-win32\\chromedriver.exe')
    driver = webdriver.Chrome(service=s, options=options)

    wait = WebDriverWait(driver, 30)

    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )


    #CLAIM RESERVATION
    name = "tfl"
    month = "03"
    day = date
    size = "2"
    timeorig = "20:30"
    picktime = timeorig.replace(":","%3A")

    #change reservation name and time
    while True:
        url = "https://www.exploretock.com/" + name + "/search?date=2024-" + month + "-" + day + "&size=" + size + "&time=" + picktime
        driver.get(url)
        time.sleep(0.5)
        try: 
            res = driver.find_element(By.XPATH, "//button[@class='Consumer-resultsListItem is-available']")
            res.click()
            print("good")
        except:
            pass
        time.sleep(random.random())
        print("trying again")

import multiprocessing
if __name__ == '__main__':
    pool = multiprocessing.Pool(8)
    results = pool.map(booking, ["09","10","11","12", "16","17", "23", "24"])
    pool.close()
    pool.join()

    print(results)

#OPTIONAL: CONFIRM RESERVATION


# login = driver.find_element(By.XPATH, "//*[@id='#maincontent']/div/div[1]/div/div/div/div/div[2]/form/div/div[1]/div")

# login.click()

# user = driver.find_element(By.ID, "email")

# email = "sqccathy@gmail.com"

# user.send_keys(email)

# pas = driver.find_element(By.ID, "password")

# password = "qichensun"

# pas.send_keys(password)

# first_name = driver.find_element(By.ID, "firstName")
# first_name.send_keys("Cathy")

# last_name = driver.find_element(By.ID, "lastName")
# last_name.send_keys("Sun")

# phone = driver.find_element(By.ID, "phone")
# phone.send_keys("9174975408")

# zip = driver.find_element(By.ID, "zipCode")
# zip.send_keys("94105")

# time.sleep(5)
# WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.XPATH,"//iframe[@title='Widget containing a Cloudflare security challenge']")))
# #WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//label[@class='ctp-checkbox-label']"))).click()

# pas.submit()

#time.sleep(4)

#final = driver.find_element(By.XPATH, "//button[./span[contains(.,'Complete reservation')]]")

#final.click()