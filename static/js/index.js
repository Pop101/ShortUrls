function k2sc(key) {
    var num = Math.abs(crc32(key)) // why crc32? because it's short
    const bases = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
    var shortcode = ''
    while (num > 0) {
        shortcode = shortcode + bases.charAt(num % bases.length)
        num = Math.floor(num / bases.length)
    }
    return shortcode;
}

// Creation/Updating functionality
$('#create-id, #create-toggle-id, #create-url, #create-key').on('input propertychange', function () {
    var id = $('#create-toggle-id').is(":checked") ? $('#create-id').val() : k2sc($('#create-key').val())
    var preview = window.location.host + '/' + id.replaceAll(/[^\w.,!+()\[\]<>\{\}\|~"\':;*$%]+/gi,'');
    $('#create-preview').text(preview).attr('href', 'https://'+$('#create-preview').text())
    $('#create-id').val(id)
    $('#create-id').prop('disabled', !$('#create-toggle-id').is(':checked'))
})

var createViewer = new JSONViewer();
$('#create-json').append(createViewer.getContainer())
                       
createViewer.showJSON({status: 'OK', message: 'Shortlink Created', id: 'ID'})

// Create Button
$('#create-btn').click(function () {
     $.ajax({
        url: "/create",
        type: "POST",
        data: JSON.stringify({id: $('#create-id').val(), key: $("#create-key").val(), url: 'http://'+$("#create-url").val().replaceAll('http://', '').replaceAll('https://', '')}),
        dataType: "json",
        contentType : 'application/json',
        success: function (data) {
            createViewer.showJSON(data);
        },
    })
})

// Tracking functionality
$('#track-id, #track-key, #track-toggle-key, #track-btn').on('input propertychange', function () {
    var id = $('#track-id').val()
    var preview = window.location.host + '/' + id.replaceAll(/[^\w.,!+()\[\]<>\{\}\|~"\':;*$%]+/gi,'');
    $('#track-preview').text(preview).attr('href', 'https://'+$('#track-preview').text())
    $('#track-key').prop('disabled', !$('#track-toggle-key').is(':checked'))
})

var trackViewer = new JSONViewer();
$('#track-json').append(trackViewer.getContainer())
                       
trackViewer.showJSON({id: 'google', created: Math.floor((new Date()).getTime() / 1000), expires: 90*24*3600+Math.floor((new Date()).getTime() / 1000)})

// Track button sends response
$('#track-btn').click(function () {
    deleteMap();
    $.ajax({
        url: "/info/"+$('#track-id').val()+($("#track-key").val().length >= 3 ? '?key='+$("#track-key").val() : ''),
        type: "GET",
        success: function (data) {
            // show json
            trackViewer.showJSON(data);
        
            // parse map info if it exists
            if(!('log' in data)) return;
            
            mappoints = {}
            for(var i in data['log']) {
                if(!('location' in data['log'][i])) continue;
                
                var latlong = data['log'][i]['location']['latitude'] + ', ' + data['log'][i]['location']['longitude']
                if(latlong in mappoints) mappoints[latlong].push(data['log'][i]['ip'] + " at " + data['log'][i]['time']);
                else mappoints[latlong] = [];
            }
        
            // change map to list
            var markers = [];
            for (let [key, value] of Object.entries(mappoints)) {
                var lat = key.split(', ')[0];
                var lon = key.split(', ')[1];
                var text = value.join('<br>');
                markers.push([lat, lon, text])
            }
        
            // create map
            if(markers.length > 0) createMap(markers);
        },
    })
})

// Set preview initial values
$('#create-preview, #track-preview').text(window.location.host + '/id').attr('href', 'https://'+$('#create-preview').text())
//$('#create-preview, #track-preview')

// Universal ajax error listener
$(document).ajaxError(function(event, request, settings) {
    console.log(event, request, settings)
    $("#status").text(('Error ' + request.status + ': "' + request.responseText+'"').substring(0, 100));
    $('#statusBox').css('opacity', '1')
    $('#statusBox').attr('class', 'lowbar error')
    setTimeout(function() {
        $('#statusBox').css('opacity', '0')
    }, 5000)
});
$(document).ajaxSuccess(function(event, request, settings) {
    $("#status").text('Success')
    $('#statusBox').css('opacity', '1')
    $('#statusBox').attr('class', 'lowbar success')
    setTimeout(function() {
        $('#statusBox').css('opacity', '0')
    }, 5000)
})