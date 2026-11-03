package vision_pkg;
    // Marker positions always remain in native 320x240 coordinates. orientation
    // rotates only glyph sampling; it cannot change the B/C coordinate contract.
    typedef struct packed {
        logic accepted, isBlue;
        logic [3:0] digit;
        logic [1:0] orientation;
        logic [7:0] quality, reason;
        logic [6:0] segments;
        logic [8:0] xMin,xMax;
        logic [7:0] yMin,yMax;
    } marker_t;
    // Sixteen completed slots are shared by both colours. isBlue carries the
    // observed colour; neither slot order nor slot address implies colour/ID.
    typedef marker_t [15:0] markerArray_t;
endpackage
