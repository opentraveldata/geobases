
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


function drawNumerical(o) {

    var nvData = {
        "key"    : "{0}".fmt(o.field),
        "values" : []
    };

    var i, c;
    for (i=0, c=o.density.length; i<c; i++) {
        nvData.values.push({
            'x' : o.density[i][0],
            'y' : o.density[i][1]
        });
    }

    nv.addGraph(function() {

        var chart = nv.models.lineChart();

        chart.xAxis.axisLabel("{0} density".fmt(o.field));
        chart.tooltips(true)
            .tooltipContent(function(key, x, y, e, graph) {
                //console.log(o.field, x, y, e);
                return '<h4>{0}</h4><p><i><b>"<= {1}" category</b>: '.fmt(key, x) +
                    '{0} points</i></p>'.fmt(y);
            });

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


function buildCanvas(id, grid_size) {

    return '' +
        '<div id="{0}" class="span{1}">'.fmt(id, grid_size) +
            '<svg style="height:250px; padding:10px;"></svg>' +
        '</div>';
}


function initialize(jsonData) {

    $('#title').html('(by {0})'.fmt(jsonData.weight === null ? 'volume' : jsonData.weight));

    var id, field, grid_size;
    var fields = [];
    var num_fields = [];

    for (field in jsonData.counters){
        if (jsonData.counters.hasOwnProperty(field)) {
            fields.push(field);
        }
    }
    fields.sort();

    for (field in jsonData.densities){
        if (jsonData.densities.hasOwnProperty(field)) {
            num_fields.push(field);
        }
    }

    var total_graphs = fields.length + num_fields.length;

    if (total_graphs > 12) {
        grid_size = 4;
    } else if (total_graphs > 4) {
        grid_size = 6;
    } else {
        grid_size = 12;
    }

    var i, c;
    for (i=0, c=fields.length; i<c; i++) {

        field = fields[i];
        id = "canvas_{0}".fmt(field);

        // Adding div and svg
        $("#container").append(buildCanvas(id, grid_size));

        // Drawing
        draw({
            'field'    : field,
            'weight'   : jsonData.weight,
            'counters' : jsonData.counters[field],
            'sumInfo'  : jsonData.sum_info[field],
            'svgId'    : '#{0} svg'.fmt(id)
        });

        // Drawing numeric fields
        if (jsonData.densities.hasOwnProperty(field)) {

            // Special id
            id = id + '_num';

            // Adding div and svg
            $("#container").append(buildCanvas(id, grid_size));

            // Drawing
            drawNumerical({
                'field'    : field,
                'weight'   : jsonData.weight,
                'density'  : jsonData.densities[field],
                'svgId'    : '#{0} svg'.fmt(id)
            });

        }
    }

}


$(document).ready(function() {

    // JSON_FILE is defined in the template
    $.getJSON(JSON_FILE, function(data){
        initialize(data);
    });

});

