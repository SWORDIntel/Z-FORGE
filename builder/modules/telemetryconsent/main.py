#!/usr/bin/env python3

import libcalamares
from libcalamares import utils
import os

# Path for the temporary override file for testing consent
OVERRIDE_FILE_PATH = "/tmp/telemetry_consent_override"

def pretty_name():
    """
    Returns a user-friendly name for the module.
    Can be localized.
    """
    # TODO: Add localization if Calamares supports it well for Python module names
    return "Telemetry Consent"

def run():
    """
    The main execution function for a Calamares view module (Python interface).
    This function is called when Calamares displays the view.
    """
    utils.log(f"TelemetryConsent module run() called.")

    # Set a default value for consent in globalstorage if not already set.
    # This ensures that if the user skips this page or if there's an issue,
    # we have a defined (safe) default.
    current_consent = libcalamares.globalstorage.value("telemetry_consent_given")
    if current_consent is None:
        utils.debug("telemetry_consent_given not found in globalstorage, defaulting to False.")
        libcalamares.globalstorage.insert("telemetry_consent_given", False)
    else:
        utils.debug(f"telemetry_consent_given already in globalstorage: {current_consent}")

    # In a real Python view module that uses QML, this `run` function might also:
    # 1. Expose Python objects or functions to the QML context.
    # 2. Load initial data to be displayed in the QML view.
    # For this subtask, the QML is mostly static, and consent is read in `leave()`.

    return None # View modules typically don't return a job result from run()

def leave(current_view_step_id: str) -> bool:
    """
    Called by Calamares when the user clicks "Next" and leaves this view.
    `current_view_step_id` is the ID of the current step in the view sequence.

    This is where we would typically read the state of the QML CheckBox.
    """
    utils.log(f"TelemetryConsent module leave() called from step_id: {current_view_step_id}")

    consent_value = False # Default to False

    # --- QML State Reading Simulation ---
    # In a real scenario with QML, you would access the CheckBox's `checked` property.
    # This might involve:
    # - Getting the QQuickView instance from Calamares (if possible for Python views).
    # - Finding the QML item by its objectName (e.g., `consentCheckBox`).
    # - Reading its `checked` property.
    # Example (conceptual, actual API may differ):
    #   qml_view = libcalamares.ui.current_qml_view() # Fictional API
    #   if qml_view:
    #       consent_checkbox_qml_object = qml_view.findChild(QtCore.QObject, "consentCheckBox")
    #       if consent_checkbox_qml_object:
    #           consent_value = consent_checkbox_qml_object.property("checked")
    #       else:
    #           utils.warning("Could not find consentCheckBox QML object.")
    #   else:
    #       utils.warning("Could not get QML view reference.")
    utils.debug("Placeholder: This is where QML state (consentCheckBox.checked) would be read.")

    # **Temporary override for subtask testing:**
    # Check if the override file exists.
    if os.path.exists(OVERRIDE_FILE_PATH):
        try:
            with open(OVERRIDE_FILE_PATH, "r") as f:
                content = f.read().strip().lower()
            if content == "true":
                consent_value = True
                utils.log(f"Consent override: Read 'true' from {OVERRIDE_FILE_PATH}, setting consent to True.")
            elif content == "false":
                consent_value = False
                utils.log(f"Consent override: Read 'false' from {OVERRIDE_FILE_PATH}, setting consent to False.")
            else:
                utils.warning(f"Invalid content in {OVERRIDE_FILE_PATH}: '{content}'. Using default consent ({consent_value}).")
            # Clean up the override file after reading
            # os.remove(OVERRIDE_FILE_PATH)
            # utils.debug(f"Removed override file: {OVERRIDE_FILE_PATH}")
        except Exception as e:
            utils.error(f"Error reading or processing override file {OVERRIDE_FILE_PATH}: {e}. Using default consent ({consent_value}).")
    else:
        # If no override file, we rely on the default set in run() or if QML could change it (which it can't directly in this sim)
        # For this simulation, if QML is purely visual, the default from run() (False) will persist unless override file is used.
        # In a real scenario, the QML interaction would directly update a Python-accessible property or Calamares internal state.
        # Here, we'll just use the default `consent_value = False` if no override.
        # To make it slightly more interactive for testing *without* the file:
        # We can assume if globalstorage still holds the default 'False' from run(), no QML interaction happened.
        # If it was somehow changed by another mechanism (not possible here), we'd use that.
        # For this simulation, it will almost always be 'False' unless the override file is used.
        # We can re-fetch from globalstorage if we imagine QML could have modified it via some binding.
        # However, current Calamares Python QML views don't easily allow QML to call back and set globalstorage directly.
        # It's usually Python reading from QML in leave().

        # For this simulation, we'll just stick to the `consent_value` which is `False` by default
        # or set by the override file. If QML could truly set it, we'd read that.
        # Let's assume the default in globalstorage is the "current state" if QML didn't touch it.
        current_gs_consent = libcalamares.globalstorage.value("telemetry_consent_given")
        if current_gs_consent is not None : # Should have been set by run()
            consent_value = current_gs_consent
            utils.debug(f"No override file. Using globalstorage value for consent: {consent_value} (likely default from run()).")
        else: # Should not happen if run() executed.
             utils.warning("telemetry_consent_given not in globalstorage at leave(). Defaulting to False.")
             consent_value = False


    # Store the determined consent value
    libcalamares.globalstorage.insert("telemetry_consent_given", consent_value)
    utils.log(f"Telemetry consent stored in globalstorage: telemetry_consent_given = {consent_value}")

    return True # True allows Calamares to proceed to the next step.
                # False would block navigation.
