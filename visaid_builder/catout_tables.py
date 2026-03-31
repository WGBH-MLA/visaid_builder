

def stringify_catear_data( d:dict) -> str:
    s = ""
    for k in d:
        if d[k] == True:
            s += ("^^" + k +  " ")
        else:
            s += ("^^" + k + ": " + d[k] + " ")
    
    return s


def stringify_keyed_data( d:dict) -> str:
    s = ""
    for k in d:
        for v in d[k]:
            s += ("*" + k + ": " + v + "\n")
    return s


def make_our_first_table( outtable ):

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

    chy_outtable = [ r for r in outtable if r["etd_data"]["etd_type"] == "chyron" ]

    for r in chy_outtable:
        tr = "\n<tr>\n"
        for f in fields1:
            tr += f"<td>{r[f]}</td>"
        #tr += f"<td>X</td>"
        tr += f"<td><img src='{r['img_data_uri']}'></td>"
        for f in fields2:
            tr += f"<td>{r['etd_data']['chyron_data'][f]}</td>"
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



def make_chyron_review_table( outtable ):

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
    
    html_table_start += f"<th>cat ears</th>"

    html_table_start += "\n</tr></thead>\n<tbody>"

    rows = ""

    chy_outtable = [ r for r in outtable if r["etd_data"]["etd_type"] == "chyron" ]

    for r in chy_outtable:
        tr = "\n<tr>\n"
        for f in fields1:
            tr += f"<td>{r[f]}</td>"
        #tr += f"<td>X</td>"
        tr += f"<td><img src='{r['img_data_uri']}'></td>"
        for f in fields2:
            tr += f"<td>{r['etd_data']['chyron_data'][f]}</td>"
        tr += f"<td>{stringify_catear_data(r['etd_data']['catear_data'])}</td>"
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
                        targets: [0, 1, 2, 5, 7]
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



def make_keyed_data_table( outtable ):

    fields1 = [ "asset_id",
                "cataloger",
                "export_date",
                "tp_time" ]
    fields2 = [ "keyed_data" ]

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

    k_outtable = [ r for r in outtable if r["etd_data"]["etd_type"] == "keyed" ]

    for r in k_outtable:
        tr = "\n<tr>\n"
        for f in fields1:
            tr += f"<td>{r[f]}</td>"
        #tr += f"<td>X</td>"
        tr += f"<td><img src='{r['img_data_uri']}'></td>"
        for f in fields2:
            tr += f"<td><pre>{stringify_keyed_data(r['etd_data']['keyed_data'])}</pre></td>"
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
                        targets: [0, 1, 2]
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



def make_etd_table( outtable ):

    fields1 = [ "asset_id",
                "cataloger",
                "export_date",
                "tp_time" ]
    fields2 = [ "etd_text" ]

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
            tr += f"<td><pre>{r[f]}</pre></td>"
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
                        targets: [0, 1, 2]
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


def make_exp_table( outtable ):

    fields1 = [ "asset_id",
                "cataloger",
                "export_date",
                "tp_time" ]
    fields2 = [ "etd_text" ]

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

    # text without line breaks
    #exp_outtable = [ r for r in outtable if ( r["etd_text"].find("\n") == -1 ) ]

    # text that should have line breaks but doesn't
    exp_outtable = [ r for r in outtable if ( r["etd_data"]["etd_type"] != "keyed" and 
                                              r["etd_text"].find("\n") == -1 and
                                              r["etd_text"].find("^") != 0 ) ]


    for r in exp_outtable:
        tr = "\n<tr>\n"
        for f in fields1:
            tr += f"<td>{r[f]}</td>"
        #tr += f"<td>X</td>"
        tr += f"<td><img src='{r['img_data_uri']}'></td>"
        for f in fields2:
            tr += f"<td><pre>{r[f]}</pre></td>"
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
                        targets: [0, 1, 2]
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
