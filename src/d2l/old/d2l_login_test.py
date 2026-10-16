USERNAME = "username"
PASSWORD = "password"

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as wait

driver = webdriver.Firefox()

def login_D2L(USERNAME, PASSWORD):
    """Given USERNAME and PASSWORD, logs into user's D2L Homepage."""

    try:
        # UA SSO Login
        driver.get("https://d2l.arizona.edu/Shibboleth.sso/Login?entityID=urn:mace:incommon:arizona.edu&target=https%3A%2F%2Fd2l.arizona.edu%2Fd2l%2FshibbolethSSO%2Flogin.d2l")
        #driver.implicitly_wait(1.0)
        wait.until(driver.find_element(by=By.CSS_SELECTOR, value="button") != None)
        driver.find_element(by=By.ID, value="username").send_keys(USERNAME)
        driver.find_element(by=By.ID, value="password").send_keys(PASSWORD)
        driver.find_element(by=By.CSS_SELECTOR, value="button").click()

        # Duo Secruity 2FA. Requires both find/click statements. Why?
        driver.implicitly_wait(1.0)
        #wait.until(driver, method)
        driver.find_element(by=By.CSS_SELECTOR, value="button").click()
        driver.find_element(by=By.CSS_SELECTOR, value="button.auth-button.positive").click()
        driver.implicitly_wait(1.0)

    except:
        pass

login_D2L(USERNAME, PASSWORD)
