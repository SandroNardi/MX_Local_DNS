import os
import meraki
import json
import requests
from my_logging import setup_logger # Import setup_logger from your logging module

# Initialize logger at the module level, enabling console output.
logger = setup_logger(enable_logging=True, console_logging=True,file_logging=True)

# Attempt to fetch API key from environment variables.
API_KEY = os.getenv("MK_CSM_KEY")
if not API_KEY:
    logger.error("Meraki API Key (MK_CSM_KEY) not found in environment variables.")
    # If the API key is critical for initial setup, the application might fail later.

# Define standard HTTP headers for Meraki API requests.
HEADERS = {
    "Authorization": f"Bearer {API_KEY}", # Use f-string for dynamic API_KEY.
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Singleton-style global variable for the Meraki Dashboard API instance.
_dashboard = None

# Caches for frequently accessed Meraki data to reduce API calls.
_organizations_cache = None
_networks_cache = {}

# Global variables to store the currently selected organization details.
API_KEY = None # Re-declared, will be set by set_api_key.
ORGANIZATION_ID = None
ORGANIZATION_NAME = None

def are_required_params_set():
    """
    Checks if the essential parameters (API_KEY, ORGANIZATION_ID) are set.
    Returns a boolean and a list of missing parameters.
    """
    missing_params = []
    if not API_KEY:
        missing_params.append("API_KEY")
    if not ORGANIZATION_ID:
        missing_params.append("ORGANIZATION_ID")
    if missing_params:
        logger.error(f"Missing required parameters: {', '.join(missing_params)}")
        return False, missing_params
    return True, []

def set_api_key(api_key=None):
    """
    Sets the global API_KEY. Prioritizes the passed argument, then environment variable.
    Logs activity but avoids logging the key itself for security.
    """
    global API_KEY

    if api_key:
        API_KEY = api_key
        logger.info("API key set from external parameter.")
    else:
        env_api_key = os.getenv("MK_CSM_KEY")
        if env_api_key:
            API_KEY = env_api_key
            logger.info("API key loaded from environment variable.")
        else:
            API_KEY = None
            logger.error("Meraki API Key (MK_CSM_KEY) not found in environment variables or passed parameter.")
    if API_KEY:
        HEADERS.update({
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        logger.debug("Global HEADERS dictionary updated with new API key.")

def is_api_not_null():
    """
    Checks if the global API_KEY is set (not None or empty).
    """
    return API_KEY is not None and API_KEY != ""

def set_organization_id(org_id):
    """
    Sets the global ORGANIZATION_ID.
    """
    global ORGANIZATION_ID
    ORGANIZATION_ID = org_id
    logger.info(f"Organization ID set to: {ORGANIZATION_ID}")


def get_organization_id():
    """
    Retrieves the currently selected global ORGANIZATION_ID.
    """
    global ORGANIZATION_ID
    logger.debug(f"Retrieving current organization ID: {ORGANIZATION_ID}")
    return ORGANIZATION_ID

def set_organization_name(org_name):
    """
    Sets the global ORGANIZATION_NAME.
    """
    global ORGANIZATION_NAME
    ORGANIZATION_NAME = org_name
    logger.info(f"Organization name set to: {ORGANIZATION_NAME}")


def get_organization_name():
    """
    Retrieves the currently selected global ORGANIZATION_NAME.
    """
    global ORGANIZATION_NAME
    logger.debug(f"Retrieving current organization name: {ORGANIZATION_NAME}")
    return ORGANIZATION_NAME


def _get_dashboard():
    """
    Initializes or returns the singleton instance of the Meraki Dashboard API client.
    Suppresses Meraki's internal logging to use the application's logger.
    """
    global _dashboard
    if _dashboard is None:
        logger.info("Initializing Meraki Dashboard API instance.")
        try:
            _dashboard = meraki.DashboardAPI(API_KEY, suppress_logging=True)
            logger.debug("Meraki Dashboard API instance created successfully.")
        except Exception as e:
            logger.exception(f"Failed to initialize Meraki Dashboard API: {e}")
            raise # Re-raise to indicate a critical setup failure
    else:
        logger.debug("Using existing Meraki Dashboard API instance.")
    return _dashboard


def _get_organizations():
    """
    Fetches the list of organizations from the Meraki API or serves from cache.
    Handles Meraki API errors and other exceptions.
    """
    global _organizations_cache
    if _organizations_cache is None:
        logger.info("Organizations cache is empty. Fetching organizations from the Meraki API...")
        dashboard = _get_dashboard()
        try:
            _organizations_cache = dashboard.organizations.getOrganizations()
            logger.info(f"Successfully fetched {len(_organizations_cache)} organizations.")
        except meraki.APIError as e:
            logger.error(f"Meraki API error fetching organizations: {e.status} - {e.message}")
            _organizations_cache = []  # Ensure cache is a list even on error.
            return {"error": "MerakiAPIError", "details": e.message, "status_code": e.status}
        except Exception as e:
            logger.exception(f"An unexpected error occurred while fetching organizations: {e}")
            _organizations_cache = []
            return {"error": "UnexpectedError", "details": str(e)}
    else:
        logger.info("Using cached organizations data.")
    return _organizations_cache


def _get_networks():
    """
    Fetches the list of networks for the current ORGANIZATION_ID from Meraki API or cache.
    Requires ORGANIZATION_ID to be set. Handles API and other errors.
    """
    if not ORGANIZATION_ID:
        logger.warning("Attempted to get networks without a selected organization ID.")
        return {"error": "NoOrganizationSelected", "details": "Please select an organization first."}

    global _networks_cache
    if ORGANIZATION_ID not in _networks_cache:
        logger.info(
            f"Networks cache for organization {ORGANIZATION_ID} is empty. Fetching networks from the Meraki API..."
        )
        dashboard = _get_dashboard()
        try:
            _networks_cache[ORGANIZATION_ID] = (
                dashboard.organizations.getOrganizationNetworks(
                    ORGANIZATION_ID
                )
            )
            logger.info(f"Successfully fetched {len(_networks_cache[ORGANIZATION_ID])} networks for organization {ORGANIZATION_ID}.")
        except meraki.APIError as e:
            logger.error(f"Meraki API error fetching networks for organization {ORGANIZATION_ID}: {e.status} - {e.message}")
            _networks_cache[ORGANIZATION_ID] = []
            return {"error": "MerakiAPIError", "details": e.message, "status_code": e.status}
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred while fetching networks for organization {ORGANIZATION_ID}: {e}"
            )
            _networks_cache[ORGANIZATION_ID] = []
            return {"error": "UnexpectedError", "details": str(e)}
    else:
        logger.info(
            f"Using cached networks data for organization {ORGANIZATION_ID}."
        )
    return _networks_cache[ORGANIZATION_ID]


def make_request(method, endpoint, payload=None):
    """
    Generic utility function to make HTTP requests to the Meraki Local DNS API.
    Constructs the URL, sets headers, sends payload, and handles various HTTP/request errors.
    """
    if not ORGANIZATION_ID:
        logger.warning(f"Attempted to make API request '{method} {endpoint}' without a selected organization ID.")
        return {"error": "NoOrganizationSelected", "details": "Please select an organization first."}

    # Construct the full API URL for local DNS operations.
    url = f"https://api.meraki.com/api/v1/organizations/{ORGANIZATION_ID}/appliance/dns/local/{endpoint}"
    try:
        logger.info(f"Making {method} request to {url}")
        if payload:
            logger.debug(f"Request Payload: {json.dumps(payload, indent=2)}")

        # Execute the HTTP request using the requests library.
        response = requests.request(
            method, url, headers=HEADERS, data=json.dumps(payload) if payload else None
        )
        response.raise_for_status()  # Raise an exception for 4xx or 5xx HTTP status codes.

        # Parse and return JSON response, or None if no content.
        if response.text.strip():
            response_json = response.json()
            logger.debug(f"API Response ({response.status_code}): {json.dumps(response_json, indent=2)}")
            return response_json
        else:
            logger.info(f"API Response ({response.status_code}): No content")
            return None

    except requests.exceptions.HTTPError as http_err:
        # Handle specific HTTP errors (e.g., 404 Not Found, 500 Internal Server Error).
        status_code = http_err.response.status_code if http_err.response else 'Unknown'
        response_text = http_err.response.text if http_err.response else 'No response text'
        logger.error(
            f"HTTP error occurred during {method} {url}: {http_err}. "
            f"Status Code: {status_code}, Response: {response_text}"
        )
        return {
            "error": "HTTPError",
            "details": response_text,
            "status_code": status_code,
        }

    except requests.exceptions.ConnectionError as conn_err:
        # Handle network-related errors (e.g., DNS failure, refused connection).
        logger.error(f"Connection error occurred during {method} {url}: {conn_err}")
        return {"error": "ConnectionError", "details": str(conn_err)}

    except requests.exceptions.Timeout as timeout_err:
        # Handle request timeouts.
        logger.error(f"Timeout error occurred during {method} {url}: {timeout_err}")
        return {"error": "TimeoutError", "details": str(timeout_err)}

    except requests.exceptions.RequestException as req_err:
        # Handle any other general requests library exception.
        logger.exception(f"A general request error occurred during {method} {url}: {req_err}")
        return {"error": "RequestException", "details": str(req_err)}
    except Exception as e:
        # Catch any unexpected errors.
        logger.exception(f"An unexpected error occurred in make_request for {method} {url}: {e}")
        return {"error": "UnexpectedError", "details": str(e)}


def get_organizations():
    """
    Fetches and formats a list of Meraki organizations for display.
    Uses the cached Meraki Dashboard API client.
    """
    logger.info("Attempting to get organizations.")
    response = _get_organizations()

    if isinstance(response, dict) and "error" in response:
        logger.error(f"Error getting organizations: {response.get('details')}")
        return response # Return the error dictionary directly.
    
    if response:
        # Format the raw organization data into a structured table format.
        table_data = [
            {
                "ID": org.get("id"),
                "Name": org.get("name"),
                "URL": org.get("url"),
                "API Enabled": org.get("api", {}).get("enabled", False),
                "Licensing Model": org.get("licensing", {}).get("model"),
            }
            for org in response
        ]
        logger.info(f"Successfully formatted {len(table_data)} organizations for display.")
        return table_data
    else:
        logger.info("No organizations found or response was empty.")
        return []


def list_networks():
    """
    Fetches and formats a list of networks for the current organization for display.
    Uses the cached Meraki Dashboard API client.
    """
    logger.info(f"Attempting to list networks for organization ID: {ORGANIZATION_ID}")
    response = _get_networks()

    if isinstance(response, dict) and "error" in response:
        logger.error(f"Error getting networks: {response.get('details')}")
        return response # Return the error dictionary directly.

    if response:
        # Format the raw network data into a structured table format.
        table_data = [
            {
                "ID": network.get("id"),
                "Name": network.get("name"),
                "Type": network.get("type"),
                "Time Zone": network.get("timeZone"),
                "Tags": ", ".join(network.get("tags", [])), # Join tags into a single string.
            }
            for network in response
        ]
        logger.info(f"Successfully formatted {len(table_data)} networks for display.")
        return table_data
    else:
        logger.info("No networks found or response was empty for the selected organization.")
        return []


def list_profiles():
    """
    Fetches all local DNS profiles and enriches them with associated network information.
    Combines data from profiles, network assignments, and network lists.
    """
    logger.info("Attempting to list profiles with associated networks.")
    try:
        # Fetch raw profiles using the generic API request function.
        profiles_response = make_request("GET", "profiles")
        if isinstance(profiles_response, dict) and "error" in profiles_response:
            logger.error(f"Error fetching profiles: {profiles_response.get('details')}")
            return profiles_response

        if not profiles_response or "items" not in profiles_response:
            logger.info("No profiles found.")
            return []
        
        profiles_data = profiles_response["items"]
        logger.debug(f"Fetched {len(profiles_data)} raw profiles.")

        # Fetch network assignments to link profiles to networks.
        assignments = list_network_assignments()
        if isinstance(assignments, dict) and "error" in assignments:
            logger.error(f"Error fetching network assignments for profiles: {assignments.get('details')}")
            return assignments # Propagate the error.

        if not assignments:
            logger.info("No network assignments found for profiles.")
            assignments = []

        # Fetch all networks to get network names by ID.
        networks = list_networks()
        if isinstance(networks, dict) and "error" in networks:
            logger.error(f"Error fetching networks for profiles: {networks.get('details')}")
            return networks
        
        network_map = (
            {network["ID"]: network["Name"] for network in networks} if networks else {}
        )
        logger.debug(f"Created network map with {len(network_map)} entries.")

        # Create a mapping from profile ID to its assigned network details.
        profile_to_network = {}
        for assignment in assignments:
            profile_id = assignment.get("Profile ID")
            network_id = assignment.get("Network ID")
            if profile_id and network_id:
                profile_to_network[profile_id] = {
                    "Network ID": network_id,
                    "Network Name": network_map.get(network_id, "[unknown]"), # Use "[unknown]" if network name not found.
                }
        logger.debug(f"Mapped {len(profile_to_network)} profiles to networks.")

        # Format the profiles data for display, including network assignment status.
        table_data = []
        for profile in profiles_data:
            profile_id = profile.get("profileId")
            profile_name = profile.get("name")

            if profile_id in profile_to_network:
                network_info = profile_to_network[profile_id]
                table_data.append(
                    {
                        "Profile ID": profile_id,
                        "Name": profile_name,
                        "Network ID": network_info.get("Network ID"),
                        "Network Name": network_info.get("Network Name"),
                    }
                )
            else:
                table_data.append(
                    {
                        "Profile ID": profile_id,
                        "Name": profile_name,
                        "Network ID": "[unassigned]",
                        "Network Name": "[unassigned]",
                    }
                )
        logger.info(f"Successfully formatted {len(table_data)} profiles for display.")
        return table_data
    except Exception as e:
        logger.exception(f"An unexpected error occurred in list_profiles: {e}")
        return {"error": "UnexpectedError", "details": str(e)}


def create_profile(profile_name):
    """
    Creates a new local DNS profile with the given name.
    """
    logger.info(f"Attempting to create profile with name: '{profile_name}'")
    payload = {"name": profile_name}
    response = make_request("POST", "profiles", payload)
    
    if isinstance(response, dict) and "error" in response:
        logger.error(f"Failed to create profile '{profile_name}': {response.get('details')}")
        return response
    else:
        profile_id = response.get("profileId")
        name = response.get("name")
        logger.info(f"Profile '{name}' (ID: {profile_id}) created successfully.")
        return { # Return structured success response.
            "Profile ID": profile_id,
            "Name": name,
        }


def delete_profile(profile_id):
    """
    Deletes a local DNS profile by its ID.
    """
    logger.info(f"Attempting to delete profile with ID: '{profile_id}'")
    response = make_request("DELETE", f"profiles/{profile_id}")
    
    if isinstance(response, dict) and "error" in response:
        logger.error(f"Failed to delete profile '{profile_id}': {response.get('details')}")
    else:
        logger.info(f"Profile '{profile_id}' deleted successfully.")
    return response


def create_dns_record(profile_id, hostname, address):
    """
    Creates a new local DNS record (hostname to IP address) associated with a specific profile.
    """
    logger.info(f"Attempting to create DNS record: Hostname='{hostname}', Address='{address}', Profile ID='{profile_id}'")
    payload = {
        "hostname": hostname,
        "address": address,
        "profile": {"id": profile_id},
    }
    response = make_request("POST", "records", payload)
    
    if isinstance(response, dict) and "error" in response:
        logger.error(f"Failed to create DNS record '{hostname}' for profile '{profile_id}': {response.get('details')}")
    else:
        record_id = response.get("recordId")
        logger.info(f"DNS record '{hostname}' (ID: {record_id}) created successfully for profile '{profile_id}'.")
    return response


def list_dns_records():
    """
    Fetches and formats a list of all local DNS records for the current organization.
    """
    logger.info("Attempting to list DNS records.")
    response = make_request("GET", "records")
    
    if isinstance(response, dict) and "error" in response:
        logger.error(f"Error fetching DNS records: {response.get('details')}")
        return response

    if response and "items" in response:
        # Format the raw DNS record data into a structured table format.
        table_data = [
            {
                "Record ID": record.get("recordId"),
                "Hostname": record.get("hostname"),
                "Address": record.get("address"),
                "Profile ID": record.get("profile", {}).get("id"),
            }
            for record in response["items"]
        ]
        logger.info(f"Successfully formatted {len(table_data)} DNS records for display.")
        return table_data
    logger.info("No DNS records found or response was empty.")
    return []


def delete_dns_record(record_id):
    """
    Deletes a local DNS record by its ID.
    """
    logger.info(f"Attempting to delete DNS record with ID: '{record_id}'")
    response = make_request("DELETE", f"records/{record_id}")
    
    if isinstance(response, dict) and "error" in response:
        logger.error(f"Failed to delete DNS record '{record_id}': {response.get('details')}")
    else:
        logger.info(f"DNS record '{record_id}' deleted successfully.")
    return response


def assign_profile_to_network(network_id, profile_id):
    """
    Assigns a local DNS profile to a specific network.
    """
    logger.info(f"Attempting to assign profile '{profile_id}' to network '{network_id}'.")
    payload = {
        "items": [
            {"network": {"id": network_id}, "profile": {"id": profile_id}},
        ]
    }
    response = make_request("POST", "profiles/assignments/bulkCreate", payload)
    
    if isinstance(response, dict) and "error" in response:
        logger.error(f"Failed to assign profile '{profile_id}' to network '{network_id}': {response.get('details')}")
    else:
        logger.info(f"Profile '{profile_id}' successfully assigned to network '{network_id}'.")
    return response


def list_network_assignments():
    """
    Fetches all network assignments and enriches them with network and profile names.
    Combines data from assignments, networks, and profiles lists.
    """
    logger.info("Attempting to list network assignments.")
    try:
        # Fetch networks to get their names.
        networks_response = _get_networks()
        if isinstance(networks_response, dict) and "error" in networks_response:
            logger.error(f"Error fetching networks for assignments: {networks_response.get('details')}")
            return networks_response
        
        network_map = {network["id"]: network["name"] for network in networks_response}
        logger.debug(f"Created network map with {len(network_map)} entries for assignments.")

        # Fetch profiles to get their names.
        profiles_response = make_request("GET", "profiles")
        if isinstance(profiles_response, dict) and "error" in profiles_response:
            logger.error(f"Error fetching profiles for assignments: {profiles_response.get('details')}")
            return profiles_response

        profiles = profiles_response.get("items", []) if profiles_response else []
        profile_map = {profile["profileId"]: profile["name"] for profile in profiles}
        logger.debug(f"Created profile map with {len(profile_map)} entries for assignments.")

        # Fetch the raw assignments.
        assignments_response = make_request("GET", "profiles/assignments")
        if isinstance(assignments_response, dict) and "error" in assignments_response:
            logger.error(f"Error fetching raw assignments: {assignments_response.get('details')}")
            return assignments_response

        if assignments_response and "items" in assignments_response:
            table_data = []
            for assignment in assignments_response["items"]:
                network_id = assignment.get("network", {}).get("id")
                profile_id = assignment.get("profile", {}).get("id")

                # Format assignment data, including resolved network and profile names.
                table_data.append(
                    {
                        "Assignment ID": assignment.get("assignmentId"),
                        "Network ID": network_id,
                        "Network Name": network_map.get(network_id, "[unknown]"),
                        "Profile ID": profile_id,
                        "Profile Name": profile_map.get(profile_id, "[unknown]"),
                    }
                )
            logger.info(f"Successfully formatted {len(table_data)} network assignments for display.")
            return table_data
        logger.info("No network assignments found or response was empty.")
        return []
    except Exception as e:
        logger.exception(f"An unexpected error occurred in list_network_assignments: {e}")
        return {"error": "UnexpectedError", "details": str(e)}


def remove_network_assignment(assignment_id):
    """
    Removes a network assignment by its assignment ID.
    """
    logger.info(f"Attempting to remove network assignment with ID: '{assignment_id}'")
    payload = {"items": [{"assignmentId": assignment_id}]}
    response = make_request("POST", "profiles/assignments/bulkDelete", payload)
    
    if isinstance(response, dict) and "error" in response:
        logger.error(f"Failed to remove network assignment '{assignment_id}': {response.get('details')}")
    else:
        logger.info(f"Network assignment '{assignment_id}' removed successfully.")
    return response

def get_current_params():
    """
    Returns a dictionary of current application parameters, including a masked API key.
    Useful for displaying current configuration in the UI.
    """
    # Mask the API key for security when displaying.
    api_key = API_KEY
    masked_api_key = "*" * max(len(api_key) - 4, 0) + api_key[-4:] if api_key else "N/A"

    # Get organization ID and name from the module's stored variables.
    org_id = get_organization_id() or "N/A"
    org_name = get_organization_name() or "N/A"

    params = {
        "API Key": masked_api_key,
        "Organization ID": org_id,
        "Organization Name": org_name,
    }
    return params


def main():
    """
    Placeholder for the main function of this module if run independently.
    Currently logs start and finish messages.
    """
    logger.info("Main function of local_dns_logic.py started.")
    logger.info("Main function of local_dns_logic.py finished.")


if __name__ == "__main__":
    """
    Entry point for the script when executed directly.
    """
    logger.info("local_dns_logic.py script executed directly.")
    main()