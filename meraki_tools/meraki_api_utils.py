# meraki_api_utils.py (MODIFIED)
import os
import meraki
from my_logging import setup_logger
from typing import Optional, Union, Any, List, Dict, Tuple

logger = setup_logger(enable_logging=True, console_logging=True, file_logging=True)

var="new change"

class MerakiAPIWrapper: # <--- NEW CLASS DEFINITION
    def __init__(self, initial_api_key: Optional[str] = None, enable_caching: bool = False):
        self._api_key: Optional[str] = None
        self._organization_id: Optional[str] = None
        self._organization_name: Optional[str] = None
        self._network_id: Optional[str] = None
        self._network_name: Optional[str] = None
        self._enable_caching: bool = enable_caching

        self._dashboard: Optional[meraki.DashboardAPI] = None
        self._organizations_cache: Optional[List[Dict[str, Any]]] = None
        self._networks_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None

        # Call the setter method to initialize API key, handling env var fallback
        self.set_api_key(initial_api_key, source="initialization")

        # Global variable to store the required application setup parameters (now instance-specific)
        self._required_app_setup_param: Dict[str, bool] = {}


    # --- Get/Set and Is_Not_Null functions for API_KEY ---
    def set_api_key(self, api_key: Optional[str] = None, source: Optional[str] = None) -> None:
        """
        Sets the instance's API_KEY. Prioritizes the passed argument, then environment variable.
        Logs activity but avoids logging the key itself for security.
        """
        if api_key:
            self._api_key = api_key
            logger.info(f"API key set from provided argument. Source: {source if source else 'direct_call'}")
        else:
            env_api_key = os.getenv("MK_CSM_KEY")
            if env_api_key:
                self._api_key = env_api_key
                logger.info("API key loaded from environment variable (MK_CSM_KEY).")
            else:
                self._api_key = None
                logger.error("Meraki API Key (MK_CSM_KEY) not found in environment variables or passed parameter.")
        
        if self._api_key:
            logger.debug("API_KEY updated. Initializing Meraki Dashboard API client.")
            # Re-initialize dashboard if API key is set or changed
            self._dashboard = meraki.DashboardAPI(self._api_key, suppress_logging=True)
        else:
            logger.warning("API_KEY is currently not set. Dashboard API client not initialized.")
            self._dashboard = None # Ensure dashboard is None if key is not set

    def is_api_key_set(self) -> bool:
        """
        Checks if the instance's API_KEY is set (not None or empty).
        """
        return self._api_key is not None and self._api_key != ""

    def get_headers(self) -> Dict[str, str]:
        """Returns the HTTP headers for Meraki API requests using the instance's API key."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # --- Get/Set and Is_Not_Null functions for ORGANIZATION_ID and ORGANIZATION_NAME ---
    def get_organization_id(self) -> Optional[str]:
        """Retrieves the currently selected instance's ORGANIZATION_ID."""
        return self._organization_id

    def set_organization_id(self, organization_id: str, organization_name: Optional[str] = None) -> None:
        """Sets the instance's ORGANIZATION_ID and optionally ORGANIZATION_NAME."""
        if organization_id:
            self._organization_id = organization_id
            logger.info(f"Organization id set to: {self._organization_id}")
            if organization_name:
                self._organization_name = organization_name
                logger.info(f"Organization name set to: {self._organization_name}")
            else:
                logger.debug("Organization name not provided when setting id.")
        else:
            logger.warning("Attempted to set an empty or None Organization id.")

    def get_organization_name(self) -> Optional[str]:
        """Retrieves the currently selected instance's ORGANIZATION_NAME."""
        return self._organization_name

    def is_organization_id_set(self) -> bool:
        """Checks if the instance's ORGANIZATION_ID is set (not None or empty)."""
        return self._organization_id is not None and self._organization_id != ""

    # --- Get/Set and Is_Not_Null functions for NETWORK_ID and NETWORK_NAME ---
    def get_network_id(self) -> Optional[str]:
        """Retrieves the currently selected instance's NETWORK_ID."""
        return self._network_id

    def set_network_id(self, network_id: str, network_name: Optional[str] = None) -> None:
        """Sets the instance's NETWORK_ID and optionally NETWORK_NAME."""
        if network_id:
            self._network_id = network_id
            logger.info(f"Network ID set to: {self._network_id}")
            if network_name:
                self._network_name = network_name
                logger.info(f"Network name set to: {self._network_name}")
            else:
                logger.debug("Network name not provided when setting id.")
        else:
            logger.warning("Attempted to set an empty or None Network id.")

    def get_network_name(self) -> Optional[str]:
        """Retrieves the currently selected instance's NETWORK_NAME."""
        return self._network_name

    def is_network_id_set(self) -> bool:
        """Checks if the instance's NETWORK_ID is set (not None or empty)."""
        return self._network_id is not None and self._network_id != ""

    # --- Meraki Dashboard API and Caching Functions ---
    def get_dashboard(self) -> Optional[meraki.DashboardAPI]:
        """
        Returns the singleton instance of the Meraki Dashboard API client for this wrapper.
        Initializes it if not already done.
        """
        if self._dashboard is None:
            if not self._api_key:
                logger.error("Cannot initialize Meraki Dashboard API: API Key is not set.")
                return None
            logger.info("Initializing Meraki Dashboard API instance.")
            try:
                self._dashboard = meraki.DashboardAPI(self._api_key, suppress_logging=True)
                logger.debug("Meraki Dashboard API instance created successfully.")
            except Exception as e:
                logger.exception(f"Failed to initialize Meraki Dashboard API: {e}")
                raise # Re-raise to indicate a critical setup failure
        else:
            logger.debug("Using existing Meraki Dashboard API instance.")
        return self._dashboard

    def _get_organizations(self, use_cache: bool = False) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetches the list of organizations from the Meraki API or serves from cache.
        """
        organizations_data: Union[List[Dict[str, Any]], Dict[str, Any]]

        should_attempt_cache_read = use_cache and self._enable_caching

        if should_attempt_cache_read and self._organizations_cache is not None:
            logger.info("Using cached organizations data.")
            organizations_data = self._organizations_cache
        else:
            # ... (your existing logic, adapted to use self._dashboard, self._enable_caching, self._organizations_cache)
            dashboard = self.get_dashboard()
            if not dashboard:
                return {"error": "DashboardAPIError", "details": "Meraki Dashboard API not initialized."}
            try:
                fetched_data = dashboard.organizations.getOrganizations()
                if self._enable_caching:
                    self._organizations_cache = fetched_data
                    logger.info(f"Successfully fetched {len(fetched_data)} organizations and stored in cache.")
                else:
                    logger.info(f"Successfully fetched {len(fetched_data)} organizations (not cached).")
                organizations_data = fetched_data
            except meraki.APIError as e:
                logger.error(f"Meraki API error fetching organizations: {e.status} - {e.message}")
                if self._enable_caching:
                    self._organizations_cache = []
                return {"error": "MerakiAPIError", "details": e.message, "status_code": e.status}
            except Exception as e:
                logger.exception(f"An unexpected error occurred while fetching organizations: {e}")
                if self._enable_caching:
                    self._organizations_cache = []
                return {"error": "UnexpectedError", "details": str(e)}
        return organizations_data


    def _get_networks(self, organization_id: Optional[str] = None, use_cache: bool = False) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetches the list of networks for the specified ORGANIZATION_ID from Meraki API or cache.
        """
        current_organization_id = organization_id if organization_id is not None else self.get_organization_id()

        if not current_organization_id:
            logger.warning("Attempted to get networks without a selected organization id (neither passed nor global).")
            return {"error": "NoOrganizationSelected", "details": "Please select an organization first."}

        networks_data: Union[List[Dict[str, Any]], Dict[str, Any]]

        if self._networks_cache is None:
            self._networks_cache = {}

        should_attempt_cache_read = use_cache and self._enable_caching

        if should_attempt_cache_read and current_organization_id in self._networks_cache:
            logger.info(f"Using cached networks data for organization {current_organization_id}.")
            networks_data = self._networks_cache[current_organization_id]
        else:
            # ... (your existing logic, adapted to use self._dashboard, self._enable_caching, self._networks_cache)
            dashboard = self.get_dashboard()
            if not dashboard:
                return {"error": "DashboardAPIError", "details": "Meraki Dashboard API not initialized."}
            try:
                fetched_data = dashboard.organizations.getOrganizationNetworks(
                    current_organization_id
                )
                if self._enable_caching:
                    self._networks_cache[current_organization_id] = fetched_data
                    logger.info(f"Successfully fetched {len(fetched_data)} networks for organization {current_organization_id} and stored in cache.")
                else:
                    logger.info(f"Successfully fetched {len(fetched_data)} networks for organization {current_organization_id} (not cached).")
                networks_data = fetched_data
            except meraki.APIError as e:
                logger.error(f"Meraki API error fetching networks for organization {current_organization_id}: {e.status} - {e.message}")
                if self._enable_caching:
                    self._networks_cache[current_organization_id] = []
                return {"error": "MerakiAPIError", "details": e.message, "status_code": e.status}
            except Exception as e:
                logger.exception(
                    f"An unexpected error occurred while fetching networks for organization {current_organization_id}: {e}"
                )
                if self._enable_caching:
                    self._networks_cache[current_organization_id] = []
                return {"error": "UnexpectedError", "details": str(e)}
        return networks_data


    def list_organizations(self, use_cache: bool = False) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetches and formats a list of Meraki organizations for display.
        """
        logger.info("Attempting to get organizations.")
        
        raw_response = self._get_organizations(use_cache=use_cache)

        if isinstance(raw_response, dict) and "error" in raw_response:
            logger.error(f"Error getting organizations: {raw_response.get('details')}")
            return raw_response
        
        if isinstance(raw_response, list):
            organizations_data: List[Dict[str, Any]] = raw_response

            if organizations_data:
                table_data: List[Dict[str, Any]] = [
                    {
                        "id": org.get("id"),
                        "name": org.get("name"),
                        "url": org.get("url"),
                        "api enabled": org.get("api", {}).get("enabled", False),
                        "licensing model": org.get("licensing", {}).get("model"),
                    }
                    for org in organizations_data
                ]
                logger.info(f"Successfully formatted {len(table_data)} organizations for display.")
                return table_data
            else:
                logger.info("No organizations found or response was empty.")
                return []
        else:
            logger.error(f"Unexpected response type from _get_organizations(): {type(raw_response)}. Response: {raw_response}")
            return {"error": "UnexpectedReturnType", "details": "Internal function returned an unexpected type."}

    def list_networks(self, organization_id: Optional[str] = None, use_cache: bool = False) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetches and formats a list of networks for the current or specified organization for display.
        """
        target_organization_id = organization_id if organization_id is not None else self.get_organization_id()
        logger.info(f"Attempting to list networks for organization id: {target_organization_id}")
        
        response = self._get_networks(organization_id=organization_id, use_cache=use_cache)

        if isinstance(response, dict) and "error" in response:
            logger.error(f"Error getting networks: {response.get('details')}")
            return response
        elif isinstance(response, list):
            if not response:
                logger.info("No networks found for the selected organization.")
                return []
            
            table_data: List[Dict[str, Any]] = [
                {
                    "id": network.get("id"),
                    "name": network.get("name"),
                    "yype": network.get("type"),
                    "time zone": network.get("timeZone"),
                    "tags": ", ".join(network.get("tags", [])),
                }
                for network in response
            ]
            logger.info(f"Successfully formatted {len(table_data)} networks for display.")
            return table_data
        else:
            logger.error(f"Unexpected response type from _get_networks(): {type(response)}. Response: {response}")
            return []

    # --- New functionality: Parameter setup and checking ---
    def _check_required_parameter_order(self, required_params: Dict[str, bool]) -> bool:
        """
        Checks if the required parameters are ordered correctly (api_key -> organization_id -> network_id).
        If a later parameter is required, all preceding ones must also be required.
        """
        api_key_required = required_params.get("api_key", False)
        organization_id_required = required_params.get("organization_id", False)
        network_id_required = required_params.get("network_id", False)

        if organization_id_required and not api_key_required:
            logger.error("Invalid required_app_setup_parm: 'organization_id' cannot be required if 'api_key' is not.")
            return False
        if network_id_required and (not api_key_required or not organization_id_required):
            logger.error("Invalid required_app_setup_parm: 'network_id' cannot be required if 'api_key' or 'organization_id' is not.")
            return False
        return True

    def setup_application_parameters(
        self,
        required_app_setup_parm: Dict[str, bool],
        app_setup_param: Optional[Dict[str, str]] = None,
        enable_caching: Optional[bool] = None # Now optional, uses instance's default if None
    ) -> bool:
        """
        Configures application parameters based on requirements and provided values.
        """
        logger.info("Attempting to set up application parameters.")

        if enable_caching is not None: # Update instance caching setting if provided
            self._enable_caching = enable_caching
        logger.info(f"Application caching enabled: {self._enable_caching}")

        if not self._check_required_parameter_order(required_app_setup_parm):
            return False

        self._required_app_setup_param = required_app_setup_parm

        effective_params: Dict[str, str] = app_setup_param if app_setup_param is not None else {}

        if required_app_setup_parm.get("api_key"):
            api_key_val = effective_params.get("api_key")
            self.set_api_key(api_key_val, source="effective_params_or_env")
            
            if not self.is_api_key_set():
                logger.error("Failed to set API Key, which is required.")
                return False
        else:
            logger.debug("API Key is not required by setup parameters.")

        if required_app_setup_parm.get("organization_id"):
            if not self.is_api_key_set():
                logger.error("Cannot set Organization id: API Key is not set, but is a prerequisite.")
                return False
            
            organization_id_val = effective_params.get("organization_id")
            org_name_val = effective_params.get("org_name")
            
            if organization_id_val:
                self.set_organization_id(organization_id_val, org_name_val)
            else:
                logger.error("Organization id is required but not provided in effective parameters.")
                return False
            
            if not self.is_organization_id_set():
                logger.error("Failed to set Organization id, which is required.")
                return False
        else:
            logger.debug("Organization id is not required by setup parameters.")

        if required_app_setup_parm.get("network_id"):
            if not self.is_api_key_set() or not self.is_organization_id_set():
                logger.error("Cannot set Network id: API Key or Organization id not set, but are prerequisites.")
                return False

            network_id_val = effective_params.get("network_id")
            network_name_val = effective_params.get("net_name")

            if network_id_val:
                self.set_network_id(network_id_val, network_name_val)
            else:
                logger.error("Network id is required but not provided in effective parameters.")
                return False
            
            if not self.is_network_id_set():
                logger.error("Failed to set Network id, which is required.")
                return False
        else:
            logger.debug("Network id is not required by setup parameters.")

        logger.info("Application parameter setup complete.")
        return True

    def check_current_parameters_status(self) -> Tuple[bool, List[str]]:
        """
        Checks if all currently required parameters are set based on the instance's settings.
        """
        if not self._required_app_setup_param:
            logger.warning("No required application setup parameters have been defined yet. Call setup_application_parameters first.")
            return False, ["No required parameters defined"]

        required_app_setup_parm = self._required_app_setup_param
        missing_params: List[str] = []

        if not self._check_required_parameter_order(required_app_setup_parm):
            return False, ["Invalid required_app_setup_parm configuration stored in instance"]

        if required_app_setup_parm.get("api_key") and not self.is_api_key_set():
            missing_params.append("API_KEY")
        
        if required_app_setup_parm.get("organization_id") and not self.is_organization_id_set():
            missing_params.append("ORGANIZATION_ID")
        
        if required_app_setup_parm.get("network_id") and not self.is_network_id_set():
            missing_params.append("NETWORK_ID")
        
        if missing_params:
            logger.error(f"Missing required parameters: {', '.join(missing_params)}")
            return False, missing_params
        
        logger.info("All currently required parameters are set.")
        return True, []

    def get_current_app_params(self) -> Dict[str, Dict[str, str]]:
        """
        Returns a dictionary of current application parameters based on the instance's settings.
        """
        required_app_setup_param = self._required_app_setup_param

        params: Dict[str, Dict[str, str]] = {}

        if required_app_setup_param.get("api_key", False):
            api_key = self._api_key
            masked_api_key = "*" * max(len(api_key) - 4, 0) + api_key[-4:] if api_key else "N/A"
            params["api_key"] = {
                "value": masked_api_key,
                "label": "API Key"
            }

        if required_app_setup_param.get("organization_id", False):
            organization_id = self.get_organization_id() or "N/A"
            organization_name = self.get_organization_name() or "N/A"
            params["organization_id"] = {
                "value": organization_id,
                "label": "Organization ID"
            }
            params["organization_name"] = {
                "value": organization_name,
                "label": "Organization Name"
            }

        if required_app_setup_param.get("network_id", False):
            network_id = self.get_network_id() or "N/A"
            network_name = self.get_network_name() or "N/A"
            params["network_id"] = {
                "value": network_id,
                "label": "Network ID"
            }
            params["network_name"] = {
                "value": network_name,
                "label": "Network Name"
            }

        return params