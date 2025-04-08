import streamlit as st
import time # Placeholder for simulating work
import base64 # For embedding the logo
import os     # For path handling if needed
import configparser # To read config file
import requests # Will be needed for actual API call
import json # For handling API responses
import re # Import re module
from basecrm.client import Client # Ensure Client is imported if not already global

# ----------------------------------------------------------------
# Configuration Loading Function (Defined Globally)
# ----------------------------------------------------------------
CONFIG_FILE = "parameters.config"

def load_config():
    """Load configuration from parameters.config."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        # Use st.exception for better error display in Streamlit >= 1.30
        st.exception(FileNotFoundError(f"Configuration file '{CONFIG_FILE}' not found."))
        st.stop()
    config.read(CONFIG_FILE)
    return config

# Define Monday API URL globally as it's truly constant
MONDAY_API_URL = "https://api.monday.com/v2"
BOARD_ID = 1242580452 # The board ID you provided

# ----------------------------------------------------------------
# Initial Session State Setup (Global)
# ----------------------------------------------------------------
if "current_step" not in st.session_state:
    st.session_state["current_step"] = 1
if "deal_id" not in st.session_state:
    st.session_state["deal_id"] = ""
if "monday_data" not in st.session_state:
    st.session_state["monday_data"] = None # Placeholder for fetched data
if "note_written" not in st.session_state:
    st.session_state["note_written"] = None # None, True, or False
if "show_error" not in st.session_state:
    st.session_state["show_error"] = None
if "all_groups" not in st.session_state:
     st.session_state["all_groups"] = [] # Initialize as empty list
if "selected_groups" not in st.session_state:
     st.session_state["selected_groups"] = [] # Initialize as empty list
if "success_message" not in st.session_state:
     st.session_state["success_message"] = None # For success messages
if "processing" not in st.session_state:
    st.session_state["processing"] = False # Add processing flag


# ----------------------------------------------------------------
# Helper Functions (Defined Globally)
# ----------------------------------------------------------------

def get_logo_base64():
    """Reads the logo file and returns its Base64 encoded string."""
    logo_file = "Logo_2024_DxO_Black.png"
    try:
        with open(logo_file, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.error(f"Logo file not found: {logo_file}. Please ensure it's in the same directory.")
        return None

def fetch_monday_data(deal_id, board_id_to_query, monday_api_url, api_key):
    """Fetch all group names (titles) from the specified Monday.com board."""
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
        "API-Version": "2023-10"
    }
    query = f"""
    query {{
      boards(ids: [{board_id_to_query}]) {{
        groups {{
          id
          title
        }}
      }}
    }}
    """
    payload = json.dumps({"query": query})
    st.write(f"Querying Groups from Monday.com Board ID: {board_id_to_query}...")

    try:
        response = requests.post(monday_api_url, headers=headers, data=payload, timeout=15)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            error_message = f"Monday API Error fetching groups: {result['errors']}"
            print(f"Error: {error_message}")
            return None, error_message

        # Extract groups safely
        groups = []
        if result.get("data") and result["data"].get("boards"):
            board_data = result["data"]["boards"][0]
            if board_data:
                groups = board_data.get("groups", [])

        if not groups:
            return [], "No groups found on the specified Monday.com board."

        # Return list of {'id': group_id, 'title': group_title}
        fetched_groups = [{"id": group["id"], "title": group["title"]} for group in groups]
        st.write(f"Fetched {len(fetched_groups)} groups from Monday.com.")
        return fetched_groups, None

    except requests.exceptions.RequestException as e:
        error_message = f"Network or HTTP error connecting to Monday API: {e}"
        print(f"Error: {error_message}") # Log error
        return None, error_message
    except json.JSONDecodeError:
        error_message = "Error decoding JSON response from Monday API."
        print(f"Error: {error_message}") # Log error
        return None, error_message
    except Exception as e:
        error_message = f"An unexpected error occurred during Monday API call: {e}"
        print(f"Error: {error_message}") # Log error
        return None, error_message

def write_note_to_zendesk(deal_id, monday_data_summary):
    """Placeholder: Write a note to Zendesk Sell Deal."""
    # IMPORTANT: This function will also need API keys passed or loaded.
    # For now, it remains a placeholder.
    st.write(f"Simulating writing note to Zendesk Sell for Deal ID: {deal_id}...")
    st.write(f"Note Content: {monday_data_summary}")
    time.sleep(1.5) # Simulate API call
    if deal_id == "zerror": # Simulate a Zendesk error
         return False, "Failed to write note to Zendesk (Simulated Error)"
    return True, None

def reset_app():
    """Resets the session state to start over."""
    st.session_state["current_step"] = 1
    st.session_state["deal_id"] = ""
    st.session_state["monday_data"] = None # Keep this for potential future use
    st.session_state["note_written"] = None
    st.session_state["show_error"] = None
    st.session_state["all_groups"] = [] # Reset groups
    st.session_state["selected_groups"] = [] # Reset selected groups
    if "selected_group_details" in st.session_state:
        del st.session_state["selected_group_details"]
    st.query_params.clear()

def get_status_index_from_label(board_id, column_id, target_label, api_key):
    """Queries Monday to find the index for a given status label."""
    headers = {"Authorization": api_key, "Content-Type": "application/json", "API-Version": "2023-10"}
    query = f"""
    query ($boardId: ID!, $columnId: String!) {{
        boards(ids: [$boardId]) {{
            columns(ids: [$columnId]) {{
                settings_str
            }}
        }}
    }}
    """
    variables = {"boardId": board_id, "columnId": column_id}
    payload = json.dumps({"query": query, "variables": variables})

    try:
        response = requests.post(MONDAY_API_URL, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            raise Exception(f"API error fetching column settings: {result['errors']}")

        settings_str = result["data"]["boards"][0]["columns"][0]["settings_str"]
        settings = json.loads(settings_str)
        labels_map = settings.get("labels", {})

        for index, label in labels_map.items():
            if label == target_label:
                print(f"Found index '{index}' for label '{target_label}'")
                # Monday API expects index to be integer for mutation
                return int(index), None 

        return None, f"Label '{target_label}' not found in settings for column '{column_id}'. Found: {labels_map}"

    except Exception as e:
        print(f"Error getting status index for label '{target_label}': {e}")
        return None, f"Error getting status index: {e}"

def update_monday_item_status(item_id, status_column_id, new_status_label, api_key):
    """Updates the status column using GraphQL Variables."""

    status_index, error_msg = get_status_index_from_label(
        BOARD_ID, status_column_id, new_status_label, api_key
    )
    if error_msg:
        print(f"Error finding status index for item {item_id}: {error_msg}")
        return False, error_msg

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json", # Still needed
        "API-Version": "2023-10"
    }

    # --- FIX: Parameterized Mutation using Variables ---
    mutation = """
    mutation ChangeStatusValue($itemId: ID!, $boardId: ID!, $columnId: String!, $statusValue: JSON!) {
      change_column_value(
        item_id: $itemId,
        board_id: $boardId,
        column_id: $columnId,
        value: $statusValue
      ) {
        id # Request the item id back on success
      }
    }
    """
    variables = {
        "itemId": str(item_id),       # Ensure Item ID is a string for ID! type
        "boardId": BOARD_ID,         # Board ID can often be Int or ID, keep as is for now
        "columnId": status_column_id,# Column ID is String!
        # --- Try sending as JSON string instead of raw dict ---
        # Previous attempt: "statusValue": {"index": status_index} 
        "statusValue": json.dumps({"index": status_index}) # Convert dict to JSON string
        # --- End Change ---
    }
    # --- End FIX ---

    # --- FIX: Send using json parameter ---
    payload = {"query": mutation, "variables": variables}
    # --- End FIX ---

    try:
        # --- FIX: Use json=payload ---
        response = requests.post(MONDAY_API_URL, headers=headers, json=payload, timeout=10)
        # --- End FIX ---
        print(f"Update status attempt for item {item_id} using index {status_index} via Variables. Response Status Code: {response.status_code}")
        response_text = response.text
        response.raise_for_status()
        result = response.json()
        print(f"Update status attempt for item {item_id} using index {status_index} via Variables. Response JSON: {result}")

        if "errors" in result and result["errors"]: # Check if errors key exists and is not empty/null
            error_message = f"Monday API GraphQL Error updating status via Variables: {result['errors']}"
            print(f"Error: {error_message}")
            return False, error_message

        # --- FIX: Reinstate stricter success check --- 
        if not result.get("data") or not result["data"].get("change_column_value") or not result["data"]["change_column_value"].get("id"):
             error_message = f"Monday API response structure unexpected or indicates failure using Variables. Full response: {result}"
             print(f"Error: {error_message}")
             return False, error_message
        # --- End FIX ---

        print(f"Successfully updated status via Variables for Monday item {item_id} to index '{status_index}' ('{new_status_label}')")
        return True, None

    except requests.exceptions.RequestException as e:
        error_message = f"Network/HTTP error (Variables method): {e}. Response text: {response_text if 'response_text' in locals() else 'N/A'}"
        print(f"Error: {error_message}")
        return False, error_message
    except json.JSONDecodeError:
         error_message = f"Failed to decode JSON response (Variables method). Response text: {response_text if 'response_text' in locals() else 'N/A'}"
         print(f"Error: {error_message}")
         return False, error_message
    except Exception as e:
        error_message = f"Unexpected error (Variables method): {e}"
        print(f"Error: {error_message}")
        return False, error_message

# --- NEW: Zendesk Owner Email to Monday User ID Mapping ---
# Based on get_monday_users.py output and assuming these emails match Zendesk owners
ZENDESK_OWNER_EMAIL_TO_MONDAY_ID = {
    "asoni@dxo.com": 47981810,        # Anand SONI
    "nbeaumont@dxo.com": 41505346,    # Nicolas BEAUMONT
    "jcinquin@dxo.com": 45440204,     # Julien CINQUIN
    "msato@dxo.com": 45440202,        # Masaya Sato
    "sbakir@dxo.com": 45440162,       # Stefan BAKIR
    "mplant@dxo.com": 45440206,       # Michael Wayne Plant
    "yshi@dxo.com": 45440205,         # Yangkun SHI
    "kdare@dxo.com": 68681569,        # Killian DARE
    "mandrianoelison@dxo.com": 69767169, # Marina Andrianoelison
    "mfernandes@dxo.com": 70228860,   # Maryjo FERNANDES
    # Add/verify others as needed
}
# --- END NEW MAPPING ---

# --- NEW: Zendesk Helper Function ---
def get_zendesk_deal_owner_email(deal_id, z_api_key):
    """Fetches the email address of the owner of a Zendesk Sell deal."""
    try:
        print(f"Fetching Zendesk deal details for ID: {deal_id}...")
        z_client = Client(access_token=z_api_key)
        # Retrieve the deal object
        deal = z_client.deals.retrieve(id=int(deal_id))

        if not deal or not deal.get('owner_id'):
            print(f"Warning: Could not find deal or owner_id for Deal ID {deal_id}")
            return None, f"Could not find deal or owner ID for Zendesk Deal {deal_id}."

        owner_id = deal['owner_id']
        print(f"Found Owner ID: {owner_id} for Deal ID {deal_id}. Fetching owner details...")

        # Retrieve the owner's user object using the owner_id
        owner = z_client.users.retrieve(id=owner_id)

        if not owner or not owner.get('email'):
            print(f"Warning: Could not find owner details or email for Owner ID {owner_id}")
            return None, f"Could not find owner details or email for Owner ID {owner_id} (Deal {deal_id})."

        owner_email = owner['email'].lower() # Use lower case for consistent matching
        print(f"Found Owner Email: {owner_email} for Deal ID {deal_id}")
        return owner_email, None # Return email and no error

    except Exception as e:
        error_message = f"Error fetching Zendesk deal owner email for Deal ID {deal_id}: {e}"
        print(f"Error: {error_message}")
        # Check for specific error types if needed (e.g., 404 Not Found)
        if "Not Found" in str(e):
             return None, f"Zendesk Deal ID {deal_id} not found."
        return None, error_message
# --- END NEW ZENDESK HELPER ---

# --- NEW: Monday Helper Function ---
def update_monday_item_person(item_id, monday_user_id, m_api_key):
    """Updates the Person column of a specific item on Monday.com."""
    headers = {
        "Authorization": m_api_key,
        "Content-Type": "application/json",
        "API-Version": "2023-10"
    }
    mutation = """
    mutation AssignPerson($itemId: ID!, $boardId: ID!, $columnId: String!, $personValue: JSON!) {
      change_column_value(
        item_id: $itemId,
        board_id: $boardId,
        column_id: $columnId,
        value: $personValue
      ) {
        id
      }
    }
    """
    # Format for people column: {"personsAndTeams": [{"id": <user_id>, "kind": "person"}]}
    person_json_value = json.dumps({
        "personsAndTeams": [{"id": int(monday_user_id), "kind": "person"}]
    })

    variables = {
        "itemId": str(item_id),
        "boardId": BOARD_ID, # Use global BOARD_ID
        "columnId": PERSON_COLUMN_ID, # Use the specific Person column ID
        "personValue": person_json_value
    }
    payload = {"query": mutation, "variables": variables}

    try:
        response = requests.post(MONDAY_API_URL, headers=headers, json=payload, timeout=10)
        print(f"Assign Person attempt for item {item_id} to user {monday_user_id}. Response Status Code: {response.status_code}")
        response_text = response.text
        response.raise_for_status()
        result = response.json()
        print(f"Assign Person attempt for item {item_id} to user {monday_user_id}. Response JSON: {result}")

        if "errors" in result and result["errors"]:
            error_message = f"Monday API GraphQL Error assigning person: {result['errors']}"
            print(f"Error: {error_message}")
            return False, error_message

        if not result.get("data") or not result["data"].get("change_column_value") or not result["data"]["change_column_value"].get("id"):
            error_message = f"Monday API response structure unexpected assigning person. Full response: {result}"
            print(f"Error: {error_message}")
            return False, error_message

        print(f"Successfully assigned Person (User ID: {monday_user_id}) to Monday item {item_id}")
        return True, None

    except requests.exceptions.RequestException as e:
        error_message = f"Network/HTTP error assigning person: {e}. Response text: {response_text if 'response_text' in locals() else 'N/A'}"
        print(f"Error: {error_message}")
        return False, error_message
    except json.JSONDecodeError:
        error_message = f"Failed to decode JSON response assigning person. Response text: {response_text if 'response_text' in locals() else 'N/A'}"
        print(f"Error: {error_message}")
        return False, error_message
    except Exception as e:
        error_message = f"Unexpected error assigning person: {e}"
        print(f"Error: {error_message}")
        return False, error_message
# --- END NEW MONDAY HELPER ---

# --- NEW: Product Order Priority ---
# Lower number means higher priority (appears first)
PRODUCT_ORDER_PRIORITY = {
    "PhotoLab": 1,
    "Nik": 2, # Use short prefix if display name is Nik Collection X
    "PureRaw": 3,
    "FilmPack": 4,
    "ViewPoint": 5,
    # Add other base names if necessary
}
DEFAULT_PRIORITY = 99 # For products not in the list
# --- Adjustments based on common prefixes ---
PRODUCT_ORDER_PRIORITY["Nik Collection"] = 2 # Handle full name too
# --- END NEW PRIORITY ---

# ----------------------------------------------------------------
# Main App Execution Starts Here
# ----------------------------------------------------------------

# --- Load Config and API Keys ---
config = load_config()
try:
    monday_api_key = config.get("monday", "api_key").strip().strip('"')
    if not monday_api_key:
        st.error("Monday.com API key missing/empty in parameters.config")
        st.stop()

    # Load Zendesk API key
    zendesk_api_key = config.get("zendesk", "api_key").strip().strip('"')
    if not zendesk_api_key:
         st.error("Zendesk Sell API key missing/empty in parameters.config under [zendesk]")
         st.stop()

except (configparser.NoSectionError, configparser.NoOptionError) as e:
    st.error(f"Could not find required section or key in parameters.config: {e}")
    st.stop()

# --- Define Column IDs and Status Labels ---
PERSON_COLUMN_ID = "person" # Confirmed Person column ID
STATUS_COLUMN_ID = "status"
MAC_LINK_COLUMN_ID = "mac_dowload_link0" # From user's API playground output
WIN_LINK_COLUMN_ID = "win_download_link"  # From user's API playground output
STATUS_LABEL_NOT_USED = "Not used"

# --- REVISED: Base Product Name Mapping (Prefix -> Base Name) ---
BASE_PRODUCT_MAPPING = {
    "DFP": "FilmPack",    # Check DFP before FP
    "DVP": "ViewPoint",   # Check DVP before VP
    "PR": "PureRaw",
    "PL": "PhotoLab",
    "NIK": "Nik Collection",
    "VP": "ViewPoint",
    "FP": "FilmPack",
}
# Define the order for checking regex patterns to handle overlaps
REGEX_PREFIX_ORDER = ["DFP", "DVP", "PR", "PL", "NIK", "VP", "FP"]
# --- END REVISED ---

# --- NEW HELPER: Get Mapped Product Name ---
def get_product_display_name(group_title):
    """Applies regex mapping to get user-friendly product name."""
    product_display_name = group_title # Default
    for prefix in REGEX_PREFIX_ORDER:
        # Match prefix followed by one or more digits (\d+)
        # Optional space or hyphen: \s?-?
        # Word boundaries \b ensure we don't match inside another word (e.g., "PROMO" shouldn't match "PR")
        # re.IGNORECASE makes the prefix matching case-insensitive
        match = re.search(rf'\b({prefix})\s?-?(\d+)\b', group_title, re.IGNORECASE)
        if match:
            matched_prefix = match.group(1).upper() # Get the matched prefix (e.g., 'PR'), ensure uppercase for dict lookup
            version_number = match.group(2)        # Get the version number string (e.g., '4')
            base_name = BASE_PRODUCT_MAPPING.get(matched_prefix)
            if base_name:
                product_display_name = f"{base_name} {version_number}"
                # print(f"Mapped group '{group_title}' to display name '{product_display_name}' using pattern '{matched_prefix}{version_number}'") # Optional debug
                break # Use the first match found based on REGEX_PREFIX_ORDER
    return product_display_name
# --- END NEW HELPER ---

# ----------------------------------------------------------------
# CSS Styling (Inspired by POM-Discount-App.py)
# ----------------------------------------------------------------
st.markdown("""
<style>
:root {
  --primary-color: #0073ea; /* Monday.com-like blue */
  --success-color: #00c875; /* Monday.com-like green */
  --error-color: #e2445c;   /* Monday.com-like red */
  --text-color: #333;
  --bg-color: linear-gradient(135deg, #f5f7fa, #e9ecef);
  --card-bg-color: #ffffff;
  --input-bg-color: #ffffff;
  --subtitle-color: #555;
  --progress-bg: #e0e0e0;
  --progress-fill: var(--primary-color);
  --logo-filter: none;
  --info-box-bg: #e8f4ff;
  --info-box-border: var(--primary-color);
  --error-box-bg: #ffebee;
  --error-box-border: var(--error-color);
  --success-box-bg: #e6faf0; /* Lighter green */
  --success-box-border: var(--success-color);
}

@media (prefers-color-scheme: dark) {
  :root {
    --text-color: #f0f0f0;
    --bg-color: linear-gradient(135deg, #1c1c1c, #2c2c2c);
    --card-bg-color: #2f2f2f;
    --input-bg-color: #3a3a3a;
    --subtitle-color: #ccc;
    --progress-bg: #555;
    --progress-fill: var(--primary-color);
    --logo-filter: invert(1) brightness(2); /* Adjust if using a logo */
    --info-box-bg: #1c3342;
    --info-box-border: var(--primary-color);
    --error-box-bg: #3c1c1c;
    --error-box-border: var(--error-color);
    --success-box-bg: #1a382b; /* Darker green */
    --success-box-border: var(--success-color);
  }
}

body {
    background: var(--bg-color);
    color: var(--text-color);
    font-family: 'Roboto', sans-serif; /* Consider adding Google Font import if needed */
}

.main-title {
    font-size: 1.8rem !important; /* Slightly larger */
    text-align: center;
    width: 100%;
    margin: 1rem auto 0.5rem auto; /* Adjust margins */
    font-weight: 600;
}

.subtitle {
    font-size: 1.1rem;
    text-align: center;
    margin-bottom: 2rem;
    color: var(--subtitle-color);
    font-weight: 400;
}

.card {
    background: var(--card-bg-color);
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 1.5rem;
    border: none;
}

/* --- Progress Bar Styles --- */
.progress-container {
    width: 100%;
    max-width: 500px;
    margin: 0 auto 2rem auto; /* Increased bottom margin */
    position: relative;
}
.progress-bar {
    height: 4px; /* Slightly thicker */
    background: var(--progress-bg);
    position: relative;
    margin: 0 auto;
    margin-top: 15px; /* Space for numbers */
    border-radius: 2px;
}
.progress-fill {
    position: absolute;
    height: 100%;
    background: var(--progress-fill);
    transition: width 0.4s ease-in-out; /* Smoother transition */
    border-radius: 2px;
}
.step-indicators {
    display: flex;
    justify-content: space-between;
    position: absolute;
    width: 100%;
    top: 0; /* Align numbers above the bar start */
}
.step-indicator {
    width: 24px; /* Slightly larger */
    height: 24px;
    background: var(--progress-bg);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    color: white;
    font-weight: bold;
    position: relative;
    z-index: 2;
    transform: translateY(-50%); /* Center vertically on the node */
    transition: all 0.3s ease;
    border: 2px solid var(--card-bg-color); /* Border to lift from bar */
}
.step-indicator.active {
    background: var(--primary-color);
    transform: translateY(-50%) scale(1.1); /* Slightly larger when active */
}
.step-indicator.completed {
    background: var(--success-color);
}
.step-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 8px; /* Space between bar and labels */
}
.step-label {
    width: 33.33%;
    text-align: center;
    font-size: 0.8rem; /* Slightly larger labels */
    color: #888;
    transition: color 0.3s ease;
    font-weight: 500;
}
.step-label.active {
    color: var(--primary-color);
}
.step-label.completed {
    color: var(--success-color);
}

/* --- Input and Button Styles --- */
input, .stButton>button {
    border-radius: 6px !important;
    transition: all 0.3s ease !important;
}
input {
    background: var(--input-bg-color) !important;
    color: var(--text-color) !important;
    border: 1px solid #ddd !important; /* Keep border for input */
    padding: 0.75rem 1rem !important;
}
input:focus {
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color) 20%, transparent) !important; 
}
.stButton>button { /* Style for PRIMARY buttons (like Next, Proceed) */
    background-color: var(--primary-color) !important;
    color: white !important;
    font-weight: 700 !important; /* Make bolder (was 600) */
    font-size: 1.05rem !important; /* Slightly larger font */
    padding: 0.8rem 1.5rem !important; /* Adjust padding slightly */
    transition: all 0.3s ease !important;
    width: auto !important; /* Allow button to size naturally */
    display: inline-block !important; /* Ensure correct layout */
    border-radius: 6px !important;
    border: none !important; /* Cleaner look for primary button */
    line-height: 1.5; /* Ensure text fits well */
}
.stButton>button:hover {
    background-color: color-mix(in srgb, var(--primary-color) 85%, black) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px color-mix(in srgb, var(--primary-color) 20%, transparent) !important;
}
.secondary-btn .stButton>button { /* Style for secondary buttons like 'Back' */
    background: transparent !important;
    color: var(--primary-color) !important;
    border: 1px solid var(--primary-color) !important;
    /* Make secondary slightly smaller/lighter */
     font-weight: 600 !important;
     font-size: 0.95rem !important;
     padding: 0.7rem 1.4rem !important;
     width: auto !important; /* Allow button to size naturally */
     display: inline-block !important; /* Ensure correct layout */
     line-height: 1.5;
}
.secondary-btn .stButton>button:hover {
    background: color-mix(in srgb, var(--primary-color) 10%, transparent) !important;
    color: var(--primary-color) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px color-mix(in srgb, var(--primary-color) 15%, transparent) !important;
}


