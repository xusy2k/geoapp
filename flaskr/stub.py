import json
import locale

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from .auth import login_required
from .db import db_query
from .utils_bokeh import accumulated_stats, time_stats

locale.setlocale(locale.LC_ALL, "")

bp = Blueprint("stub", __name__, url_prefix="/stub")

BASE_URL = "http://localhost:5000"


def format_number(number):
    return f"{round(number, 2):n} €"


@bp.route("/")
@login_required
def index():
    """Homepage"""
    ctx = dict()
    try:
        summary = db_query(
            "SELECT MIN(p_month), MAX(p_month), SUM(amount) FROM app_paystats"
        )[0]
        ctx["dates_txt"] = f"{summary['min']} - {summary['max']}"
        ctx["total_accumulated"] = format_number(summary["sum"])
    except IndexError:
        pass
    ctx["accumulated_stats"], ctx["accumulated_div"] = accumulated_stats()
    ctx["time_stats"], ctx["time_div"] = time_stats()
    ctx["BOKEH_VERSION"] = "2.4.1"
    return render_template("stub/index.html", **ctx)


#
# API
#
@bp.route("/api/v1/postal_codes/")
@login_required
def postal_codes():
    """Retrieve all postal codes"""

    base_url = f"{BASE_URL}/stub/api/v1/postal_code/"
    sql = "SELECT id, code from app_postalcode"
    result = []
    for row in db_query(sql):
        result.append(
            dict(
                {
                    "id": row["id"],
                    "code": row["code"],
                    "geo_url": f"""{base_url}{row['id']}/""",
                }
            )
        )
    return json.dumps(result), 200, {"ContentType": "application/json"}


@bp.route("/api/v2/postal_codes/")
@login_required
def postal_codesV2():
    """Retrieve all postal codes in GeoJson format
    It contains 2 different URLs for detail information:
    a) For description
    b) For Statitistics information
    """
    base_url = f"{BASE_URL}/stub/api/v1/postal_code"
    sql = "SELECT id, code, ST_AsGeoJSON(the_geom) FROM app_postalcode"
    result = []
    data = dict({"type": "FeatureCollection", "features": []})
    for row in db_query(sql):
        result.append(
            dict(
                {
                    "type": "Feature",
                    "id": row["id"],
                    "properties": dict(
                        {
                            "code": row["code"],
                            "geo_stats_url": f"""{base_url}/stats/{row['id']}/""",
                        }
                    ),
                    "geometry": json.loads(row["st_asgeojson"]),
                }
            )
        )
    data["features"] = result
    return json.dumps(data), 200, {"ContentType": "application/json"}


@bp.route("/api/v1/postal_code/<int:id>/", methods=("GET", "POST"))
@login_required
def postal_code(id):
    """It retrieves GIS information"""
    sql = f"SELECT ST_AsGeoJSON(the_geom) from app_postalcode where id={id}"
    try:
        response = json.loads(db_query(sql)[0]["st_asgeojson"])
        return response, 200, {"ContentType": "application/json"}
    except IndexError:
        abort(404, f"Postal Code id '{id}' doesn't exist.")


@bp.route("/api/v1/postal_code/stats/<int:id>/", methods=("GET", "POST"))
@login_required
def postal_code_stats(id):
    """It retrieves Statitistics information from a id

    * p_month: Month
    * p_gender: Gender
    * p_age: Age
    * p_code: Postal Code
    * p_id: Postal Code Id
    * total: Total amount
    * html: Summarized verion in html
    """
    sql = f"""SELECT
                ps.p_month
                , ps.p_gender
                , ps.p_age
                , pc.code
                , pc.id
                , SUM(ps.amount) AS total
            FROM
                app_postalcode pc
                LEFT JOIN app_paystats ps ON (ps.postal_code_id = pc.id)
            WHERE
                1=1
                AND pc.id = {id}
            GROUP BY 1, 2, 3, 4, 5
            ORDER BY 1, 2, 3, 4, 5"""
    result = []
    total = 0
    summary = dict()

    html = "<table class='table table-hover'><tbody>"

    html_zipcode = None
    gender_dict_txt = dict({"M": "Male", "F": "Female"})

    for row in db_query(sql):
        try:
            p_month = row.pop("p_month")
            total_tmp = row.pop("total")
            total += total_tmp
            row["p_month"] = p_month.strftime("%d-%m-%Y")
            row["total"] = f"{round(total_tmp, 2)}"
            result.append(row)

            if html_zipcode is None:
                html_zipcode = f"""<tr><td>ZIPCODE: {row["code"]}</td></tr>"""
                html += html_zipcode

            if row["p_age"] not in summary:
                summary[row["p_age"]] = dict()

            if row["p_gender"] not in summary[row["p_age"]]:
                summary[row["p_age"]][row["p_gender"]] = dict({"total": 0})

            total_age_gender = summary[row["p_age"]][row["p_gender"]]["total"]
            total_age_gender = total_age_gender + total_tmp
            summary[row["p_age"]][row["p_gender"]]["total"] = total_age_gender
        except (TypeError, AttributeError):
            pass

    summary_json = dict()
    if summary:

        for k, gender_dict in summary.items():
            summary_json[k] = dict()
            total_gender = 0
            total_gender_tmp = 0
            ul_gender = f"{k} <ul class='summary'>"
            tb_gender = f"<table class='table tsummary'><thead><tr><th colspan='2'>{k}</tr></thead><tbody>"
            for k2, v in gender_dict.items():
                total_gender_tmp = v["total"]
                total_gender += total_gender_tmp
                summary_json[k][k2] = format_number(total_gender_tmp)
                ul_gender += f"<li>{gender_dict_txt[k2]}: {summary_json[k][k2]}</li>"
                tb_gender += f"<tr><td class=k>{gender_dict_txt[k2]}</td><td class=v>{summary_json[k][k2]}</td></tr>"
            summary_json[k]["A"] = format_number(total_gender)
            tb_gender += f"""</tbody><tfoot><tr><td class=k>TOTAL</td><td class=v>{summary_json[k]["A"]}</td></tr></tfoot></table>"""
            ul_gender += f"</ul>"
            # html += f"<tr><td>{ul_gender}</td></tr>"
            html += f"<tr><td>{tb_gender}</td></tr>"
        html += "</tbody></table>"

        summary_json["html"] = html
    else:
        summary_json["html"] = "There is no data for this ZIPCODE"

    return json.dumps(summary_json), 200, {"ContentType": "application/json"}
