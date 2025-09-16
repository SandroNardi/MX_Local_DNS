from pywebio.output import toast, put_markdown, use_scope
from pywebio.input import input_group, select, input as pywebio_input
from pywebio import start_server, config
from my_logging import setup_logger  # Setup logger and log storage
from pywebio.session import register_thread
import threading
import container_page
import gui
import os
import local_dns_logic as logic
import about

# Initialize logger with console output enabled for debugging and monitoring.
logger = setup_logger(enable_logging=True, console_logging=True,file_logging=True)

# Application setup parameters, potentially from environment variables or defaults.
app_setup_param = {"api_key": os.getenv("MK_CSM_KEY"), "org_id": "991866"}

def get_valid_api_key(initial_api_key=None):
    """
    Prompts the user for an API key if not provided initially, and validates it.
    Keeps prompting until a valid API key is entered or the user cancels.
    """
    current_api_key = initial_api_key
    while True:
        if not current_api_key:
            # Request API key from user via PyWebIO input group.
            api_key_data = input_group(
                "Enter API Key",
                [pywebio_input("API Key", name="api_key", type="password", required=True)]
            )
            if not api_key_data or not api_key_data.get("api_key"):
                toast("API key is required to proceed. Exiting application.", color="error")
                return None
            current_api_key = api_key_data["api_key"]
        
        # Set the API key in the logic module and check its validity.
        logic.set_api_key(current_api_key)
        if logic.is_api_not_null(): # Assuming this checks if the API key is valid/set.
            return current_api_key
        else:
            toast("Invalid API key. Please try again.", color="error")
            current_api_key = None # Reset to prompt again.

def retrieve_organizations():
    """
    Fetches the list of organizations using the configured API key.
    Handles potential errors during retrieval and displays toasts.
    """
    organizations = logic.get_organizations()
    if isinstance(organizations, dict) and "error" in organizations:
        toast(f"Error retrieving organizations: {organizations.get('details')}", color="error")
        return None
    if not organizations:
        toast("No organizations found with the provided API key. Exiting application.", color="error")
        return None
    return organizations

def select_organization(org_id_param, organizations):
    """
    Selects an organization based on a provided ID or by prompting the user.
    Validates the selected organization and sets it in the logic module.
    """
    valid_org_ids = {org["ID"] for org in organizations}
    selected_id = None
    selected_org_name = None

    # Attempt to use the organization ID provided as a parameter.
    if org_id_param in valid_org_ids:
        selected_id = org_id_param
        selected_org_name = next(org["Name"] for org in organizations if org["ID"] == selected_id)
        logic.set_organization_id(selected_id)
        logic.set_organization_name(selected_org_name)
        put_markdown(f"### Organization selected: [{selected_id}] - {selected_org_name}")
        return selected_id, selected_org_name
    else:
        # If parameter is invalid or not provided, prompt the user.
        if org_id_param is not None:
            toast(f"Invalid organization ID '{org_id_param}'. Please select a valid organization.", color="error")

        # Create options for the dropdown select input.
        options = [{"label": f"[{org['ID']}] - {org['Name']}", "value": org["ID"]} for org in organizations]
        org_selection = input_group(
            "Select an Organization",
            [select("Organization", name="org_id", options=options, required=True)]
        )
        if not org_selection or not org_selection.get("org_id"):
            toast("Organization selection is required. Exiting application.", color="error")
            return None, None

        # Set the selected organization in the logic module.
        selected_id = org_selection["org_id"]
        selected_org_name = next(org["Name"] for org in organizations if org["ID"] == selected_id)
        logic.set_organization_id(selected_id)
        logic.set_organization_name(selected_org_name)
        put_markdown(f"### Organization selected: [{selected_id}] - {selected_org_name}")
        return selected_id, selected_org_name


def app_setup(app_setup_param):
    """
    Main setup function for the application.
    Orchestrates API key validation, organization retrieval, and organization selection.
    Returns True if setup is successful and all required parameters are set, False otherwise.
    """
    logger.info("Entering app_setup function.")

    try:
        # Use a PyWebIO scope to manage output for the setup phase.
        with use_scope('app', clear=True):
            initial_api_key = app_setup_param.get("api_key")
            org_id_param = app_setup_param.get("org_id")

            # Step 1: Secure a valid API Key. If this fails, return False.
            api_key = get_valid_api_key(initial_api_key)
            if api_key is None:
                return False

            # Step 2: Retrieve the list of organizations. If this fails, return False.
            organizations = retrieve_organizations()
            if organizations is None:
                return False

            # Step 3: Select an organization. If this fails, return False.
            selected_id, _ = select_organization(org_id_param, organizations)
            if selected_id is None:
                return False

            # Step 4: Final check if all required parameters are set in logic.
            if logic.are_required_params_set():
                logger.info("All required parameters set - starting the app.")
                return True
            else:
                logger.error("Application setup failed: Required parameters not set in logic.")
                toast("Application setup failed: Required parameters not set.", color="error", duration=0)
                return False

    except Exception as e:
        # Catch and log any unexpected errors during setup.
        logger.exception(f"An unexpected error occurred in app_setup: {e}")
        toast(f"An unexpected error occurred during setup: {e}", color="error", duration=0)
        return False

def get_current_param_from_logic():
    """
    Retrieves current parameters from the logic module.
    Used for displaying current application state.
    """
    return logic.get_current_params()


def app():
    """
    The main PyWebIO application function.
    Initializes the UI, sets up background tasks, and orchestrates the application flow.
    """
    logger.info("Starting PyWebIO application.")
    try:
        # Create and register a background thread to update the log display in the UI.
        t = threading.Thread(target=container_page.update_log_display)
        register_thread(t)

        # Render the application header with project name and current parameters.
        container_page.render_header(project=about.APP_INFO.get("name"), get_current_params_func=get_current_param_from_logic)

        t.start()  # Start the log update thread.

        # Setup and display the main GUI menus ONLY if app_setup is successful.
        if app_setup(app_setup_param):
            gui.app_main_menu() # Proceed to the main application menu.
        else:
            # If setup fails, log and inform the user.
            logger.info("Application setup failed. Not proceeding to main menu.")
            put_markdown("## Application could not start. Please check logs for details.", color="error")

    except Exception as e:
        # Log and show error toast if any unexpected error occurs during application startup.
        logger.exception(f"An unexpected error occurred during application startup: {e}")
        toast(f"An unexpected error occurred during startup: {e}", color="error", duration=0)

if __name__ == "__main__":
    """
    Entry point of the script.
    Configures PyWebIO and starts the server.
    """
    logger.info("Application script started.")
    # Apply custom CSS styles from the wrapper module for UI customization.
    config(css_style=container_page.get_css_style())
    # Start PyWebIO server on port 8080 with debug enabled for development.
    start_server(app, port=8080, debug=True)