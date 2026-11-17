// The two Routes (spec §5), named as `kindle-send send --route` and `plan` name
// them. Their labels come from `kindle-send plan`. Pure, no QML.
.pragma library

var EMAIL = "email"
var USB = "usb"

// "usb" stays "usb"; anything else is Email, the default Route.
function normalize(route) { return route === USB ? USB : EMAIL }

// The Route `Tab` switches to.
function other(route) { return route === USB ? EMAIL : USB }
