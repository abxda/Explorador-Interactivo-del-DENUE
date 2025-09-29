window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, latlng) {
            return L.circleMarker(latlng);
        },
        function1: function(feature) {
                const color = feature.properties.color;
                return {
                    fillColor: color,
                    color: color,
                    weight: 1,
                    fillOpacity: 0.8,
                    radius: 4
                };
            }

            ,
        function2: function(feature, layer) {
            if (feature.properties && feature.properties.nom_estab) {
                layer.bindTooltip(`${feature.properties.nom_estab} (${feature.properties.nombre_act})`);
            }
        }

    }
});