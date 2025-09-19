import logging
import os

log_entries = []

class ListHandler(logging.Handler):
    """Custom logging handler that appends log messages to a shared list."""
    def emit(self, record):
        log_entry = self.format(record)
        log_entries.append(log_entry)

def setup_logger(enable_logging=True, console_logging=False, file_logging=False):
    logger = logging.getLogger('app_logger')
    logger.setLevel(logging.INFO)

    # Remove all existing handlers
    logger.handlers.clear()

    if not enable_logging:
        # Disable all logging by setting level to CRITICAL+1
        logger.setLevel(logging.CRITICAL + 1)
        return logger

    # Modified formatter to include %(filename)s
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(message)s')

    # Add ListHandler to capture logs in list
    list_handler = ListHandler()
    list_handler.setFormatter(formatter)
    logger.addHandler(list_handler)

    if console_logging:
        # Add console handler to log to console in parallel
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if file_logging:
        # Add FileHandler to log to 'app.log'
        # 'w' mode truncates the file if it exists, starting a new log file
        file_handler = logging.FileHandler('app.log', mode='w')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Example Usage:
if __name__ == "__main__":
    # --- Scenario 1: Basic logging with list and console ---
    print("--- Scenario 1: Basic logging with list and console ---")
    log_entries.clear() # Clear previous logs for fresh test
    logger1 = setup_logger(enable_logging=True, console_logging=True, file_logging=False)
    logger1.info("This is an info message for scenario 1.")
    logger1.warning("This is a warning message for scenario 1.")
    print(f"Log entries in list (Scenario 1): {log_entries}")
    print("-" * 50)

    # --- Scenario 2: Logging to file, list, and console ---
    print("--- Scenario 2: Logging to file, list, and console ---")
    log_entries.clear() # Clear previous logs for fresh test
    # Ensure app.log is created/overwritten for this scenario
    logger2 = setup_logger(enable_logging=True, console_logging=True, file_logging=True)
    logger2.info("This is the first info message for scenario 2.")
    logger2.debug("This debug message should not appear (level is INFO).")
    logger2.error("An error occurred in scenario 2.")
    print(f"Log entries in list (Scenario 2): {log_entries}")
    print("Check 'app.log' file in the current directory for file logging.")
    print("-" * 50)

    # --- Scenario 3: Disable all logging ---
    print("--- Scenario 3: Disable all logging ---")
    log_entries.clear() # Clear previous logs for fresh test
    logger3 = setup_logger(enable_logging=False)
    logger3.info("This message should not be logged anywhere.")
    print(f"Log entries in list (Scenario 3): {log_entries}")
    print("-" * 50)

    # --- Scenario 4: Re-enabling logging with file, demonstrating file overwrite ---
    print("--- Scenario 4: Re-enabling logging with file (demonstrates overwrite) ---")
    log_entries.clear() # Clear previous logs for fresh test
    # Calling setup_logger again with file_logging=True will truncate app.log
    logger4 = setup_logger(enable_logging=True, console_logging=False, file_logging=True)
    logger4.info("This is a new log message for scenario 4.")
    logger4.critical("Critical issue in scenario 4!")
    print(f"Log entries in list (Scenario 4): {log_entries}")
    print("Check 'app.log' again. It should only contain logs from Scenario 4 now.")
    print("-" * 50)

    # Clean up the log file created for demonstration
    if os.path.exists('app.log'):
        print("Removing 'app.log' for cleanup.")
        os.remove('app.log')