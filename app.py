import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import os



def extract_info(soup):
    st.subheader("1. Business Information:")
    business_name = soup.find('h1', class_='business-name')
    if business_name:
        st.write(f"Business Name: {business_name.text.strip()}")

    business_description = soup.find('div', class_='business-description')
    if business_description:
        st.write(f"Business Description: {business_description.text.strip()[:200]}...")  # First 200 characters

    st.subheader("\n2. Appointment Availability:")
    availability_message = soup.find('span', id='no-times-available-message')
    if availability_message:
        st.write(f"Availability Message: {availability_message.text.strip()}")

    calendar = soup.find('div', class_='calendar')
    if calendar and not calendar.find_all():
        st.write("Calendar is empty, suggesting no available appointments.")

    st.subheader("\n3. Appointment Types:")
    appointment_types = soup.find_all('input', attrs={'name': 'appointmentType'})
    for apt_type in appointment_types:
        type_name = soup.find('label', attrs={'for': apt_type.get('id')})
        if type_name:
            st.write(f"- {type_name.text.strip()}")
            duration = soup.find('span', id=f"appointment-{apt_type.get('value')}-duration")
            if duration:
                st.write(f"  Duration: {duration.text.strip()}")

    st.subheader("\n4. Time Zone Information:")
    timezone_container = soup.find('div', id='timezone-container')
    if timezone_container:
        timezone_label = timezone_container.find('span', id='timezone-label')
        if timezone_label:
            st.write(f"Default Time Zone: {timezone_label.text.strip()}")

    st.subheader("\n5. Contact Information:")
    phone_field = soup.find('input', id='phone')
    if phone_field:
        st.write("Phone field is present in the form.")

    email_field = soup.find('input', id='email')
    if email_field:
        st.write("Email field is present in the form.")

    st.subheader("\n6. Additional Information:")
    script_tags = soup.find_all('script', type='text/javascript')
    for script in script_tags:
        if script.string:
            if 'window.Acuity' in script.string:
                acuity_data = script.string
                break

    if 'acuity_data' in locals():
        # Extract JSON-like data
        start = acuity_data.find('{')
        end = acuity_data.rfind('}') + 1
        json_data = acuity_data[start:end]
        
        try:
            data = json.loads(json_data)
            if 'bootstrap' in data:
                st.write(f"Owner ID: {data['bootstrap'].get('ownerId', 'Not found')}")
                st.write(f"Default to Client Timezone: {data['bootstrap'].get('defaultToClientTimezone', 'Not specified')}")
        except json.JSONDecodeError:
            st.write("Could not parse additional Acuity data.")

    st.subheader("\n7. Scheduling Steps:")
    steps = soup.find_all('h2', class_='step-title')
    if steps:
        st.write("The scheduling process includes these steps:")
        for step in steps:
            st.write(f"- {step.text.strip()}")

    st.subheader("\n8. Form Fields:")
    form_fields = soup.find_all('input', class_='form-control')
    if form_fields:
        st.write("The following form fields are required:")
        for field in form_fields:
            st.write(f"- {field.get('name', 'Unnamed field')} (Type: {field.get('type', 'Not specified')})")

    st.subheader("\n9. Recaptcha Information:")
    recaptcha_script = soup.find('script', attrs={'src': lambda x: x and 'recaptcha' in x})
    if recaptcha_script:
        st.write("Google reCAPTCHA is implemented on this page.")
        site_key = soup.find('script', text=lambda t: t and 'RECAPTCHA_SITE_KEY' in t)
        if site_key:
            key = site_key.string.split("'")[1]
            st.write(f"reCAPTCHA Site Key: {key}")

    st.subheader("\n10. Powered By:")
    powered_by = soup.find('div', class_='poweredby-content')
    if powered_by:
        st.write(f"This scheduling system is powered by: {powered_by.text.strip()}")
    return availability_message



