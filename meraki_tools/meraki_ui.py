# type: ignore

from pywebio.output import put_html, put_buttons, put_scope, use_scope, put_markdown, put_collapse, put_scrollable, toast, popup
from pywebio.session import download, run_js # Import PyWebIO session functions for download and JavaScript execution.
import threading # For managing background threads.
import time # For time-related operations, like sleep.
import io # For in-memory text streams (used for CSV generation).
import csv # For CSV file operations.
import os # For interacting with the operating system, like file paths.
from my_logging import setup_logger, log_entries # Custom logging setup and log entry storage.
import about # Module containing application information.
from pywebio.input import input_group, select, input as pywebio_input
import meraki_api_utils
from typing import Dict, List,Any, Optional, cast # Import necessary types from typing module
from meraki_api_utils import MerakiAPIWrapper 

# Initialize logger for the module, enabling console output.
logger = setup_logger(enable_logging=True, console_logging=True, file_logging=True)

# --- Global variables for log display management ---
last_displayed_log_index = 0 # Tracks the index of the last log entry displayed in the UI.
log_entries_lock = threading.Lock() # A lock to ensure thread-safe access to log_entries.

# Configuration for navigation buttons in the header.
nav_buttons: List[Dict[str, Any]] = [
    {"label": "Current Param", "value": "current_param"},
    {"label": "App Restart", "value": "app_restart"},
    {"label": "About", "value": "about"},
]

