import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_extensions.enrich import html, DashProxy, LogTransform, ServersideOutputTransform, MultiplexerTransform
import feffery_antd_components as fac

dbc_css = "/home/wuc/dashapps/css/dbc.min.css"
app = DashProxy(
  __name__, 
  external_stylesheets=[
    dbc.themes.BOOTSTRAP
  ],
  external_scripts = [
    {'src': 'https://deno.land/x/corejs@v3.31.1/index.js', 'type': 'module'}
  ],
  transforms=[
    LogTransform(), ServersideOutputTransform(), MultiplexerTransform()
  ],
  use_pages=True
)

header = dbc.NavbarSimple(
    [
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem('spatial', href='/'),
                dbc.DropdownMenuItem("atlas", href='/atlas'),
                dbc.DropdownMenuItem("reik", href='/reik'),
            ],
            nav=True,
            in_navbar=True,
            label="Dataset",
        ),
    ],
    brand="Omics-viewer",
    color="dark",
    dark=True,
    # sticky='top',
    className='dbc-Navbar-main'
)

app.layout = dmc.NotificationsProvider(html.Div([
    header,
    dash.page_container
]))


#run server
if __name__ == "__main__":
  app.run(
    host='::',
    port='8050',
    threaded=True,
    proxy=None,
    debug=False,
    use_reloader=False
    # jupyter_mode='external'
  )
