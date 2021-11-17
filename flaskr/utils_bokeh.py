import numpy as np
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import FuncTickFormatter

from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.models import HoverTool
from .db import db_query


COLORS = ["#718dbf", "#e84d60"]


TickFormatterCodeFormatThousends = """
    var new_tick = Math.abs(tick);
    var scale = "";
    if ((new_tick / 1e9) >= 0.1) {
        new_tick = new_tick / 1e6;
        scale = " m";
    } else if (( new_tick/ 1e6 ) >= 0.1) {
        new_tick = new_tick / 1000;
        scale = " k";
    } else {
        scale = ""
    }
    return new_tick+scale
"""


def accumulated_stats():
    """Accumulated statistics"""
    slots_qs = db_query("SELECT DISTINCT p_age FROM app_paystats ORDER BY p_age")
    slots = []
    genders = ["M", "F"]
    data = dict({"slots": [], "M": [], "F": []})
    for slot in slots_qs:
        age = slot["p_age"]
        slots.append(age)
        data["slots"].append(age)
        sql = f"SELECT p_gender, SUM(amount) as total FROM app_paystats WHERE p_age='{age}'GROUP BY 1 ORDER BY 1"
        for slot_age in db_query(sql):
            data[slot_age["p_gender"]].append(slot_age["total"])

    p = figure(
        x_range=slots,
        width=300,
        height=200,
        title="Turnover by age and gender",
        toolbar_location=None,
        tools="hover",
        tooltips="$name @slots: @$name",
    )

    p.vbar_stack(
        genders,
        x="slots",
        width=0.9,
        color=COLORS,
        source=data,
        legend_label=["Masc", "Fem"],
    )

    p.y_range.start = 0
    p.x_range.range_padding = 0.1
    p.xgrid.grid_line_color = None
    p.axis.minor_tick_line_color = None
    p.outline_line_color = None
    p.legend.location = "top_left"
    p.legend.orientation = "horizontal"

    p.title = "Turnover by age and gender"
    p.yaxis.formatter = FuncTickFormatter(code=TickFormatterCodeFormatThousends)

    script, div = components(p)
    return script, div


def time_stats():
    """Time series statistics"""
    result = dict({"M": [], "F": []})
    lines = []
    x_values = []
    for row_month in db_query("SELECT DISTINCT(p_month) FROM app_paystats ORDER BY 1"):
        p_month = row_month["p_month"]
        x_values.append(p_month)
        for gender in ["M", "F"]:
            sql = (
                f"SELECT SUM(amount) as total FROM app_paystats WHERE p_month='{p_month}' "
                f"AND p_gender='{gender}'"
            )
            for row in db_query(sql):
                total = row["total"]
                result[gender].append(total)

    x_values = np.array(x_values, dtype=np.datetime64)
    x_range = (x_values[0], x_values[-1])
    TOOLS = "pan,wheel_zoom,reset,hover,save"
    p = figure(
        plot_width=300,
        height=200,
        sizing_mode="scale_width",
        tools=TOOLS,
        x_axis_type="datetime",
        x_range=x_range,
    )
    p.title = "Turnover by age and gender"
    data_m = dict({"x": x_values, "y": np.array(result["M"], dtype=np.int32)})
    data_f = dict({"x": x_values, "y": np.array(result["F"], dtype=np.int32)})
    color = COLORS[0]
    line = p.line(
        "x",
        "y",
        source=ColumnDataSource(data=data_m),
        color=color,
        legend_label="Masc.",
        line_width=2,
        alpha=0.8,
        muted_color=color,
        muted_alpha=0.2,
    )
    lines.append(line)
    hover_tool = HoverTool(
        tooltips=[
            ("Fecha", "@x{%F}"),
            ("Masc.", "@y{0,0}€"),
        ],
        formatters={"@x": "datetime"},
        mode="mouse",
        renderers=[line],
    )
    p.tools.append(hover_tool)

    color = COLORS[1]
    line = p.line(
        "x",
        "y",
        source=ColumnDataSource(data=data_f),
        color=color,
        legend_label="Fem.",
        line_width=2,
        alpha=0.8,
        muted_color=color,
        muted_alpha=0.2,
    )
    lines.append(line)
    hover_tool = HoverTool(
        tooltips=[
            ("Fecha", "@x{%F}"),
            ("Fem.", "@y{0,0}€"),
        ],
        formatters={"@x": "datetime"},
        mode="mouse",
        renderers=[line],
    )
    p.tools.append(hover_tool)

    p.yaxis.formatter = FuncTickFormatter(code=TickFormatterCodeFormatThousends)

    script, div = components(p)
    return script, div
