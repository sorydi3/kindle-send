// Stands in for Quickshell.Io Process: runs nothing, asks FakeWorld what the
// command would print, then reports it like a real run would.
import QtQuick

QtObject {
  id: p
  property var command: []
  property bool running: false
  property QtObject stdout: null
  signal started()
  signal exited(int exitCode, int exitStatus)
  onRunningChanged: if (running) {
    const cmd = p.command.slice()
    FakeWorld.later(function() {
      const a = FakeWorld.answer(cmd)
      if (p.stdout && p.stdout.reset) p.stdout.reset()
      p.started()
      for (let i = 0; i < a.lines.length; i++) if (p.stdout) p.stdout.feed(a.lines[i])
      p.running = false
      p.exited(a.code, 0)
    }, FakeWorld.delayFor(cmd))
  }
}
