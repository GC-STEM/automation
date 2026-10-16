#! /usr/bin/env python3
# -*- coding: 'utf_8' -*-

#234567890123456789012345678901234567890123456789012345678901234567890123456789
"""========================== MAIN COMMENT BLOCK ==============================
Script : D2L Login
Author : Mike Benson
Date   : January ##, 2023
Version: .01
History:
Purpose: To login to D2L thru Shibboleth SSO and Duo Security if necessary.
Sources: Adapted from https://www.selenium.dev/documentation
============================================================================"""


"""======================= Import Standard Libraries ======================="""
# NONE


"""===================== Import Third-Party Libraries ======================"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


"""======================== Define Pseudo Constants ========================"""
# PEP8: Constants in UPPERCASE_WITH_UNDERSCORES.

driver = webdriver.Firefox() # Set to your preferred browser.

USERNAME = "username"
PASSWORD = "password"

DEST_URL = "https://d2l.arizona.edu"
DEST_METHOD = "UA NetID Login"       # Uncomment your 2FA method
#DEST_METHOD = "Non UA NetID Login"
#DEST_METHOD = "ASU Login"
#DEST_METHOD = "NAU Login"

LOGIN_URL = "https://d2l.arizona.edu/d2l/loginh/"

SSO_URL = "https://shibboleth.arizona.edu/idp/profile/SAML2/Redirect/SSO"

DUO_URL = "duosecurity.com"
DUO_METHOD = "Send Me A Push "
#DUO_METHOD = "Call Me "
#DUO_METHOD = "Enter a Passcode "

"""============================ Local Functions ============================"""
# PEP8: Function and variable names in lowercase_with_underscores.

def login_d2l(USERNAME = "",
              PASSWORD = "",
              DEST_URL = "https://d2l.arizona.edu",
              DEST_METHOD = "UA NetID Login",
              SSO_URL = "https://shibboleth.arizona.edu/idp/profile/SAML2/Redirect/SSO",
              DUO_URL = "duosecurity.com",
              DUO_METHOD = "Send Me A Push "
              ):
    """Logs into D2L"""
    try:
        if DEST_METHOD == "UA NetID Login":
            WebDriverWait(driver, timeout=10).until(EC.element_to_be_clickable((By.ID, "ualoginbutton")))
            driver.get("https://d2l.arizona.edu/Shibboleth.sso/Login?entityID=urn:mace:incommon:arizona.edu&target=https%3A%2F%2Fd2l.arizona.edu%2Fd2l%2FshibbolethSSO%2Flogin.d2l")
            WebDriverWait(driver, timeout=10).until(EC.url_contains(SSO_URL))
            login_sso(USERNAME, PASSWORD, DEST_URL, SSO_URL, DUO_URL, DUO_METHOD)
            return
        elif DEST_METHOD == "Non UA NetID Login":
            #ToDo: Add procedure.
            pass
            return
        elif DEST_METHOD == "ASU Login" or "NAU Login":
            #ToDo: Click on down arrow to make visible.
            if DEST_METHOD == "ASU Login":
                #ToDo: Click on <ASU Login> button
                #ToDo: Create ASU Shibboleth login function
                pass
                return
            elif DEST_METHOD == "NAU Login":
                #ToDo: Click on <NAU Login> button
                #ToDo: Create NAU Shibboleth login function
                pass
                return
            else:
                #ToDo: Handle exceptions
                pass
                return
        else:
            #ToDo: Handle exceptions
            pass
            return
        # ToDo: Handle Alerts
        #       Invalid username or password.

        # ToDo: Handle stale request.

        # ToDo: Handle Not Authorized https://d2l.arizona.edu/shibua.html

    # ToDo: Handle other cases.

    except:
        # ToDo: Add exception handling.
        pass
        return


def login_sso(USERNAME = "",
              PASSWORD = "",
              DEST_URL = "https://d2l.arizona.edu",
              SSO_URL = "https://shibboleth.arizona.edu/idp/profile/SAML2/Redirect/SSO",
              DUO_URL = "duosecurity.com",
              DUO_METHOD = "Send Me A Push "
              ):
    """Logs into UA SSO with Duo Security MFA"""
    try:
        # UA SSO Login
        WebDriverWait(driver, timeout=10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button")))

        if SSO_URL in driver.current_url:
            if USERNAME == "" or None:
                # ToDo: Wait for user to manually input username.
                # ToDo: Wait for cursor/focus to move out of username field.
                pass
            else:
                driver.find_element(by=By.ID, value="username").clear
                driver.find_element(by=By.ID, value="username").send_keys(USERNAME)
            if PASSWORD == "" or None:
                # ToDo: Wait for user to manually input password
                # ToDo: Wait for <Login> button click.
                pass
            else:
                driver.find_element(by=By.ID, value="password").clear
                driver.find_element(by=By.ID, value="password").send_keys(PASSWORD)
                driver.find_element(by=By.CSS_SELECTOR, value="button").click()

            # ToDo: Handle Alerts
            #       Invalid username or password.

            # ToDo: Handle stale request.

            # ToDo: Handle Not Authorized https://d2l.arizona.edu/shibua.html

        # ToDo: Handle other cases.

        # Duo Security MFA
        WebDriverWait(driver, timeout=10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button")))

        if DUO_URL in driver.current_url:
            if DUO_METHOD == "Send Me A Push ":
                driver.find_element(by=By.CSS_SELECTOR, value="button").click()
                driver.find_element(by=By.CSS_SELECTOR, value="button").click()
            elif DUO_METHOD == "Call Me ":
                # ToDo: Figure out how to click second button.
                # Possibly using 'Locators: Relative Locators OR
                # 'Finders: Evaluating a subset of the DOM' OR
                # 'Finders: Optimized locator'
                pass
            elif DUO_METHOD == "Enter a Passcode ":
                pass # ToDo: Figure out how to click third button.
            #driver.page_source.find()
            WebDriverWait(driver, timeout=70).until(EC.url_changes(DEST_URL))
            return True
        #else:
            # ToDo: Add exception handling for unexpected URL.
            #return False
    except:
        # ToDo: Add exception handling.
        pass


"""============================= Local Classes ============================="""
# PEP8: Class and exception names in CamelCase (i.e., CapWords).
# PEP8: Exception names that are errors end with "Error" (e.g. CamelCaseError).


"""=========================== Main Entry Point ============================"""
# Open DEST_URL webpage and wait for page to load.
driver.get(DEST_URL)
#WebDriverWait(driver, timeout=10).until(document_initialised)
#WebDriverWait(driver, timeout=10).until(EC.element_to_be_clickable((By.ID, "ualoginbutton"))).click

# If need to login, then login.
if LOGIN_URL in driver.current_url:
    login_d2l(USERNAME, PASSWORD, DEST_URL, DEST_METHOD, SSO_URL, DUO_URL, DUO_METHOD)
#elif DEST_URL in driver.current_url:
