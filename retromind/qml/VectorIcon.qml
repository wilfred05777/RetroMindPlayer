import QtQuick
import QtQuick.Shapes

Item {
    id: icon
    property string name: "play"
    property color color: "#FFFFFF"
    implicitWidth: 22
    implicitHeight: 22
    property bool filled: ["play", "pause", "previous", "next", "stop"].indexOf(name) >= 0
    property string outline: {
        switch (name) {
        case "play": return "M8 5 L19 12 L8 19 Z"
        case "pause": return "M6 5 H10 V19 H6 Z M14 5 H18 V19 H14 Z"
        case "previous": return "M5 5 H7 V19 H5 Z M19 5 L9 12 L19 19 Z"
        case "next": return "M17 5 H19 V19 H17 Z M5 5 L15 12 L5 19 Z"
        case "stop": return "M6 6 H18 V18 H6 Z"
        case "shuffle": return "M3 6 H6 C10 6 14 18 18 18 H21 M18 15 L21 18 L18 21 M3 18 H6 C8 18 10 14 11 12 M14 8 C16 6 17 6 18 6 H21 M18 3 L21 6 L18 9"
        case "repeat": return "M4 10 V8 C4 6 6 5 8 5 H20 M17 2 L20 5 L17 8 M20 14 V16 C20 18 18 19 16 19 H4 M7 16 L4 19 L7 22"
        case "repeat-one": return "M4 10 V8 C4 6 6 5 8 5 H20 M17 2 L20 5 L17 8 M20 14 V16 C20 18 18 19 16 19 H4 M7 16 L4 19 L7 22 M10 11 L12 9 V15"
        case "volume": return "M3 9 H7 L12 5 V19 L7 15 H3 Z M16 8 C19 10 19 14 16 16 M19 5 C24 9 24 15 19 19"
        case "mute": return "M3 9 H7 L12 5 V19 L7 15 H3 Z M16 9 L22 15 M22 9 L16 15"
        case "fullscreen": return "M3 9 V3 H9 M15 3 H21 V9 M21 15 V21 H15 M9 21 H3 V15"
        case "exit-fullscreen": return "M9 3 V9 H3 M15 3 V9 H21 M21 15 H15 V21 M3 15 H9 V21"
        case "queue": return "M3 5 H21 M3 11 H21 M3 17 H13 M17 15 L22 18 L17 21 Z"
        case "video": return "M3 5 H21 V19 H3 Z M10 9 L15 12 L10 15 Z"
        case "heart": return "M12 20 L4 12 C-2 5 6 0 12 7 C18 0 26 5 20 12 Z"
        default: return ""
        }
    }
    Shape {
        width: 24; height: 24
        scale: Math.min(icon.width, icon.height) / 24
        transformOrigin: Item.TopLeft
        antialiasing: true
        ShapePath {
            strokeColor: icon.filled ? "transparent" : icon.color
            strokeWidth: 1.7
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: icon.filled ? icon.color : "transparent"
            PathSvg { path: icon.outline }
        }
    }
}