/* --- Info/Error/Success Boxes --- */
.info-box, .error-box, .success-box {
    border-left: 4px solid;
    padding: 1rem; /* More padding */
    border-radius: 4px;
    margin-bottom: 1.5rem; /* More space below */
    font-size: 0.95rem; /* Slightly larger text */
}
.info-box {
    background: var(--info-box-bg);
    border-color: var(--info-box-border);
}
.error-box {
    background: var(--error-box-bg);
    border-color: var(--error-box-border);
    color: color-mix(in srgb, var(--error-color) 80%, black); /* Darker text for light bg */
}
.success-box {
    background: var(--success-box-bg);
    border-color: var(--success-box-border);
    color: color-mix(in srgb, var(--success-color) 70%, black); /* Darker text for light bg */
}
@media (prefers-color-scheme: dark) {
    .error-box { color: color-mix(in srgb, var(--error-color) 80%, white); } /* Lighter text for dark bg */
    .success-box { color: color-mix(in srgb, var(--success-color) 80%, white); } /* Lighter text for dark bg */
}

.error-box strong, .success-box strong, .info-box strong {
    font-weight: 600;
}

/* --- Other Styles --- */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.fade-in { animation: fadeIn 0.5s ease; }

/* Placeholder for Logo */
.logo-container { text-align: center; margin-bottom: 1rem; }
.logo { 
    max-width: 144px !important; /* Match POM-Discount-App */
    width: 144px !important;     /* Match POM-Discount-App */
    height: auto !important; 
    filter: var(--logo-filter); 
    margin: 0 auto; /* Ensure centering */
    display: block; /* Ensure centering */
}

