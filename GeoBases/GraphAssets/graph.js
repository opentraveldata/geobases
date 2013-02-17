
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

    var weight      = jsonData.meta.weight;
    var node_fields = jsonData.meta.node_fields;

    data = [];
    var node_id, node, node_data, edge_id, edge;

    for (node_id in jsonData.nodes) {
        if (jsonData.nodes.hasOwnProperty(node_id)) {

            node = jsonData.nodes[node_id];

            node_data = {
                'name'        : node_id,
                'id'          : node_id,
                'data'        : {
                    'weight' : node.weight,
                    "$color" : "#70A35E",
                    "$type"  : "circle",
                    "$dim"   : 11
                },
                'adjacencies' : []
            };

            for (edge_id in node.edges) {
                if (node.edges.hasOwnProperty(edge_id)) {

                    edge = node.edges[edge_id];

                    node_data.adjacencies.push({
                        'nodeFrom' : edge.from,
                        'nodeTo'   : edge.to,
                        'data'     : {
                            'weight' : edge.weight,
                            "$color" : "#F0F8FF",
                        }
                    });

                }
            }

            data.push(node_data);
        }
    }


    var fd = new $jit.ForceDirected({
        //id of the visualization container
        injectInto: 'infovis',
        //Enable zooming and panning
        //by scrolling and DnD
        Navigation: {
            enable: true,
        //Enable panning events only if we're dragging the empty
        //canvas (and not a node).
        panning: 'avoid nodes',
        zooming: 10 //zoom speed. higher is more sensible
        },
        // Change node and edge styles such as
        // color and width.
        // These properties are also set per node
        // with dollar prefixed data-properties in the
        // JSON structure.
        Node: {
            overridable: true
        },
        Edge: {
            overridable: true,
            color: '#23A4FF',
            lineWidth: 0.4
        },
        //Native canvas text styling
        Label: {
            type: 'HTML', //Native or HTML
            size: 10,
            style: 'bold'
        },
        //Add Tips
        Tips: {
            enable: true,
            onShow: function(tip, node) {
                //count connections
                var count = 0;
                node.eachAdjacency(function() { count++; });
                //display node info in tooltip
                tip.innerHTML = "<div class=\"tip-title\">" + node.name + "</div>"
                    + "<div class=\"tip-text\"><b>connections:</b> " + count + "</div>"
                    + "<div class=\"tip-text\"><b>weight:</b> " + node.data.weight + "</div>";
            }
        },
        // Add node events
        Events: {
            enable: true,
            type: 'Native',
            //Change cursor style when hovering a node
            onMouseEnter: function() {
                fd.canvas.getElement().style.cursor = 'move';
            },
            onMouseLeave: function() {
                fd.canvas.getElement().style.cursor = '';
            },
            //Update node positions when dragged
            onDragMove: function(node, eventInfo, e) {
                var pos = eventInfo.getPos();
                node.pos.setc(pos.x, pos.y);
                fd.plot();
            },
            //Implement the same handler for touchscreens
            onTouchMove: function(node, eventInfo, e) {
                $jit.util.event.stop(e); //stop default touchmove event
                this.onDragMove(node, eventInfo, e);
            },
            //Add also a click handler to nodes
            onClick: function(node) {
                if(!node) return;
                // Build the right column relations list.
                // This is done by traversing the clicked node connections.
                var html = "<h4>" + node.name + "</h4><b> connections:</b><ul><li>",
                    list = [];
                node.eachAdjacency(function(adj){
                    list.push(adj.nodeTo.name);
                });
                //append connections information
                console.log(html);
                console.log(list);
            }
        },
        //Number of iterations for the FD algorithm
        iterations: 200,
        //Edge length
        levelDistance: 130,
        // Add text to the labels. This method is only triggered
        // on label creation and only for DOM labels (not native canvas ones).
        onCreateLabel: function(domElement, node){
            domElement.innerHTML = node.name;
            var style = domElement.style;
            style.fontSize = "0.8em";
            style.color = "#ddd";
        },
        // Change node styles when DOM labels are placed
        // or moved.
        onPlaceLabel: function(domElement, node){
            var style = domElement.style;
            var left = parseInt(style.left);
            var top = parseInt(style.top);
            var w = domElement.offsetWidth;
            style.left = (left - w / 2) + 'px';
            style.top = (top + 10) + 'px';
            style.display = '';
        }
    });
    // load JSON data.
    fd.loadJSON(data);
    // compute positions incrementally and animate.
    fd.computeIncremental({
        iter: 40,
        property: 'end',
        onStep: function(perc){
            //console.log(perc + '% loaded...');
        },
        onComplete: function(){
            //console.log('done');
            fd.animate({
                modes: ['linear'],
                transition: $jit.Trans.Elastic.easeOut,
                duration: 2500
            });
        }
    });
}


$(document).ready(function() {

    $("#infovis").css({
        "height": $(window).height() * 0.90
    });

    $("#infovis").css({
        "width": $(window).width() * 0.99
    });

    // JSON_FILE is defined in the template
    $.getJSON(JSON_FILE, function(data){
        initialize(data);
    });

});

