from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
import time
import json
import os

# Connect to your existing Chrome debugging session
options = webdriver.ChromeOptions()
options.debugger_address = "localhost:9222"
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)



def scrape_units():
    scraped_units = []

    floor_rows = driver.find_elements(By.XPATH, "//div[@id='available-grid']/div")

    for floor_row in floor_rows:
        try:
            floor_label = floor_row.find_element(By.XPATH, ".//div[1]/button/label")
            floor_number = floor_label.text.strip()

            unit_buttons = floor_row.find_elements(By.XPATH, ".//div[2]/div/a/button")

            for unit_button in unit_buttons:
                label_text = unit_button.find_element(By.TAG_NAME, "label").text.strip()
                unit_number = label_text.splitlines()[0]  # First line is unit number

                class_attr = unit_button.get_attribute("class").lower()
                is_taken = "grayunitcard" in class_attr

                # Collect data as dict
                scraped_units.append({
                    'floor': floor_number,
                    'unit': unit_number,
                    'taken': is_taken
                })

                print(floor_number, unit_number, is_taken)

        except Exception as e:
            print("Error scraping floor row:", e)

    return scraped_units



blocks = ["Blk 1", "Blk 2"]

all_units = []

for block_name in blocks:
    print(block_name)
    # Select the block
    block_select_elem = driver.find_element(By.XPATH, "/html/body/app-root/div[2]/app-bto-details/section/div/div[5]/div/div[2]/div/div/div[3]/select")
    block_select = Select(block_select_elem)
    block_select.select_by_visible_text(f'Blk {block_name}')
    time.sleep(2)  # wait for page update, adjust if needed

    # Scrape units for the selected block
    units = scrape_units()

    # Add block info to each unit
    for unit in units:
        unit['block'] = block_name

    # Append to master list
    all_units.extend(units)

# Define path
output_path = "all_blocks_units.json"
changes_path = "unit_changes.json"

# Step 1: Load previous data (if exists)
if os.path.exists(output_path):
    with open(output_path, "r") as f:
        previous_units = json.load(f)

    # Step 2: Create a lookup dict from previous data
    previous_lookup = {
        (item['block'], item['floor'], item['unit']): item['taken']
        for item in previous_units
    }

    # Step 3: Compare and record changes
    changes = []
    for unit in all_units:
        key = (unit['block'], unit['floor'], unit['unit'])
        prev_taken = previous_lookup.get(key)

        if prev_taken is not None and prev_taken != unit['taken']:
            changes.append({
                "block": unit['block'],
                "floor": unit['floor'],
                "unit": unit['unit'],
                "was_taken": prev_taken,
                "now_taken": unit['taken']
            })

    # Step 4: Save changes if any
    if changes:
        with open(changes_path, "w") as f:
            json.dump(changes, f, indent=2)
        print(f"{len(changes)} unit(s) changed. Changes saved to {changes_path}")
    else:
        print("No unit changes since last scrape.")

else:
    print("No previous data found. Skipping comparison.")

# Step 5: Save latest scrape (overwrite previous)
with open(output_path, "w") as f:
    json.dump(all_units, f, indent=2)

print(f"Scraped data from {len(blocks)} blocks saved to {output_path}")


import green_updater

