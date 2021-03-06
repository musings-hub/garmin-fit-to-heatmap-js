__author__ = 'randomindividual'

import fitdecode
import logging
import os
import sys
import concurrent.futures

GENERATE_VANILLA_INCLUDE = False
OUTPUT_FILENAME = "heatmap-datapoints.js"
DEDUPE_OUTPUT = True
JS_TEMPLATE = """
<div id="map" style="height: 500px;"></div>
<script type="text/javascript" src="https://maps.googleapis.com/maps/api/js?key=GOOGLE_MAPS_API_KEY&amp;libraries=visualization"></script>

<script>
var heatmapData = [
  %s
];
var heatmapCenter = new google.maps.LatLng(46.798476, 8.231787);

map = new google.maps.Map(document.getElementById('map'), {
  center: heatmapCenter,
  zoom: 1,
  mapTypeId: 'roadmap'
});

var heatmap = new google.maps.visualization.HeatmapLayer({
  data: heatmapData
});
heatmap.setMap(map);
heatmap.set('radius', 20);
heatmap.set('maxIntensity', 6000);
heatmap.set('opacity', 0.6);
</script>
"""

def emit_js(fn): 
  logging.info("scheduled conversion: %s" % fn)
  with fitdecode.FitReader(fn, check_crc=fitdecode.CrcCheck.DISABLED) as fit:
    coords = set()
    for frame in fit:
      # we won't even try if this frame isn't a FitDataMessage
      if not isinstance(frame, fitdecode.FitDataMessage):
        continue

      # we'll rely on fit data being ordered in perfect
      # sequence for now.
      buf = {}
      for field in frame.fields:
        if not field.value:
          continue
        # https://docs.microsoft.com/en-us/previous-versions/windows/embedded/cc510650(v=msdn.10)?redirectedfrom=MSDN#remarks
        if "position_lat" == field.name:
          buf['lat'] = str(field.value * ( 180 / 2**31 ))
        if "position_long" == field.name:
          buf['long'] = str(field.value * ( 180 / 2**31 ))
        if "altitude" == field.name:
          buf['alt'] = str(field.value)
          if len(buf) == 3:
            coords.add(
              "new google.maps.LatLng(%s,%s),\n" % (buf['lat'], buf['long']))
          buf = {}
    if len(coords):
      logging.info("converted: %s" % fn)
      return "".join(coords)
    return False

with open(OUTPUT_FILENAME,'w') as fp:
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(emit_js, fp.path): fp.path for fp in os.scandir(sys.argv[1])}
    for future in concurrent.futures.as_completed(futures):
      try:
        data = future.result()
        if data:
          fp.write(data)
          fp.flush()
      except Exception as e:
        logging.warning("exception: %s" % (e))

if DEDUPE_OUTPUT:
  ul = set(open(OUTPUT_FILENAME).readlines())
  with open(OUTPUT_FILENAME, 'w') as fp:
    fp.writelines(ul)

if GENERATE_VANILLA_INCLUDE:
  with open(OUTPUT_FILENAME, 'r+') as fp:
    c = fp.read()
    fp.seek(0, 0)
    fp.write("var datapoints = [\n" + c + "];")
else:
  with open(OUTPUT_FILENAME, 'r+') as fp:
    c = fp.read()
    fp.seek(0,0)
    fp.write(JS_TEMPLATE % c)
