# --- 0. IMPORTACIONES ---
import logging
import sys
from io import StringIO
from pathlib import Path


import dash_leaflet as dl
import duckdb
import geopandas as gpd
import pandas as pd
import plotly.express as px
from dash.dependencies import Input, Output, State
from dash_extensions.javascript import assign

from dash import dcc, html, no_update, ctx
from dash_extensions.enrich import DashProxy

# --- 1. CONFIGURACIÓN Y LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'censo_denue.duckdb'
SCIAN_CSV_PATH = BASE_DIR / 'scian_mapa_limpio.csv'

try:
    scian_df = pd.read_csv(SCIAN_CSV_PATH)
    scian_cols = ['sector_codigo', 'subsector_codigo', 'rama_codigo', 'subrama_codigo', 'clase_codigo']
    for col in scian_cols:
        if col in scian_df.columns:
            scian_df[col] = scian_df[col].astype(str).str.strip()
    logging.info(f"Archivo SCIAN cargado correctamente con {len(scian_df)} filas.")
except FileNotFoundError:
    logging.warning(f"No se encontró el archivo {SCIAN_CSV_PATH}.")
    scian_df = pd.DataFrame()
except Exception as e:
    logging.error(f"Error cargando SCIAN: {e}")
    scian_df = pd.DataFrame()

def get_db_connection():
    return duckdb.connect(database=str(DB_PATH), read_only=True)

def get_initial_states():
    try:
        with get_db_connection() as con:
            states = con.execute("SELECT DISTINCT entidad FROM denue ORDER BY entidad").fetchdf()['entidad'].tolist()
        logging.info(f"Estados cargados: {len(states)}.")
        return states
    except Exception as e:
        logging.error(f"Error obteniendo estados: {e}")
        return []

# --- 2. FUNCIONES AUXILIARES, CONSTANTES Y COLORES ---
COLS_TO_LABELS = {'per_ocu': 'Personal Ocupado'}
PER_OCU_ORDER = [
    '0 a 5 personas', '6 a 10 personas', '11 a 30 personas',
    '31 a 50 personas', '51 a 100 personas', '101 a 250 personas',
    '251 y más personas'
]
PER_OCU_COLORS = {
    '0 a 5 personas': '#1f77b4',
    '6 a 10 personas': '#ff7f0e',
    '11 a 30 personas': '#2ca02c',
    '31 a 50 personas': '#d62728',
    '51 a 100 personas': '#9467bd',
    '101 a 250 personas': '#8c564b',
    '251 y más personas': '#e377c2',
}

# PASO 1: CREACIÓN - Función para pointToLayer. Su única misión es crear un circleMarker.
assign_point_to_layer = assign("function(feature, latlng){return L.circleMarker(latlng);}")

# PASO 2: ESTILO - Función para style. Su misión es colorear y dar estilo al objeto ya creado.
assign_style = assign("""
function(feature){
    const color = feature.properties.color;
    return {
        fillColor: color,
        color: color,
        weight: 1,
        fillOpacity: 0.8,
        radius: 4
    };
}
""")

# PASO 3: INTERACTIVIDAD - Función para onEachFeature. Su misión es añadir el tooltip.
assign_on_each_feature = assign("""
function(feature, layer){
    if (feature.properties && feature.properties.nom_estab) {
        layer.bindTooltip(`${feature.properties.nom_estab} (${feature.properties.nombre_act})`);
    }
}
""")

def generate_graph(df, x_col, color_col):
    if df.empty or x_col not in df.columns or color_col not in df.columns:
        return create_empty_graph("No hay datos para mostrar.")
    grouping_cols = list(set([x_col, color_col]))
    gb_df = df.groupby(grouping_cols).size().reset_index(name='count')

    if x_col == 'per_ocu':
            gb_df[x_col] = pd.Categorical(gb_df[x_col], categories=PER_OCU_ORDER, ordered=True)
            gb_df = gb_df.sort_values(x_col)

    fig = px.bar(gb_df, x=x_col, y='count', color=color_col, template='plotly_white', color_discrete_map=PER_OCU_COLORS)
    fig.update_layout(
        xaxis={'tickmode': 'linear'}, margin={'l': 10, 'r': 10, 't': 30, 'b': 10}, height=300,
        legend_title_text=COLS_TO_LABELS.get(color_col, color_col)
    )
    fig.update_xaxes(title_text=COLS_TO_LABELS.get(x_col, x_col), tickangle=-45)
    fig.update_yaxes(title_text='Unidades Económicas')
    return fig
