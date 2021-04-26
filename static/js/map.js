function deleteMap() {
    try {$("#map").remove()} catch(e) {}
    $("#mapParent").empty()
}
function createMap(markers) {
    try {$("#map").remove()} catch(e) {}
    $("#mapParent").empty().append('<div id="map"></div>')
    var map = new L.Map('map');
    
    L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
        maxZoom: 18
    }).addTo(map);
    map.attributionControl.setPrefix('');
    
    //Loop through the markers array
    var avglon = 0, avglat = 0;
    for (var i=0; i<markers.length; i++) {
        var lat = parseFloat(markers[i][0]),
            lon = parseFloat(markers[i][1]);
        console.log(lat, lon, markers, i)
        avglat += lat;
        avglon += lon;
        
        var popupText = markers[i][2];

        var markerLocation = new L.LatLng(lat, lon);
        var marker = new L.Marker(markerLocation);
        map.addLayer(marker);

        marker.bindPopup(popupText);
    }
    
    var center = new L.LatLng(avglat / markers.length, avglon / markers.length); 
    map.setView(center, 13);
}