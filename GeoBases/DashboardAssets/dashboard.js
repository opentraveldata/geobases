
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

function initialize(jsonData) {
}


$(document).ready(function() {

    $("#canvas").css({
        "height": ($(window).height() - 50) * 0.95
    });

    $("#canvas").css({
        "width": $(window).width() * 0.90
    });

    // JSON_FILE is defined in the template
    $.getJSON(JSON_FILE, function(data){
        initialize(data);
    });

});

