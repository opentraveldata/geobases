
if (!String.fmt) {
    String.prototype.fmt = function() {
        var formatted = this;
        var i;
        for (i=0; i<arguments.length; i++) {
            var regexp = new RegExp('\\{'+i+'\\}', 'gi');
            formatted = formatted.replace(regexp, arguments[i]);
        }
        return formatted;
    };
}


function haversine(lat1, lng1, lat2, lng2) {

    lat1 = lat1 / 180 * Math.PI;
    lat2 = lat2 / 180 * Math.PI;
    lng1 = lng1 / 180 * Math.PI;
    lng2 = lng2 / 180 * Math.PI;

    return 2 * 6371.0 * Math.asin(Math.sqrt(
        Math.pow(Math.sin(0.5 * (lat1 - lat2)), 2) +
        Math.pow(Math.sin(0.5 * (lng1 - lng2)), 2) *
        Math.cos(lat1) * Math.cos(lat2)));
}


/**
 *
 * Popup management
 *
 */

/**
 * Loading popup
 * @param {string} divId Container for the popup
 * @see #centerPopup
 * @see #disablePopup
 */
function loadPopup(divId) {

    // First background fade in
    $("#backgroundPopup").css({
        "opacity": "0.7"
    });
    $("#backgroundPopup").fadeIn("slow");

    // Then the popup over the background
    $(divId).fadeIn("slow");

}


/**
 * Disabling popup
 * @param {string} divId Container for the popup
 * @see #loadPopup
 */
function disablePopup(divId) {

    // Background fade out
    $("#backgroundPopup").fadeOut("slow");

    // Popup fade out
    $(divId).fadeOut("slow");

}


/**
 * Centering popup
 * @param {string} divId Container for the popup
 * @see #loadPopup
 */
function centerPopup(divId) {

    // Using jQuery functions to
    // have cross-browser compatibility
    var windowWidth = $(window).width();
    var windowHeight = $(window).height();

    var popupHeight = $(divId).height();
    var popupWidth = $(divId).width();

    // Centering
    $(divId).css({
        //"position": "absolute",
        "top": windowHeight/2 - popupHeight/2,
        "left": windowWidth/2 - popupWidth/2
    });

}


function sortPointX(a, b) {
    return a.lng() - b.lng();
}


function sortPointY(a, b) {
    return a.lat() - b.lat();
}


function overflow(text) {

    if (typeof text !== "string") {
        return text;
    }

    if (text.length < 30) {
        return text;
    }

    return ('' + text).slice(0, 25) + '...';

}


