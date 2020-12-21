import dash
import dash_bootstrap_components as dbc

# meta_tags are required for the app layout to be mobile responsive
# bootstrapTheme = 'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'
app = dash.Dash(__name__, suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.SPACELAB],
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}]
                )
server = app.server
