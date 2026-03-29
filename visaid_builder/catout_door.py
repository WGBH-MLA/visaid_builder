
import argparse
from pathlib import Path
import json

import catout_tables


def tablify_catouts( paths:list ) -> list:
    """
    Takes a list of filepaths to catout JSON files.

    Returns a table (list of dictionaries) with all target output fields.

    This function operates at the aggregate level over lots of catouts.  
    
    It operates only at the level of explicit data structures.  Parsing of human-entered
    data happens separately.
    """

    catout_table = []

    # iterate through filepaths, accumulating rows
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

            # each catout has multiple rows, one or more for each editor_item
            new_rows = []
            for ei in catoutd["editor_items"]:

                etd_recs = parse_etd( ei["etd_text"] )

                # it is possible to have multiple records for a single editor_item
                for etd_rec in etd_recs:
                    r = {}

                    r["asset_id"] = catoutd["asset_id"]
                    r["cataid_id"] = catoutd["cataid_id"]
                    r["cataid_ver"] = catoutd["cataid_ver"]
                    r["cataloger"] = catoutd["cataloger"]
                    r["export_date"] = catoutd["export_date"].split("T")[0]
                    r["tp_time"] = ei["tp_time"]
                    r["tf_label"] = ei["tf_label"]
                    r["tp_id"] = ei["tp_id"]
                    r["img_fname"] = ei["img_fname"]
                    r["aid_text"] = ei["aid_text"]
                    r["etd_text"] = ei["etd_text"]

                    r["etd_data"] = etd_rec

                    r["img_data_uri"] = ei["img_data_uri"]

                    new_rows.append(r)

            catout_table += new_rows

    return catout_table



def parse_etd( etd_text:str ) -> list:
    """
    Parsing logic of human edited/entered values.
    Takes a string of raw text and returns a list of dictionaries.
    """

    # allow multiple records per etd text
    edt_recs = []

    # divide multiplexed editor text and strip surrounding whitespace
    etd_secs = [ s.strip() for s in etd_text.split("\n+++") if s.strip() ]

    for sec in etd_secs:

        lines = [ s.strip() for s in sec.split("\n") if s.strip() ]
        ears_lines = [ l for l in lines if l[:2] == "^^" ]

        if not len(sec):
            # empty section
            r = parse_keyed_sec(sec)
        elif sec[0] == "*":
            # starts with asterisk -> keyed data section
            r = parse_keyed_sec(sec)
        elif ( len(lines) - len(ears_lines) )  >= 2:
            # at least two non-catears lines -> chyron data section
            r = parse_chyron_sec(sec)
        else:
            # other etd value
            r = parse_other_sec(sec)

        edt_recs.append(r)

    return edt_recs



def parse_empty_sec( sec:str ) -> dict:
    r = {}
    r["etd_type"] = "empty"
    return r


def parse_keyed_sec( sec:str ) -> dict:
    """
    Parse as keyed/bullet list of values
    """
    r = {}
    r["etd_type"] = "keyed"

    return r


def parse_chyron_sec( sec:str ) -> dict:
    """
    Parse as chyron data
    (i.e., KSL Chyron note-4 conventions)
    """
    r = {}
    r["etd_type"] = "chyron"

    lines = [ s.strip() for s in sec.split("\n") if s.strip() ]
    ears_lines = [ l for l in lines if l[:2] == "^^" ]
    n4lines = [ l for l in lines if l not in ears_lines ]

    assert len(n4lines) >= 2, "Must have at least 2 note4-style lines for chyron sec"

    r["name_as_written"] = n4lines[0]
    r["name_normalized"] = n4lines[1]

    if len(n4lines) > 2:
        r["person_attributes"] = "; ".join(n4lines[2:])
    else:
        r["person_attributes"] = ""

    r["catear_data"] = parse_catears(ears_lines)

    return r


def parse_other_sec( sec:str ) -> dict:
    r = {}
    r["etd_type"] = "other"
    return r


def parse_catears ( lines:list ) -> dict:
    d = {}

    #stub
    d["ears"] = "\n".join(lines)

    return d



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

    html_str = catout_tables.make_contrib_review_table(catout_table)

    html_fname = "catout_table.html"

    with open(html_fname, "w") as f:
        f.write(html_str)
        print(f"Wrote HTML table to {html_fname}")



if __name__ == "__main__":
    main()