def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def print_element_info(element, depth=0):
    indent = "  " * depth
    info = []
    info.append(f"{indent}Tag: {element.tag_name}")
    info.append(f"{indent}Text: {element.text.strip()}")
    info.append(f"{indent}Attributes:")
    for attr, value in element.get_property('attributes').items():
        info.append(f"{indent}  {attr}: {value}")
    info.append(f"{indent}Classes: {element.get_attribute('class')}")
    info.append(f"{indent}ID: {element.get_attribute('id')}")
    info.append(f"{indent}Name: {element.get_attribute('name')}")
    info.append(f"{indent}Value: {element.get_attribute('value')}")
    info.append(f"{indent}Href: {element.get_attribute('href')}")
    info.append(f"{indent}Style: {element.get_attribute('style')}")
    info.append(f"{indent}Is Displayed: {element.is_displayed()}")
    info.append(f"{indent}Is Enabled: {element.is_enabled()}")
    info.append(f"{indent}Location: {element.location}")
    info.append(f"{indent}Size: {element.size}")
    info.append(f"{indent}CSS: {element.value_of_css_property('display')}")
    
    children = element.find_elements(By.XPATH, "./*")
    if children:
        info.append(f"{indent}Children:")
        for child in children:
            info.extend(print_element_info(child, depth + 1))
    
    return info

def scrape_scheduling_page(url):
    driver = setup_driver()
    all_info = []
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    all_info.append("Page Title: " + driver.title)
    all_info.append("Page URL: " + driver.current_url)
    all_info.append(driver.page_source)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    with st.expander('Extracted Info'):
        availability_message = extract_info(soup)
    return all_info, availability_message




def main(freq=60):
    st.title("Egyptian Consulate Scheduling Scraper")
    url = "https://app.acuityscheduling.com/schedule.php?owner=29805901&all=1&PHPSESSID=sehgvlmp5q67mjjs10mvltl7sv"
    if 'last_run' not in st.session_state:st.session_state.last_run = []
    if 'data' not in st.session_state:st.session_state.data = []
    if 'found_appointments' not in st.session_state:st.session_state.found_appointments = []

    current_time = time.time()
    data, availability_message = scrape_scheduling_page(url)


    st.write(f"Latest Run: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))}")
    if availability_message:
        st.info(availability_message.text.strip())
        if "No times are available" in availability_message.text:
            st.error("No times are available.")
            found_appointments = False
        else:
            st.success("Appointments are available!")
            found_appointments = True   
    else:
        st.error("Could not find Available Appointments message.")
        found_appointments = False
    st.session_state.last_run.append(current_time)
    st.session_state.data.append(data)
    st.session_state.found_appointments.append(found_appointments)
    st.write(f"Found Appointments: {found_appointments}")
    with st.expander("Show Data"):
        for d in data[:-1]:
            st.write(d)
        st.markdown(data[-1], unsafe_allow_html=True)

    if found_appointments:
        with open("successful_runs.log", "a") as file:
            file.write(f"Run at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))}\n")
            for d in data:
                file.write(d + "\n")
            file.write("\n")
    else:
        with open("failed_runs.log", "a") as file:
            file.write(f"Run at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))}\n")
            for d in data[:-1]:
                file.write(d + "\n")
            file.write("\n")


    #Older information
    st.header("Previous Runs")
    with st.expander("Show Last 10 Runs"):
        count = 0
        for i in range(len(st.session_state.last_run) - 1, -1, -1):
            st.subheader(f"Run {i + 1}")
            st.write(f"Found Appointments: {st.session_state.found_appointments[i]} Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.session_state.last_run[i]))}")
            count += 1
            if count >= 10:
                break



    # Rerun the app after freq seconds
    with st.empty():
        for i in range(freq):
            st.write(f"Time until rerun: {freq - i} seconds")
            time.sleep(1)
    st.write("Rerunning...")
    st.rerun()

if __name__ == "__main__":
    st.set_page_config(page_title="Egyptian Consulate Scheduling Scraper", page_icon="🕵️", layout='wide')

    # create log files if they don't exist
    if not os.path.exists("successful_runs.log"):
        with open("successful_runs.log", "w") as file:
            file.write("Successful Runs\n\n")
    if not os.path.exists("failed_runs.log"):
        with open("failed_runs.log", "w") as file:
            file.write("Failed Runs\n\n")

    with open("successful_runs.log", "r") as file:
        successful_runs = file.read()
        st.download_button("Download successful runs log", successful_runs, "successful_runs.log", "text/plain")
    
    with open("failed_runs.log", "r") as file:
        failed_runs = file.read()
        st.download_button("Download failed runs log", failed_runs, "failed_runs.log", "text/plain")
    main(3)