from dash import Dash, Input, Output, dcc, html

app = Dash(__name__)

app.layout = html.Div(
    [
        html.Button("Fetch from localhost", id="your_trigger"),
        dcc.Store(id="your_store"),
        html.Div(id="your_display"),
    ]
)

# Clientside callback that fetches from localhost
app.clientside_callback(
    """
    async function(n_clicks) {
        if (!n_clicks) {
            return window.dash_clientside.no_update;
        }
        try {
            const response = await fetch("http://localhost:9000/hello");
            console.log("Response from localhost:", response);
            const data = await response.text();  // or .json()
            return data;
        } catch (err) {
            return "Error: " + err.message;
        }
    }
    """,
    Output("your_store", "data"),
    Input("your_trigger", "n_clicks"),
)


# Server-side callback just to display the data
@app.callback(Output("your_display", "children"), Input("your_store", "data"))
def show(data):
    return f"Response: {data}" if data else "Click to fetch"


if __name__ == "__main__":
    app.run(debug=True)
