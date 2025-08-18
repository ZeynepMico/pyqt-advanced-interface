# MapTabWidget.py DOSYASININ TAM VE DÜZELTİLMİŞ İÇERİĞİ

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QGroupBox, QVBoxLayout, QFormLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox
)
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from geopy.distance import geodesic
import pymap3d as pm

WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
WGS84_B = WGS84_A * (1 - WGS84_F)

WGS84_MODEL = pm.Ellipsoid(WGS84_A, WGS84_B)

class MapApiHandler(QObject):
    targetCoordsSet = pyqtSignal(float, float)

    @pyqtSlot(float, float)
    def onMapClick(self, lat, lon):
        self.targetCoordsSet.emit(lat, lon)

class MapTabWidget(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.route_points = []
        self.map_ready = False
        self.map_api_handler = MapApiHandler()
        self.initUI()
        self.init_map()

    def initUI(self):
        tab_layout = QHBoxLayout(self)

        controls_panel = QGroupBox("Map Controls")
        controls_layout = QVBoxLayout(controls_panel)
        controls_panel.setFixedWidth(300)
        controls_layout.setContentsMargins(5, 5, 5, 5)

        map_options_group = QGroupBox("Map View Options")
        map_options_layout = QFormLayout(map_options_group)
        self.comboMapLayer = QComboBox()
        self.comboMapLayer.addItems([
            "Standard (OSM)", "Uydu (Esri World Imagery)", "Topoğrafik (OpenTopoMap)"
        ])
        map_options_layout.addRow("Map Layer:", self.comboMapLayer)
        controls_layout.addWidget(map_options_group)

        inner_tab_widget = QTabWidget()
        location_tab = QWidget()
        location_layout = QVBoxLayout(location_tab)
        location_layout.setContentsMargins(2, 8, 2, 2)

        home_position_group = QGroupBox("Home Position")
        home_layout = QFormLayout(home_position_group)
        self.mapLatInput = QLineEdit("")
        self.mapLonInput = QLineEdit("")
        self.homeAltInput = QLineEdit("")
        home_layout.addRow("Latitude (Lat):", self.mapLatInput)
        home_layout.addRow("Longitude (Lon):", self.mapLonInput)
        home_layout.addRow("Altitude (m):", self.homeAltInput)
        self.btnUpdateMap = QPushButton("Show on Map")
        home_layout.addRow(self.btnUpdateMap)
        
        target_position_group = QGroupBox("Target Position")
        distance_layout = QFormLayout(target_position_group)
        self.targetLatInput = QLineEdit("")
        self.targetLonInput = QLineEdit("")
        self.targetAltInput = QLineEdit("")
        self.btnCalculateDistance = QPushButton("Calculate and Draw a Route")
        distance_layout.addRow("Target Latitude:", self.targetLatInput)
        distance_layout.addRow("Target Longitude:", self.targetLonInput)
        distance_layout.addRow("Target Altitude (m):", self.targetAltInput)
        distance_layout.addRow(self.btnCalculateDistance)
        
        self.lblDistanceResult = QLabel("Result: Waiting...")
        location_layout.addWidget(home_position_group)
        location_layout.addWidget(target_position_group)
        location_layout.addWidget(self.lblDistanceResult)
        location_layout.addStretch()

        simulation_tab = QWidget()
        simulation_layout = QVBoxLayout(simulation_tab)
        sim_group = QGroupBox("Simulation Controls")
        sim_buttons_layout = QVBoxLayout(sim_group)
        self.btnStartSim = QPushButton("Start Simulation")
        self.btnStopSim = QPushButton("Stop Simulation")
        sim_buttons_layout.addWidget(self.btnStartSim)
        sim_buttons_layout.addWidget(self.btnStopSim)
        simulation_layout.addWidget(sim_group)
        simulation_layout.addStretch()

        inner_tab_widget.addTab(location_tab, "Location")
        inner_tab_widget.addTab(simulation_tab, "Sim")
        controls_layout.addWidget(inner_tab_widget)

        self.lblCurrentCoords = QLabel("Current Location: Waiting...")
        self.lblCurrentCoords.setWordWrap(True)
        self.btnClearRoute = QPushButton("Clear All Routes")
        controls_layout.addWidget(self.lblCurrentCoords)
        controls_layout.addWidget(self.btnClearRoute)

        self.mapView = QWebEngineView()
        self.mapView.setMinimumSize(400, 400)
        
        self.channel = QWebChannel()
        self.channel.registerObject("mapApi", self.map_api_handler)
        self.mapView.page().setWebChannel(self.channel)

        right_panel = QGroupBox("Calculation Results")
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel.setFixedWidth(280)
        results_form_layout = QFormLayout()
        self.lblHomeEcefX = QLineEdit("N/A"); self.lblHomeEcefX.setReadOnly(True)
        self.lblHomeEcefY = QLineEdit("N/A"); self.lblHomeEcefY.setReadOnly(True)
        self.lblHomeEcefZ = QLineEdit("N/A"); self.lblHomeEcefZ.setReadOnly(True)
        results_form_layout.addRow("Home ECEF-X (m):", self.lblHomeEcefX)
        results_form_layout.addRow("Home ECEF-Y (m):", self.lblHomeEcefY)
        results_form_layout.addRow("Home ECEF-Z (m):", self.lblHomeEcefZ)
        self.lblTargetEcefX = QLineEdit("N/A"); self.lblTargetEcefX.setReadOnly(True)
        self.lblTargetEcefY = QLineEdit("N/A"); self.lblTargetEcefY.setReadOnly(True)
        self.lblTargetEcefZ = QLineEdit("N/A"); self.lblTargetEcefZ.setReadOnly(True)
        results_form_layout.addRow("Target ECEF-X (m):", self.lblTargetEcefX)
        results_form_layout.addRow("Target ECEF-Y (m):", self.lblTargetEcefY)
        results_form_layout.addRow("Target ECEF-Z (m):", self.lblTargetEcefZ)
        self.lblAzimuth = QLineEdit("N/A"); self.lblAzimuth.setReadOnly(True)
        self.lblElevation = QLineEdit("N/A"); self.lblElevation.setReadOnly(True)
        self.lblSlantRange = QLineEdit("N/A"); self.lblSlantRange.setReadOnly(True)
        results_form_layout.addRow("Azimuth (°):", self.lblAzimuth)
        results_form_layout.addRow("Elevation (°):", self.lblElevation)
        results_form_layout.addRow("3D Distance (m):", self.lblSlantRange)
        right_panel_layout.addLayout(results_form_layout)
        right_panel_layout.addStretch()

        tab_layout.addWidget(controls_panel)
        tab_layout.addWidget(self.mapView, 1)
        tab_layout.addWidget(right_panel)

        self.btnUpdateMap.clicked.connect(self.manual_update_map)
        self.btnCalculateDistance.clicked.connect(self.calculate_distance_and_draw_route)
        self.btnClearRoute.clicked.connect(self.clear_route)
        self.btnStartSim.clicked.connect(self.main_window.simulator.start)
        self.btnStopSim.clicked.connect(self.main_window.simulator.stop)
        self.comboMapLayer.currentIndexChanged.connect(self.change_map_layer)
        self.mapView.loadFinished.connect(self.on_map_load_finished)
        self.map_api_handler.targetCoordsSet.connect(self.update_target_fields)

    def init_map(self):
        qwebchannel_js_path = "qrc:///qtwebchannel/qwebchannel.js"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>QtMap Integration</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <script src="{qwebchannel_js_path}"></script>
            <style> #map {{ height: 100vh; }} body {{ padding: 0; margin: 0; }} </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map, currentLayer, baseLayers;
                var marker, targetMarker, liveRouteLine, staticRouteLine;
                var mapApi;
                var mapInitialized = false;

                window.onload = function() {{
                    new QWebChannel(qt.webChannelTransport, function (channel) {{
                        mapApi = channel.objects.mapApi;
                        console.log("JS: Python 'mapApi' nesnesi başarıyla yüklendi.");
                    }});
                }};

                function initializeMap() {{
                    try {{
                        baseLayers = {{
                            'standard': L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '&copy; OpenStreetMap' }}),
                            'satellite': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{ attribution: '&copy; Esri' }}),
                            'topo': L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '&copy; OpenTopoMap' }})
                        }};
                        map = L.map('map').setView([41.0, 29.0], 5);
                        currentLayer = baseLayers.standard;
                        currentLayer.addTo(map);

                        marker = L.marker([0, 0]).addTo(map).bindPopup("Live Position");
                        var targetIcon = L.icon({{ iconUrl: 'https://raw.githack.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png', shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png', iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41] }});
                        targetMarker = L.marker([0, 0], {{ opacity: 0, icon: targetIcon }}).addTo(map);
                        liveRouteLine = L.polyline([], {{color: 'blue', weight: 5}}).addTo(map);
                        staticRouteLine = L.polyline([], {{color: 'red'}}).addTo(map);

                        map.on('click', function(e) {{
                            if (mapApi) {{
                                var lat = e.latlng.lat;
                                var lon = e.latlng.lng;
                                mapApi.onMapClick(lat, lon);
                            }}
                        }});
                        mapInitialized = true; 
                    }} catch (e) {{
                        console.error("Map initialization failed: ", e);
                        mapInitialized = false;
                    }}
                }}
                
                initializeMap();

                setTimeout(function() {{
                    if (!mapInitialized) {{
                        var mapDiv = document.getElementById('map');
                        mapDiv.innerHTML = `
                            <div style="text-align: center; padding-top: 50px; font-family: sans-serif;">
                                <h2 style="color: #d9534f;">Map Layer Error</h2>
                                <p>Map layers could not be loaded. This might be due to a network issue or a problem with the map provider.</p>
                            </div>`;
                        mapDiv.style.backgroundColor = '#f0f0f0';
                    }}
                }}, 5000);
                
                // **** İŞTE DÜZELTİLEN SATIR BURASI ****
                // 'key' yerine 'layerKey' kullanıldı.
                function changeBaseLayer(layerKey) {{
                    if (map.hasLayer(currentLayer)) {{
                        map.removeLayer(currentLayer);
                    }}
                    var newLayer = baseLayers[layerKey]; // Hata buradaydı: 'key' yerine 'layerKey' olmalı
                    if (newLayer) {{
                        newLayer.addTo(map);
                        currentLayer = newLayer;
                    }}
                }}
                
                function updateMap(lat, lon) {{ if (!mapInitialized) return; var newLatLng = new L.LatLng(lat, lon); marker.setLatLng(newLatLng); map.panTo(newLatLng); }}
                function addPointToRoute(lat, lon) {{ if (!mapInitialized) return; liveRouteLine.addLatLng([lat, lon]); }}
                function drawStaticRoute(lat1, lon1, lat2, lon2) {{ if (!mapInitialized) return; var pointList = [new L.LatLng(lat1, lon1), new L.LatLng(lat2, lon2)]; staticRouteLine.setLatLngs(pointList); map.fitBounds(staticRouteLine.getBounds()); }}
                function showTargetMarker(lat, lon) {{ if (!mapInitialized) return; var newLatLng = new L.LatLng(lat, lon); targetMarker.setLatLng(newLatLng); targetMarker.setOpacity(1); targetMarker.bindPopup("Target Position"); }}
                function clearAllRoutes() {{ if (!mapInitialized) return; liveRouteLine.setLatLngs([]); staticRouteLine.setLatLngs([]); targetMarker.setOpacity(0); }}
            </script>
        </body>
        </html>
        """
        self.mapView.setHtml(html_content)

    def on_map_load_finished(self, success):
        if success:
            self.map_ready = True
            self.main_window.append_to_log("Map engine successfully loaded and ready.", color='green')
        else:
            self.map_ready = False
            error_message = "Map engine failed to load. Please check your internet connection."
            self.main_window.append_to_log(error_message, color='red')
            QMessageBox.warning(self, "Map Loading Error", "The map could not be loaded.\nAn internet connection is required for map features.")
            fallback_html = """
            <!DOCTYPE html><html><head><style>body{display:flex;justify-content:center;align-items:center;height:100vh;margin:0;font-family:sans-serif;background-color:#f0f0f0;}.container{text-align:center;}h2{color:#d9534f;}</style></head>
            <body><div class="container"><h2>Map Could Not Be Loaded</h2><p>Please check your internet connection.</p></div></body></html>
            """
            self.mapView.setHtml(fallback_html)

    @pyqtSlot(float, float)
    def update_target_fields(self, lat, lon):
        self.targetLatInput.setText(f"{lat:.6f}")
        self.targetLonInput.setText(f"{lon:.6f}")
        self.main_window.append_to_log(f"Target position set from map: Lat: {lat:.4f}, Lon: {lon:.4f}", color="purple")
        if self.map_ready:
            self.mapView.page().runJavaScript(f"showTargetMarker({lat}, {lon});")

    def move_marker(self, lat, lon):
        if not self.map_ready: return
        self.mapView.page().runJavaScript(f"updateMap({lat}, {lon});")
        self.lblCurrentCoords.setText(f"Current Location:\nLatitude: {lat:.6f}\nLongitude: {lon:.6f}")

    def add_point_to_live_route(self, lat, lon):
        if not self.map_ready: return
        self.route_points.append((lat, lon))
        self.mapView.page().runJavaScript(f"addPointToRoute({lat}, {lon});")
        self.main_window.append_to_log(f"Live position received: Lat: {lat}, Lon: {lon}", color='orange')

    def manual_update_map(self):
        try:
            lat = float(self.mapLatInput.text())
            lon = float(self.mapLonInput.text())
            self.move_marker(lat, lon)
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numbers for latitude and longitude.")

    def calculate_distance_and_draw_route(self):
        try:
            lat1, lon1, alt1 = float(self.mapLatInput.text()), float(self.mapLonInput.text()), float(self.homeAltInput.text())
            lat2, lon2, alt2 = float(self.targetLatInput.text()), float(self.targetLonInput.text()), float(self.targetAltInput.text())
            
            distance_km = geodesic((lat1, lon1), (lat2, lon2)).km
            self.lblDistanceResult.setText(f"Surface Distance: {distance_km:.2f} km")
            
            x_home, y_home, z_home = pm.geodetic2ecef(lat1, lon1, alt1, ell=WGS84_MODEL)
            x_target, y_target, z_target = pm.geodetic2ecef(lat2, lon2, alt2, ell=WGS84_MODEL)
            az, el, rng = pm.geodetic2aer(lat2, lon2, alt2, lat1, lon1, alt1, ell=WGS84_MODEL)
            
            self.lblHomeEcefX.setText(f"{x_home:,.2f}")
            self.lblHomeEcefY.setText(f"{y_home:,.2f}")
            self.lblHomeEcefZ.setText(f"{z_home:,.2f}")
            self.lblTargetEcefX.setText(f"{x_target:,.2f}")
            self.lblTargetEcefY.setText(f"{y_target:,.2f}")
            self.lblTargetEcefZ.setText(f"{z_target:,.2f}")
            self.lblAzimuth.setText(f"{az:.4f}")
            self.lblElevation.setText(f"{el:.4f}")
            self.lblSlantRange.setText(f"{rng:,.2f}")
            
            if self.map_ready:
                self.mapView.page().runJavaScript(f"drawStaticRoute({lat1}, {lon1}, {lat2}, {lon2});")
                self.mapView.page().runJavaScript(f"showTargetMarker({lat2}, {lon2});")
            self.main_window.append_to_log(f"Calculation complete. Azimuth: {az:.2f}°, Elevation: {el:.2f}°", color='purple')
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numbers for all fields.")
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"An error occurred: {e}")

    def clear_route(self):
        self.route_points.clear()
        if self.map_ready:
            self.mapView.page().runJavaScript("clearAllRoutes();")
        self.main_window.append_to_log("All routes cleared from map.", color='orange')
        for field in [self.lblHomeEcefX, self.lblHomeEcefY, self.lblHomeEcefZ,
                      self.lblTargetEcefX, self.lblTargetEcefY, self.lblTargetEcefZ,
                      self.lblAzimuth, self.lblElevation, self.lblSlantRange]:
            field.setText("N/A")
        self.lblDistanceResult.setText("Result: Waiting...")

    def change_map_layer(self):
        if not self.map_ready: return
        layer_name = self.comboMapLayer.currentText()
        # Python tarafında 'key' adında bir değişken tanımlanıyor
        if "Uydu" in layer_name: key = 'satellite'
        elif "Topoğrafik" in layer_name: key = 'topo'
        else: key = 'standard'
        # Bu 'key' değişkeni JS'e 'layerKey' olarak gönderiliyor
        self.mapView.page().runJavaScript(f"changeBaseLayer('{key}');")
        self.main_window.append_to_log(f"Map layer changed to: {layer_name}", color='blue')