import re
import csv
import io

import pprint


def parse_contrib_val( v:str) -> (str, str):
    
    rolematch = re.search(r'\((.*?)\)', v)

    if rolematch:
        role = rolematch.group(1).strip()
        name = v.split("(")[0].strip()
    else:
        role = ""
        name = v.split("^")[0].strip()

    return (name, role )



def make_contrib_ingest( outtable ):

    # get down to just the important values
    data = [ { "guid": r["asset_id"], 
               "etd_type": r["etd_data"]["etd_type"],
               "chyron_data": r["etd_data"]["chyron_data"],
               "keyed_data": r["etd_data"]["keyed_data"],
               "catear_data": r["etd_data"]["catear_data"] }
              for r in outtable ]

    guids = list(set( [ r["guid"] for r in data ] ) )

    #pprint.pprint(data) # diag

    guid_contribs = {}
    for guid in guids:
        all_guid_contribs = []
        for r in [r for r in data if r["guid"] == guid]:
            if r["etd_type"] == "chyron":
                if ("sens" not in r["catear_data"]):              
                    d = {}
                    d["name_normalized"] = r["chyron_data"]["name_normalized"]
                    d["role"] = ""
                    all_guid_contribs.append(d)
            elif r["etd_type"] == "keyed":
                if "contrib" in r["keyed_data"]:
                    for c in r["keyed_data"]["contrib"]:
                        d = {}
                        d["name_normalized"], d["role"] = parse_contrib_val(c)
                        all_guid_contribs.append(d)

        # get just unique contributors
        if all_guid_contribs:
            guid_contribs[guid] = []
            for c in all_guid_contribs:
                if c not in guid_contribs[guid]:
                    guid_contribs[guid].append(c)


    #pprint.pprint(guid_contribs) # diag

    max_contribs = max( [ len(guid_contribs[guid]) for guid in guid_contribs ] ) 
    
    print(f"Will create contributor records for {len(guid_contribs)} items.")
    print(f"Max contributors per item: {max_contribs}")

    csv_header_row = ["Asset", "Asset.id"]
    for _ in range(max_contribs):
        csv_header_row += ["Contribution", "Contribution.contributor", "Contribution.contributor_role"]

    csv_rows = [ csv_header_row ]

    contrib_recs = 0
    for guid in guid_contribs:
        row = ["", guid]
 
        for c in guid_contribs[guid]:
            row += [ "", c["name_normalized"], c["role"] ]
            contrib_recs += 1
 
        pad = max_contribs - len(guid_contribs[guid])
        for _ in range(pad):
            row += [ "", "", ""]

        csv_rows.append(row)

    print(f"Recorded {contrib_recs} contributor records.")
    #pprint.pprint(csv_rows) # diag

    out_io = io.StringIO()
    csv.writer(out_io).writerows(csv_rows)
    csv_string = out_io.getvalue()

    # print(csv_string) # diag

    return csv_string

