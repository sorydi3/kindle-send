// PROTOTYPE, throwaway: wayfinder ticket "Settings layout: one form, or first-run steps?"
// (sorydi3/kindle-send#30), branch prototype/settings-layout. Never merge.
//
// Three layouts for Settings inside the Picker card, switchable with Alt+Left/Right.
// Alt+M flips between first run (nothing set) and configured (stub values).
// Nothing is saved: values live in memory, the password is never stored or logged.
import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui as Ui

FocusScope {
  id: proto

  signal back()

  property int variant: 0
  readonly property var variantNames: ["A · One form", "B · Steps on first run, then the form", "C · Rows, edit one at a time"]
  property bool firstRun: true

  property string kindle: ""
  property string gmail: ""
  property string password: ""        // typed this session only
  property bool passwordStored: false
  property string folders: ""
  property string savedNote: ""

  readonly property var fields: [
    { key: "kindle", label: "Kindle address", placeholder: "…@kindle.com",
      question: "What is your Kindle's email address?",
      help: "Find it at amazon.com → Manage Your Content and Devices → Devices." },
    { key: "gmail", label: "Gmail address", placeholder: "…@gmail.com",
      question: "Which Gmail address sends the Books?",
      help: "Amazon must list it as an approved sender, or it drops every Book." },
    { key: "password", label: "Gmail app password", placeholder: "16 letters",
      question: "Paste a Gmail app password",
      help: "Create one at myaccount.google.com/apppasswords. It needs 2-Step Verification." },
    { key: "folders", label: "Book folders", placeholder: "~/Books, ~/Downloads",
      question: "Where do you keep your Books?",
      help: "The folders the Picker lists, separated by commas." }
  ]

  function value(key) {
    return key === "kindle" ? kindle : key === "gmail" ? gmail : key === "password" ? password : folders
  }
  function setValue(key, v) {
    if (key === "kindle") kindle = v
    else if (key === "gmail") gmail = v
    else if (key === "password") password = v
    else folders = v
  }
  function missing(key) {
    if (key === "password") return !passwordStored && password === ""
    return value(key).trim() === ""
  }
  function placeholder(field) {
    return field.key === "password" && passwordStored ? "Stored. Type to replace it." : field.placeholder
  }
  function shown(key) {
    if (key === "password") return password ? "•".repeat(password.length) + " (new)" : passwordStored ? "Stored" : "Not set"
    return value(key) || "Not set"
  }
  function missingCount() {
    let n = 0
    for (let i = 0; i < fields.length; i++) if (missing(fields[i].key)) n++
    return n
  }
  function save() {
    const n = missingCount()
    if (n > 0) { savedNote = n + " still needed before Books can be sent."; return }
    if (password) { passwordStored = true; password = "" }
    firstRun = false
    savedNote = "Saved. (Prototype: nothing was written.)"
  }

  function reset() {
    savedNote = ""
    password = ""
    folders = "~/Books, ~/Downloads"
    if (firstRun) { kindle = ""; gmail = ""; passwordStored = false }
    else { kindle = "reader_42@kindle.com"; gmail = "me.example@gmail.com"; passwordStored = true }
    view.active = false
    view.active = true
    Qt.callLater(function() { view.forceActiveFocus() })
  }

  // Unhandled keys from the fields bubble up here.
  Keys.onPressed: function(event) {
    if (event.key === Qt.Key_Escape) { event.accepted = true; proto.back() }
  }
  Shortcut { enabled: proto.visible; sequence: "Alt+Right"; onActivated: { proto.variant = (proto.variant + 1) % 3; proto.reset() } }
  Shortcut { enabled: proto.visible; sequence: "Alt+Left"; onActivated: { proto.variant = (proto.variant + 2) % 3; proto.reset() } }
  Shortcut { enabled: proto.visible; sequence: "Alt+M"; onActivated: { proto.firstRun = !proto.firstRun; proto.reset() } }

  // Covers the Book list underneath.
  Rectangle { anchors.fill: parent; color: Color.menu.background }

  Loader {
    id: view
    anchors.fill: parent
    focus: true
    sourceComponent: proto.variant === 0 ? formView : proto.variant === 1 ? stepsView : rowsView
  }

  // --- A: one form ---------------------------------------------------------
  Component {
    id: formView
    FocusScope {
      focus: true
      Column {
        width: parent.width
        spacing: Style.space(12)

        Text {
          text: proto.firstRun ? "Set up Send to Kindle" : "Settings"
          color: Color.menu.text
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.heading
        }

        Repeater {
          model: proto.fields
          delegate: Column {
            id: entry
            required property var modelData
            required property int index
            width: parent.width
            spacing: Style.space(4)

            Text {
              text: entry.modelData.label + (proto.missing(entry.modelData.key) ? "  ·  needed" : "")
              color: proto.missing(entry.modelData.key) ? Color.menu.selectedText : Color.menu.text
              font.family: Style.font.menuFamily
              font.pixelSize: Style.font.body
            }
            Ui.TextField {
              width: parent.width
              focus: entry.index === 0
              password: entry.modelData.key === "password"
              foreground: Color.menu.text
              accent: Color.menu.selectedText
              text: proto.value(entry.modelData.key)
              placeholderText: proto.placeholder(entry.modelData)
              onTextEdited: proto.setValue(entry.modelData.key, text)
              onAccepted: proto.save()
            }
            Text {
              width: parent.width
              text: entry.modelData.help
              wrapMode: Text.Wrap
              color: Color.menu.text
              opacity: 0.72
              font.family: Style.font.menuFamily
              font.pixelSize: Style.font.bodySmall
            }
          }
        }
      }

      Column {
        anchors.bottom: parent.bottom
        width: parent.width
        spacing: Style.space(6)
        Text {
          visible: text !== ""
          width: parent.width
          horizontalAlignment: Text.AlignHCenter
          text: proto.savedNote
          color: Color.menu.text
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.body
        }
        Text {
          width: parent.width
          horizontalAlignment: Text.AlignHCenter
          text: "Tab  Next field      Enter  Save      Esc  Back to Books"
          color: Color.menu.text
          opacity: 0.5
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.bodySmall
        }
      }
    }
  }

  // --- B: steps on first run, then the form ---------------------------------
  Component {
    id: stepsView
    FocusScope {
      id: steps
      focus: true
      property int step: 0
      property bool nudge: false
      readonly property var current: proto.fields[step]

      Loader {
        anchors.fill: parent
        active: !proto.firstRun
        focus: !proto.firstRun
        sourceComponent: formView
      }

      Item {
        anchors.fill: parent
        visible: proto.firstRun

        Column {
          anchors.verticalCenter: parent.verticalCenter
          anchors.verticalCenterOffset: -Style.space(30)
          width: parent.width
          spacing: Style.space(10)

          Text {
            text: "Step " + (steps.step + 1) + " of " + proto.fields.length
            color: Color.menu.text
            opacity: 0.72
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.bodySmall
          }
          Text {
            width: parent.width
            wrapMode: Text.Wrap
            text: steps.current.question
            color: Color.menu.text
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.heading
          }
          Text {
            width: parent.width
            wrapMode: Text.Wrap
            text: steps.current.help
            color: Color.menu.text
            opacity: 0.72
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.body
          }
          Ui.TextField {
            id: stepField
            width: parent.width
            focus: proto.firstRun
            password: steps.current.key === "password"
            foreground: Color.menu.text
            accent: Color.menu.selectedText
            text: proto.value(steps.current.key)
            placeholderText: proto.placeholder(steps.current)
            onTextEdited: { proto.setValue(steps.current.key, text); steps.nudge = false }
            onAccepted: {
              if (proto.missing(steps.current.key)) { steps.nudge = true; return }
              if (steps.step < proto.fields.length - 1) steps.step++
              else proto.save()
            }
            Keys.onBacktabPressed: function(event) { event.accepted = true; steps.step = Math.max(0, steps.step - 1) }
            Keys.onTabPressed: function(event) { event.accepted = true }
          }
          Text {
            visible: steps.nudge
            text: "Needed before Books can be sent."
            color: Color.menu.selectedText
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.bodySmall
          }
        }

        Text {
          anchors.bottom: parent.bottom
          width: parent.width
          horizontalAlignment: Text.AlignHCenter
          text: (steps.step < proto.fields.length - 1 ? "Enter  Next" : "Enter  Finish")
            + (steps.step > 0 ? "      Shift+Tab  Back" : "") + "      Esc  Back to Books"
          color: Color.menu.text
          opacity: 0.5
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.bodySmall
        }
      }

      onStepChanged: { nudge = false; stepField.text = proto.value(proto.fields[step].key) }
    }
  }

  // --- C: rows, edit one at a time ------------------------------------------
  Component {
    id: rowsView
    FocusScope {
      id: rows
      property int cursor: 0
      property int editing: -1
      focus: true

      Keys.onPressed: function(event) {
        event.accepted = false  // unhandled keys (Esc) go on up to proto
        if (rows.editing >= 0) {
          if (event.key === Qt.Key_Escape) { event.accepted = true; rows.editing = -1; rows.forceActiveFocus() }
          return
        }
        if (event.key === Qt.Key_Up) { event.accepted = true; rows.cursor = Math.max(0, rows.cursor - 1) }
        else if (event.key === Qt.Key_Down) { event.accepted = true; rows.cursor = Math.min(proto.fields.length - 1, rows.cursor + 1) }
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) { event.accepted = true; rows.editing = rows.cursor }
      }

      Column {
        width: parent.width
        spacing: Style.space(4)

        Text {
          bottomPadding: Style.space(8)
          text: proto.firstRun ? "Set up Send to Kindle" : "Settings"
          color: Color.menu.text
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.heading
        }

        Repeater {
          model: proto.fields
          delegate: Rectangle {
            id: row
            required property var modelData
            required property int index
            readonly property bool hasCursor: index === rows.cursor
            readonly property bool isEditing: index === rows.editing
            readonly property color ink: hasCursor ? Color.menu.selectedText : Color.menu.text
            width: parent.width
            height: Style.space(isEditing ? 92 : 54)
            radius: Style.cornerRadius
            color: hasCursor ? Color.menu.selectedBackground : "transparent"

            Column {
              anchors.left: parent.left
              anchors.leftMargin: Style.space(12)
              anchors.right: badge.left
              anchors.rightMargin: Style.space(12)
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(4)

              Text {
                text: row.modelData.label
                color: row.ink
                font.family: Style.font.menuFamily
                font.pixelSize: Style.font.title
              }
              Text {
                visible: !row.isEditing
                width: parent.width
                elide: Text.ElideRight
                text: proto.shown(row.modelData.key) + (row.hasCursor ? "  ·  " + row.modelData.help : "")
                color: Color.menu.text
                opacity: 0.72
                font.family: Style.font.menuFamily
                font.pixelSize: Style.font.bodySmall
              }
              Ui.TextField {
                id: editor
                visible: row.isEditing
                width: parent.width
                password: row.modelData.key === "password"
                foreground: Color.menu.text
                accent: Color.menu.selectedText
                placeholderText: proto.placeholder(row.modelData)
                onAccepted: {
                  proto.setValue(row.modelData.key, text)
                  rows.editing = -1
                  rows.forceActiveFocus()
                  if (proto.missingCount() === 0) proto.save()
                }
              }
            }

            Rectangle {
              id: badge
              visible: proto.missing(row.modelData.key)
              anchors.right: parent.right
              anchors.rightMargin: Style.space(12)
              anchors.verticalCenter: parent.verticalCenter
              width: badgeText.implicitWidth + Style.space(16)
              height: badgeText.implicitHeight + Style.space(6)
              radius: height / 2
              color: "transparent"
              border.color: row.ink
              border.width: 1
              Text {
                id: badgeText
                anchors.centerIn: parent
                text: "Needed"
                color: row.ink
                font.family: Style.font.menuFamily
                font.pixelSize: Style.font.caption
              }
            }

            onIsEditingChanged: if (isEditing) {
              editor.text = row.modelData.key === "password" ? "" : proto.value(row.modelData.key)
              editor.forceActiveFocus()
            }
          }
        }
      }

      Column {
        anchors.bottom: parent.bottom
        width: parent.width
        spacing: Style.space(6)
        Text {
          visible: text !== ""
          width: parent.width
          horizontalAlignment: Text.AlignHCenter
          text: proto.savedNote
          color: Color.menu.text
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.body
        }
        Text {
          width: parent.width
          horizontalAlignment: Text.AlignHCenter
          text: rows.editing >= 0 ? "Enter  Keep      Esc  Cancel" : "Up/Down  Move      Enter  Edit      Esc  Back to Books"
          color: Color.menu.text
          opacity: 0.5
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.bodySmall
        }
      }
    }
  }
}