#MainMenu, footer, header { visibility: hidden; }
.main .block-container {
    padding-top: 2rem;
    padding-left: 1rem;
    padding-right: 1rem;
    padding-bottom: 1rem;
}
/* Reduce vertical space caused by st.form */
div[data-testid="stForm"] {
    border: none;
    padding: 0;
}

/* Target checkboxes using a potentially fragile selector */
/* This aims for checkboxes within the main app area */
/* Consider adding a container div with a class if more precision is needed */
div[data-testid="stVerticalBlock"] div[data-testid="stCheckbox"] input[type="checkbox"] {
    border: 2px solid #999 !important; /* Darker gray, thicker border */
    width: 1.2em; /* Slightly larger */
    height: 1.2em;
    cursor: pointer;
    margin-top: 0.2rem; /* Add margin to align better vertically */
}
/* Adjust label alignment - Target the block containing the label */
/* This assumes the label is the first element in the horizontal block created by columns */
div[data-testid="stHorizontalBlock"] > div:first-child {
    padding-top: 0.1rem; /* Try less padding for alignment */
}

/* --- Enhance Button Styles --- */
/* General Input Style */
input {
    background: var(--input-bg-color) !important;
    color: var(--text-color) !important;
    border: 1px solid #ddd !important;
    padding: 0.75rem 1rem !important;
    border-radius: 6px !important;
    transition: all 0.3s ease !important;
}
input:focus {
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color) 20%, transparent) !important;
}

