
import argparse
from pathlib import Path
import json


def tablify_catouts( paths:list ):

    catout_table = []

    for file_path in paths:

        catoutd = None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                catoutd = json.load(f)

        except json.JSONDecodeError as e:
            print(f"Error: '{file_path.name}' is not valid JSON. {e}")
        except PermissionError:
            print(f"Error: Permission denied when reading '{file_path.name}'.")
        except Exception as e:
            print(f"An unexpected error occurred with '{file_path.name}': {e}")            
    
        if catoutd:
            catout_table += tablify_catoutd(catoutd)

    return catout_table


def tablify_catoutd( catoutd:dict ):

    catout_rows = []

    for i in catoutd["editor_items"]:
        r = {}

        r["asset_id"] = catoutd["asset_id"]
        r["cataid_id"] = catoutd["cataid_id"]
        r["cataid_ver"] = catoutd["cataid_ver"]
        r["cataloger"] = catoutd["cataloger"]
        r["export_date"] = catoutd["export_date"].split("T")[0]
        r["tp_time"] = i["tp_time"]
        r["tf_label"] = i["tf_label"]
        r["etd_text"] = i["etd_text"]
        
        parse_edt(r)

        if "img_fname" in i:
            r["img_fname"] = i["img_fname"]
        else:
            r["img_fname"] = f'{r["asset_id"]}_{r["tp_time"]}.jpg'

        r["img_data_uri"] = i["img_data_uri"]

        catout_rows.append(r)
    
    return catout_rows


def parse_edt( r:dict ):

    r["name_as_written"] = ""
    r["name_normalized"] = ""
    r["person_attributes_list"] = []

    if not len(r["etd_text"]):
        pass
    elif r["etd_text"][0] == "*":
        # KIE data
        pass
    else:
        # Parse as Chyron note4
        n4list = [ i for i in r["etd_text"].split("\n") if i ]
        if len(n4list) > 0:
            r["name_as_written"] = n4list[0]
        if len(n4list) > 1:
            r["name_normalized"] = n4list[1]
        if len(n4list) > 2:
            r["person_attributes_list"] = n4list[2:]

    r["person_attributes"] = " ".join(r["person_attributes_list"])


def make_html_table( outtable ):

    fields1 = [ "asset_id",
                "cataloger",
                "export_date",
                "tp_time" ]
    fields2 = [ "name_normalized",
                "person_attributes" ]
    
    html_css = """
    <link rel="stylesheet" href="https://cdn.datatables.net/2.0.0/css/dataTables.dataTables.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/searchpanes/2.3.0/css/searchPanes.dataTables.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/select/2.0.0/css/select.dataTables.css">    
    <style>
        body{padding: 20px; font-family: sans-serif;}
        table{background-color: #E8E8E8;}
        td{border: 1px solid black;}
        th{border: 1px solid black;}
        img{height: 180px;}
        #catdoor{ max-width: 1200px; margin: 0 auto; }
    </style>
    """

    html_start = f"<!DOCTYPE html>\n<html lang='en'>\n<head>\n<title>cat door</title>\n{html_css}\n</head>\n<body>\n"
    
    html_table_start = "<table id='catdoor'><thead><tr>\n"

    for f in fields1:
        html_table_start += f"<th>{f}</th>"
    html_table_start += f"<th>img_data_uri</th>"
    for f in fields2:
        html_table_start += f"<th>{f}</th>"

    html_table_start += "\n</tr></thead>\n<tbody>"

    rows = ""

    for r in outtable:
        tr = "\n<tr>\n"
        for f in fields1:
            tr += f"<td>{r[f]}</td>"
        #tr += f"<td>X</td>"
        tr += f"<td><img src='{r['img_data_uri']}'></td>"
        for f in fields2:
            tr += f"<td>{r[f]}</td>"
        tr += "\n</tr>\n"
        rows += tr
    
    html_table_end = "</tbody></table>"

    html_scripts = """
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.datatables.net/2.0.0/js/dataTables.js"></script>

    <script src="https://cdn.datatables.net/searchpanes/2.3.0/js/dataTables.searchPanes.js"></script>
    <script src="https://cdn.datatables.net/searchpanes/2.3.0/js/searchPanes.dataTables.js"></script>
    <script src="https://cdn.datatables.net/select/2.0.0/js/dataTables.select.js"></script>
    <script>
        $(document).ready(function() {
            $('#catdoor').DataTable({
                // layout: defines where the facets (searchPanes) appear
                layout: {
                    top1: {
                        searchPanes: {
                            // Set to false so it only shows what we explicitly ask for in columnDefs
                            show: false 
                        }
                    }
                },
                // configures the faceting behavior
                columnDefs: [
                    {
                        searchPanes: {
                            show: true
                        },
                        targets: [0, 1, 2, 5] 
                    },
                    {
                        searchPanes: {
                            show: false
                        },
                        targets: '_all' // Hide everything else explicitly
                    }
                ]
            });
        });
    </script>    
    """

    html_end = "\n\n</body></html>"

    html_str = html_start + html_table_start + rows + html_table_end + html_scripts + html_end

    return html_str


def main():

    parser = argparse.ArgumentParser(
        prog='catoutout',
        description='Outputs information from a collection of cataid output (catout) files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "paths", 
        type=str,
        metavar="CATOUTPATH",
        nargs="+",
        help="Path to a single catout JSON file or a directory with many")

    args = parser.parse_args()
    pattern = "*_catout*.json"
    catout_paths = []

    for path_str in args.paths:
        input_path = Path(path_str)

        if not input_path.exists():
            print(f"Warning: '{path_str}' does not exist. Skipping...")
            continue

        if input_path.is_file():
            # Check if the single file matches our required naming convention
            if input_path.match(pattern):
                catout_paths.append(input_path)
            else:
                print(f"Warning: File '{path_str}' does not match pattern {pattern}. Skipping.")
            
        elif input_path.is_dir():
            # Find all matching files within the directory
            matches = list(input_path.glob(pattern))
            catout_paths.extend(matches)

    # De-duplicate and sort for a clean list
    catout_paths = sorted(list(set(catout_paths)))

    if catout_paths:
        catout_table = tablify_catouts( catout_paths )
    else:
        print("No valid catout files specified.  Exiting.")
        return

    html_str = make_html_table(catout_table)

    html_fname = "catout_table.html"

    with open(html_fname, "w") as f:
        f.write(html_str)
        print(f"Wrote HTML table to {html_fname}")



if __name__ == "__main__":
    main()