
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

    if (typeof text === "number") {
        return text;
    }

    text = '' + text;

    if (text.length < 25) {
        return text;
    }

    return ('' + text).slice(0, 20) + '...';

}



function draw(field, weight, fieldData, sumInfo, svgId) {

    var weight_label, weight_format;

    var nvData = {
        "key"    : "{0}".fmt(field),
        "values" : fieldData
    };

    nv.addGraph(function() {

        var chart = nv.models.discreteBarChart()
            .x(function(d) { return '"{0}"'.fmt(overflow(d[0])); })
            .y(function(d) { return d[1]; })
            .staggerLabels(true)
            .tooltips(true)
            .tooltipContent(function(key, x, y, e, graph) {
                sumInfo = parseFloat(sumInfo);
                e.value = parseFloat(e.value);

                var p = 100 * e.value / sumInfo;
                //console.log(field, x, y, p, e.value, sumInfo);
                return '<h4>{0}</h4><p><i><b>{1}</b>: '.fmt(key, x) +
                    '{0}% ({1}/{2})</i></p>'.fmt(p.toFixed(1),
                                                 e.value.toFixed(1),
                                                 sumInfo.toFixed(1));
            })
            .showValues(true);

        chart.xAxis.axisLabel(field);

        // If weight is null, format yAxis as integers
        if (weight === null) {
            chart.yAxis
                .tickFormat(d3.format('.0f'));
                //.axisLabel(null)
        } else {
            chart.yAxis
                .tickFormat(d3.format('.2f'));
                //.axisLabel(weight)
        }

        d3.select(svgId)
            .datum([nvData])
            .transition()
            .duration(500)
            .call(chart);

        nv.utils.windowResize(chart.update);

        return chart;

    });

}


function buildCanvas(id) {

    return '' +
        '<div id="{0}" class="span4">'.fmt(id) +
            '<svg style="height:250px; padding:10px;"></svg>' +
        '</div>';
}


function initialize(jsonData) {

    $('#title').html('(by {0})'.fmt(jsonData.weight === null ? 'volume' : jsonData.weight));

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
                 jsonData.sum_info[field],
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

