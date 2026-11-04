# How does the Nautilus right-click entry hand Books to the plugin?

Type: grilling
Status: open
Blocked by: 05, 07
Parent: ../map.md

## Question

The plugin can be reached from outside the shell two ways (see [What can an omarchy-shell menu and service plugin do?](03-plugin-api-facts.md)): summon the menu with the selected files as a payload, or call a service `IpcHandler` directly. Should right-click open the picker with the files preselected (so the Route can be confirmed) or send straight away with no UI?