def create_empty_graph(message="Selecciona filtros y carga datos."):
    fig = px.scatter()
    fig.add_annotation(text=message, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font={'size': 14, 'color': "grey"})
    fig.update_layout(
        xaxis={'visible': False}, yaxis={'visible': False}, plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)', margin={'l': 0, 'r': 0, 't': 0, 'b': 0}, height=300
    )
    return fig
def create_geojson(df):
    if df is None or df.empty: return None
    if 'id' not in df.columns:
        df['id'] = range(len(df))
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitud, df.latitud)).__geo_interface__

# --- 3. LAYOUT DE LA APLICACIÓN ---
app = DashProxy(__name__, suppress_callback_exceptions=True)
server = app.server
if not scian_df.empty:
    sector_data = scian_df[['sector_nombre', 'sector_codigo']].drop_duplicates()
    sector_options = []
    for _, row in sector_data.iterrows():
        full_text = row['sector_nombre']
        truncated_text = (full_text[:10] + '...') if len(full_text) > 10 else full_text
        sector_options.append({'label': truncated_text, 'value': row['sector_codigo'], 'title': full_text})
else:
    sector_options = []

app.layout = html.Div(id='main-layout', children=[
    dcc.Store(id='intermediate-data-store'),
    html.Div(id='left-column', children=[
        html.Div(id='control-card', className="div-card", children=[
            html.Div(className='control-wrapper', children=[
                html.B('1. Selecciona un Estado:'),
                dcc.Dropdown(id='state-dropdown', options=get_initial_states(), placeholder="Selecciona...", clearable=True)
            ]),
            html.Div(className='control-wrapper', children=[
                html.B('2. Selecciona un Municipio:'),
                dcc.Dropdown(id='municipality-dropdown', disabled=True, placeholder="Primero selecciona un estado...", clearable=True)
            ]),
            html.Button('3. Cargar Datos', id='load-button', n_clicks=0),
            html.Button('4. Centrar en Datos', id='center-button', n_clicks=0, style={'margin-top': '10px'})
        ]),
        html.Div(id='context-card', className="div-card", children=[
            html.B("4. Filtra los Resultados"),
            html.Div(className='filter-container', children=[
                html.Div(className='scian-filters', children=[
                    dcc.Dropdown(id='sector-dropdown', placeholder="Filtra por Sector...", options=sector_options, clearable=True),
                    dcc.Dropdown(id='subsector-dropdown', placeholder="Filtra por Subsector...", disabled=True, clearable=True),
                    dcc.Dropdown(id='rama-dropdown', placeholder="Filtra por Rama...", disabled=True, clearable=True),
                    dcc.Dropdown(id='subrama-dropdown', placeholder="Filtra por Subrama...", disabled=True, clearable=True),
                ]),
                html.Div(className='per-ocu-filter', children=[
                    html.B("Personal Ocupado:"),
                    dcc.Checklist(id='per-ocu-checklist', className="filter-title", options=[], value=[])
                ]),
            ]),
            dcc.Graph(id='contextual_graph', figure=create_empty_graph(), config={'displayModeBar': False}),
            html.Div(id='point-info-display', style={'marginTop': '20px'}),
            dcc.Checklist(['Filtrar por vista del mapa'], id="filter_map_view", value=[], style={'marginTop': 'auto'}),
        ])
    ]),
    html.Div(className="div-card", id='main-map-card', children=[
        dl.Map([
            dl.TileLayer(url='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'),
            # CAMBIO: Usar dl.GeoJSON con la jerarquía correcta de propiedades
            dl.GeoJSON(
                id='points-geojson',
                pointToLayer=assign_point_to_layer,    # 1. Crear el objeto
                style=assign_style,                   # 2. Pintar el objeto
                onEachFeature=assign_on_each_feature  # 3. Añadirle interactividad
            ),
            dl.LocateControl(locateOptions={'enableHighAccuracy': True})
        ], center=[23.63, -102.55], zoom=5, id='main_map', style={'height': '100%'})
    ]),
])

# --- 4. CALLBACKS ---
# (El resto de los callbacks no cambia)
@app.callback(Output('municipality-dropdown', 'options'), Output('municipality-dropdown', 'disabled'), Output('municipality-dropdown', 'placeholder'), Input('state-dropdown', 'value'))
def update_municipality_dropdown(selected_state):
    if not selected_state: return [], True, "Primero selecciona un estado..."
    try:
        with get_db_connection() as con:
            municipalities = con.execute("SELECT DISTINCT municipio FROM denue WHERE entidad = ? ORDER BY municipio", [selected_state]).fetchdf()['municipio'].tolist()
        return [{'label': m, 'value': m} for m in municipalities], False, "Selecciona un municipio..."
    except Exception as e:
        logging.error(f"Error en callback de municipio: {e}")
        return [], True, "Error al cargar municipios."

