
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



function draw(o) {

    var weight_label, weight_format;

    var nvData = {
        "key"    : "{0}".fmt(o.field),
        "values" : o.counters
    };

    nv.addGraph(function() {

        var chart = nv.models.discreteBarChart()
            .x(function(d) { return '"{0}"'.fmt(overflow(d[0])); })
            .y(function(d) { return d[1]; })
            .staggerLabels(true)
            .tooltips(true)
            .tooltipContent(function(key, x, y, e, graph) {
                sumInfo = parseFloat(o.sumInfo);
                e.value = parseFloat(e.value);

                var p = 100 * e.value / sumInfo;
                //console.log(o.field, x, y, p, e.value, o.sumInfo);
                return '<h4>{0}</h4><p><i><b>{1}</b>: '.fmt(key, x) +
                    '{0}% ({1}/{2})</i></p>'.fmt(p.toFixed(1),
                                                 e.value.toFixed(1),
                                                 o.sumInfo.toFixed(1));
            })
            .showValues(true);

        chart.xAxis.axisLabel(o.field);

        // If o.weight is null, format yAxis as integers
        if (o.weight === null) {
            chart.yAxis
                .tickFormat(d3.format('.0f'));
                //.axisLabel(null)
        } else {
            chart.yAxis
                .tickFormat(d3.format('.2f'));
                //.axisLabel(o.weight)
        }

        d3.select(o.svgId)
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
    var fields = [];

    for (field in jsonData.counters){
        if (jsonData.counters.hasOwnProperty(field)) {
            fields.push(field);
        }
    }
    fields.sort();

    var i, c;
    for (i=0, c=fields.length; i<c; i++) {

        field = fields[i];
        id = "canvas_{0}".fmt(field);

        // Adding div and svg
        $("#container").append(buildCanvas(id));

        // Drawing
        draw({
            'field'    : field,
            'weight'   : jsonData.weight,
            'counters' : jsonData.counters[field],
            'sumInfo'  : jsonData.sum_info[field],
            'svgId'    : '#{0} svg'.fmt(id)
        });
    }
}


$(document).ready(function() {

    // JSON_FILE is defined in the template
    $.getJSON(JSON_FILE, function(data){
        initialize(data);
    });

});