/* --- Specific style for the FORM SUBMIT button ("Next") --- */
div[data-testid="stForm"] button[data-testid="stFormSubmitButton"] {
    background-color: var(--primary-color) !important;
    color: white !important;
    font-weight: 700 !important; /* Bold */
    font-size: 1.05rem !important; /* Larger */
    padding: 0.8rem 1.5rem !important;
    width: auto !important;
    display: inline-block !important;
    border-radius: 6px !important;
    border: none !important;
    line-height: 1.5;
    transition: all 0.3s ease !important;
}
div[data-testid="stForm"] button[data-testid="stFormSubmitButton"]:hover {
    background-color: color-mix(in srgb, var(--primary-color) 85%, black) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px color-mix(in srgb, var(--primary-color) 20%, transparent) !important;
}

/* --- Style for OTHER primary buttons (like "Proceed") --- */
/* Selects buttons NOT inside a form, using stButton class */
div[data-testid="stVerticalBlock"]:not(div[data-testid="stForm"] *) .stButton>button {
     background-color: var(--primary-color) !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    padding: 0.8rem 1.5rem !important;
    width: 100% !important; /* Make Proceed full width */
    display: block !important;
    border-radius: 6px !important;
    border: none !important;
    line-height: 1.5;
    transition: all 0.3s ease !important;
}
div[data-testid="stVerticalBlock"]:not(div[data-testid="stForm"] *) .stButton>button:hover {
    background-color: color-mix(in srgb, var(--primary-color) 85%, black) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px color-mix(in srgb, var(--primary-color) 20%, transparent) !important;
}