@app.callback(Output('intermediate-data-store', 'data'), Input('load-button', 'n_clicks'), State('state-dropdown', 'value'), State('municipality-dropdown', 'value'), prevent_initial_call=True)
def load_data_to_store(n_clicks, state, municipality):
    if not state or not municipality: return no_update
    try:
        with get_db_connection() as con:
            
            df = con.execute("""
    SELECT 
        nom_estab, raz_social, codigo_act, nombre_act, per_ocu, entidad, cve_mun, 
        municipio, cve_loc, localidad, telefono, correoelec, www, latitud, longitud
    FROM denue 
    WHERE entidad = ? AND municipio = ?
""", [state, municipality]).fetchdf()
        logging.info(f"Datos cargados desde DB para {municipality}, {state}: {len(df)} registros.")
        return df.to_json(date_format='iso', orient='split')
    except Exception as e:
        logging.exception(f"Error cargando datos a dcc.Store: {e}")
        return None


@app.callback(
    Output('main_map', 'center'),
    Output('main_map', 'zoom'),
    Input('center-button', 'n_clicks'),
    State('intermediate-data-store', 'data'),
    prevent_initial_call=True
)
def center_on_data(n_clicks, jsonified_data):
    if not jsonified_data:
        return no_update, no_update
    try:
        df = pd.read_json(StringIO(jsonified_data), orient='split')
        if df.empty or 'latitud' not in df.columns or 'longitud' not in df.columns:
            return no_update, no_update
        centroid_lat = df['latitud'].mean()
        centroid_lon = df['longitud'].mean()
        center = [float(centroid_lat), float(centroid_lon)]
        zoom = 13  # Zoom fijo para nivel ciudad (ajusta si es necesario: 11=amplio, 13=detallado)
        logging.info(f"Centroide calculado y mapa centrado en: {center} con zoom: {zoom}")
        return center, zoom
    except Exception as e:
        logging.error(f"Error al centrar mapa: {e}")
        return no_update, no_update



def create_chained_dropdown_callback(output_id, input_id, parent_col, child_col, child_name_col):
    @app.callback(Output(output_id, 'options'), Output(output_id, 'disabled'), Output(output_id, 'value'), Input(input_id, 'value'), prevent_initial_call=True)
    def update_dropdown(parent_code):
        if not parent_code or scian_df.empty: return [], True, None
        try:
            filtered_df = scian_df[scian_df[parent_col] == str(parent_code)]
            options_df = filtered_df[[child_name_col, child_col]].drop_duplicates()
            options = []
            for _, row in options_df.iterrows():
                full_text = row[child_name_col]
                truncated_text = (full_text[:10] + '...') if len(full_text) > 10 else full_text
                options.append({'label': truncated_text, 'value': row[child_col], 'title': full_text})
            return options, False, None
        except Exception as e:
            logging.error(f"Error en callback {input_id}->{output_id}: {e}")
            return [], True, None
create_chained_dropdown_callback('subsector-dropdown', 'sector-dropdown', 'sector_codigo', 'subsector_codigo', 'subsector_nombre')
create_chained_dropdown_callback('rama-dropdown', 'subsector-dropdown', 'subsector_codigo', 'rama_codigo', 'rama_nombre')
create_chained_dropdown_callback('subrama-dropdown', 'rama-dropdown', 'rama_codigo', 'subrama_codigo', 'subrama_nombre')

@app.callback(Output('per-ocu-checklist', 'options'), Output('per-ocu-checklist', 'value'), Input('intermediate-data-store', 'data'))
def update_checklist_options(jsonified_data):
    if jsonified_data is None: return [], []
    try:
        df = pd.read_json(StringIO(jsonified_data), orient='split')
        df['per_ocu'] = pd.Categorical(df['per_ocu'], categories=PER_OCU_ORDER, ordered=True)
        per_ocu_options = df['per_ocu'].cat.categories.tolist()
        return per_ocu_options, per_ocu_options
    except Exception as e:
        logging.exception(f"Error actualizando checklist: {e}")
        return [], []