def get_css_style():
    """
    Reads and returns the content of the 'style.css' file.
    Used to apply custom CSS to the PyWebIO application.
    """
    logger.info("Attempting to get CSS style from styles.css.")
    # Construct the absolute path to style.css.
    css_file_path = os.path.join(os.path.dirname(__file__), 'style.css')
    try:
        with open(css_file_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
            logger.debug(f"Successfully read styles.css from {css_file_path}.")
            return css_content
    except FileNotFoundError:
        error_msg = f"Error: styles.css not found at {css_file_path}"
        logger.error(error_msg)
        return ""
    except Exception as e:
        logger.exception(f"An unexpected error occurred while reading styles.css: {e}")
        return ""

def app_setup(app_scope_name: str, required_app_setup_param: Dict[str, Any], app_setup_param: Optional[Dict[str, Any]] = None, enable_caching: Optional[bool]=True) -> Optional[MerakiAPIWrapper]:
    """
    Main setup function for the application.
    Initializes and configures the MerakiAPIWrapper instance.
    Returns the configured MerakiAPIWrapper instance if setup is successful, None otherwise.
    """
    logger.info("Entering app_setup function.")

    try:
        _enable_caching_val: bool = enable_caching if enable_caching is not None else False

        # 1. Instantiate the MerakiAPIWrapper
        # Pass initial API key from app_setup_param and caching preference to the constructor.
        initial_api_key_from_param = app_setup_param.get("api_key") if app_setup_param else None
        api_wrapper = MerakiAPIWrapper(
            initial_api_key=initial_api_key_from_param,
            enable_caching=_enable_caching_val
        )

        # 2. Use the setup_application_parameters method on the instance to apply initial config.
        # This handles environment variables and app_setup_param for all required fields
        # and updates the internal state of api_wrapper.
        initial_setup_success = api_wrapper.setup_application_parameters(
            required_app_setup_param,
            app_setup_param=app_setup_param,
            enable_caching=_enable_caching_val # Pass to ensure consistency
        )

        if not initial_setup_success:
            logger.error("Initial application parameter setup failed.")
            toast("Initial application parameter setup failed. Please check your configuration.", color="error", duration=0)
            return None

        # Now handle interactive prompts if parameters are still missing after initial setup
        with use_scope(app_scope_name, clear=True):
            # Step 1: Secure a valid API Key if required and not already set
            if required_app_setup_param.get("api_key") and not api_wrapper.is_api_key_set():
                logger.info("API Key required and not set. Prompting user.")
                # Pass the api_wrapper instance to the helper function
                api_key_from_user = get_valid_api_key(api_wrapper, initial_api_key=api_wrapper._api_key) # Use _api_key for its current value
                if api_key_from_user is None: # User cancelled or invalid key
                    return None

            # Step 2: Retrieve and Select Organization if required and not already set
            organizations = None
            if required_app_setup_param.get("organization_id") and not api_wrapper.is_organization_id_set():
                logger.info("Organization ID required and not set. Retrieving organizations.")
                # Pass the api_wrapper instance to the helper function
                organizations = retrieve_organizations(api_wrapper)
                if organizations is None:
                    return None

                organization_id_param = app_setup_param.get("organization_id") if app_setup_param else None
                selected_organization_id, _ = select_organization(
                    api_wrapper,
                    organization_id_param,
                    organizations,
                )
                if selected_organization_id is None:
                    return None
            elif required_app_setup_param.get("organization_id") and api_wrapper.is_organization_id_set():
                # If org is already set, we might still need to retrieve organizations for later UI elements
                # or to confirm the pre-selected one is valid.
                logger.info(f"Organization ID already set: {api_wrapper.get_organization_id()}.")
                organizations = retrieve_organizations(api_wrapper) # Refresh org list
                if organizations is None:
                    return None


            # Step 3: Retrieve and Select Network if required and not already set
            networks = None
            if required_app_setup_param.get("network_id") and not api_wrapper.is_network_id_set():
                logger.info("Network ID required and not set. Retrieving networks.")
                # Pass the api_wrapper instance to the helper function
                networks = retrieve_networks(api_wrapper)
                if networks is None:
                    return None

                network_id_param = app_setup_param.get("network_id") if app_setup_param else None
                selected_network_id, _ = select_network(
                    api_wrapper,
                    network_id_param,
                    networks,
                )
                if selected_network_id is None:
                    return None
            elif required_app_setup_param.get("network_id") and api_wrapper.is_network_id_set():
                logger.info(f"Network ID already set: {api_wrapper.get_network_id()}.")
                networks = retrieve_networks(api_wrapper) # Refresh network list
                if networks is None:
                    return None


            # Step 4: Final check if all required parameters are set
            all_set, missing = api_wrapper.check_current_parameters_status()
            if all_set:
                logger.info("All required parameters set - returning MerakiAPIWrapper instance.")
                return api_wrapper # Return the configured instance
            else:
                logger.error(f"Application setup failed: Missing parameters: {', '.join(missing)}")
                toast(f"Application setup failed: Missing parameters: {', '.join(missing)}", color="error", duration=0)
                return None

    except Exception as e:
        logger.exception(f"An unexpected error occurred in app_setup: {e}")
        toast(f"An unexpected error occurred during setup: {e}", color="error", duration=0)
        return None

def show_about_popup():
    """
    Displays an 'About' popup containing application information from the 'about' module.
    """
    logger.info("Displaying 'About' popup.")
    info = about.APP_INFO # Get application info.
    with popup("About " + info["name"],size='large'): # Create a PyWebIO popup.
        put_markdown(f"## {info['name']} (v{info['version']})")
        put_markdown(f"**Description:** {info['description']}")
        put_markdown(f"**Author:** {info['author']}")
        put_markdown("---")
        put_markdown("**Relevant Resources:**")
        for name, link in info["links"].items():
            put_markdown(f"- [{name}]({link})")
        put_markdown("---")
        put_markdown(f"**License:** {info['license_name']}")
        put_markdown(f"```\n{info['license_text']}\n```") # Display license text in a code block.
    logger.debug("'About' popup displayed.")

def show_current_params_popup():
    """
    Displays a 'Current Parameters' popup showing the application's current configuration.
    Requires a function to retrieve parameters; raises an error if none is provided.
    """
    logger.info("Displaying 'Current Parameters' popup.")
    try:
        # Call the updated get_current_app_params function
        params = meraki_api_utils.get_current_app_params()

        with popup("Current Parameters"):
            put_markdown("## Application Parameters")
            # Iterate through the dictionary items
            for param_key, param_details in params.items():
                # Access the 'label' for the display name and 'value' for the actual value
                display_label = param_details.get('label', param_key.replace('_', ' ').title()) # Fallback to title-cased key
                display_value = param_details.get('value', 'N/A')

                put_markdown(f"**{display_label}:** `{display_value}`")  # Display each parameter.
        logger.debug("'Current Parameters' popup displayed.")
    except Exception as e:
        logger.exception(f"An error occurred while displaying current parameters: {e}")
        
def restart_app_client_side():
    """
    Triggers a client-side page reload, effectively restarting the PyWebIO application.
    """
    logger.warning("Initiating client-side application restart (page reload).")
    run_js("location.reload()") # Executes JavaScript to reload the browser page.

def render_header(project_name):
    """
    Renders the application's header, including a project title, navigation buttons,
    and a collapsible log display.
    """
    logger.info(f"Rendering header for project: {project_name}")
    try:
        # Top Gradient Bar (for visual styling).
        put_html('<div class="top-gradient-bar"></div>')
        logger.debug("Rendered top gradient bar.")
        # Top Bar with project title.
        put_html(f'<div class="top-bar">{project_name}</div>')
        logger.debug(f"Rendered top bar with project name: {project_name}.")
        # Main Layout Container for navigation and application content.
        put_html('<div class="main-layout-container">')
        logger.debug("Rendered main layout container.")
        # Create PyWebIO scopes for navigation, logs, and main application content.
        put_scope('nav')
        put_scope('log_scope')
        with use_scope ('log_scope'):
            # Collapsible section for displaying logs.
            put_collapse('Logs', [
                    put_scrollable(put_scope('log_display_content'), height=200, keep_bottom=True, scope='rolling_log_container'), # Scrollable area for logs.
                    put_buttons([{'label': 'Download CSV', 'value': 'download'}], onclick=download_logs_as_csv) # Button to download logs.
                ], open=False) # Logs section is initially closed.
            logger.debug("Rendered log display collapse and download button.")
        put_scope('app')
        # Close the main layout container div.
        put_html('</div>')

        # Render navigation buttons within the 'nav' scope.
        if nav_buttons:
            with use_scope('nav', clear=True):
                def handle_nav_click(btn_value):
                    logger.info(f"Navigation button clicked: {btn_value}")
                    if btn_value == 'about':
                        show_about_popup()
                    elif btn_value == 'app_restart':
                        restart_app_client_side()
                    elif btn_value == 'current_param':
                        show_current_params_popup()
                    else:
                        put_markdown(f"**Nav button clicked:** {btn_value}") # Fallback for other buttons.
                put_buttons(nav_buttons, onclick=handle_nav_click) # type: ignore
            logger.debug(f"Rendered navigation buttons: {[btn['label'] for btn in nav_buttons]}.")

        # Initial content displayed in the 'app' scope.
        with use_scope('app', clear=True):
            put_markdown(f"# Welcome to {project_name}")
            put_markdown("Use the navigation to manage DNS records, profiles, and networks.")
            logger.info("Rendered initial welcome message in app scope.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during header rendering: {e}")

def download_logs_as_csv(btn_value):
    """
    Generates a CSV file from the accumulated log entries and triggers a browser download.
    """
    logger.info(f"Initiating log download as CSV. Button value: {btn_value}")
    try:
        output = io.StringIO() # Create an in-memory text buffer.
        writer = csv.writer(output)
        writer.writerow(['Timestamp - Level - Message']) # Write CSV header.
        with log_entries_lock: # Acquire lock for thread-safe access to log_entries.
            for entry in log_entries:
                writer.writerow([entry]) # Write each log entry as a row.
        csv_data = output.getvalue().encode('utf-8') # Get CSV content as bytes.
        output.close()
        logger.debug(f"Prepared {len(log_entries)} log entries for CSV download.")

        download('app_logs.csv', csv_data) # Trigger browser download.
        logger.info("Triggered 'app_logs.csv' download using session.download.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during CSV log download: {e}")

def update_log_display():
    """
    Function intended to run in a background thread. Periodically checks for new log entries
    and appends them to the log display in the UI. Automatically scrolls to the bottom.
    """
    global last_displayed_log_index
    logger.info("Starting log display update thread.")

    while True: # Loop indefinitely to continuously update.
        try:
            current_log_count = 0
            with log_entries_lock: # Acquire lock to read log_entries count.
                current_log_count = len(log_entries)

            if current_log_count > last_displayed_log_index:
                with use_scope('log_display_content', clear=False): # Append to existing content.
                    for i in range(last_displayed_log_index, current_log_count):
                        entry = log_entries[i]
                        put_markdown(f"```\n{entry}```") # Display log entry in a markdown code block.

                last_displayed_log_index = current_log_count # Update the last displayed index.
                logger.debug(f"Appended {current_log_count - last_displayed_log_index} new log entries.")

                # Scroll the log display to the bottom using JavaScript.
                run_js(f'document.querySelector("[scope=\'rolling_log_container\'] .pywebio-scrollable-container").scrollTop = document.querySelector("[scope=\'rolling_log_container\'] .pywebio-scrollable-container").scrollHeight;')

        except Exception as e:
            logger.exception(f"An unexpected error occurred in update_log_display thread: {e}")
        time.sleep(2) # Wait for 2 seconds before checking for new logs again.

def get_valid_api_key(initial_api_key=None):
    """
    Prompts the user for an API key if not provided initially, and validates it.
    Keeps prompting until a valid API key is entered or the user cancels.
    Uses wrapper_functions.py functions for setting and validating the API key.
    """
    

    current_api_key = initial_api_key
    while True:
        if not current_api_key:
            api_key_data = input_group(
                "Enter API Key",
                [pywebio_input("API Key", name="api_key", type="password", required=True)]
            )
            assert isinstance(api_key_data, dict), "Expected api_key_data to be a dict"
            if not api_key_data or not api_key_data.get("api_key"):
                toast("API key is required to proceed. Exiting application.", color="error")
                return None
            current_api_key = api_key_data["api_key"]

        # Use wrapper_functions to set and validate the API key
        meraki_api_utils.set_api_key(current_api_key)
        if meraki_api_utils.is_api_key_set():
            return current_api_key
        else:
            toast("Invalid API key. Please try again.", color="error")
            current_api_key = None  # Reset to prompt again

def retrieve_organizations():
    """
    Fetches the list of organizations using the configured API key.
    Handles potential errors during retrieval and displays toasts.
  
    """



    organizations = meraki_api_utils.list_organizations()
    if isinstance(organizations, dict) and "error" in organizations:
        toast(f"Error retrieving organizations: {organizations.get('details')}", color="error")
        return None
    if not organizations:
        toast("No organizations found with the provided API key. Exiting application.", color="error")
        return None
    return organizations

def retrieve_networks() -> Optional[List[Dict[str, str]]]:
    """
    Fetches the list of networks using the configured API key and potentially
    the currently selected organization.
    Handles potential errors during retrieval and displays toasts.
    Receives logic functions and logger by reference.
    """
    

    networks = meraki_api_utils.list_networks()
    if isinstance(networks, dict) and "error" in networks:
        toast(f"Error retrieving networks: {networks.get('details')}", color="error")
        logger.error(f"Failed to retrieve networks: {networks.get('details')}")
        return None
    if not networks:
        toast("No networks found. Please ensure an organization is selected and it contains networks.", color="error")
        logger.info("No networks found for the current context.")
        return None
    logger.info(f"Successfully retrieved {len(networks)} networks.")
    return cast(List[Dict[str, str]], networks) # <-- Add cast here 

def select_organization(organization_id_param, organizations, ):
    """
    Selects an organization based on a provided ID or by prompting the user.
    Validates the selected organization and sets it in the logic module using wrapper_functions.
    Receives logger by reference.
    """
   
    valid_organization_ids = {org["id"] for org in organizations}
    selected_id = None
    selected_org_name = None

    # Use the organization ID provided as a parameter if valid
    if organization_id_param in valid_organization_ids:
        selected_id = organization_id_param
        selected_org_name = next(org["name"] for org in organizations if org["id"] == selected_id)
        meraki_api_utils.set_organization_id(selected_id, organization_name=selected_org_name)
        put_markdown(f"### Organization selected: [{selected_id}] - {selected_org_name}")
        return selected_id, selected_org_name

    # If parameter is invalid or not provided, prompt the user to select from organizations
    if organization_id_param is not None:
        toast(f"Invalid organization id '{organization_id_param}'. Please select a valid organization.", color="error")

    # Build options for selection input
    options: List[Dict[str,str]] = [{"label": f"[{org['id']}] - {org['name']}", "value": org["id"]} for org in organizations]

    # Explicit check for options type
    if not isinstance(options, list):
        logger.error("Options for organization selection must be a list.")
        toast("Internal error: Invalid options for organization selection.", color="error")
        return None, None

    # Prompt user to select organization using PyWebIO select input
    org_selection = input_group(
        "Select an Organization",
        [select("Organization", name="organization_id", options=options, required=True)] # type: ignore
    )

    # Explicit check for org_selection type and content
    if not isinstance(org_selection, dict) or not org_selection.get("organization_id"):
        toast("Organization selection is required. Exiting application.", color="error")
        return None, None

    selected_id = org_selection["organization_id"]
    selected_org_name = next(org["name"] for org in organizations if org["id"] == selected_id)
    meraki_api_utils.set_organization_id(selected_id, organization_name=selected_org_name)
    put_markdown(f"### Organization selected: [{selected_id}] - {selected_org_name}")
    return selected_id, selected_org_name


def select_network(network_id_param: Optional[str], networks: List[Dict[str, str]], ):
    """
    Selects a network based on a provided ID or by prompting the user.
    Validates the selected network and sets it in the logic module using wrapper_functions.

    """

    # Assuming network objects use "ID" consistently, like organizations.
    valid_network_ids = {network["id"] for network in networks} # Changed from "id" to "ID"
    selected_id = None
    selected_network_name = None

    # Use the network ID provided as a parameter if valid
    if network_id_param is not None and network_id_param in valid_network_ids:
        selected_id = network_id_param
        selected_network_name = next(network["name"] for network in networks if network["id"] == selected_id)
        meraki_api_utils.set_network_id(selected_id, network_name=selected_network_name) # type: ignore
        put_markdown(f"### Network selected: [{selected_id}] - {selected_network_name}")
        return selected_id, selected_network_name

    # If parameter is invalid or not provided, prompt the user to select from networks
    if network_id_param is not None: # Only show toast if a parameter was provided but invalid
        toast(f"Invalid network id '{network_id_param}'. Please select a valid network.", color="error")

    # Build options for selection input
    # Assuming network objects use "ID" consistently, like organizations.
    options: List[Dict[str,str]] = [{"label": f"[{network['id']}] - {network['name']}", "value": network["id"]} for network in networks]

    # Explicit check for options type
    if not isinstance(options, list):
        logger.error("Options for network selection must be a list.")
        toast("Internal error: Invalid options for network selection.", color="error")
        return None, None

    # Prompt user to select network using PyWebIO select input
    network_selection = input_group(
        "Select a Network",
        [select("Network", name="network_id", options=options, required=True)] #type: ignore
    )

    # Explicit check for network_selection type and content
    if not isinstance(network_selection, dict) or not network_selection.get("network_id"): 
        toast("Network selection is required. Exiting application.", color="error")
        return None, None

    selected_id = network_selection["network_id"] 
    selected_network_name = next(network["name"] for network in networks if network["id"] == selected_id)
    meraki_api_utils.set_network_id(selected_id, network_name=selected_network_name) # type: ignore
    put_markdown(f"### Network selected: [{selected_id}] - {selected_network_name}")
    return selected_id, selected_network_name