#! /usr/bin/env python3
# -*- coding: 'utf_8' -*-

'''========================== MAIN COMMENT BLOCK ==============================
Script : D2L
Author : Mike Benson
Date   : January ##, 2023
Version: .01
History:
Purpose: To create student folders from a D2L classlist
============================================================================'''


'''======================= Import Standard Libraries ======================='''
import webbrowser   # Convenient web-browser controller


'''===================== Import Third-Party Libraries ======================'''
from selenium import webdriver
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

'''========== Import Local Application/Library Specific Libraries =========='''
# NONE


'''======================== Define Pseudo Constants ========================'''
# PEP8: Constants in UPPERCASE_WITH_UNDERSCORES.

driver = webdriver.Firefox()

USERNAME = "username"
PASSWORD = "password"

DEST_URL = "https://d2l.arizona.edu"
DEST_EXPIRED = "https://d2l.arizona.edu/d2l/loginh/?sessionExpired"
DEST_METHOD = "UA NetID Login"
#DEST_METHOD = "Non UA NetID Login"
#DEST_METHOD = "ASU Login"
#DEST_METHOD = "NAU Login"

LOGIN_URL = "https://d2l.arizona.edu/d2l/loginh/"
UA_LOGIN_BUTTON = "https://d2l.arizona.edu/Shibboleth.sso/Login?entityID=urn:mace:incommon:arizona.edu&target=https%3A%2F%2Fd2l.arizona.edu%2Fd2l%2FshibbolethSSO%2Flogin.d2l"

SSO_URL = "https://shibboleth.arizona.edu/idp/profile/SAML2/Redirect/SSO"

DUO_URL = "duosecurity.com"
DUO_METHOD = "Send Me A Push "
#DUO_METHOD = "Call Me "
#DUO_METHOD = "Enter a Passcode "


'''============================ Local Functions ============================'''
# PEP8: Function and variable names in lowercase_with_underscores.

def login_d2l():
	'''Logs into D2L'''
	try:
		if DEST_METHOD == "UA NetID Login":
			WebDriverWait(driver, timeout=10).until(EC.element_to_be_clickable((By.ID, "ualoginbutton")))
			#driver.get("https://d2l.arizona.edu/Shibboleth.sso/Login?entityID=urn:mace:incommon:arizona.edu&target=https%3A%2F%2Fd2l.arizona.edu%2Fd2l%2FshibbolethSSO%2Flogin.d2l")
			driver.get(UA_LOGIN_BUTTON)
			WebDriverWait(driver, timeout=10).until(EC.url_contains(SSO_URL))
			#login_sso(USERNAME, PASSWORD, DEST_URL, DEST_METHOD, SSO_URL, DUO_URL, DUO_METHOD)
			login_sso()
			return
		elif DEST_METHOD == "Non UA NetID Login":
			#TODO: Add procedure.
			pass
			return
		elif DEST_METHOD == "ASU Login" or "NAU Login":
			#TODO: Click on down arrow to make visible.
			if DEST_METHOD == "ASU Login":
				#TODO: Click on <ASU Login> button
				#TODO: Create ASU Shibboleth login function
				pass
				return
			elif DEST_METHOD == "NAU Login":
				#TODO: Click on <NAU Login> button
				#TODO: Create NAU Shibboleth login function
				pass
				return
			else:
				#TODO: Handle exceptions
				pass
				return
		else:
			#TODO: Handle exceptions
			pass
			return
		# TODO: Handle Alerts
		#       Invalid username or password.

		# TODO: Handle stale request.

		# TODO: Handle Not Authorized https://d2l.arizona.edu/shibua.html

	# TODO: Handle other cases.

	except:
		# TODO: Add exception handling.
		pass
		return


