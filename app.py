import dash
import dash_auth
import dash_bootstrap_components as dbc

# Keep this out of source code repository - save in a file or a database
VALID_USERNAME_PASSWORD_PAIRS = {
    'prm88': 'xxx',
    'jkg47': 'xxx',
    'fa286': 'xxx',
    'cjf79': 'xxx',
    'lg349': 'xxx'
}

# meta_tags are required for the app layout to be mobile responsive
# bootstrapTheme = 'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'
app = dash.Dash(__name__, suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.SPACELAB],
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}]
                )
auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)
server = app.server