@app.callback(Output('main_map', 'bounds'), Input('intermediate-data-store', 'data'), prevent_initial_call=True)
def fit_map_to_bounds(jsonified_data):
    if not jsonified_data: return no_update
    try:
        df = pd.read_json(StringIO(jsonified_data), orient='split')
        if df.empty: return no_update
        min_lat, max_lat = df.latitud.min(), df.latitud.max()
        min_lon, max_lon = df.longitud.min(), df.longitud.max()
        lat_buffer = (max_lat - min_lat) * 0.1
        lon_buffer = (max_lon - min_lon) * 0.1
        if lat_buffer == 0: lat_buffer = 0.01
        if lon_buffer == 0: lon_buffer = 0.01
        bounds = [[float(min_lat - lat_buffer), float(min_lon - lon_buffer)], [float(max_lat + lat_buffer), float(max_lon + lon_buffer)]]
        logging.info(f"Ajustando mapa a los límites (float estándar): {bounds}")
        return bounds
    except Exception as e:
        logging.exception(f"Error al ajustar los límites del mapa: {e}")
        return no_update

@app.callback(
    Output('points-geojson', 'data'),
    Output('contextual_graph', 'figure'),
    [Input('intermediate-data-store', 'data'), Input('per-ocu-checklist', 'value'), Input('sector-dropdown', 'value'), Input('subsector-dropdown', 'value'), Input('rama-dropdown', 'value'), Input('subrama-dropdown', 'value'), Input('filter_map_view', 'value'), Input('main_map', 'bounds')]
)
def update_dashboard_from_filters(jsonified_data, per_ocu_filter, sector_code, subsector_code, rama_code, subrama_code, filter_bounds_val, map_bounds):
    if not jsonified_data: return None, create_empty_graph()
    try:
        triggered_id = ctx.triggered_id
        df = pd.read_json(StringIO(jsonified_data), orient='split')
        df['codigo_act'] = df['codigo_act'].astype(str).str.strip()
        df_filtered = df.copy()
        scian_code = subrama_code or rama_code or subsector_code or sector_code
        if scian_code:
            df_filtered = df_filtered[df_filtered['codigo_act'].str.startswith(str(scian_code))]
        if triggered_id != 'intermediate-data-store':
            df_filtered = df_filtered[df_filtered['per_ocu'].isin(per_ocu_filter)]
        if filter_bounds_val and map_bounds:
            ll, ur = map_bounds
            df_filtered = df_filtered[(df_filtered['latitud'].between(ll[0], ur[0])) & (df_filtered['longitud'].between(ll[1], ur[1]))]
        fig = generate_graph(df_filtered, 'per_ocu', 'per_ocu')
        if len(df_filtered) > 10000:
            df_for_map = df_filtered.sample(n=10000, random_state=1)
        else:
            df_for_map = df_filtered
        if not df_for_map.empty:
            df_for_map = df_for_map.assign(color=df_for_map['per_ocu'].map(PER_OCU_COLORS))
        points_geojson = create_geojson(df_for_map)
        logging.info(f"Visualización actualizada con {len(df_filtered)} registros para gráfica y {len(df_for_map)} para mapa.")
        return points_geojson, fig
    except Exception as e:
        logging.exception(f"ERROR en actualización de visualización: {e}")
        return None, create_empty_graph("Error al procesar datos")

@app.callback(
    Output('point-info-display', 'children'),
    Input('points-geojson', 'clickData'),
    prevent_initial_call=True
)
def display_point_info(feature):
    logging.info(f"Click detectado. Feature: {feature}")
    if feature is None or 'properties' not in feature:
        return ""
    props = feature['properties']
    info_layout = html.Div([
            html.Hr(),
            html.H5(props.get('nom_estab', 'Nombre no disponible')),
            
            # Datos generales
            html.P([html.B("Razón Social: "), props.get('raz_social', '-')]),
            html.P([html.B("Actividad: "), props.get('nombre_act', '-')]),
            html.P([html.B("Código Actividad: "), props.get('codigo_act', '-')]),
            html.P([html.B("Personal Ocupado: "), props.get('per_ocu', '-')]),
            html.P([html.B("Entidad: "), props.get('entidad', '-')]),
            html.P([html.B("Municipio: "), props.get('municipio', '-')]),
            html.P([html.B("Localidad: "), props.get('localidad', '-')]),
            
            # Contacto
            html.P([html.B("Teléfono: "), props.get('telefono', '-')]),
            html.P([html.B("Correo: "), props.get('correoelec', '-')]),
            html.P([html.B("Web: "), props.get('www', '-')]),
            
            html.Hr(),  # Línea final para separar
        ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '5px'})
    return info_layout

# --- 5. INICIO DE LA APLICACIÓN ---
if __name__ == "__main__":
    logging.info("="*50)
    logging.info("🚀 INICIANDO APLICACIÓN DASH...")
    logging.info("="*50)
    app.run(debug=True, port=8050)