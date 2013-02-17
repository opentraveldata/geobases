
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

    if (jsonData.points.length === 0){
        alert('No data available.');
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

    var i, j, e;
    var row = '<tr>';

    for (j=0 ; j<f ; j++) {
        row += '<td><i>{0}</i></td>'.fmt(fields[j]);
    }

    row += '</tr>';

    $('#canvas table thead').append(row);

    // Load the data
    for (i=0 ; i<n ; i++) {

        e = jsonData.points[i];

        row = '<tr style="height:25px;">';

        for (j=0 ; j<f ; j++) {
            field = fields[j];
            row += '<td>{0}</td>'.fmt(overflow(e[field]));
        }

        row += '</tr>';

        $('#canvas table tbody').append(row);

    }

    $('#canvas table').dataTable({
        /* Define where objects are displayed
           f: filtering input
           i: general information
           t: table*/
        /* Define number of results displayed */
        "iDisplayLength": 20,
        /* Define the dropdown for results pagination */
        "aLengthMenu": [[10, 20, 50, -1], [10, 20, 50, "All"]]
    });

}

$(document).ready(function() {

    $("#canvas").css({
        "height": $(window).height()*0.90
    });

    $("#canvas").css({
        "width": $(window).width()*0.99
    });

    // JSON_FILE is defined in the template
    $.getJSON(JSON_FILE, function(data){
        initialize(data);
    });

});

