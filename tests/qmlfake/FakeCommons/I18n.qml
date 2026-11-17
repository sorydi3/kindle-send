// Stands in for Omarchy's qs.Commons I18n: numbers as English writes them.
pragma Singleton
import QtQuick

QtObject {
  readonly property string formatLocale: "en-US"

  function formatNumber(value, decimals) {
    const n = Number(value)
    return decimals === undefined ? String(n) : n.toFixed(decimals)
  }
}
