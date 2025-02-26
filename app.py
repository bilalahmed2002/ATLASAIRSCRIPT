from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor
import time
from bs4 import BeautifulSoup

app = Flask(__name__)

# Function to fetch AWB details
def fetch_awb_data(awb_number):
    output_data = {
        "AWB Number": awb_number,
        "Total Pieces": "",
        "Total Weight": "",
        "Route": "",
        "Flight Number": "",
        "Flight Date": "",
        "ULD Info": [],
        "Error": "",
    }

    # Selenium setup
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    try:
        driver.get("https://jumpseat.atlasair.com/aa/tracktracehtml/TrackTrace.html?pe=403&se=21678591")
        wait = WebDriverWait(driver, 20)

        # Enter AWB number
        awb_input = wait.until(EC.visibility_of_element_located((By.ID, "txtAwb")))
        awb_input.clear()
        awb_input.send_keys(awb_number)

        # Submit
        submit_button = wait.until(EC.element_to_be_clickable((By.ID, "AwbSubmit")))
        submit_button.click()

        # Wait for results
        time.sleep(3)

        # Parse page
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Extract data
        awb_info_table = soup.find("table", {"id": "tblAWBInfo"})
        if awb_info_table:
            rows = awb_info_table.find_all("tr")
            for row in rows:
                columns = [col.text.strip() for col in row.find_all("td")]
                if len(columns) == 4:
                    output_data["Total Pieces"] = columns[2]
                    output_data["Total Weight"] = columns[3]

        booking_info_table = soup.find("table", {"id": "tblBookingInfo"})
        if booking_info_table:
            rows = booking_info_table.find_all("tr")
            for row in rows:
                columns = [col.text.strip() for col in row.find_all("td")]
                if len(columns) >= 4:
                    output_data["Route"] = columns[0]
                    output_data["Flight Number"] = columns[1]
                    output_data["Flight Date"] = columns[2]

        status_info_table = soup.find("table", {"id": "tblStatusInfo"})
        if status_info_table:
            rows = status_info_table.find_all("tr")
            for row in rows:
                columns = [col.text.strip() for col in row.find_all("td")]
                if len(columns) == 3 and columns[0] != "ULD Number":
                    output_data["ULD Info"].append(f"{columns[0]}/{columns[1]}")

    except Exception as e:
        output_data["Error"] = str(e)
    finally:
        driver.quit()

    return output_data

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/process', methods=['POST'])
def process():
    awb_input = request.form.get("awb_input")
    # Extract and format AWB numbers
    awb_numbers = [f"{line.split()[0]}-{line.split()[1]}" for line in awb_input.splitlines() if "\t" in line]
    
    # Dynamically set max_workers to the number of AWBs
    max_workers = len(awb_numbers)
    
    # Process AWB numbers in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(fetch_awb_data, awb_numbers))

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
