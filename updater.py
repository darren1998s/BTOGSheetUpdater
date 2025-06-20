import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# Authorize with your credentials
creds = ServiceAccountCredentials.from_json_keyfile_name(
    "PRIVATE CREDENTIALS HERE.json",
    ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)

# Open your Google Sheet and worksheet
sheet = client.open("GOOGLE SHEET NAME").worksheet("ACTUAL SHEET NAME")

# Floor to row mapping (floors 15 to 2 correspond to rows 4 to 17)
# zip(range(top floor, bottom floor - 1)), range(row for top floor, row for bottom floor + 1)
floor_to_row = {str(f): i for f, i in zip(range(15, 2-1, -1), range(4, 18))}

# Unit number to column number mapping (columns B to S = 2 to 19)
unit_row = sheet.row_values(3)[1:]  # Get units from B3:S3, skip A3
unit_to_col = {}
for idx, val in enumerate(unit_row):
    if val.strip():
        unit_to_col[val.strip()] = idx + 2  # columns start at B=2

# Load scraped units from JSON
with open("all_blocks_units.json", "r") as f:
    scraped_units = json.load(f)

# Define range start/end in the sheet for batch update
start_row = 4 # Top floor row
end_row = 17 # Bottom floor row
start_col = 2 # 2nd Col, first col is the floor index
end_col = 19  # last column with units # In the screen shot, column 19 is S.

num_rows = end_row - start_row + 1
num_cols = end_col - start_col + 1

# Initialize the data grid with 'FALSE' (all available)
data_grid = [[False for _ in range(num_cols)] for _ in range(num_rows)]


# Fill data_grid with scraped data
for item in scraped_units:
    floor = item['floor'].replace("#", "").strip()
    try:
        floor = str(int(floor))  # convert "09" to "9"
    except ValueError:
        print(f"Skipping invalid floor: {floor}")
        continue
    unit = item['unit']
    taken = item['taken']

    if floor not in floor_to_row or unit not in unit_to_col:
        print(f"Skipping unknown floor/unit: Floor {floor}, Unit {unit}")
        continue

    row_idx = floor_to_row[floor] - start_row  # zero-based row index for data_grid
    col_idx = unit_to_col[unit] - start_col    # zero-based col index for data_grid

    data_grid[row_idx][col_idx] = True if taken else False


# Cells to leave blank (not update)
cells_to_clear = ['K17', 'L17', 'N17', 'O17', 'R17']

from gspread.utils import a1_to_rowcol

for cell in cells_to_clear:
    r, c = a1_to_rowcol(cell)  # convert to absolute sheet row/col
    row_idx = r - start_row    # zero-based index for data_grid
    col_idx = c - start_col

    if 0 <= row_idx < len(data_grid) and 0 <= col_idx < len(data_grid[0]):
        data_grid[row_idx][col_idx] = None  # leave blank / clear


# Construct A1 notation range string, e.g. "B4:S17"
from gspread.utils import rowcol_to_a1
range_start = rowcol_to_a1(start_row, start_col)  # e.g. B4
range_end = rowcol_to_a1(end_row, end_col)        # e.g. S17
range_str = f"{range_start}:{range_end}"

# Batch update all checkboxes in one request
sheet.update(range_str, data_grid)

print(f"Batch updated checkboxes in range {range_str}")



def col_letter_to_index(col):
    """Convert A1-style column letters (e.g., 'X', 'AI') to 1-based index (e.g., X=24, AI=35)"""
    index = 0
    for char in col:
        index = index * 26 + (ord(char.upper()) - ord('A') + 1)
    return index


# Step 1: Get cells in X4:AI17 (row-major)
raw_cells = sheet.range("X4:AI17")

# Step 2: Rearrange to column-major order
start_col = col_letter_to_index("X")
end_col = col_letter_to_index("AI")
num_cols = end_col - start_col + 1
num_rows = 14  # rows 4 - 17

existing_cells = []
for col_offset in range(num_cols):
    for row_offset in range(num_rows):
        index = row_offset * num_cols + col_offset
        existing_cells.append(raw_cells[index])

existing_values = [cell.value.strip() for cell in existing_cells if cell.value.strip()]
existing_tags = set(existing_values)  # e.g., {"#11-110", "#13-103", ...}

# Step 2: Get taken units from latest scrape
new_tags = []
for item in scraped_units:
    if item['taken']:
        floor = item['floor'].replace("#", "").strip()
        try:
            floor = (int(floor))
        except ValueError:
            continue
        unit = item['unit'].strip()
        tag = f"#{floor:02d}-{unit}"  # <-- zero-padded floor
        if tag not in existing_tags and tag not in new_tags:
            new_tags.append(tag)

# Step 3: Find blank cells in X20:Y34 to insert new tags
empty_cells = [cell for cell in existing_cells if not cell.value.strip()]
num_to_add = min(len(empty_cells), len(new_tags))

for i in range(num_to_add):
    empty_cells[i].value = new_tags[i]

# Step 4: Batch update modified cells (only if there's something to add)
if num_to_add > 0:
    sheet.update_cells(empty_cells[:num_to_add])
    print(f"Appended {num_to_add} new units to X4 onwards")
else:
    print("No new units to append to X4 onwards")



# Format: "18 Jun, 11:31"
now_str = datetime.now().strftime("%d %b, %H:%M")

# Update cell V3 with the timestamp
sheet.update_acell("V3", now_str)
print(f"Updated V3 with timestamp: {now_str}")