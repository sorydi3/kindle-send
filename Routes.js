// The two Routes (spec §5), named as `kindle-send send --route` and `plan` name
// them. `plan` sends only these ids; the plugin labels them. Pure, no QML.
.pragma library

var EMAIL = "email"
var USB = "usb"

// "usb" stays "usb"; anything else is Email, the default Route.
function normalize(route) { return route === USB ? USB : EMAIL }

// The Route `Tab` switches to.
function other(route) { return route === USB ? EMAIL : USB }

// A Route's label from the catalog (tr: Catalog.js's translator); a Route
// with none shows its id.
function label(route, tr) { return tr.t("route." + route, route) }
