# type: ignore
# project_logic.py
import os
import meraki
import json
import requests
from meraki_tools.my_logging import setup_logger

logger = setup_logger(enable_logging=True, console_logging=True, file_logging=True)

class ProjectLogic:
    def __init__(self, api_utils):
        """
        Initializes the ProjectLogic class with an API_Utils instance.
        This instance will be used for all API interactions within this class.
        """
        self._api_utils = api_utils
        logger.info("ProjectLogic initialized with API_Utils instance.")

    def _make_request(self, method, endpoint, payload=None):
        """
        Generic utility function to make HTTP requests to the Meraki Local DNS API.
        Constructs the URL, sets headers, sends payload, and handles various HTTP/request errors.
        """
        # Access self._api_utils instead of passing api_utils as an argument
        url = f"https://api.meraki.com/api/v1/organizations/{self._api_utils.get_organization_id()}/appliance/dns/local/{endpoint}"
        try:
            logger.info(f"Making {method} request to {url}")
            if payload:
                logger.debug(f"Request Payload: {json.dumps(payload, indent=2)}")

            response = requests.request(
                method, url, headers=self._api_utils.get_headers(), data=json.dumps(payload) if payload else None
            )
            response.raise_for_status()

            if response.text.strip():
                response_json = response.json()
                logger.debug(f"API Response ({response.status_code}): {json.dumps(response_json, indent=2)}")
                return response_json
            else:
                logger.info(f"API Response ({response.status_code}): No content")
                return None

        except requests.exceptions.HTTPError as http_err:
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
            logger.error(f"Connection error occurred during {method} {url}: {conn_err}")
            return {"error": "ConnectionError", "details": str(conn_err)}
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout error occurred during {method} {url}: {timeout_err}")
            return {"error": "TimeoutError", "details": str(timeout_err)}
        except requests.exceptions.RequestException as req_err:
            logger.exception(f"A general request error occurred during {method} {url}: {req_err}")
            return {"error": "RequestException", "details": str(req_err)}
        except Exception as e:
            logger.exception(f"An unexpected error occurred in make_request for {method} {url}: {e}")
            return {"error": "UnexpectedError", "details": str(e)}

    def list_profiles(self):
        """
        Fetches all local DNS profiles and enriches them with associated network information.
        """
        logger.info("Attempting to list profiles with associated networks.")
        try:
            profiles_response = self._make_request("GET", "profiles")
            if isinstance(profiles_response, dict) and "error" in profiles_response:
                logger.error(f"Error fetching profiles: {profiles_response.get('details')}")
                return profiles_response

            if not profiles_response or "items" not in profiles_response:
                logger.info("No profiles found.")
                return []

            profiles_data = profiles_response["items"]
            logger.debug(f"Fetched {len(profiles_data)} raw profiles.")

            # Call the method on self
            assignments = self.list_network_assignments()
            if isinstance(assignments, dict) and "error" in assignments:
                logger.error(f"Error fetching network assignments for profiles: {assignments.get('details')}")
                return assignments

            if not assignments:
                logger.info("No network assignments found for profiles.")
                assignments = []

            # Access self._api_utils for list_networks
            networks = self._api_utils.list_networks()
            if isinstance(networks, dict) and "error" in networks:
                logger.error(f"Error fetching networks for profiles: {networks.get('details')}")
                return networks

            network_map = ({network["id"]: network["name"] for network in networks} if networks else {})
            logger.debug(f"Created network map with {len(network_map)} entries.")

            profile_to_network = {}
            for assignment in assignments:
                profile_id = assignment.get("profile id")
                network_id = assignment.get("network id")
                if profile_id and network_id:
                    profile_to_network[profile_id] = {
                        "network id": network_id,
                        "network name": network_map.get(network_id, "[unknown]"),
                    }
            logger.debug(f"Mapped {len(profile_to_network)} profiles to networks.")

            table_data = []
            for profile in profiles_data:
                profile_id = profile.get("profileId")
                profile_name = profile.get("name")

                if profile_id in profile_to_network:
                    network_info = profile_to_network[profile_id]
                    table_data.append(
                        {
                            "profile id": profile_id,
                            "name": profile_name,
                            "network id": network_info.get("network id"),
                            "network name": network_info.get("network name"),
                        }
                    )
                else:
                    table_data.append(
                        {
                            "profile id": profile_id,
                            "name": profile_name,
                            "network id": "[unassigned]",
                            "network name": "[unassigned]",
                        }
                    )
            logger.info(f"Successfully formatted {len(table_data)} profiles for display.")
            return table_data
        except Exception as e:
            logger.exception(f"An unexpected error occurred in list_profiles: {e}")
            return {"error": "UnexpectedError", "details": str(e)}

    def create_profile(self, profile_name):
        """Creates a new local DNS profile with the given name."""
        logger.info(f"Attempting to create profile with name: '{profile_name}'")
        payload = {"name": profile_name}
        response = self._make_request("POST", "profiles", payload)

        if isinstance(response, dict) and "error" in response:
            logger.error(f"Failed to create profile '{profile_name}': {response.get('details')}")
            return response
        else:
            profile_id = response.get("profileId")
            name = response.get("name")
            logger.info(f"Profile '{name}' (ID: {profile_id}) created successfully.")
            return {
                "profile id": profile_id,
                "name": name,
            }

    def delete_profile(self, profile_id):
        """Deletes a local DNS profile by its ID."""
        logger.info(f"Attempting to delete profile with ID: '{profile_id}'")
        response = self._make_request("DELETE", f"profiles/{profile_id}")

        if isinstance(response, dict) and "error" in response:
            logger.error(f"Failed to delete profile '{profile_id}': {response.get('details')}")
        else:
            logger.info(f"Profile '{profile_id}' deleted successfully.")
        return response

    def create_dns_record(self, profile_id, hostname, address):
        """
        Creates a new local DNS record (hostname to IP address) associated with a specific profile.
        """
        logger.info(f"Attempting to create DNS record: Hostname='{hostname}', Address='{address}', Profile ID='{profile_id}'")
        payload = {
            "hostname": hostname,
            "address": address,
            "profile": {"id": profile_id},
        }
        response = self._make_request("POST", "records", payload)

        if isinstance(response, dict) and "error" in response:
            logger.error(f"Failed to create DNS record '{hostname}' for profile '{profile_id}': {response.get('details')}")
        else:
            record_id = response.get("recordId")
            logger.info(f"DNS record '{hostname}' (ID: {record_id}) created successfully for profile '{profile_id}'.")
        return response

    def list_dns_records(self):
        """Fetches and formats a list of all local DNS records for the current organization."""
        logger.info("Attempting to list DNS records.")
        response = self._make_request("GET", "records")

        if isinstance(response, dict) and "error" in response:
            logger.error(f"Error fetching DNS records: {response.get('details')}")
            return response

        if response and "items" in response:
            table_data = [
                {
                    "record id": record.get("recordId"),
                    "hostname": record.get("hostname"),
                    "address": record.get("address"),
                    "profile id": record.get("profile", {}).get("id"),
                }
                for record in response["items"]
            ]
            logger.info(f"Successfully formatted {len(table_data)} DNS records for display.")
            return table_data
        logger.info("No DNS records found or response was empty.")
        return []

    def delete_dns_record(self, record_id):
        """Deletes a local DNS record by its ID."""
        logger.info(f"Attempting to delete DNS record with ID: '{record_id}'")
        response = self._make_request("DELETE", f"records/{record_id}")

        if isinstance(response, dict) and "error" in response:
            logger.error(f"Failed to delete DNS record '{record_id}': {response.get('details')}")
        else:
            logger.info(f"DNS record '{record_id}' deleted successfully.")
        return response

    def assign_profile_to_network(self, network_id, profile_id):
        """Assigns a local DNS profile to a specific network."""
        logger.info(f"Attempting to assign profile '{profile_id}' to network '{network_id}'.")
        payload = {
            "items": [
                {"network": {"id": network_id}, "profile": {"id": profile_id}},
            ]
        }
        response = self._make_request("POST", "profiles/assignments/bulkCreate", payload)

        if isinstance(response, dict) and "error" in response:
            logger.error(f"Failed to assign profile '{profile_id}' to network '{network_id}': {response.get('details')}")
        else:
            logger.info(f"Profile '{profile_id}' successfully assigned to network '{network_id}'.")
        return response

    def list_network_assignments(self):
        """
        Fetches all network assignments and enriches them with network and profile names.
        """
        logger.info("Attempting to list network assignments.")
        try:
            # Access self._api_utils for list_networks
            networks_response = self._api_utils.list_networks()
            if isinstance(networks_response, dict) and "error" in networks_response:
                logger.error(f"Error fetching networks for assignments: {networks_response.get('details')}")
                return networks_response

            network_map = {network["id"]: network["name"] for network in networks_response}
            logger.debug(f"Created network map with {len(network_map)} entries for assignments.")

            profiles_response = self._make_request("GET", "profiles")
            if isinstance(profiles_response, dict) and "error" in profiles_response:
                logger.error(f"Error fetching profiles for assignments: {profiles_response.get('details')}")
                return profiles_response

            profiles = profiles_response.get("items", []) if profiles_response else []
            profile_map = {profile["profileId"]: profile["name"] for profile in profiles}
            logger.debug(f"Created profile map with {len(profile_map)} entries for assignments.")

            assignments_response = self._make_request("GET", "profiles/assignments")
            if isinstance(assignments_response, dict) and "error" in assignments_response:
                logger.error(f"Error fetching raw assignments: {assignments_response.get('details')}")
                return assignments_response

            if assignments_response and "items" in assignments_response:
                table_data = []
                for assignment in assignments_response["items"]:
                    network_id = assignment.get("network", {}).get("id")
                    profile_id = assignment.get("profile", {}).get("id")

                    table_data.append(
                        {
                            "assignment id": assignment.get("assignmentId"),
                            "network id": network_id,
                            "network name": network_map.get(network_id, "[unknown]"),
                            "profile id": profile_id,
                            "profile name": profile_map.get(profile_id, "[unknown]"),
                        }
                    )
                logger.info(f"Successfully formatted {len(table_data)} network assignments for display.")
                return table_data
            logger.info("No network assignments found or response was empty.")
            return []
        except Exception as e:
            logger.exception(f"An unexpected error occurred in list_network_assignments: {e}")
            return {"error": "UnexpectedError", "details": str(e)}

    def remove_network_assignment(self, assignment_id):
        """Removes a network assignment by its assignment ID."""
        logger.info(f"Attempting to remove network assignment with ID: '{assignment_id}'")
        payload = {"items": [{"assignmentId": assignment_id}]}
        response = self._make_request("POST", "profiles/assignments/bulkDelete", payload)

        if isinstance(response, dict) and "error" in response:
            logger.error(f"Failed to remove network assignment '{assignment_id}': {response.get('details')}")
        else:
            logger.info(f"Network assignment '{assignment_id}' removed successfully.")
        return response