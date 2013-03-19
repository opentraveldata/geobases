
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


function draw(field, weight, fieldData, svgId) {

    var weight_label, weight_format;

    var nvData = {
        "key"    : "Bar chart for {0}".fmt(field),
        "values" : fieldData
    };

    nv.addGraph(function() {

        var chart = nv.models.discreteBarChart()
            .x(function(d) { return d[0] })
            .y(function(d) { return d[1] })
            .staggerLabels(true)
            .tooltips(false)
            .showValues(true);

        chart.xAxis.axisLabel(field);

        if (weight !== null) {
            weight_label = weight;
            weight_format = ',.2f';

            chart.yAxis
                .axisLabel(weight_label)
                .tickFormat(d3.format(weight_format));
        }


        d3.select(svgId)
            .datum([nvData])
            .transition()
            .duration(500)
            .call(chart);

        nv.utils.windowResize(chart.update);

        // Custom
        $('.nv-axisMaxMin').attr('display', 'none');
        $('.nv-y .tick').attr('display', 'none');
        return chart;

    });

}


function buildCanvas(id) {

    return '' +
        '<div id="{0}" class="span4">'.fmt(id) +
            '<svg style="height:300px; padding:10px;"></svg>' +
        '</div>';
}


function initialize(jsonData) {

    var id, field;

    for (field in jsonData.counters){
        if (jsonData.counters.hasOwnProperty(field)) {

            id = "canvas_{0}".fmt(field);

            // Adding div and svg
            $("#container").append(buildCanvas(id));

            // Drawing
            draw(field,
                 jsonData.weight,
                 jsonData.counters[field],
                 '#{0} svg'.fmt(id));
        }
    }
}


$(document).ready(function() {

    // JSON_FILE is defined in the template
    $.getJSON(JSON_FILE, function(data){
        initialize(data);
    });

});

