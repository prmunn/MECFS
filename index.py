import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output

# Connect to main app.py file
from app import app
from app import server

# Connect to your app pages
from apps import mecfs_dash_app_proteomic_cytokine_comparison
from apps import mecfs_dash_app_clinical_data_lineplots
from apps import mecfs_dash_app_clinical_data_filters
from apps import mecfs_dash_app_clinical_data_sunburst
from apps import mecfs_dash_app_cytokine_data_filters
from apps import mecfs_dash_app_metabolomic_violin_plots
from apps import mecfs_dash_app_scrna_summary_3dscatterplot
from apps import mecfs_dash_app_scrna_summary_lineplots
from apps import mecfs_dash_app_scrna_summary_barplots

# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "18rem",
    "padding": "2rem 1rem",
    # "background-color": "#f8f9fa",
    # "background-color": "#536878",
    # "background-color": "#a9a9a9",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "20rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

card_sidebar = html.Div(
    [
        dbc.Card(
    [
        dbc.CardImg(src="/assets/dna-red.gif", top=True, bottom=False,
                    title="Genomics Innovation Hub", alt='Rotating DNA'),
        dbc.CardBody(
            [
                # html.H3("Genomics Innovation Hub", className="card-title", style={"text-align": "center"}),
                # html.Br(),
                html.H3("ME/CFS Database", className="card-subtitle", style={"text-align": "center"}),
                html.Br(),
                dbc.Nav(
                    [
                        # dbc.NavLink("Demographic Line Plot", href="/page-1", id="page-1-link", active='exact'),
                        dbc.NavLink("Demographic Sunburst", href="/page-1", id="page-1-link", active='exact'),
                        dbc.NavLink("Demographic Scatter Plot", href="/page-2", id="page-2-link", active='exact'),
                        dbc.NavLink("Cytokine Scatter Plot", href="/page-3", id="page-3-link", active='exact'),
                        dbc.NavLink("Proteomic / Cytokine Comparison", href="/page-4", id="page-4-link", active='exact'),
                        dbc.NavLink("Metabolomic Violin Plots", href="/page-5", id="page-5-link", active='exact'),
                        dbc.NavLink("scRNA-seq Scatter Plot", href="/page-6", id="page-6-link", active='exact'),
                        dbc.NavLink("scRNA-seq Line Plot", href="/page-7", id="page-7-link", active='exact'),
                        # dbc.NavLink("scRNA-seq Bar Plots", href="/page-8", id="page-8-link", active='exact'),
                        # dbc.NavLink("Page 4", href="/page-4", id="page-4-link"),
                    ],
                    vertical=True,
                    pills=True,
                ),
            ]
        ),
    ],
    color="dark",   # https://bootswatch.com/default/ for more card colors
    style={"height":"100vh", "width":"18rem", "left": 0, "position":"fixed"},
    inverse=True,   # change color of text (black or white)
    outline=False,  # True = remove the block colors from the background and header
    )],
    # style={"width": "18rem"},
    # style=SIDEBAR_STYLE,
)

# sidebar = html.Div(
#     [
#         html.H2("ME/CFS", className="display-4"),
#         html.Hr(),
#         html.P(
#             "A simple sidebar layout with navigation links", className="lead"
#         ),
#         dbc.Nav(
#             [
#                 dbc.NavLink("scRNA-seq Scatter Plot", href="/page-1", id="page-1-link"),
#                 dbc.NavLink("scRNA-seq Line Plot", href="/page-2", id="page-2-link"),
#                 dbc.NavLink("scRNA-seq Bar Plots", href="/page-3", id="page-3-link"),
#                 dbc.NavLink("Page 4", href="/page-4", id="page-4-link"),
#             ],
#             vertical=True,
#             pills=True,
#         ),
#     ],
#     style=SIDEBAR_STYLE,
# )

content = html.Div(id="page-content", style={"padding": "2rem"}, children=[])

# content = html.Div(id="page-content", style=CONTENT_STYLE, children=[])

app.layout = dbc.Container([
    dcc.Location(id='url'),
    dbc.Row([
        dbc.Col(card_sidebar, width=2),
        dbc.Col(content, width=9, style={"margin-left": "20rem"})
    ])
], fluid=True)

# app.layout = html.Div([dcc.Location(id="url"), card_sidebar, content])

# app.layout = html.Div([
#     dcc.Location(id='url', refresh=False),
#     html.Div([
#         dcc.Link('scRNA-seq Summary |', href='/apps/mecfs_dash_app_1'),
#         dcc.Link('| Test', href='/apps/mecfs_dash_app_test_only'),
#     ], className="row"),
#     html.Div(id='page-content', children=[])
# ])


# this callback uses the current pathname to set the active state of the
# corresponding nav link to true, allowing users to tell see page they are on
@app.callback(
    [Output(f"page-{i}-link", "active") for i in range(1, 8)],
    [Input("url", "pathname")],
)
def toggle_active_links(pathname):
    if pathname == "/":
        # Treat page 1 as the homepage / index
        return True, False, False, False, False, False, False
    return [pathname == f"/page-{i}" for i in range(1, 8)]


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    # if pathname == '/apps/mecfs_dash_app_1':
    #     return mecfs_dash_app_1.layout
    # if pathname == '/apps/mecfs_dash_app_test_only':
    #     return mecfs_dash_app_test_only.layout
    # else:
    #     return "404 Page Error! Please choose a link"
    # if pathname in ["/", "/page-1"]:
    #     return mecfs_dash_app_clinical_data_lineplots.layout
    if pathname in ["/", "/page-1"]:
        return mecfs_dash_app_clinical_data_sunburst.layout
    elif pathname == "/page-2":
        return mecfs_dash_app_clinical_data_filters.layout
    elif pathname == "/page-3":
        return mecfs_dash_app_cytokine_data_filters.layout
    elif pathname == "/page-4":
        return mecfs_dash_app_proteomic_cytokine_comparison.layout
    elif pathname == "/page-5":
        return mecfs_dash_app_metabolomic_violin_plots.layout
    elif pathname == "/page-6":
        return mecfs_dash_app_scrna_summary_3dscatterplot.layout
    elif pathname == "/page-7":
        return mecfs_dash_app_scrna_summary_lineplots.layout
    # elif pathname == "/page-8":
    #     return mecfs_dash_app_scrna_summary_barplots.layout
    # elif pathname == "/page-4":
    #     return dbc.Jumbotron(html.H1("Oh cool, this is page 4!", className="text-success"))
    #     # return html.P("Oh cool, this is page 3!")

    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


if __name__ == '__main__':
    app.run_server(debug=False)
