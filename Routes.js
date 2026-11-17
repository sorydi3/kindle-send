// The two Routes (spec §5), named as `kindle-send send --route` and `plan` name
// them. `plan` sends only these ids; the plugin labels them. Pure, no QML.
.pragma library

var EMAIL = "email"
var USB = "usb"

// What the Picker calls each Route.
var LABELS = { "email": "Email", "usb": "USB" }

// "usb" stays "usb"; anything else is Email, the default Route.
function normalize(route) { return route === USB ? USB : EMAIL }

// The Route `Tab` switches to.
function other(route) { return route === USB ? EMAIL : USB }

// A Route's label: from `labels` when given (e.g. translated), else LABELS;
// a Route with neither shows its id.
function label(route, labels) { return (labels && labels[route]) || LABELS[route] || route }
