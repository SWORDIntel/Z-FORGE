import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import org.kde.kirigami 2.16 as Kirigami

Kirigami.ScrollablePage {
    id: root
    title: qsTr("Telemetry Consent")

    // Property to hold consent state, accessible by Python (theoretically)
    // In a real Calamares QML module, this might be achieved by setting a
    // property on an object exposed from Python, or by Calamares C++ <-> QML bindings.
    // For this subtask, Python will simulate reading this.
    property bool consentGiven: consentCheckBox.checked

    Component.onCompleted: {
        console.log("TelemetryConsent QML Loaded. Default consent checkbox state: " + consentCheckBox.checked);
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.largeSpacing

        Kirigami.Heading {
            Layout.fillWidth: true
            level: 1
            text: qsTr("Help Us Improve")
            // font.pixelSize: Kirigami.Theme.fontSizeHuge
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            text: qsTr("To help us improve our operating system, you can choose to send anonymous system information and usage statistics. This data helps us understand which features are most popular, identify areas for improvement, and fix bugs more effectively.")
            wrapMode: Text.WordWrap
            // font.pixelSize: Kirigami.Theme.fontSizeSmall
            padding: Kirigami.Units.smallSpacing
        }

        Label {
            Layout.fillWidth: true
            text: qsTr("The data collected is anonymized and does not include any personal or sensitive information such as IP addresses, hostnames (unless you explicitly allow it for specific debugging scenarios not covered here), or file contents. We are committed to your privacy.")
            wrapMode: Text.WordWrap
            // font.pixelSize: Kirigami.Theme.fontSizeSmall
            padding: Kirigami.Units.smallSpacing
        }

        CheckBox {
            id: consentCheckBox
            Layout.topMargin: Kirigami.Units.largeSpacing
            text: qsTr("I agree to send anonymous system information and usage statistics.")
            checked: false // Default to opt-out
            onCheckedChanged: {
                // This is where, in a fully integrated setup, Calamares might be notified
                // or a Python-exposed property would be updated directly.
                console.log("Telemetry consent checkbox changed to: " + checked);
                // root.consentGiven = checked; // Update our exposed property
            }
        }

        Item { // Spacer
            Layout.fillWidth: true
            Layout.preferredHeight: Kirigami.Units.largeSpacing
        }

        Label {
            Layout.fillWidth: true
            text: qsTr("You can review our <a href=\"#\">Privacy Policy</a> for more details on what data is collected and how it is used. You can change this setting at any time after installation from the system settings.")
            wrapMode: Text.WordWrap
            textFormat: Text.RichText
            // font.pixelSize: Kirigami.Theme.fontSizeSmall
            onLinkActivated: {
                // In a real module, this would open a browser or a dialog with the privacy policy.
                // For now, just log.
                console.log("Privacy Policy link clicked. URL: " + link);
                // Qt.openUrlExternally(link); // Example if 'link' was a full URL
            }
        }
    }
}