/* --- Style for secondary buttons (like 'Back') --- */
.secondary-btn .stButton>button {
    background: transparent !important;
    color: var(--primary-color) !important;
    border: 1px solid var(--primary-color) !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.7rem 1.4rem !important;
    width: 100% !important; /* Make Back full width */
    display: block !important;
    line-height: 1.5;
    border-radius: 6px !important;
    transition: all 0.3s ease !important;
}
.secondary-btn .stButton>button:hover {
    background: color-mix(in srgb, var(--primary-color) 10%, transparent) !important;
    color: var(--primary-color) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px color-mix(in srgb, var(--primary-color) 15%, transparent) !important;
}

/* --- DIRECT SPECIFIC FIX FOR NEXT BUTTON --- */
/* More specific and direct styling for the Next button */
.stButton > button[kind="formSubmit"],
button[kind="formSubmit"],
button[data-testid="baseButton-secondary"], 
button[data-testid="stFormSubmitButton"] {
    background-color: #0073ea !important; /* Hardcoded blue color */
    color: white !important;
    font-weight: 700 !important; 
    border: none !important;
    font-size: 1.05rem !important;
    padding: 0.8rem 1.5rem !important;
}

/* Ensure this button is never overridden */
form button[type="submit"] {
    background-color: #0073ea !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
}

</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------
# Streamlit App Layout
# ----------------------------------------------------------------

# --- Title and Logo ---
logo_base64 = get_logo_base64()
if logo_base64:
    st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_base64}" alt="DxO Logo" class="logo"/></div>', unsafe_allow_html=True)
else:
    # Fallback or leave empty if logo fails to load
    st.markdown('<div class="logo-container"></div>', unsafe_allow_html=True)

st.markdown('<h1 class="main-title">Get Product Activation Codes</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Fetch activation code from Monday.com and add it as an internal note to a Zendesk Sell Deal.</p>', unsafe_allow_html=True)

# --- Progress Bar ---
progress_percent = (st.session_state["current_step"] - 1) * 50
step_labels = ["Enter Deal ID", "Select Product", "Result"]
step_indicators_html = ""
step_labels_html = ""

for i, label in enumerate(step_labels):
    step_num = i + 1
    indicator_class = ""
    label_class = ""
    # --- FIX: Progress Bar Completion Logic ---
    is_successful_completion = (
        step_num == len(step_labels) and # Is it the last step?
        st.session_state["current_step"] == step_num and # Is it the current step?
        st.session_state.get("note_written") is True # Was the overall process successful?
    )

    if is_successful_completion or st.session_state["current_step"] > step_num:
        indicator_class = "completed"
        label_class = "completed"
    elif st.session_state["current_step"] == step_num:
        indicator_class = "active"
        label_class = "active"
    # --- End FIX ---

    step_indicators_html += f'<div class="step-indicator {indicator_class}">{step_num}</div>'
    step_labels_html += f'<div class="step-label {label_class}">{label}</div>'

st.markdown(f"""
<div class="progress-container">
    <div class="step-indicators">
        {step_indicators_html}
    </div>
    <div class="progress-bar">
        <div class="progress-fill" style="width: {progress_percent}%;"></div>
    </div>
    <div class="step-labels">
        {step_labels_html}
    </div>
</div>
""", unsafe_allow_html=True)

# --- Error Display ---
if st.session_state.get("show_error") and st.session_state.current_step != 3: # Only show generic error box if not on Step 3
    st.error(st.session_state["show_error"])
    st.session_state["show_error"] = None # Clear error after showing

# --- REMOVE Success Message Display Here ---
# We will handle success display within Step 3
# if st.session_state.get("success_message"):
#     st.success(st.session_state["success_message"])
#     st.session_state["success_message"] = None

# ----------------------------------------------------------------
# App Steps Logic
# ----------------------------------------------------------------

