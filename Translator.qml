// The translator the plugin's JS text functions take (Catalog.js): the
// plugin's own catalogs in i18n/ through Omarchy's Commons.Translations,
// numbers through Commons.I18n.formatNumber and times through
// Qt.locale(Commons.I18n.formatLocale). It follows the language picked
// under Setup > Language; bindings that call it re-render on a switch.
import QtQuick
import qs.Commons as Commons

QtObject {
  id: root

  readonly property Commons.Translations strings: Commons.Translations {
    directory: Qt.resolvedUrl("i18n")
  }

  function t(key, fallback) {
    return root.strings.t(key, fallback);
  }

  function tn(key, count, fallback) {
    return root.strings.tn(key, count, fallback);
  }

  function num(value, decimals) {
    return Commons.I18n.formatNumber(value, decimals);
  }

  // A time of day (ms since the epoch) as Omarchy's language writes it: its
  // format locale, not the one the shell started with.
  function time(ms) {
    return new Date(ms).toLocaleTimeString(Qt.locale(Commons.I18n.formatLocale), Locale.ShortFormat);
  }
}
