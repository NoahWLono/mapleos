import QtQuick 2.15
import QtQuick.Controls 2.15
Rectangle {
    width: 1920; height: 1080; color: "#171a20"
    Image { anchors.fill: parent; source: "/usr/share/backgrounds/mapleos/maple.png"; fillMode: Image.PreserveAspectCrop }
    Rectangle { anchors.fill: parent; color: "#800c1016" }
    Rectangle {
        anchors.centerIn: parent; width: 420; height: 430; radius: 22; color: "#ef171a20"
        Column {
            anchors.centerIn: parent; width: 330; spacing: 16
            Label { text: "MapleOS"; color: "#e0b876"; font.pixelSize: 40; font.bold: true }
            Label { text: "Your machine. Your agents. Your permission."; color: "#e8e2d9"; font.pixelSize: 12 }
            TextField { id: username; width: parent.width; placeholderText: "Username"; focus: true }
            TextField { id: password; width: parent.width; placeholderText: "Password"; echoMode: TextInput.Password; onAccepted: login.clicked() }
            ComboBox { id: session; width: parent.width; model: sessionModel; textRole: "name"; currentIndex: Math.max(0, sessionModel.lastIndex) }
            Button { id: login; width: parent.width; text: "Sign in"; onClicked: { status.text = ""; sddm.login(username.text, password.text, session.currentIndex); } }
            Label { id: status; color: "#e88388"; text: "" }
            Row {
                spacing: 16
                Button { text: "Restart"; onClicked: sddm.reboot() }
                Button { text: "Power off"; onClicked: sddm.powerOff() }
            }
        }
    }
    Connections { target: sddm; function onLoginFailed() { status.text = "Login failed. Please try again."; password.text = ""; } }
}