# --- Main Processing Function ---
def process_activation_request(deal_id, group_ids, group_map, m_api_key, z_api_key):
    """
    Fetches codes and links, writes formatted Zendesk note, and attempts to update Monday status.
    Returns: (bool: overall_success, str: message)
    """
    note_messages = []
    items_found_details = [] # List to store tuples: (item_id, activation_code, product_display_name, mac_link_url, win_link_url)
    items_found_count = 0
    global_error = None
    monday_update_successes = 0
    monday_update_failures = 0
    monday_update_error_msgs = []
    monday_person_successes = 0
    monday_person_failures = 0
    monday_person_error_msgs = []
    owner_email = None
    owner_warning = None
    monday_user_id_to_assign = None
    zendesk_success = False # Initialize zendesk flag

    print(f"Processing request for Deal ID: {deal_id}, Groups: {group_ids}")

    # --- NEW: Fetch Owner Email Early ---
    print("Fetching Zendesk Deal Owner details...")
    owner_email, owner_error = get_zendesk_deal_owner_email(deal_id, z_api_key)
    if owner_error:
        return False, owner_error
    if not owner_email:
        return False, f"Could not retrieve owner email for Zendesk Deal {deal_id}."
    print(f"Proceeding with Owner Email: {owner_email}")
    # --- END NEW ---

    # --- Look up Monday User ID ---
    monday_user_id_to_assign = ZENDESK_OWNER_EMAIL_TO_MONDAY_ID.get(owner_email)
    if not monday_user_id_to_assign:
        owner_warning = f"Warning: Owner email '{owner_email}' not found in ZENDESK_OWNER_EMAIL_TO_MONDAY_ID map. Person column will not be updated."
        print(owner_warning)
    else:
        print(f"Found Monday User ID {monday_user_id_to_assign} for owner email {owner_email}")

    # 1. Find codes and links for each group
    for group_id in group_ids:
        group_title = group_map.get(group_id, f"Group ID {group_id}")
        print(f"Checking group: {group_title} ({group_id}) for display name {group_title}")

        # --- REVISED: Determine Product Display Name using Regex ---
        product_display_name = get_product_display_name(group_title)
        print(f"Checking group: {group_title} ({group_id}) for display name {product_display_name}")

        headers = {"Authorization": m_api_key, "Content-Type": "application/json", "API-Version": "2023-10"}
        
        # --- Restore Full Query using Variables ---
        query = """
        query GetGroupItems($boardId: ID!, $groupId: String!, $columnIds: [String!]!) {
          boards(ids: [$boardId]) {
            groups(ids: [$groupId]) {
              items_page(limit: 500) { # Restore limit
                items {
                  id
                  name
                  column_values(ids: $columnIds) {
                    id
                    text
                    value
                  }
                }
              }
            }
          }
        }
        """
        variables = {
            "boardId": str(BOARD_ID), 
            "groupId": group_id,
            # Use the defined constants - user needs to verify these IDs
            "columnIds": [STATUS_COLUMN_ID, MAC_LINK_COLUMN_ID, WIN_LINK_COLUMN_ID] 
        }
        # --- End Restored Query ---
        payload_dict = {"query": query, "variables": variables}
        
        # --- Remove Detailed Logging (optional, keep if needed) ---
        # print("-" * 20)
        # print(f"DEBUG: Preparing request for group_id: {group_id}")
        # print(f"DEBUG: URL: {MONDAY_API_URL}")
        # masked_key = headers.get("Authorization", "NotSet")
        # if len(masked_key) > 10:
        #      masked_key = masked_key[:5] + "..." + masked_key[-5:]
        # print(f"DEBUG: Headers: {{...}}")
        # print(f"DEBUG: Payload Dict: {payload_dict}")
        # print("-" * 20)
        # --- End Removed Logging ---

        try:
            response = requests.post(MONDAY_API_URL, headers=headers, json=payload_dict, timeout=15)
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                 raise Exception(f"Monday API Error fetching items for group {group_id}: {result['errors']}")

            # --- Restore Item Processing Logic --- 
            items = []
            if result.get("data", {}).get("boards", []) and result["data"]["boards"][0].get("groups", []):
                 group_data = result["data"]["boards"][0]["groups"][0]
                 if group_data and group_data.get("items_page"):
                      items = group_data["items_page"].get("items", [])

            found_in_group = False
            for item in reversed(items):
                item_id = item["id"]
                activation_code = item["name"]
                status_val = None
                mac_link_url, win_link_url = "N/A", "N/A"
                
                # Use try-except around column value processing for robustness
                try: 
                    for cv in item["column_values"]:
                        col_id = cv.get("id")
                        if col_id == STATUS_COLUMN_ID:
                            status_val = cv.get("text")
                        elif col_id == MAC_LINK_COLUMN_ID:
                            mac_link_url = cv.get("text") or "N/A"
                            if mac_link_url == "N/A" and cv.get("value"):
                                try:
                                    link_data = json.loads(cv["value"])
                                    mac_link_url = link_data.get("url", "N/A")
                                except (json.JSONDecodeError, TypeError): pass # Keep N/A
                        elif col_id == WIN_LINK_COLUMN_ID:
                             win_link_url = cv.get("text") or "N/A"
                             if win_link_url == "N/A" and cv.get("value"):
                                  try:
                                       link_data = json.loads(cv["value"])
                                       win_link_url = link_data.get("url", "N/A")
                                  except (json.JSONDecodeError, TypeError): pass # Keep N/A
                except Exception as e_proc: # Catch errors during column value processing
                    print(f"Warning: Error processing column values for item {item_id}: {e_proc}")
                    continue # Skip this item if columns can't be processed

                if status_val == STATUS_LABEL_NOT_USED:
                    print(f"Found 'Not used' code: {activation_code} (Item ID: {item_id}) in group {group_title}")
                    items_found_count += 1
                    items_found_details.append((item_id, activation_code, product_display_name, mac_link_url, win_link_url))
                    found_in_group = True
                    break

            if not found_in_group:
                print(f"No 'Not used' code found in group: {group_title}")
            # --- End Restored Item Processing Logic ---

        except Exception as e:
            error_message = f"Failed processing group {group_title}: {e}" # Removed (Simplified Query) note
            print(f"Error: {error_message}")
            if not global_error: global_error = f"Error during Monday.com processing: {e}" # Removed note

    # --- NEW: Sort found items based on product priority ---
    def get_sort_key(item_detail):
        product_display_name = item_detail[2] # Index 2 is product_display_name
        # Extract base name (e.g., "PhotoLab" from "PhotoLab 8", "Nik" from "Nik Collection 7")
        # Handle multi-word names like "Nik Collection"
        base_name_parts = []
        for part in product_display_name.split(' '):
            if part.isdigit():
                 break # Stop if we hit the version number
            base_name_parts.append(part)
        base_name = " ".join(base_name_parts) 
        
        # Handle potential variations (e.g., check "Nik Collection" then "Nik")
        priority = PRODUCT_ORDER_PRIORITY.get(base_name)
        if priority is None and ' ' in base_name:
             # Try first word if full name not found (e.g., for "Nik Collection")
             priority = PRODUCT_ORDER_PRIORITY.get(base_name.split(' ')[0])
        
        return priority if priority is not None else DEFAULT_PRIORITY

    if items_found_details:
        print(f"Sorting {len(items_found_details)} found items by product priority...")
        items_found_details.sort(key=get_sort_key)
        print("Items sorted.")
    # --- END NEW SORT ---

    # 2. Format note messages from found items (now sorted)
    if not items_found_details:
        # If no items were found at all across all groups searched
        print("No 'Not used' activation codes found in any selected group.")
        if global_error:
            return False, global_error # Return processing error if one occurred
        else:
            # If processing completed but no codes found, treat as error for user flow
            return False, f"No '{STATUS_LABEL_NOT_USED}' activation codes found in the selected groups for Deal ID {deal_id}."
    else:
        for item_id, code, prod_name, mac_url, win_url in items_found_details:
            note_entry = f"Product Name: {prod_name}\n"
            note_entry += f"Activation Code: {code}\n"
            note_entry += f"[MAC Download Link]({mac_url})\n" if mac_url != "N/A" else "MAC Download Link: N/A\n"
            note_entry += f"[WIN Download Link]({win_url})" if win_url != "N/A" else "WIN Download Link: N/A"
            note_messages.append(note_entry)

    # 3. Attempt to write note to Zendesk
    print("Attempting to write note to Zendesk...")
    zendesk_note_content = "Activation Codes\n\n" + "\n\n-----------\n\n".join(note_messages)

    try:
        z_client = Client(access_token=z_api_key)
        z_client.notes.create({
            "resource_type": "deal",
            "resource_id": int(deal_id),
            "content": zendesk_note_content
        })
        print(f"Successfully added note to Zendesk Deal ID {deal_id}")
        zendesk_success = True
    except Exception as e:
        zendesk_error_msg = f"Failed to write note to Zendesk Deal ID {deal_id}: {e}"
        print(f"Error: {zendesk_error_msg}")
        return False, global_error or zendesk_error_msg

    # 4. Update Monday Status AND Assign Person
    if zendesk_success:
        print(f"Zendesk note added. Attempting to update Monday.com status for {len(items_found_details)} item(s)...")
        target_status_label = "Sent & put in B2B CRM"
        # Reset counters for Monday updates for this run
        monday_update_successes = 0
        monday_update_failures = 0
        monday_update_error_msgs = []
        monday_person_successes = 0 # Reset person counters too
        monday_person_failures = 0
        monday_person_error_msgs = []

        for item_id, _, _, _, _ in items_found_details:
            # --- Update Status (Existing) ---
            print(f"Attempting to update status for item {item_id} to '{target_status_label}'...")
            update_ok, update_msg = update_monday_item_status(
                item_id,
                STATUS_COLUMN_ID,
                target_status_label,
                m_api_key
            )
            # --- Assign Person (NEW - Conditional on Status Success and Mapping) ---
            if update_ok:
                monday_update_successes += 1
                print(f"Successfully updated status for item {item_id}.")
                # --- Assign Person logic moved inside status success ---
                if monday_user_id_to_assign: # Only try if we found a mapping
                     print(f"Attempting to assign Person (User ID: {monday_user_id_to_assign}) to item {item_id}...")
                     person_ok, person_msg = update_monday_item_person(
                         item_id,
                         monday_user_id_to_assign,
                         m_api_key
                     )
                     if person_ok:
                         monday_person_successes += 1
                         print(f"Successfully assigned Person to item {item_id}.")
                     else:
                         monday_person_failures += 1
                         person_error_detail = f"Item {item_id}: {person_msg}"
                         monday_person_error_msgs.append(person_error_detail)
                         print(f"Failed to assign Person to item {item_id}: {person_msg}")
                else:
                     # If no mapping, mention it (can be logged more quietly if needed)
                     print(f"Skipping Person assignment for item {item_id} (owner email '{owner_email}' not mapped).")
                # --- End Assign Person --- 
            else:
                # Status update failed, log errors (existing logic)
                monday_update_failures += 1
                error_detail = f"Item {item_id}: {update_msg}" # Status error msg
                monday_update_error_msgs.append(error_detail)
                print(f"Failed to update status for item {item_id}: {update_msg}")
                # Don't attempt to assign person if status update failed

        # --- Construct Final Message (Modified) ---
        success_parts = []
        failure_parts = []
        final_overall_success = True # Assume success unless status update fails

        success_parts.append(f"Added note to Zendesk Deal {deal_id}")

        if monday_update_failures == 0:
             success_parts.append(f"updated status for {monday_update_successes} item(s) on Monday.com")
        else:
             failure_parts.append(f"failed to update status for {monday_update_failures}/{len(items_found_details)} item(s)")
             if monday_update_error_msgs: failure_parts.append(f"(Status Errors: {'; '.join(monday_update_error_msgs)})" )
             final_overall_success = False # Status update failure makes overall process fail

        # Check person assignment outcome only if mapping existed
        if monday_user_id_to_assign:
            if monday_person_failures == 0:
                 # Only report success if we actually assigned (person_successes > 0 implies items_found_details > 0)
                 if monday_person_successes > 0:
                     success_parts.append(f"assigned owner for {monday_person_successes} item(s)")
            else:
                 failure_parts.append(f"failed to assign owner for {monday_person_failures}/{len(items_found_details)} item(s)")
                 if monday_person_error_msgs: failure_parts.append(f"(Owner Assign Errors: {'; '.join(monday_person_error_msgs)})" )
                 # Optional: Decide if person failure makes overall process fail. Let's say no for now.
                 # final_overall_success = False 
        elif owner_warning: # Add the warning if no mapping existed
             # Append warning to failure parts for visibility, but don't mark process as failed
             failure_parts.append("(Owner not assigned: owner email not mapped)") 


        # Build final message string
        final_message = "Process Summary: " # Add a prefix
        final_message += " & ".join(success_parts) + "." # Use '&' for brevity
        if failure_parts:
             final_message += " However, " + " and ".join(failure_parts).strip() + "."

        print(f"Final Outcome: Success={final_overall_success}, Message={final_message}")
        return final_overall_success, final_message
        # --- End Modified Final Message ---

    return False, global_error or zendesk_error_msg or "An unknown error occurred before Monday update attempt."