function initialize(jsonData) {

    // Set map options
    var parisLocation = new google.maps.LatLng(48.8, 2.33);

    var mapTypeIds = [];

    // Creating list of available map types, adding OSM
    for(var type in google.maps.MapTypeId) {
        if (google.maps.MapTypeId.hasOwnProperty(type)) {
            mapTypeIds.push(google.maps.MapTypeId[type]);
        }
    }
    mapTypeIds.push("MQ");
    mapTypeIds.push("OSM");

    var mapOptions = {
        zoom      : 2,
        center    : parisLocation,
        mapTypeId : "OSM",
        mapTypeControlOptions: {
            mapTypeIds: mapTypeIds
        }
    };

    // Create the map
    var map = new google.maps.Map(document.getElementById("canvas"), mapOptions);

    // Setting tiles
    map.mapTypes.set("MQ", new google.maps.ImageMapType({
        getTileUrl  : function(coord, zoom) {
            return "http://otile3.mqcdn.com/tiles/1.0.0/osm/" + zoom + "/" + coord.x + "/" + coord.y + ".png";
        },
        tileSize    : new google.maps.Size(256, 256),
        name        : "MapQuest",
        maxZoom     : 18
    }));

    map.mapTypes.set("OSM", new google.maps.ImageMapType({
        getTileUrl  : function(coord, zoom) {
            return "http://tile.openstreetmap.org/" + zoom + "/" + coord.x + "/" + coord.y + ".png";
        },
        tileSize    : new google.maps.Size(256, 256),
        name        : "OpenStreetMap",
        maxZoom     : 18
    }));

    if (jsonData.points.length === 0){
        return;
    }

    // Computing fields order
    var fields = [];
    var field;
    for (field in jsonData.points[0]) {
        if (jsonData.points[0].hasOwnProperty(field)) {
            if (field !== '__lab__' && field !== '__col__') {
                fields.push(field);
            }
        }
    }

    fields.sort(function(a, b) {
        return b.toLowerCase() < a.toLowerCase();
    });

    var f = fields.length;
    var n = jsonData.points.length;

    var point_color     = jsonData.meta.point_color;
    var point_size      = jsonData.meta.point_size;
    var base_icon       = jsonData.meta.base_icon;
    var icon_type       = jsonData.meta.icon_type;
    var link_duplicates = jsonData.meta.link_duplicates;

    var with_markers = icon_type   !== null;
    var with_circles = point_size  !== null;
    var with_colors  = point_color !== null;

    var getMarkerIcon  = function (color) { return color + '_' + base_icon; };
    var getCircleColor;

    if (with_markers || ! with_colors) {
        getCircleColor = function (color) { return 'black'; };
    } else {
        getCircleColor = function (color) { return color; };
    }

    var markersArray = [];
    var circlesArray = [];
    var centersArray = [];
    var bounds       = new google.maps.LatLngBounds();
    var infowindow   = new google.maps.InfoWindow();

    // closure fun
    function closeInfoWindow() {
        var i, c;
        for (i=0, c=markersArray.length; i<c; i++) {
            infowindow.close(map, markersArray[i]);
        }
    }

    var i, j, c, e, s, latlng, marker, circle, circle_col, has_circle;
    var max_value = 0;

    // Load the data
    for (i=0 ; i<n ; i++) {

        e = jsonData.points[i];
        s = parseFloat(e.__siz__);

        latlng = new google.maps.LatLng(e.lat, e.lng);

        if (isNaN(latlng.lat()) || isNaN(latlng.lng())) {
            //console.log(e.__lab__ + ' had no position: ' + e.lat + e.lng)
            continue;
        }

        has_circle = (! isNaN(s)) && s > 0;
        circle_col = getCircleColor(e.__col__);

        if (! with_markers && ! has_circle) {
            // If no markers, only circles are displayed.
            // If no circle too, let's move on
            // Note that lines will not go through these
            continue;
        }

        marker = new google.maps.Marker({
            position    : latlng,
            animation   : null,
            title       : e.__lab__,
            clickable   : true,
            draggable   : false
        });

        if (with_markers) {
            marker.setMap(map);
            marker.setIcon(getMarkerIcon(e.__col__));
        }

        // Augmenting the marker type
        marker.help = ' ' +
        '<div class="infowindow medium" style="min-width: 400px;">' +
            '<h3>{0}</h3>'.fmt(e.__lab__) +
            '<table cellpadding="1">';

        for (j=0 ; j<f ; j++) {
            field = fields[j];
            marker.help += '<tr><td><i>{0}</i></td><td>{1}</td></tr>'.fmt(field, overflow(e[field]));
        }

        marker.help += ' ' +
            '</table>' +
        '</div>';

        google.maps.event.addListener(marker, 'click', function() {
            infowindow.setContent(this.help);
            infowindow.open(map, this);
        });

        google.maps.event.addListener(marker, 'rightclick', function () {
            if (this.getAnimation() === null) {
                this.setAnimation(google.maps.Animation.BOUNCE);
            } else {
                this.setAnimation(null);
            }
        });

        // Saving marker
        markersArray.push(marker);
        bounds.extend(latlng);
        centersArray.push(latlng);

        if (has_circle) {
            // We compute the biggest __siz__ value
            if (s > max_value) {
                max_value = s;
            }
            circle = new google.maps.Circle({
                center          : latlng,
                radius          : 0,
                strokeColor     : circle_col,
                strokeOpacity   : 0.25,
                strokeWeight    : 2,
                fillColor       : circle_col,
                fillOpacity     : 0.15,
                map             : map,
                clickable       : true
            });

            // Augmenting the marker type
            circle.size = s;
            circle.help = ' ' +
            '<div class="infowindow large">' +
                '<h3>{0}</h3>'.fmt(e.__lab__) +
                '<i>{0}</i> {1}<br/>'.fmt(point_size, s);

            if (with_colors) {
                circle.help += '<i>{0}</i> {1} ({2})'.fmt(point_color, e.__cat__, e.__col__);
            }

            circle.help += ' ' +
            '</div>';

            // Saving
            circlesArray.push(circle);

            google.maps.event.addListener(circle, 'click', function(event) {
                infowindow.setContent(this.help);
                infowindow.open(map, new google.maps.Marker({position : event.latLng}));
            });

        }
    }

    // Ratio of map size for circles on the map
    //var R = 100;
    var r = 0.15;

    function updateLabel(value) {
        // We update the span where r is displayed
        $('#ratio').html(parseInt(100 * parseFloat(value), 10) + '%');
    }

    function updateCircles(value) {
        // We compute the top radius given the map size
        var mapBounds = map.getBounds();
        var sw = mapBounds.getSouthWest();
        var ne = mapBounds.getNorthEast();

        var biggest = 0.5 * r * 1000 * haversine(sw.lat(), sw.lng(), ne.lat(), ne.lng());
        //var biggest = R * 1000;

        for (i=0, c=circlesArray.length; i<c; i++) {
            circle = circlesArray[i];
            circle.setRadius(Math.sqrt(circle.size / max_value) * biggest);
        }
    }

    $( "#slider" ).slider({
        range          : false,
        min            : 0,
        max            : 1.00,
        step           : 0.01,
        value          : r,
        //animate      : 'slow',
        slide          : function (event, ui) {
            updateLabel(ui.value);
        },
        stop           : function (event, ui) {
            // Updating global variable
            r = parseFloat(ui.value);

            updateCircles();
        }
    });

    // We trigger manually an updateCircles once the fitBounds is finished
    updateLabel(r);
    google.maps.event.addListenerOnce(map, 'bounds_changed', updateCircles);
    google.maps.event.addListener(map, 'zoom_changed', updateCircles);

    // If no markers, we avoid a big
    // drift to the pacific ocean :)
    if (n >= 2 && (with_markers || with_circles)) {
        map.fitBounds(bounds);
    }

    // Add specified lines
    var od, coords, line, d, help;
    var linesArray = [];

    for (i=0, c=jsonData.lines.length; i<c; i++) {

        od = jsonData.lines[i];

        coords = [];
        help   = '<div class="infowindow large">' +
                     '<h3>Duplicates</h3><table>';

        for (j=0, d=od.length; j<d; j++) {

            latlng = new google.maps.LatLng(od[j].lat, od[j].lng);

            if (! isNaN(latlng.lat()) && ! isNaN(latlng.lng())) {
                coords.push(latlng);
                help += '<tr><td>{0}</td><td>{1}</td></tr>'.fmt(od[j]['__key__'], od[j]['__lab__']);
            }
        }

        help += '</table></div>';

        line = new google.maps.Polyline({
            map             : null, // not drawn by default
            geodesic        : true,
            clickable       : true,
            path            : coords,
            strokeColor     : 'blue',
            strokeOpacity   : 0.5,
            strokeWeight    : 5
        });

        line.help = help;

        google.maps.event.addListener(line, 'click', function(event) {
            infowindow.setContent(this.help);
            infowindow.open(map, new google.maps.Marker({position : event.latLng}));
        });

        linesArray.push(line);
    }

    var toggled = false;

    function toggleLines() {
        var i, c;
        for (i=0, c=linesArray.length; i<c; i++) {
            if (linesArray[i].getMap() === null) {
                linesArray[i].setMap(map);
            } else {
                linesArray[i].setMap(null);
            }
        }
        toggled = ! toggled;
        $('#dups').text('Duplicates ({0})'.fmt(toggled ? '1' : '0'));
    }

    $('#dups').click(toggleLines);

    if (! link_duplicates) {
        // If not duplicates, we disable the button
        $('#dups').text('Duplicates');
        $('#dups').attr('disabled', 'true');
        $('#dups').css({'color': 'grey'});
    }

    // Draw hull
    var hull = new google.maps.Polyline({
        path            : centersArray,
        strokeColor     : "green",
        strokeOpacity   : 0.40,
        strokeWeight    : 3,
        //fillColor       : "green",
        //fillOpacity     : 0,
        geodesic        : true,
        clickable       : false
    });


    // Control lines state when clicking on button
    var state = 0;
    var sortedCenters;

    function connectMarkers() {
        if (state === 0) {
            hull.setPath(centersArray);
            hull.setMap(map);

        } else if (state === 1) {
            sortedCenters = centersArray.slice();
            sortedCenters.sort(sortPointY);
            sortedCenters.sort(sortPointX);
            hull.setPath(sortedCenters);

        } else if (state === 2) {
            sortedCenters = centersArray.slice();
            sortedCenters.sort(sortPointX);
            sortedCenters.sort(sortPointY);
            hull.setPath(sortedCenters);

        } else if (state === 3) {
            hull.setMap(null);
        }

        state += 1;
        state = state === 4 ? 0 : state;
        $('#connect').text('Connect ({0})'.fmt(state));
    }

    $('#connect').click(connectMarkers);

    google.maps.event.addListener(map, 'rightclick', function () {
        connectMarkers();
        // If the rightclick shall go through
        //$(this).trigger();
    });

    // Fill legend
    var cat, vol, col, row, icon;
    var msg = ' ' +
    '<table id="legendcontent" class="medium">' +
        '<tr><th><i>Icon</i></th><th><i>Color</i></th><th><i>Circle</i></th><th><i>Category</i></th><th><i>Volume</i></th></th>';

    if (with_markers) {
        row = '<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3} "{4}"</td><td>{5} points</td></tr>';
    } else {
        row = '<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3} "{4}"</td><td>' + point_size + ' {5}</td></tr>';
    }

    for (i=0, c=jsonData.categories.length; i<c ;i++) {
        cat  = jsonData.categories[i][0];
        col  = jsonData.categories[i][1].color;
        vol  = jsonData.categories[i][1].volume;

        if (with_markers) {
            icon = '<img src="{0}" alt="icon"/>'.fmt(getMarkerIcon(col));
        } else {
            icon = '(none)';
        }
        msg += row.fmt(icon, col, getCircleColor(col), point_color, cat, vol);
    }
    msg += '</table>';

    // General information
    $('#legendPopup').html(msg);
    $('#info').html('{0} <i>points on map</i> (out of {1}), {2} <i>duplicates</i>, {3} <i>{4}</i> categorie(s), <i>{5}</i> max: {6}'.fmt(markersArray.length, n, jsonData.lines.length, jsonData.categories.length, point_color, point_size, max_value));

    // Press Escape event!
    // Use keydown instead of keypress for webkit-based browsers
    $(document).keydown(function (e) {
        if (e.keyCode === 27) {
            disablePopup('#legendPopup');
            closeInfoWindow();
        }
    });
}

