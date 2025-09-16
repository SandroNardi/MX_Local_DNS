from pywebio.output import put_html, put_buttons, put_scope, use_scope, put_markdown, put_collapse, put_scrollable, put_file, popup # Import necessary PyWebIO output functions.
from pywebio.session import download, run_js # Import PyWebIO session functions for download and JavaScript execution.
import threading # For managing background threads.
import time # For time-related operations, like sleep.
import io # For in-memory text streams (used for CSV generation).
import csv # For CSV file operations.
import os # For interacting with the operating system, like file paths.
from my_logging import setup_logger, log_entries # Custom logging setup and log entry storage.
import about # Module containing application information.
import local_dns_logic as logic # Core application logic for DNS and network management.

# Initialize logger for the module, enabling console output.
logger = setup_logger(enable_logging=True, console_logging=True, file_logging=True)

# --- Global variables for log display management ---
last_displayed_log_index = 0 # Tracks the index of the last log entry displayed in the UI.
log_entries_lock = threading.Lock() # A lock to ensure thread-safe access to log_entries.

# Configuration for navigation buttons in the header.
nav_buttons = [
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

def show_current_params_popup(get_params_func=None):
    """
    Displays a 'Current Parameters' popup showing the application's current configuration.
    Can take an optional function to retrieve parameters.
    """
    logger.info("Displaying 'Current Parameters' popup.")
    try:
        if get_params_func is None:
            # Fallback to default logic module function if no custom function provided.
            params = logic.get_current_params()
        else:
            params = get_params_func()

        with popup("Current Parameters"):
            put_markdown("## Application Parameters")
            for key, value in params.items():
                put_markdown(f"**{key}:** `{value}`") # Display each parameter.
        logger.debug("'Current Parameters' popup displayed.")
    except Exception as e:
        logger.exception(f"An error occurred while displaying current parameters current parameters: {e}")

def restart_app_client_side():
    """
    Triggers a client-side page reload, effectively restarting the PyWebIO application.
    """
    logger.warning("Initiating client-side application restart (page reload).")
    run_js("location.reload()") # Executes JavaScript to reload the browser page.

def render_header(project="MX Local DNS Application", get_current_params_func=None):
    """
    Renders the application's header, including a project title, navigation buttons,
    and a collapsible log display.
    """
    logger.info(f"Rendering header for project: {project}")
    try:
        # Top Gradient Bar (for visual styling).
        put_html('<div class="top-gradient-bar"></div>')
        logger.debug("Rendered top gradient bar.")
        # Top Bar with project title.
        put_html(f'<div class="top-bar">{project}</div>')
        logger.debug(f"Rendered top bar with project name: {project}.")
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
                        show_current_params_popup(get_current_params_func)
                    else:
                        put_markdown(f"**Nav button clicked:** {btn_value}") # Fallback for other buttons.
                put_buttons(nav_buttons, onclick=handle_nav_click)
            logger.debug(f"Rendered navigation buttons: {[btn['label'] for btn in nav_buttons]}.")

        # Initial content displayed in the 'app' scope.
        with use_scope('app', clear=True):
            put_markdown(f"# Welcome to {project}")
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