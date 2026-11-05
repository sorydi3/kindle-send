// What the fake commands answer, and a log of every command and notification
// as "EVENT <json>" lines on stderr for tests/test_service_flow.py.
pragma Singleton
import QtQuick

QtObject {
  id: w
  property real t0: Date.now()
  // `kindle-send limit` answers, one per ask; the last one repeats.
  property var limits: []
  property bool kindle: true
  property int nextId: 100

  function event(e) {
    e.t = Date.now() - w.t0
    console.warn("EVENT " + JSON.stringify(e))
  }

  function later(fn, ms) {
    const t = Qt.createQmlObject("import QtQuick; Timer {}", w)
    t.interval = ms
    t.triggered.connect(function() { fn(); t.destroy() })
    t.start()
  }

  function delayFor(cmd) { return cmd[0] === "kindle-send" && cmd[1] === "send" ? 50 : 5 }

  function answer(cmd) {
    if (cmd[0] === "omarchy-notification-send") {
      const r = cmd.indexOf("-r")
      const at = r >= 0 ? r + 2 : cmd.indexOf("-p") + 1
      const id = r >= 0 ? parseInt(cmd[r + 1], 10) : w.nextId++
      w.event({ kind: "notify", id: id, urgency: cmd[cmd.indexOf("-u") + 1], headline: cmd[at], body: cmd[at + 1] })
      return { lines: r >= 0 ? [] : [String(id)], code: 0 }
    }
    w.event({ kind: "run", cmd: cmd.slice(1).join(" ") })
    if (cmd[1] === "limit") return { lines: [JSON.stringify(w.limits.length > 1 ? w.limits.shift() : w.limits[0])], code: 0 }
    if (cmd[1] === "send" && cmd[3] === "usb") {
      if (!w.kindle) return { lines: ['{"result":"failed","reason":"Kindle not plugged in. Plug it in and send again."}'], code: 0 }
      return { lines: ['{"stage":"copying"}', '{"result":"copied"}'], code: 0 }
    }
    if (cmd[1] === "send") return { lines: ['{"stage":"sending"}', '{"result":"sent"}'], code: 0 }
    if (cmd[1] === "eject") return { lines: ['{"ejected":true}'], code: 0 }
    if (cmd[1] === "kindle") return { lines: [JSON.stringify({ present: w.kindle })], code: 0 }
    return { lines: [], code: 1 }
  }
}
