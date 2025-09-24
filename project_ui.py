# type: ignore
# project_ui.py
from pywebio.output import put_markdown, put_buttons, use_scope, toast, put_datatable, put_table
from pywebio.input import input_group, input, select, actions, input as pywebio_input
from meraki_tools.my_logging import get_logger
from project_logic import ProjectLogic # Import the new ProjectLogic class
from meraki_tools.meraki_api_utils import MerakiAPIWrapper 

logger = get_logger()

class ProjectUI:
    def __init__(self, api_utils:MerakiAPIWrapper,app_scope_name):
        """
        Initializes the ProjectUI class with API_Utils and ProjectLogic instances.
        """
        self._api_utils = api_utils
        self._project_logic = ProjectLogic(api_utils)
        self.logger = get_logger()
        self.app_scope_name=app_scope_name
        self.logger.info("ProjectUI initialized with API_ with API_Utils and ProjectLogic instances.")

    def app_main_menu(self):
        """
        Displays the main navigation menu for the application after an organization is selected.
        Provides options to manage profiles, DNS records, and network associations.
        """
        self.logger.info("Entering app_main_menu function.")

        if self._api_utils is None:
            error_message = "API_Utils instance is not available. Please ensure it was set during ProjectUI initialization."
            self.logger.error(error_message)
            raise ValueError(error_message)

        try:
            with use_scope(self.app_scope_name, clear=True):
                # Access self._api_utils directly
                put_markdown(f"### Organization: {self._api_utils.get_organization_name()} (id: {self._api_utils.get_organization_id()})")
                self.logger.info(f"Displaying main menu for organization: {self._api_utils.get_organization_name()} (id: {self._api_utils.get_organization_id()})")
                put_buttons(
                    [
                        {"label": "Manage Profiles", "value": "profiles"},
                        {"label": "Manage DNS Records", "value": "dns_records"},
                        {"label": "Network Association", "value": "networks"},
                    ],
                    onclick=self.handle_main_menu_action,
                )
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in app_main_menu: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def handle_main_menu_action(self, action):
        """Handles actions triggered from the main menu buttons."""
        self.logger.info(f"Handling main menu action: {action}")
        try:
            if action == "profiles":
                self.list_profiles()
            elif action == "dns_records":
                self.list_dns_records()
            elif action == "networks":
                self.list_network_assignments()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in handle_main_menu_action for action '{action}': {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def list_profiles(self):
        """Retrieves and displays a list of all profiles for the current organization."""
        self.logger.info("Entering list_profiles function.")
        try:
            # Call method on self._project_logic instance
            profiles = self._project_logic.list_profiles()
            with use_scope(self.app_scope_name, clear=True):
                if isinstance(profiles, dict) and "error" in profiles:
                    error_msg = f"Failed to retrieve profiles: {profiles.get('error')}. Details: {profiles.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {profiles.get('status_code', 'Unknown')} - {profiles.get('error')}: {profiles.get('details')}", color="error", duration=0)
                    return

                if not profiles:
                    self.logger.info("No profiles found for the current organization.")
                    put_markdown("No profiles found.")
                else:
                    self.logger.info(f"Found {len(profiles)} profiles.")
                    put_markdown("### Profiles with Associated Networks")
                    put_datatable(profiles, height="auto")

                put_buttons(
                    [
                        {"label": "Create New Profile", "value": "create"},
                        {"label": "Delete Profile", "value": "delete"},
                        {"label": "Back to Main Menu", "value": "back"},
                    ],
                    onclick=self.handle_profiles_action,
                )
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in list_profiles: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def handle_profiles_action(self, action):
        """Handles actions triggered from the profiles management screen."""
        self.logger.info(f"Handling profiles action: {action}")
        try:
            if action == "create":
                self.create_profile_page()
            elif action == "delete":
                self.delete_profile_page()
            elif action == "back":
                self.app_main_menu()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in handle_profiles_action for action '{action}': {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def create_profile_page(self):
        """Displays a form to create a new profile."""
        self.logger.info("Entering create_profile_page function.")
        try:
            with use_scope(self.app_scope_name, clear=True):
                profile_data = input_group(
                    "Create a New Profile",
                    [
                        input("Profile Name", name="name"),
                        actions(
                            name="actions",
                            buttons=[
                                {"label": "Create", "value": "create", "color": "primary"},
                                {"label": "Back", "value": "back", "color": "secondary"},
                            ],
                        ),
                    ]
                )

                if profile_data:
                    if profile_data["actions"] == "back":
                        self.logger.info("User chose to go back from create profile page.")
                        self.list_profiles()
                    elif profile_data["actions"] == "create":
                        profile_name = profile_data["name"]
                        self.logger.info(f"Attempting to create profile with name: {profile_name}")
                        # Call method on self._project_logic instance
                        response = self._project_logic.create_profile(profile_name)
                        if isinstance(response, dict) and "error" in response:
                            error_msg = f"Failed to create profile '{profile_name}': {response.get('error')}. Details: {response.get('details')}"
                            self.logger.error(error_msg)
                            toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
                            return
                        self.logger.info(f"Profile '{profile_name}' created successfully.")
                        toast("Profile created successfully!", color="success")
                        self.list_profiles()
                else:
                    self.logger.info("Profile creation input group was cancelled or returned empty.")
                    self.list_profiles()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in create_profile_page: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def delete_profile_page(self):
        """Displays a list of profiles from which the user can select one to delete."""
        self.logger.info("Entering delete_profile_page function.")
        try:
            with use_scope(self.app_scope_name, clear=True):
                put_markdown("### Delete a Profile")
                # Call method on self._project_logic instance
                profiles = self._project_logic.list_profiles()
                if isinstance(profiles, dict) and "error" in profiles:
                    error_msg = f"Failed to retrieve profiles for deletion: {profiles.get('error')}. Details: {profiles.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {profiles.get('status_code', 'Unknown')} - {profiles.get('error')}: {profiles.get('details')}", color="error", duration=0)
                    return

                if not profiles:
                    self.logger.info("No profiles available to delete.")
                    put_markdown("No profiles available to delete.")
                    put_buttons([{"label": "Back to Profiles", "value": "back"}], onclick=lambda _: self.list_profiles())
                    return

                profile_options = [{"label": f"[{p['profile id']}] - {p['name']}", "value": p["profile id"]} for p in profiles]
                self.logger.debug(f"Profiles available for deletion: {[p['name'] for p in profiles]}")

                profile_to_delete = input_group(
                    "Select a Profile to Delete",
                    [
                        select("Profile", name="profile_id", options=profile_options),
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
                    self.handle_delete_profile_action(profile_to_delete["actions"], profile_to_delete["profile_id"])
                else:
                    self.logger.info("Profile deletion input group was cancelled or returned empty.")
                    self.list_profiles()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in delete_profile_page: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def handle_delete_profile_action(self, action, profile_id):
        """Executes the deletion of a selected profile or navigates back."""
        self.logger.info(f"Handling delete profile action: {action} for profile ID: {profile_id}")
        try:
            if action == "delete":
                self.logger.info(f"Attempting to delete profile with ID: {profile_id}")
                # Call method on self._project_logic instance
                response = self._project_logic.delete_profile(profile_id)
                if isinstance(response, dict) and "error" in response:
                    error_msg = f"Failed to delete profile '{profile_id}': {response.get('error')}. Details: {response.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
                else:
                    self.logger.info(f"Profile '{profile_id}' deleted successfully.")
                    toast("Profile deleted successfully!", color="success")
                self.list_profiles()
            elif action == "back":
                self.logger.info("User chose to go back from delete profile action.")
                self.list_profiles()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in handle_delete_profile_action for profile ID '{profile_id}': {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def list_dns_records(self):
        """Retrieves and displays a list of all DNS records for the current organization."""
        self.logger.info("Entering list_dns_records function.")
        try:
            # Call method on self._project_logic instance
            dns_records = self._project_logic.list_dns_records()
            with use_scope(self.app_scope_name, clear=True):
                if isinstance(dns_records, dict) and "error" in dns_records:
                    error_msg = f"Failed to retrieve DNS records: {dns_records.get('error')}. Details: {dns_records.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {dns_records.get('status_code', 'Unknown')} - {dns_records.get('error')}: {dns_records.get('details')}", color="error", duration=0)
                    return

                if not dns_records:
                    self.logger.info("No DNS records found for the current organization.")
                    put_markdown("No DNS records found.")
                else:
                    self.logger.info(f"Found {len(dns_records)} DNS records.")
                    put_markdown("### DNS Records with Associated Profiles")
                    put_datatable(dns_records, height="auto")

                put_buttons(
                    [
                        {"label": "Create New DNS Record", "value": "create"},
                        {"label": "Delete DNS Record", "value": "delete"},
                        {"label": "Back to Main Menu", "value": "back"},
                    ],
                    onclick=self.handle_dns_records_action,
                )
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in list_dns_records: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def handle_dns_records_action(self, action):
        """Handles actions triggered from the DNS records management screen."""
        self.logger.info(f"Handling DNS records action: {action}")
        try:
            if action == "create":
                self.create_dns_record_page()
            elif action == "delete":
                self.delete_dns_record_page()
            elif action == "back":
                self.app_main_menu()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in handle_dns_records_action for action '{action}': {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def create_dns_record_page(self):
        """Displays a form to create a new DNS record."""
        self.logger.info("Entering create_dns_record_page function.")
        try:
            with use_scope(self.app_scope_name, clear=True):
                put_markdown("### Create a New DNS Record")
                # Call method on self._project_logic instance
                profiles = self._project_logic.list_profiles()
                if isinstance(profiles, dict) and "error" in profiles:
                    error_msg = f"Failed to retrieve profiles for DNS record creation: {profiles.get('error')}. Details: {profiles.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {profiles.get('status_code', 'Unknown')} - {profiles.get('error')}: {profiles.get('details')}", color="error", duration=0)
                    return

                if not profiles:
                    self.logger.info("No profiles available for DNS record creation. User prompted to create one.")
                    put_markdown("No profiles available. Please create a profile first.")
                    put_buttons([{"label": "Back to DNS Records", "value": "back"}], onclick=lambda _: self.list_dns_records())
                    return

                profile_options = [{"label": f"[{p['profile id']}] {p['name']}", "value": p["profile id"]} for p in profiles]
                self.logger.debug(f"Profiles available for DNS record creation: {[p['name'] for p in profiles]}")

                record_data = input_group(
                    "Create DNS Record",
                    [
                        input("Hostname", name="hostname"),
                        input("Address", name="address"),
                        select("Profile", name="profile_id", options=profile_options),
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
                        self.logger.info("User chose to go back from create DNS record page.")
                        self.list_dns_records()
                        return

                    profile_id = record_data["profile_id"]
                    hostname = record_data["hostname"]
                    address = record_data["address"]
                    self.logger.info(f"Attempting to create DNS record: Hostname='{hostname}', Address='{address}', Profile ID='{profile_id}'")
                    # Call method on self._project_logic instance
                    response = self._project_logic.create_dns_record(profile_id, hostname, address)
                    if isinstance(response, dict) and "error" in response:
                        error_msg = f"Failed to create DNS record: {response.get('error')}. Details: {response.get('details')}"
                        self.logger.error(error_msg)
                        toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
                        return

                    self.logger.info(f"DNS record '{hostname}' created successfully.")
                    toast("DNS record created successfully!", color="success")
                    put_buttons([{"label": "Back to DNS Records", "value": "back"}], onclick=lambda _: self.list_dns_records())
                else:
                    self.logger.info("DNS record creation input group was cancelled or returned empty.")
                    self.list_dns_records()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in create_dns_record_page: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def delete_dns_record_page(self):
        """Displays a list of DNS records from which the user can select one to delete."""
        self.logger.info("Entering delete_dns_record_page function.")
        try:
            with use_scope(self.app_scope_name, clear=True):
                put_markdown("### Delete a DNS Record")
                # Call method on self._project_logic instance
                dns_records = self._project_logic.list_dns_records()
                if isinstance(dns_records, dict) and "error" in dns_records:
                    error_msg = f"Failed to retrieve DNS records for deletion: {dns_records.get('error')}. Details: {dns_records.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {dns_records.get('status_code', 'Unknown')} - {dns_records.get('error')}: {dns_records.get('details')}", color="error", duration=0)
                    return

                if not dns_records:
                    self.logger.info("No DNS records available to delete.")
                    put_markdown("No DNS records available to delete.")
                    put_buttons([{"label": "Back to DNS Records", "value": "back"}], onclick=lambda _: self.list_dns_records())
                    return

                record_options = [{"label": f"[{r['record id']}] - {r['hostname']}", "value": r["record id"]} for r in dns_records]
                self.logger.debug(f"DNS records available for deletion: {[r['hostname'] for r in dns_records]}")

                record_to_delete = input_group(
                    "Select a DNS Record to Delete",
                    [
                        select("DNS Record", name="record_id", options=record_options),
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
                    self.handle_delete_dns_record_action(record_to_delete["actions"], record_to_delete["record_id"])
                else:
                    self.logger.info("DNS record deletion input group was cancelled or returned empty.")
                    self.list_dns_records()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in delete_dns_record_page: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def handle_delete_dns_record_action(self, action, record_id):
        """Executes the deletion of a selected DNS record or navigates back."""
        self.logger.info(f"Handling delete DNS record action: {action} for record ID: {record_id}")
        try:
            if action == "delete":
                self.logger.info(f"Attempting to delete DNS record with ID: {record_id}")
                # Call method on self._project_logic instance
                response = self._project_logic.delete_dns_record(record_id)
                if isinstance(response, dict) and "error" in response:
                    error_msg = f"Failed to delete DNS record '{record_id}': {response.get('error')}. Details: {response.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
                else:
                    self.logger.info(f"DNS record '{record_id}' deleted successfully.")
                    toast("DNS record deleted successfully!", color="success")
                self.list_dns_records()
            elif action == "back":
                self.logger.info("User chose to go back from delete DNS record action.")
                self.list_dns_records()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in handle_delete_dns_record_action for record ID '{record_id}': {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def list_network_assignments(self):
        """Retrieves and displays a list of all network assignments for the current organization."""
        self.logger.info("Entering list_network_assignments function.")
        try:
            # Call method on self._project_logic instance
            assignments = self._project_logic.list_network_assignments()
            with use_scope(self.app_scope_name, clear=True):
                if isinstance(assignments, dict) and "error" in assignments:
                    error_msg = f"Failed to retrieve network assignments: {assignments.get('error')}. Details: {assignments.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {assignments.get('status_code', 'Unknown')} - {assignments.get('error')}: {assignments.get('details')}", color="error", duration=0)
                    return

                if not assignments:
                    self.logger.info("No network assignments found for the current organization.")
                    put_markdown("No network assignments found.")
                else:
                    self.logger.info(f"Found {len(assignments)} network assignments.")
                    put_markdown("### Networks with Associated Profiles")
                    put_datatable(assignments, height="auto")

                put_buttons(
                    [
                        {"label": "Create Network Assignment", "value": "create"},
                        {"label": "Delete Network Assignment", "value": "delete"},
                        {"label": "Back to Main Menu", "value": "back"},
                    ],
                    onclick=self.handle_network_assignments_action,
                )
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in list_network_assignments: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def handle_network_assignments_action(self, action):
        """Handles actions triggered from the network assignments management screen."""
        self.logger.info(f"Handling network assignments action: {action}")
        try:
            if action == "create":
                self.create_network_assignment_page()
            elif action == "delete":
                self.delete_network_assignment_page()
            elif action == "back":
                self.app_main_menu()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in handle_network_assignments_action for action '{action}': {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def create_network_assignment_page(self):
        """Displays a form to create a new network assignment."""
        self.logger.info("Entering create_network_assignment_page function.")
        try:
            with use_scope(self.app_scope_name, clear=True):
                put_markdown("### Create a New Network Assignment")
                # Call method on self._project_logic instance
                profiles = self._project_logic.list_profiles()
                if isinstance(profiles, dict) and "error" in profiles:
                    error_msg = f"Failed to retrieve profiles for network assignment creation: {profiles.get('error')}. Details: {profiles.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {profiles.get('status_code', 'Unknown')} - {profiles.get('error')}: {profiles.get('details')}", color="error", duration=0)
                    return

                if not profiles:
                    self.logger.info("No profiles available for network assignment. User prompted to create one.")
                    put_markdown("No profiles available. Please create a profile first.")
                    put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: self.list_network_assignments())
                    return

                # Access self._api_utils directly for list_networks
                networks = self._api_utils.list_networks()
                if isinstance(networks, dict) and "error" in networks:
                    error_msg = f"Failed to retrieve networks for network assignment creation: {networks.get('error')}. Details: {networks.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {networks.get('status_code', 'Unknown')} - {networks.get('error')}: {networks.get('details')}", color="error", duration=0)
                    return

                if not networks:
                    self.logger.info("No networks available in this organization for assignment.")
                    put_markdown("No networks available in this organization. Cannot create an assignment.")
                    put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: self.list_network_assignments())
                    return

                profile_options = [{"label": f"[{p['profile id']}] {p['name']}", "value": p["profile id"]} for p in profiles]
                network_options = [{"label": f"[{n['id']}] {n['name']}", "value": n["id"]} for n in networks]
                self.logger.debug(f"Profiles available: {[p['name'] for p in profiles]}, Networks available: {[n['name'] for n in networks]}")

                assignment_data = input_group(
                    "Create Network Assignment",
                    [
                        select("Profile", name="profile_id", options=profile_options),
                        select("Network", name="network_id", options=network_options),
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
                        self.logger.info("User chose to go back from create network assignment page.")
                        self.list_network_assignments()
                        return

                    profile_id = assignment_data["profile_id"]
                    network_id = assignment_data["network_id"]
                    self.logger.info(f"Attempting to create network assignment: Network ID='{network_id}', Profile ID='{profile_id}'")
                    # Call method on self._project_logic instance
                    response = self._project_logic.assign_profile_to_network(network_id, profile_id)
                    if isinstance(response, dict) and "error" in response:
                        error_msg = f"Failed to create network assignment (Network ID: {network_id}, Profile ID: {profile_id}): {response.get('error')}. Details: {response.get('details')}"
                        self.logger.error(error_msg)
                        toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
                        put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: self.list_network_assignments())
                        return

                    self.logger.info(f"Network assignment for Network ID '{network_id}' and Profile ID '{profile_id}' created successfully.")
                    toast("Network assignment created successfully!", color="success")
                    put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: self.list_network_assignments())
                else:
                    self.logger.info("Network assignment creation input group was cancelled or returned empty.")
                    self.list_network_assignments()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in create_network_assignment_page: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def delete_network_assignment_page(self):
        """Displays a list of network assignments from which the user can select one to delete."""
        self.logger.info("Entering delete_network_assignment_page function.")
        try:
            with use_scope(self.app_scope_name, clear=True):
                put_markdown("### Delete a Network Assignment")
                # Call method on self._project_logic instance
                assignments = self._project_logic.list_network_assignments()
                if isinstance(assignments, dict) and "error" in assignments:
                    error_msg = f"Failed to retrieve network assignments for deletion: {assignments.get('error')}. Details: {assignments.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {assignments.get('status_code', 'Unknown')} - {assignments.get('error')}: {assignments.get('details')}", color="error", duration=0)
                    return

                if not assignments:
                    self.logger.info("No network assignments available to delete.")
                    put_markdown("No network assignments available to delete.")
                    put_buttons([{"label": "Back to Network Assignments", "value": "back"}], onclick=lambda _: self.list_network_assignments())
                    return

                assignment_options = [
                    {
                        "label": f"[{a['assignment id']}] Network: {a['network id']} {a['network name']} Profile: {a['profile id']} {a['profile name']}",
                        "value": a["assignment id"],
                    }
                    for a in assignments
                ]
                self.logger.debug(f"Network assignments available for deletion: {[a['assignment id'] for a in assignments]}")

                assignment_to_delete = input_group(
                    "Select a Network Assignment to Delete",
                    [
                        select("Network Assignment", name="assignment_id", options=assignment_options),
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
                    self.handle_delete_network_assignment_action(assignment_to_delete["actions"], assignment_to_delete["assignment_id"])
                else:
                    self.logger.info("Network assignment deletion input group was cancelled or returned empty.")
                    self.list_network_assignments()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in delete_network_assignment_page: {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)

    def handle_delete_network_assignment_action(self, action, assignment_id):
        """Executes the deletion of a selected network assignment or navigates back."""
        self.logger.info(f"Handling delete network assignment action: {action} for assignment ID: {assignment_id}")
        try:
            if action == "delete":
                self.logger.info(f"Attempting to delete network assignment with ID: {assignment_id}")
                # Call method on self._project_logic instance
                response = self._project_logic.remove_network_assignment(assignment_id)
                if isinstance(response, dict) and "error" in response:
                    error_msg = f"Failed to delete network assignment '{assignment_id}': {response.get('error')}. Details: {response.get('details')}"
                    self.logger.error(error_msg)
                    toast(f"Error {response.get('status_code', 'Unknown')} - {response.get('error')}: {response.get('details')}", color="error", duration=0)
                else:
                    self.logger.info(f"Network assignment '{assignment_id}' deleted successfully.")
                    toast("Network assignment deleted successfully!", color="success")
                self.list_network_assignments()
            elif action == "back":
                self.logger.info("User chose to go back from delete network assignment action.")
                self.list_network_assignments()
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred in handle_delete_network_assignment_action for assignment ID '{assignment_id}': {e}")
            toast(f"An unexpected error occurred: {e}", color="error", duration=0)