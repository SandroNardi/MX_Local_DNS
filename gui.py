from pywebio.output import put_markdown, put_buttons, use_scope, toast,put_datatable, put_table
from pywebio.input import input_group, input, select, actions,input as pywebio_input
import local_dns_logic as logic  # Imports the core logic module for DNS and network operations.
from my_logging import setup_logger

# Initialize logger for the module, enabling console output for debugging.
logger = setup_logger(enable_logging=True, console_logging=True, file_logging=True)


def app_main_menu():
    """
    Displays the main navigation menu for the application after an organization is selected.
    Provides options to manage profiles, DNS records, and network associations.
    """
    logger.info("Entering app_main_menu function.")
    try:
        # Clear previous content and render the main menu within the 'app' scope.
        with use_scope('app', clear=True):
            put_markdown(f"### Organization: {logic.get_organization_name()} (ID: {logic.get_organization_id()})")
            logger.info(f"Displaying main menu for organization: {logic.get_organization_name()} (ID: {logic.get_organization_id()})")
            put_buttons(
                [
                    {"label": "Manage Profiles", "value": "profiles"},
                    {"label": "Manage DNS Records", "value": "dns_records"},
                    {"label": "Network Association", "value": "networks"},
                ],
                onclick=handle_main_menu_action, # Callback function for button clicks.
            )
    except Exception as e:
        logger.exception(f"An unexpected error occurred in app_main_menu: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def handle_main_menu_action(action):
    """
    Handles actions triggered from the main menu buttons, directing to respective functions.
    """
    logger.info(f"Handling main menu action: {action}")
    try:
        if action == "profiles":
            list_profiles()
        elif action == "dns_records":
            list_dns_records()
        elif action == "networks":
            list_network_assignments()

    except Exception as e:
        logger.exception(f"An unexpected error occurred in handle_main_menu_action for action '{action}': {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)

# Profiles Management
def list_profiles():
    """
    Retrieves and displays a list of all profiles for the current organization.
    Provides options to create, delete, or go back to the main menu.
    """
    logger.info("Entering list_profiles function.")
    try:
        profiles = logic.list_profiles() # Fetch profiles from the logic layer.
        with use_scope('app', clear=True):
            # Handle API errors during profile retrieval.
            if isinstance(profiles, dict) and "error" in profiles:
                error_msg = f"Failed to retrieve profiles: {profiles.get('error')}. Details: {profiles.get('details')}"
                logger.error(error_msg)
                toast(f"Error {profiles.get('status_code', 'Unknown')} - {profiles.get('error')}: {profiles.get('details')}", color="error", duration=0)
                return

            if not profiles:
                logger.info("No profiles found for the current organization.")
                put_markdown("No profiles found.")
            else:
                logger.info(f"Found {len(profiles)} profiles.")
                put_markdown("### Profiles with Associated Networks")
                put_datatable(profiles,height="auto") # Display profiles in a data table.

            put_buttons(
                [
                    {"label": "Create New Profile", "value": "create"},
                    {"label": "Delete Profile", "value": "delete"},
                    {"label": "Back to Main Menu", "value": "back"},
                ],
                onclick=handle_profiles_action, # Callback for profile management actions.
            )
    except Exception as e:
        logger.exception(f"An unexpected error occurred in list_profiles: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def handle_profiles_action(action):
    """
    Handles actions triggered from the profiles management screen.
    """
    logger.info(f"Handling profiles action: {action}")
    try:
        if action == "create":
            create_profile_page()
        elif action == "delete":
            delete_profile_page()
        elif action == "back":
            app_main_menu()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in handle_profiles_action for action '{action}': {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def create_profile_page():
    """
    Displays a form to create a new profile.
    Prompts for a profile name and handles creation or cancellation.
    """
    logger.info("Entering create_profile_page function.")
    try:
        with use_scope('app', clear=True):
            profile_data = input_group(
                "Create a New Profile",
                [
                    input("Profile Name", name="name"),
                    actions( # Buttons for form submission or cancellation.
                        name="actions",
                        buttons=[
                            {"label": "Create", "value": "create", "color": "primary"},
                            {"label": "Back", "value": "back", "color": "secondary"},
                        ],
                    ),
                ]
            )

            if profile_data: # Check if the user submitted data (not cancelled input_group).
                if profile_data["actions"] == "back":
                    logger.info("User chose to go back from create profile page.")
                    list_profiles()
                elif profile_data["actions"] == "create":
                    profile_name = profile_data["name"]
                    logger.info(f"Attempting to create profile with name: {profile_name}")
                    response = logic.create_profile(profile_name) # Call logic to create profile.
                    if isinstance(response, dict) and "error" in response:
                        error_msg = f"Failed to create profile '{profile_name}': {response.get('error')}. Details: {response.get('details')}"
                        logger.error(error_msg)
                        toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
                        return
                    logger.info(f"Profile '{profile_name}' created successfully.")
                    toast("Profile created successfully!", color="success")
                    list_profiles() # Refresh the profiles list.
            else:
                logger.info("Profile creation input group was cancelled or returned empty.")
                list_profiles()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in create_profile_page: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def delete_profile_page():
    """
    Displays a list of profiles from which the user can select one to delete.
    """
    logger.info("Entering delete_profile_page function.")
    try:
        with use_scope('app', clear=True):
            put_markdown("### Delete a Profile")
            profiles = logic.list_profiles() # Fetch profiles for selection.
            if isinstance(profiles, dict) and "error" in profiles:
                error_msg = f"Failed to retrieve profiles for deletion: {profiles.get('error')}. Details: {profiles.get('details')}"
                logger.error(error_msg)
                toast(f"Error {profiles.get('status_code', 'Unknown')} - {profiles.get('error')}: {profiles.get('details')}", color="error", duration=0)
                return

            if not profiles:
                logger.info("No profiles available to delete.")
                put_markdown("No profiles available to delete.")
                put_buttons([{"label": "Back to Profiles", "value": "back"}], onclick=lambda _: list_profiles()) # Go back if no profiles.
                return

            # Prepare options for the dropdown select input.
            profile_options = [{"label": f"[{p['Profile ID']}] - {p['Name']}", "value": p["Profile ID"]} for p in profiles]
            logger.debug(f"Profiles available for deletion: {[p['Name'] for p in profiles]}")

            profile_to_delete = input_group(
                "Select a Profile to Delete",
                [
                    select("Profile", name="profile_id", options=profile_options), # Dropdown for profile selection.
                    actions(
                        name="actions",
                        buttons=[
                            {"label": "Delete", "value": "delete", "color": "danger"},
                            {"label": "Back", "value": "back"},
                        ],
                    ),
                ],
            )
            if profile_to_delete:
                handle_delete_profile_action(profile_to_delete["actions"], profile_to_delete["profile_id"])
            else:
                logger.info("Profile deletion input group was cancelled or returned empty.")
                list_profiles()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in delete_profile_page: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def handle_delete_profile_action(action, profile_id):
    """
    Executes the deletion of a selected profile or navigates back.
    """
    logger.info(f"Handling delete profile action: {action} for profile ID: {profile_id}")
    try:
        if action == "delete":
            logger.info(f"Attempting to delete profile with ID: {profile_id}")
            response = logic.delete_profile(profile_id) # Call logic to delete profile.
            if isinstance(response, dict) and "error" in response:
                error_msg = f"Failed to delete profile '{profile_id}': {response.get('error')}. Details: {response.get('details')}"
                logger.error(error_msg)
                toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
            else:
                logger.info(f"Profile '{profile_id}' deleted successfully.")
                toast("Profile deleted successfully!", color="success")
            list_profiles() # Refresh the profiles list.
        elif action == "back":
            logger.info("User chose to go back from delete profile action.")
            list_profiles()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in handle_delete_profile_action for profile ID '{profile_id}': {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


# DNS Records Management
def list_dns_records():
    """
    Retrieves and displays a list of all DNS records for the current organization.
    Provides options to create, delete, or go back to the main menu.
    """
    logger.info("Entering list_dns_records function.")
    try:
        dns_records = logic.list_dns_records() # Fetch DNS records from the logic layer.
        with use_scope('app', clear=True):
            # Handle API errors during DNS record retrieval.
            if isinstance(dns_records, dict) and "error" in dns_records:
                error_msg = f"Failed to retrieve DNS records: {dns_records.get('error')}. Details: {dns_records.get('details')}"
                logger.error(error_msg)
                toast(f"Error {dns_records.get('status_code', 'Unknown')} - {dns_records.get('error')}: {dns_records.get('details')}", color="error", duration=0)
                return

            if not dns_records:
                logger.info("No DNS records found for the current organization.")
                put_markdown("No DNS records found.")
            else:
                logger.info(f"Found {len(dns_records)} DNS records.")
                put_markdown("### DNS Records with Associated Profiles")
                put_datatable(dns_records,height="auto") # Display DNS records in a data table.

            put_buttons(
                [
                    {"label": "Create New DNS Record", "value": "create"},
                    {"label": "Delete DNS Record", "value": "delete"},
                    {"label": "Back to Main Menu", "value": "back"},
                ],
                onclick=handle_dns_records_action, # Callback for DNS record management actions.
            )
    except Exception as e:
        logger.exception(f"An unexpected error occurred in list_dns_records: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def handle_dns_records_action(action):
    """
    Handles actions triggered from the DNS records management screen.
    """
    logger.info(f"Handling DNS records action: {action}")
    try:
        if action == "create":
            create_dns_record_page()
        elif action == "delete":
            delete_dns_record_page()
        elif action == "back":
            app_main_menu()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in handle_dns_records_action for action '{action}': {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def create_dns_record_page():
    """
    Displays a form to create a new DNS record.
    Requires selecting a profile and providing hostname and address.
    """
    logger.info("Entering create_dns_record_page function.")
    try:
        with use_scope('app', clear=True):
            put_markdown("### Create a New DNS Record")
            profiles = logic.list_profiles() # Fetch profiles to associate with the DNS record.
            if isinstance(profiles, dict) and "error" in profiles:
                error_msg = f"Failed to retrieve profiles for DNS record creation: {profiles.get('error')}. Details: {profiles.get('details')}"
                logger.error(error_msg)
                toast(f"Error {profiles.get('status_code', 'Unknown')} - {profiles.get('error')}: {profiles.get('details')}", color="error", duration=0)
                return

            if not profiles:
                logger.info("No profiles available for DNS record creation. User prompted to create one.")
                put_markdown("No profiles available. Please create a profile first.")
                put_buttons([{"label": "Back to DNS Records", "value": "back"}], onclick=lambda _: list_dns_records())
                return

            profile_options = [{"label": f"[{p['Profile ID']}] {p['Name']}", "value": p["Profile ID"]} for p in profiles]
            logger.debug(f"Profiles available for DNS record creation: {[p['Name'] for p in profiles]}")

            record_data = input_group(
                "Create DNS Record",
                [
                    input("Hostname", name="hostname"),
                    input("Address", name="address"),
                    select("Profile", name="profile_id", options=profile_options), # Dropdown for profile selection.
                    actions(
                        name="actions",
                        buttons=[
                            {"label": "Create", "value": "create", "color": "primary"},
                            {"label": "Back", "value": "back"},
                        ],
                    ),
                ],
            )
            if record_data:
                if record_data["actions"] == "back":
                    logger.info("User chose to go back from create DNS record page.")
                    list_dns_records()
                    return

                profile_id = record_data["profile_id"]
                hostname = record_data["hostname"]
                address = record_data["address"]
                logger.info(f"Attempting to create DNS record: Hostname='{hostname}', Address='{address}', Profile ID='{profile_id}'")
                response = logic.create_dns_record(profile_id, hostname, address) # Call logic to create DNS record.
                if isinstance(response, dict) and "error" in response:
                    error_msg = f"Failed to create DNS record: {response.get('error')}. Details: {response.get('details')}"
                    logger.error(error_msg)
                    toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
                    return

                logger.info(f"DNS record '{hostname}' created successfully.")
                toast("DNS record created successfully!", color="success")
                put_buttons([{"label": "Back to DNS Records", "value": "back"}], onclick=lambda _: list_dns_records())
            else:
                logger.info("DNS record creation input group was cancelled or returned empty.")
                list_dns_records()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in create_dns_record_page: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def delete_dns_record_page():
    """
    Displays a list of DNS records from which the user can select one to delete.
    """
    logger.info("Entering delete_dns_record_page function.")
    try:
        with use_scope('app', clear=True):
            put_markdown("### Delete a DNS Record")
            dns_records = logic.list_dns_records() # Fetch DNS records for selection.
            if isinstance(dns_records, dict) and "error" in dns_records:
                error_msg = f"Failed to retrieve DNS records for deletion: {dns_records.get('error')}. Details: {dns_records.get('details')}"
                logger.error(error_msg)
                toast(f"Error {dns_records.get('status_code', 'Unknown')} - {dns_records.get('error')}: {dns_records.get('details')}", color="error", duration=0)
                return

            if not dns_records:
                logger.info("No DNS records available to delete.")
                put_markdown("No DNS records available to delete.")
                put_buttons([{"label": "Back to DNS Records", "value": "back"}], onclick=lambda _: list_dns_records())
                return

            # Prepare options for the dropdown select input.
            record_options = [{"label": f"[{r['Record ID']}] - {r['Hostname']}", "value": r["Record ID"]} for r in dns_records]
            logger.debug(f"DNS records available for deletion: {[r['Hostname'] for r in dns_records]}")

            record_to_delete = input_group(
                "Select a DNS Record to Delete",
                [
                    select("DNS Record", name="record_id", options=record_options), # Dropdown for record selection.
                    actions(
                        name="actions",
                        buttons=[
                            {"label": "Delete", "value": "delete", "color": "danger"},
                            {"label": "Back", "value": "back"},
                        ],
                    ),
                ],
            )
            if record_to_delete:
                handle_delete_dns_record_action(record_to_delete["actions"], record_to_delete["record_id"])
            else:
                logger.info("DNS record deletion input group was cancelled or returned empty.")
                list_dns_records()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in delete_dns_record_page: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def handle_delete_dns_record_action(action, record_id):
    """
    Executes the deletion of a selected DNS record or navigates back.
    """
    logger.info(f"Handling delete DNS record action: {action} for record ID: {record_id}")
    try:
        if action == "delete":
            logger.info(f"Attempting to delete DNS record with ID: {record_id}")
            response = logic.delete_dns_record(record_id) # Call logic to delete DNS record.
            if isinstance(response, dict) and "error" in response:
                error_msg = f"Failed to delete DNS record '{record_id}': {response.get('error')}. Details: {response.get('details')}"
                logger.error(error_msg)
                toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
            else:
                logger.info(f"DNS record '{record_id}' deleted successfully.")
                toast("DNS record deleted successfully!", color="success")
            list_dns_records() # Refresh the DNS records list.
        elif action == "back":
            logger.info("User chose to go back from delete DNS record action.")
            list_dns_records()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in handle_delete_dns_record_action for record ID '{record_id}': {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


# Network Assignments Management
def list_network_assignments():
    """
    Retrieves and displays a list of all network assignments for the current organization.
    Provides options to create, delete, or go back to the main menu.
    """
    logger.info("Entering list_network_assignments function.")
    try:
        assignments = logic.list_network_assignments() # Fetch network assignments from the logic layer.
        with use_scope('app', clear=True):
            # Handle API errors during network assignment retrieval.
            if isinstance(assignments, dict) and "error" in assignments:
                error_msg = f"Failed to retrieve network assignments: {assignments.get('error')}. Details: {assignments.get('details')}"
                logger.error(error_msg)
                toast(f"Error {assignments.get('status_code', 'Unknown')} - {assignments.get('error')}: {assignments.get('details')}", color="error", duration=0)
                return

            if not assignments:
                logger.info("No network assignments found for the current organization.")
                put_markdown("No network assignments found.")
            else:
                logger.info(f"Found {len(assignments)} network assignments.")
                put_markdown("### Networks with Associated Profiles")
                put_datatable(assignments,height="auto") # Display network assignments in a data table.

            put_buttons(
                [
                    {"label": "Create Network Assignment", "value": "create"},
                    {"label": "Delete Network Assignment", "value": "delete"},
                    {"label": "Back to Main Menu", "value": "back"},
                ],
                onclick=handle_network_assignments_action, # Callback for network assignment actions.
            )
    except Exception as e:
        logger.exception(f"An unexpected error occurred in list_network_assignments: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def handle_network_assignments_action(action):
    """
    Handles actions triggered from the network assignments management screen.
    """
    logger.info(f"Handling network assignments action: {action}")
    try:
        if action == "create":
            create_network_assignment_page()
        elif action == "delete":
            delete_network_assignment_page()
        elif action == "back":
            app_main_menu()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in handle_network_assignments_action for action '{action}': {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def create_network_assignment_page():
    """
    Displays a form to create a new network assignment.
    Requires selecting a profile and a network.
    """
    logger.info("Entering create_network_assignment_page function.")
    try:
        with use_scope('app', clear=True):
            put_markdown("### Create a New Network Assignment")
            profiles = logic.list_profiles() # Fetch profiles for assignment.
            if isinstance(profiles, dict) and "error" in profiles:
                error_msg = f"Failed to retrieve profiles for network assignment creation: {profiles.get('error')}. Details: {profiles.get('details')}"
                logger.error(error_msg)
                toast(f"Error {profiles.get('status_code', 'Unknown')} - {profiles.get('error')}: {profiles.get('details')}", color="error", duration=0)
                return

            if not profiles:
                logger.info("No profiles available for network assignment. User prompted to create one.")
                put_markdown("No profiles available. Please create a profile first.")
                put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: list_network_assignments())
                return

            networks = logic.list_networks() # Fetch networks for assignment.
            if isinstance(networks, dict) and "error" in networks:
                error_msg = f"Failed to retrieve networks for network assignment creation: {networks.get('error')}. Details: {networks.get('details')}"
                logger.error(error_msg)
                toast(f"Error {networks.get('status_code', 'Unknown')} - {networks.get('error')}: {networks.get('details')}", color="error", duration=0)
                return

            if not networks:
                logger.info("No networks available in this organization for assignment.")
                put_markdown("No networks available in this organization. Cannot create an assignment.")
                put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: list_network_assignments())
                return

            profile_options = [{"label": f"[{p['Profile ID']}] {p['Name']}", "value": p["Profile ID"]} for p in profiles]
            network_options = [{"label": f"[{n['ID']}] {n['Name']}", "value": n["ID"]} for n in networks]
            logger.debug(f"Profiles available: {[p['Name'] for p in profiles]}, Networks available: {[n['Name'] for n in networks]}")

            assignment_data = input_group(
                "Create Network Assignment",
                [
                    select("Profile", name="profile_id", options=profile_options), # Dropdown for profile selection.
                    select("Network", name="network_id", options=network_options), # Dropdown for network selection.
                    actions(
                        name="actions",
                        buttons=[
                            {"label": "Create", "value": "create", "color": "primary"},
                            {"label": "Back", "value": "back"},
                        ],
                    ),
                ],
            )
            if assignment_data:
                if assignment_data["actions"] == "back":
                    logger.info("User chose to go back from create network assignment page.")
                    list_network_assignments()
                    return

                profile_id = assignment_data["profile_id"]
                network_id = assignment_data["network_id"]
                logger.info(f"Attempting to create network assignment: Network ID='{network_id}', Profile ID='{profile_id}'")
                response = logic.assign_profile_to_network(network_id, profile_id) # Call logic to create assignment.
                if isinstance(response, dict) and "error" in response:
                    error_msg = f"Failed to create network assignment (Network ID: {network_id}, Profile ID: {profile_id}): {response.get('error')}. Details: {response.get('details')}"
                    logger.error(error_msg)
                    toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
                    put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: list_network_assignments())
                    return

                logger.info(f"Network assignment for Network ID '{network_id}' and Profile ID '{profile_id}' created successfully.")
                toast("Network assignment created successfully!", color="success")
                put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: list_network_assignments())
            else:
                logger.info("Network assignment creation input group was cancelled or returned empty.")
                list_network_assignments()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in create_network_assignment_page: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def delete_network_assignment_page():
    """
    Displays a list of network assignments from which the user can select one to delete.
    """
    logger.info("Entering delete_network_assignment_page function.")
    try:
        with use_scope('app', clear=True):
            put_markdown("### Delete a Network Assignment")
            assignments = logic.list_network_assignments() # Fetch assignments for selection.
            if isinstance(assignments, dict) and "error" in assignments:
                error_msg = f"Failed to retrieve network assignments for deletion: {assignments.get('error')}. Details: {assignments.get('details')}"
                logger.error(error_msg)
                toast(f"Error {assignments.get('status_code', 'Unknown')} - {assignments.get('error')}: {assignments.get('details')}", color="error", duration=0)
                return

            if not assignments:
                logger.info("No network assignments available to delete.")
                put_markdown("No network assignments available to delete.")
                put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: list_network_assignments())
                return

            # Prepare options for the dropdown select input, showing detailed assignment info.
            assignment_options = [
                {
                    "label": f"[{a['Assignment ID']}] Network: {a['Network ID']} {a['Network Name']} Profile: {a['Profile ID']} {a['Profile Name']}",
                    "value": a["Assignment ID"],
                }
                for a in assignments
            ]
            logger.debug(f"Network assignments available for deletion: {[a['Assignment ID'] for a in assignments]}")

            assignment_to_delete = input_group(
                "Select a Network Assignment to Delete",
                [
                    select("Network Assignment", name="assignment_id", options=assignment_options), # Dropdown for assignment selection.
                    actions(
                        name="actions",
                        buttons=[
                            {"label": "Delete", "value": "delete", "color": "danger"},
                            {"label": "Back", "value": "back"},
                        ],
                    ),
                ],
            )
            if assignment_to_delete:
                handle_delete_network_assignment_action(assignment_to_delete["actions"], assignment_to_delete["assignment_id"])
            else:
                logger.info("Network assignment deletion input group was cancelled or returned empty.")
                list_network_assignments()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in delete_network_assignment_page: {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)


def handle_delete_network_assignment_action(action, assignment_id):
    """
    Executes the deletion of a selected network assignment or navigates back.
    """
    logger.info(f"Handling delete network assignment action: {action} for assignment ID: {assignment_id}")
    try:
        if action == "delete":
            logger.info(f"Attempting to delete network assignment with ID: {assignment_id}")
            response = logic.remove_network_assignment(assignment_id) # Call logic to delete assignment.
            if isinstance(response, dict) and "error" in response:
                error_msg = f"Failed to delete network assignment '{assignment_id}': {response.get('error')}. Details: {response.get('details')}"
                logger.error(error_msg)
                toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
            else:
                logger.info(f"Network assignment '{assignment_id}' deleted successfully.")
                toast("Network assignment deleted successfully!", color="success")
            list_network_assignments() # Refresh the network assignments list.
        elif action == "back":
            logger.info("User chose to go back from delete network assignment action.")
            list_network_assignments()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in handle_delete_network_assignment_action for assignment ID '{assignment_id}': {e}")
        toast(f"An unexpected error occurred: {e}", color="error", duration=0)