# The Picker takes the app password

The Picker's Settings take the Gmail app password in a masked field and hand it to `kindle-send` over stdin, which stores it in GNOME Keyring. This reverses the original rule that the Picker never sees the password and that only `secret-tool` in a terminal prompts for it. Setup in the Picker is otherwise impossible without dropping into a terminal for one step, and omarchy-shell's own network panel already takes Wi-Fi passwords this way.

## Consequences

The password never goes on a command line, into `shell.json`, a log or a file the Picker writes; it lives in QML memory only until it is handed over, and the field is cleared once stored. `kindle-send setup` in a terminal keeps using `secret-tool`'s own prompt.
