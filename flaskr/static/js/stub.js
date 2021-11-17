//
// Scripts
//
document.addEventListener("DOMContentLoaded", function (event) {
  let BASE_API = "http://localhost:5000/";
  let div_map = document.getElementById("id_map");
  let map = null;
  let sidebar = document.getElementById("sidebar");
  let main_header = document.getElementById("main-header");

  let selected = null;
  let status = document.getElementById("status");

  var myModal = new bootstrap.Modal(document.getElementById("myModal"));

  let highlightStyle = new ol.style.Style({
    fill: new ol.style.Fill({
      color: "rgba(255,255,255,0.7)",
    }),
    stroke: new ol.style.Stroke({
      color: "#9933CC",
      width: 3,
    }),
  });

  let attribution = new ol.control.Attribution({
    collapsible: false,
  });
  const centerCoordinates = ol.proj.fromLonLat([-3.74922, 40.463667]);
  const initialZoom = 10;

  let view = new ol.View({
    center: ol.proj.transform([-3.74922, 40.463667], "EPSG:4326", "EPSG:3857"),
    zoom: initialZoom,
  });

  let map_controls = ol.control.defaults().extend([
    attribution,
    new ol.control.ScaleLine({
      className: "ol-scale-line",
      target: document.getElementById("scale-line"),
    }),
  ]);

  let map_layers = [
    new ol.layer.Group({
      title: "Base maps",
      slug: "base_map",
      layers: [
        new ol.layer.Tile({
          title: "Base maps",
          source: new ol.source.OSM(),
        }),
      ],
    }),
  ];
  map = new ol.Map({
    controls: ol.control.defaults({ attribution: false }).extend([attribution]),
    projection: new ol.proj.Projection("EPSG:4326"),
    units: "m",
    target: "id_map",
    layers: map_layers,
    view: view,
  });

  function getLayer(code) {
    var BreakException = {};
    let layer = null;
    try {
      map.getLayers().forEach(function (el) {
        //console.log(`layer: ${el.get("code")}`);
        if (el.get("code") === code) {
          layer = el;
          throw BreakException;
        }
      });
    } catch (e) {
      if (e !== BreakException) {
        throw e;
      }
    }
    return layer;
  }

  function centerTo(code) {
    let tmp_layer = getLayer(code);
    if (tmp_layer) {
      tmp_layer.setStyle(highlightStyle);
      let source = tmp_layer.getSource();
      var feature = source.getFeatures()[0];
      var point = feature.getGeometry();
      view.fit(point);
    }
  }

  function drawPostalCode(postalCode) {
    let source = new ol.source.Vector({
      format: new ol.format.GeoJSON(),
      url: postalCode.geo_url,
    });

    var vector = new ol.layer.Vector({
      source: source,
    });
    vector.set("code", postalCode.code);
    map.addLayer(vector);
    //centerTo(postalCode.code);
  }

  function fetchPostalCodes() {
    let urlPostalCodes = "./api/v2/postal_codes/";
    const arrayPostalCodes = fetch(urlPostalCodes)
      .then((res) => res.json())
      .then((response) => {
        const data = response;
        return data;
      })
      .then((data) => {
        data.features.forEach(function (el) {
          let source = new ol.source.Vector({
            features: new ol.format.GeoJSON().readFeatures(el, {
              dataProjection: "EPSG:4326",
              featureProjection: "EPSG:3857",
            }),
          });
          var vector = new ol.layer.Vector({
            source: source,
          });
          vector.set("code", el.properties.code);
          map.addLayer(vector);
        });
      });
  }
  fetchPostalCodes();

  map.on("pointermove", function (e) {
    if (selected !== null) {
      selected.setStyle(undefined);
      selected = null;
    }

    map.forEachFeatureAtPixel(e.pixel, function (f) {
      selected = f;
      f.setStyle(highlightStyle);
      return true;
    });

    if (selected) {
      let code = "";
      if (selected.get("code")) {
        code = "ZIPCODE: " + selected.get("code");
      }
      if (status) {
        status.innerHTML = code;
      }
      document.body.style.cursor = "pointer";
    } else {
      if (status) {
        status.innerHTML = "&nbsp;";
      }
      document.body.style.cursor = "inherit";
    }
  });

  map.on("singleclick", function (e) {
    if (selected !== null) {
      selected.setStyle(undefined);
      selected = null;
    }

    map.forEachFeatureAtPixel(e.pixel, function (f) {
      selected = f;
      f.setStyle(highlightStyle);
      return true;
    });

    let modalTitle = "Turnover by age and gender";
    if (selected) {
      geo_stats_url = selected.get("geo_stats_url");
      if (geo_stats_url) {
        fetch(geo_stats_url)
          .then((res) => res.json())
          .then((response) => {
            const data = response;
            return data;
          })
          .then((data) => {
            popupContent = data.html;
            myModalContent.innerHTML = popupContent;
            myModal.show();
          });
      } else {
        let coordinate = e.coordinate;
        let hdms = ol.coordinate.toStringHDMS(ol.proj.toLonLat(coordinate));
        let popupContent =
          "<p>ZIPCODE:  " +
          selected.get("code") +
          "</p><code>" +
          hdms +
          "</code><br />";
        myModalTitle.innerHTML = modalTitle;
        myModalContent.innerHTML = popupContent;
        overlay.setPosition(coordinate);
        myModal.show();
      }
    }
  });

  function check_map_height() {
    let new_width = window.innerWidth - sidebar.clientWidth;
    let new_height = window.innerHeight - main_header.clientHeight;
    div_map.clientWidth = new_width;
    div_map.style.width = new_width + "px";

    div_map.clientHeight = new_height;
    div_map.style.height = new_height + "px";
    if (map) {
      setTimeout(function () {
        map.updateSize();
      }, 200);
    }
  }

  new ResizeObserver(check_map_height).observe(div_map);
  window.onresize = check_map_height;
  check_map_height();
});
