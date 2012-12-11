
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

    var mapOptions = {
        zoom      : 2,
        center    : parisLocation,
        mapTypeId : google.maps.MapTypeId.ROADMAP
    };

    // Create the map
    var map = new google.maps.Map(document.getElementById("canvas"), mapOptions);

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
    var point_color = jsonData.meta.point_color;
    var point_size  = jsonData.meta.point_size;
    var base_icon   = jsonData.meta.base_icon;
    var icon_type   = jsonData.meta.icon_type;

    var with_markers = icon_type   !== null;
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
    document.closeInfoWindow = function() {
        var i, c;
        for (i=0, c=markersArray.length; i<c; i++) {
            infowindow.close(map, markersArray[i]);
        }
    };

    var i, j, c, e, s, latlng, marker, circle, ccol;
    var max_value = 0;

    // Load the data
    for (i=0 ; i<n ; i++) {

        e = jsonData.points[i];

        latlng = new google.maps.LatLng(e.lat, e.lng);

        if (isNaN(latlng.lat()) || isNaN(latlng.lng())) {
            //console.log(e.__lab__ + ' had no position: ' + e.lat + e.lng)
            continue;
        }

        marker = new google.maps.Marker({
            position    : latlng,
            //animation   : google.maps.Animation.DROP,
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
        '<div class="infowindow" style="min-width:400px; max-height:300px; overflow-y:auto;">' +
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

        // Saving marker
        markersArray.push(marker);
        bounds.extend(latlng);
        centersArray.push(latlng);

        // We compute the biggest __siz__ value
        s    = parseFloat(e.__siz__);
        ccol = getCircleColor(e.__col__);

        if ((! isNaN(s)) && s > 0) {
            if (s > max_value) {
                max_value = s;
            }
            circle = new google.maps.Circle({
                center          : latlng,
                radius          : 0,
                strokeColor     : ccol,
                strokeOpacity   : 0.25,
                strokeWeight    : 2,
                fillColor       : ccol,
                fillOpacity     : 0.15,
                map             : map,
                clickable       : true
            });

            // Augmenting the marker type
            circle.size = s;
            circle.help = ' ' +
            '<div>' +
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
    var r = 0.075;

    google.maps.event.addListener(map, 'idle', function() {
        // We compute the top radius given the map size
        var mapBounds = map.getBounds();
        var sw = mapBounds.getSouthWest();
        var ne = mapBounds.getNorthEast();

        var biggest = r * 1000 * haversine(sw.lat(), sw.lng(), ne.lat(), ne.lng());
        //var biggest = R * 1000;

        for (i=0, c=circlesArray.length; i<c; i++) {
            circle = circlesArray[i];
            circle.setRadius(Math.sqrt(circle.size / max_value) * biggest);
        }

    });

    // If no markers, we avoid a big
    // drift to the pacific ocean :)
    if (n >= 2) {
        map.fitBounds(bounds);
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

    $('#lines').click(function() {
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
        $(this).text('Lines (' + state + ')');
    });

    // Fill legend
    var cat, vol, col;
    var msg = ' ' +
    '<table style="width:100%; align:center;">' +
        '<tr><th><i>Icon</i></th><th><i>Color</i></th><th><i>Category</i></th><th><i>Volume</i></th></th>';

    var line = '<tr><td>{0}</td><td>{1}</td><td>{2} "{3}"</td><td>{4} points</td></tr>';

    for (i=0, c=jsonData.categories.length; i<c ;i++) {
        cat  = jsonData.categories[i][0];
        col  = jsonData.categories[i][1].color;
        vol  = jsonData.categories[i][1].volume;

        if (with_markers) {
            msg += line.fmt('<img src="{0}" alt="No icon"/>'.fmt(getMarkerIcon(col)), col, point_color, cat, vol);
        } else {
            msg += line.fmt('No icon', col, point_color, cat, vol);
        }
    }
    msg += '</table>';

    // General information
    $('#legendPopup').html(msg);
    $('#info').html('{0} points, {1} <i>{2}</i> categorie(s), <i>{3}</i> max: {4}'.fmt(n, jsonData.categories.length, point_color, point_size, max_value));

}

$(document).ready(function() {

    $("#canvas").css({
        "height": $(window).height()*0.90
    });

    $("#canvas").css({
        "width": $(window).width()*0.99
    });

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

    $('.popup').css({
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

    // Press Escape event!
    // Use keydown instead of keypress for webkit-based browsers
    $(document).keydown(function (e) {
        if (e.keyCode === 27) {
            disablePopup('#legendPopup');
            document.closeInfoWindow();
        }
    });

    $.getJSON(JSON_FILE, function(data){
        initialize(data);
    });

});

