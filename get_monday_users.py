import requests
import json
import configparser
import os

CONFIG_FILE = "parameters.config"
MONDAY_API_URL = "https://api.monday.com/v2"

def load_config():
    """Load configuration from parameters.config."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Configuration file '{CONFIG_FILE}' not found.")
        exit()
    config.read(CONFIG_FILE)
    return config

def get_monday_users(api_key):
    """Fetches all active users from Monday.com account."""
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
        "API-Version": "2023-10"
    }
    # Query to get users, requesting id and name
    query = """
    query {
      users (kind: all) {
        id
        name
        email # Added email for potential cross-referencing
        is_guest
        is_pending
        is_view_only
      }
    }
    """
    payload = json.dumps({"query": query})

    try:
        print("Fetching users from Monday.com...")
        response = requests.post(MONDAY_API_URL, headers=headers, data=payload, timeout=20)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            print(f"Monday API Error fetching users: {result['errors']}")
            return None

        if result.get("data") and result["data"].get("users"):
            return result["data"]["users"]
        else:
            print("No users found or unexpected response structure.")
            print(f"Full Response: {result}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Network or HTTP error connecting to Monday API: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from Monday API.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == "__main__":
    config = load_config()
    try:
        monday_api_key = config.get("monday", "api_key").strip().strip('"')
        if not monday_api_key:
            print("Error: Monday.com API key missing/empty in parameters.config")
            exit()
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        print(f"Error: Could not find required section or key in parameters.config: {e}")
        exit()

    users = get_monday_users(monday_api_key)

    if users:
        print("\n--- Monday.com Users ---")
        # Filter out pending/guest/view-only users if desired, focus on active members
        active_users = [
            user for user in users
            if not user.get('is_guest') and not user.get('is_pending') and not user.get('is_view_only')
        ]

        if not active_users:
             print("No active, non-guest, non-pending, non-view-only users found.")
             print("Showing all fetched users instead:")
             active_users = users # Show all if filtering yields none

        for user in active_users:
            user_id = user.get('id')
            user_name = user.get('name')
            user_email = user.get('email', 'N/A')
            print(f"Name: {user_name:<30} | ID: {user_id:<15} | Email: {user_email}")
        print("------------------------")
        print("\nUse these IDs to build your ZENDESK_OWNER_TO_MONDAY_USER mapping dictionary.")
    else:
        print("Failed to retrieve user list.") 