$(document).ready(function() {

    $('#backgroundPopup').css({
        'display'    : 'none',
        'position'   : 'fixed',
        '_position'  : 'absolute', /* hack for internet explorer 6*/
        'height'     : '100%',
        'width'      : '100%',
        'top'        : '0',
        'left'       : '0',
        'background' : '#000000',
        'border'     : '0px solid #cecece',
        'z-index'    : '1'
    });

    $('#legendPopup').css({
        'display'    : 'none',
        'position'   : 'fixed',
        '_position'  : 'absolute', /* hack for internet explorer 6*/
        'height'     : '500px',
        'width'      : '750px',
        'padding'    : '0px',
        'text-align' : 'center',
        'color'      : 'white',
        'background' : 'rgba(0, 0, 0, 0)',
        'border'     : '0px solid #cecece',
        'z-index'    : '2'
    });

    $('#legend').click(function() {
        centerPopup('#legendPopup');
        loadPopup('#legendPopup');
    });

    $("#backgroundPopup").click(function () {
        disablePopup('#legendPopup');
    });

    $('#legend').attr('title', 'Display legend.');
    $('#connect').attr('title', 'Draw lines between points. Click again to change sorting.');
    $('#dups').attr('title', 'Toggle lines between duplicates.');
    $('#ratio').attr('title', 'Circle size (%)');
    $('#slider').attr('title', 'Circle size (%)');

    // This is weird, but $(window).height seems to change after
    // document is ready
    setTimeout(function () {
        $("#canvas").css({
            "height": $(window).height() * 0.90
        });
        $("#canvas").css({
            "width": $(window).width() * 0.99
        });
    }, 300);

    setTimeout(function () {
        // JSON_FILE is defined in the template
        $.getJSON(JSON_FILE, function(data){
            initialize(data);
        });
    }, 500);

});