# --- Step 1: Enter Deal ID ---
if st.session_state["current_step"] == 1:
    with st.form(key="deal_id_form"):
        deal_id_input = st.text_input(
            "Zendesk Sell Deal ID",
            key="deal_id_input_key",
            placeholder=None,
            help="The unique identifier for the deal in Zendesk Sell."
        )
        st.markdown("<i>Please input the deal ID for which you need activation codes.</i>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Next")

        if submitted:
            deal_id = deal_id_input.strip()
            if not deal_id.isdigit():
                st.session_state["show_error"] = "Please enter a valid numeric Deal ID."
                st.rerun()
            else:
                st.session_state["deal_id"] = deal_id
                with st.spinner("Fetching groups from Monday.com..."):
                    fetched_groups, error_msg = fetch_monday_data(
                        deal_id,
                        BOARD_ID,
                        MONDAY_API_URL,
                        monday_api_key
                    )
                if error_msg and fetched_groups is None:
                    st.session_state["show_error"] = error_msg
                    st.session_state["all_groups"] = []
                    st.rerun()
                else:
                    st.session_state["all_groups"] = fetched_groups if fetched_groups is not None else []
                    st.session_state["selected_groups"] = [] # Start with empty selection now
                    st.session_state["current_step"] = 2
                    st.session_state["show_error"] = error_msg 
                    st.rerun()