def login_sso():
	'''Logs into UA SSO with Duo Security MFA'''
	try:
		# UA SSO Login
		WebDriverWait(driver, timeout=10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button")))

		if SSO_URL in driver.current_url:
			if USERNAME == "" or None:
				# TODO: Wait for user to manually input username.
				# TODO: Wait for cursor/focus to move out of username field.
				pass
			else:
				driver.find_element(by=By.ID, value="username").clear
				driver.find_element(by=By.ID, value="username").send_keys(USERNAME)
			if PASSWORD == "" or None:
				# TODO: Wait for user to manually input password
				# TODO: Wait for <Login> button click.
				pass
			else:
				driver.find_element(by=By.ID, value="password").clear
				driver.find_element(by=By.ID, value="password").send_keys(PASSWORD)
				driver.find_element(by=By.CSS_SELECTOR, value="button").click()

			# TODO: Handle Alerts
			#       Invalid username or password.

			# TODO: Handle stale request.

			# TODO: Handle Not Authorized https://d2l.arizona.edu/shibua.html

		# TODO: Handle other cases.

		# Duo Security MFA
		WebDriverWait(driver, timeout=10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button")))

		if DUO_URL in driver.current_url:
			if DUO_METHOD == "Send Me A Push ":
				driver.find_element(by=By.CSS_SELECTOR, value="button").click()
				driver.find_element(by=By.CSS_SELECTOR, value="button").click()
			elif DUO_METHOD == "Call Me ":
				# TODO: Figure out how to click second button.
				# Possibly using 'Locators: Relative Locators OR
				# 'Finders: Evaluating a subset of the DOM' OR
				# 'Finders: Optimized locator'
				pass
			elif DUO_METHOD == "Enter a Passcode ":
				pass # TODO: Figure out how to click third button.
			#driver.page_source.find()
			WebDriverWait(driver, timeout=70).until(EC.url_changes(DEST_URL))
			return True
		#else:
			# TODO: Add exception handling for unexpected URL.
			#return False
	except:
		# TODO: Add exception handling.
		pass


def get_my_courses(search_term = "",
	               role = "Instructor",
				   term = "All",
				   dept = "All",
				   course_start_from = None,
				   course_start_to = None,
				   course_end_from = None,
				   course_end_to = None,
				   status = "All"
				   ):

	'''Given filter arguments, retrieves list of D2L course that meet filters.

	Filter arguments:
	role = []
	term = []
	dept = []
	start_from = date
	start_to = date
	end_from = date
	end_to = date
	status = []

	returns list of D2L courses
	'''
	#try:
	driver.get("https://d2l.arizona.edu/d2l/le/manageCourses/search/6725")
	#if DEST_EXPIRED in driver.current_url:
		#driver.get(UA_LOGIN_BUTTON)
	#WebDriverWait(driver, timeout=10).until(EC.element_to_be_clickable((By.ID, "d2l_1_86_271")))
	driver.implicitly_wait(10)
	course_count_text = driver.find_element(by=By.XPATH, value="//span [contains(text(), 'items in the list.')]").text
	course_count_list = course_count_text.split(' ')
	course_count = int(course_count_list[0])



	#driver.find_elements(by=By.CLASS_NAME, value="d2l-grid-cell").text

	#page_count = int(driver.find_element(by=By.CLASS_NAME, value="d2l-numericpager-pagecount").text)
	#print(type(page_count))
	#print(f"page_count = {page_count}")
	#select_element = driver.find_element(by=By.ID, value="filtersData$roleIds")
	#select = Select(select_element)
	#select.select_by_visible_text(role)
	#driver.implicitly_wait(1.0)
	#number_element = driver.find_element(by=By.CLASS_NAME, value="d2l-grid-action-container-count-nosearch d2l-hidden")
	#print(number_element)
	#grid_rows = driver.find_elements(by=By.CLASS_NAME, value="d2l-grid-row")
	#print(type(grid_rows), len(grid_rows))
	#for row in grid_rows:
		#print(row.text)
	#return
	#except:
		#return

def get_classlist():
	return



# Following functions from https://intoli.com/blog/clear-the-firefox-browser-cache/
'''
def get_clear_site_data_button(driver):
	return driver.find_element_by_css_selector('#clearSiteDataButton')


def get_clear_site_data_dialog(driver):
	return driver.find_element_by_css_selector(dialog_selector)


def get_clear_site_data_confirmation_button(driver):
	return driver.find_element_by_css_selector('#clearButton')


def clear_firefox_cache(driver, timeout=10):
	driver.get('about:preferences#privacy')
	wait = WebDriverWait(driver, timeout)
'''


'''============================= Local Classes ============================='''
# PEP8: Class and exception names in CamelCase (i.e., CapWords).
# PEP8: Exception names that are errors end with "Error" (e.g. CamelCaseError).

class Course:
	def __init__(self, num, name, code, term, dept, start, end, url):
		self.num = num
		self.name = name
		self.code = code
		self.term = term
		self.dept = dept
		self.start = start
		self.end = end
		self.url = url


'''=========================== Main Entry Point ============================'''
if __name__ == '__main__':


	# Open DEST_URL webpage and wait for page to load.
	driver.get(DEST_URL)
	# Wait for page to finish loading.

	# If not logged into D2L, login.
	if LOGIN_URL in driver.current_url:
		#login_d2l(USERNAME, PASSWORD, DEST_URL, DEST_METHOD, SSO_URL, DUO_URL, DUO_METHOD)
		login_d2l()
	WebDriverWait(driver, timeout=70).until(EC.url_contains(DEST_URL))
	#TODO: Handle DEST_URL not loading

	# TODO: Read D2L course classlist for student names & emails
	get_my_courses()

	#driver.quit
'''
	# Following code from https://intoli.com/blog/clear-the-firefox-browser-cache/
	dialog_selector = '#dialogOverlay-0 > groupbox:nth-child(1) > browser:nth-child(2)'

	accept_dialog_script = (
		f"const browser = document.querySelector('{dialog_selector}');" +
		"browser.contentDocument.documentElement.querySelector('#clearButton').click();"
	)

	def get_clear_site_data_button(driver):
		return driver.find_element_by_css_selector('#clearSiteDataButton')


	def get_clear_site_data_dialog(driver):
		return driver.find_element_by_css_selector(dialog_selector)


	def get_clear_site_data_confirmation_button(driver):
		return driver.find_element_by_css_selector('#clearButton')


	def clear_firefox_cache(driver, timeout=10):
		driver.get('about:preferences#privacy')
		wait = WebDriverWait(driver, timeout)

		# Click the "Clear Data..." button under "Cookies and Site Data".
		wait.until(get_clear_site_data_button)
		get_clear_site_data_button(driver).click()

		# Accept the "Clear Data" dialog by clicking on the "Clear" button.
		wait.until(get_clear_site_data_dialog)
		driver.execute_script(accept_dialog_script)

		# Accept the confirmation alert.
		wait.until(EC.alert_is_present())
		alert = Alert(driver)
		alert.accept()
'''