# --- Step 2: Select Product ---
elif st.session_state["current_step"] == 2:
    deal_id = st.session_state.get("deal_id", "N/A")
    all_groups = st.session_state.get("all_groups", [])
    # Ensure selected_titles is initialized correctly
    selected_titles = st.session_state.get("selected_groups", [])

    st.markdown(f'<div class="info-box">Select the products for Deal ID <strong>{deal_id}</strong>.</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("Available Products:")
    st.markdown("Please select the product(s) you need:")

    if not all_groups:
        st.warning("No product groups were found on the Monday.com board.")
    else:
        # Need to reconstruct selected_titles based on current checkbox state before rendering buttons
        current_selection = []
        for group in all_groups:
            group_id = group["id"]
            group_title = group["title"]
            checkbox_key = f"group_checkbox_{group_id}"
            mapped_name = get_product_display_name(group_title)
            if mapped_name != group_title:
                display_label = f"{group_title} ({mapped_name})"
            else:
                display_label = group_title
            col1, col2 = st.columns([10, 1])
            with col1:
                st.markdown(f'{display_label}', unsafe_allow_html=True) 
            with col2:
                 is_checked = st.checkbox(
                     label="\u00A0", 
                     value=st.session_state.get(checkbox_key, False), # Read state if exists, default False
                     key=checkbox_key,
                     label_visibility='collapsed'
                 )
            if is_checked:
                current_selection.append(group_title)
        # Update session state based on current UI state
        st.session_state.selected_groups = current_selection
        # Now use the updated state for button logic
        selected_titles = st.session_state.selected_groups 
            
        st.markdown(" ")
        st.markdown(f"**Selected {len(selected_titles)} out of {len(all_groups)} products.**")
        st.markdown("---")

    # --- Render Buttons with Disabled State ---
    proceed_disabled_logic = len(selected_titles) == 0 or st.session_state.processing
    back_disabled_logic = st.session_state.processing

    if st.button("Proceed with Selected Products", disabled=proceed_disabled_logic):
        # --- Set processing flag and rerun to disable buttons --- 
        st.session_state.processing = True
        # Store current selections needed for processing *before* rerun
        st.session_state._current_selection_ids = [g["id"] for g in all_groups if g["title"] in selected_titles]
        st.session_state._current_selection_map = {g["id"]: g["title"] for g in all_groups if g["title"] in selected_titles}
        st.rerun() # Rerun immediately to show disabled buttons and spinner

    # --- Processing logic runs AFTER the rerun if processing was set --- 
    if st.session_state.processing:
        # Use selections stored before the rerun
        selected_group_ids = st.session_state.get("_current_selection_ids", [])
        selected_group_map = st.session_state.get("_current_selection_map", {})
        current_deal_id = st.session_state.deal_id # Already in state

        # Clean up temporary state variables
        if "_current_selection_ids" in st.session_state: del st.session_state._current_selection_ids
        if "_current_selection_map" in st.session_state: del st.session_state._current_selection_map
        
        # --- Update Spinner Text ---
        with st.spinner("Please wait a few seconds... Finding codes and updating CRM..."):
        # --- End Update Spinner Text ---
            final_success, message = process_activation_request(
                current_deal_id,
                selected_group_ids,
                selected_group_map,
                monday_api_key,
                zendesk_api_key
            )

        # Process result and transition
        st.session_state["note_written"] = final_success
        if final_success:
            st.session_state["success_message"] = message
            st.session_state["show_error"] = None
            st.session_state.processing = False # Reset before moving step
            st.session_state.current_step = 3
        else:
            st.session_state["success_message"] = None
            st.session_state["show_error"] = message
            st.session_state.processing = False # Reset on error

        # Clean up checkbox states (can stay here or move fully to reset_app)
        # for group in all_groups: # Maybe not needed here if state clears on step change
        #     checkbox_key = f"group_checkbox_{group['id']}"
        #     if checkbox_key in st.session_state:
        #         del st.session_state[checkbox_key]
        st.rerun() # Rerun to show Step 3 or error on Step 2

    # Render Back button
    st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
    if st.button("Back (Enter Different ID)", disabled=back_disabled_logic):
        st.session_state.processing = False # Ensure reset if going back
        reset_app() # reset_app should clean checkbox keys if needed
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# --- Step 3: Result ---
elif st.session_state["current_step"] == 3:
    # --- FIX: Structured Success Display ---
    if st.session_state.get("note_written") is True:
        st.balloons() # Add some celebration!
        st.markdown("### Success!")
        st.markdown("Please refresh your Zendesk deal page to see the activation code(s) in the internal notes.")
        # Display the detailed message from the processing function
        if st.session_state.get("success_message"):
             # Use the existing success box styling
             st.markdown(f'<div class="success-box">{st.session_state["success_message"]}</div>', unsafe_allow_html=True)
             st.session_state["success_message"] = None # Clear after showing

    elif st.session_state.get("show_error"): # Check if error occurred instead
         st.error(st.session_state["show_error"]) # Display error if process failed (using st.error)
         st.session_state["show_error"] = None
    else:
         # Fallback if state is somehow step 3 without success/error message
         st.warning("Processing complete, but final status unclear. Please check Zendesk and Monday.")
    # --- End FIX ---

    # Start Over button remains
    if st.button("Start Over"):
        # Clear note_written state when starting over from result page
        if 'note_written' in st.session_state: del st.session_state['note_written']
        reset_app()
        st.rerun()

# --- Fallback for invalid state ---
else:
    st.error("An unexpected error occurred in the application flow. Please start over.")
    if st.button("Start Over"):
        reset_app()
        st.rerun()
