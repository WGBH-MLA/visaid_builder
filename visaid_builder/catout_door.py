
import argparse
from pathlib import Path
import json

from . import catout_tables
from . import catout_ingests

# not used yet
VALID_CATEARS = [
    "home",
    "away",
    "miss",
    "sens",
    "cw",
    "note",
    "np" ]


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
            r = parse_sec_empty(sec)
        elif sec[0] == "*":
            # starts with asterisk -> keyed data section
            r = parse_sec_keyed(sec)
        elif ( len(lines) - len(ears_lines) )  >= 2:
            # at least two non-catears lines -> chyron data section
            r = parse_sec_chyron(sec)
        else:
            # other etd value
            r = parse_sec_other(sec)

        edt_recs.append(r)

    return edt_recs



def parse_sec_empty( sec:str ) -> dict:
    r = {}
    r["etd_type"] = "empty"
    r["chyron_data"] = {}
    r["keyed_data"] = {}
    r["catear_data"] = {}
    return r


def parse_sec_keyed( sec:str ) -> dict:
    """
    Parse as keyed/bullet list of values
    """

    lines = [ s.strip() for s in sec.split("\n") if s.strip() ]
    ears_lines = [ l for l in lines if l[:2] == "^^" ]
    key_lines = [ l for l in lines if 
                  ( l[:1] == "*" and 
                    l.find(":") >= 2 and
                    ( l.find(" ") > l.find(":") or l.find(" ") == -1 ) ) ]

    d = {}
    for l in key_lines:
        k = l[1:l.find(":")]
        v = l[l.find(":")+1:].strip()
        d.setdefault(k, []).append(v)

    r = {}
    r["etd_type"] = "keyed"
    r["chyron_data"] = {}
    r["keyed_data"] = d
    r["catear_data"] = parse_catears(ears_lines)
    return r


def parse_sec_chyron( sec:str ) -> dict:
    """
    Parse as chyron data
    (i.e., KSL Chyron note-4 conventions)
    """

    lines = [ s.strip() for s in sec.split("\n") if s.strip() ]
    ears_lines = [ l for l in lines if l[:2] == "^^" ]
    n4lines = [ l for l in lines if l not in ears_lines ]

    assert len(n4lines) >= 2, "Must have at least 2 note4-style lines for chyron sec"

    d = {}
    d["name_as_written"] = n4lines[0]
    d["name_normalized"] = n4lines[1]

    if len(n4lines) > 2:
        d["person_attributes"] = "; ".join(n4lines[2:])
    else:
        d["person_attributes"] = ""

    r = {}
    r["etd_type"] = "chyron"
    r["chyron_data"] = d
    r["keyed_data"] = {}
    r["catear_data"] = parse_catears(ears_lines)
    return r


def parse_sec_other( sec:str ) -> dict:

    lines = [ s.strip() for s in sec.split("\n") if s.strip() ]
    ears_lines = [ l for l in lines if l[:2] == "^^" ]

    r = {}
    r["etd_type"] = "other"
    r["chyron_data"] = {}
    r["keyed_data"] = {}
    r["catear_data"] = parse_catears(ears_lines)
    return r


def parse_catears ( lines:list ) -> dict:
    d = {}

    for l in lines:
        assert l[:2] == "^^", "Cat ear line must begin with '^^'"

        # potentially allow more than one catear per line
        catears = [ c.strip() for c in l.split("^^") if c.strip() ]

        for c in catears:
            invalid_catear = False

            # look for key-value catears
            if c.find(":") == 0:
                invalid_catear = True

            elif c.find(":") > 0:
                # key is substring up to colon
                k = c[:c.find(":")]
                # value is everything after
                v = c[c.find(":")+1:].strip()
            
            elif c.find(" ") != -1:
                # key is substring up to first space
                k = c[:c.find(" ")]
                # value is everything after
                v = c[c.find(" ")+1:].strip()

            else:
                # non-key-value catear
                k = c
                v = True
            
            if not k.isalnum():
                invalid_catear = True

            if not invalid_catear:
                d[k] = v

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

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Path to the output file")

    parser.add_argument(
        "-t", "--type",
        type=str,
        default="html-etd",
        help="Type of output to write")


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

    # Choose the output type
    if args.type == "html-etd":
        out_str = catout_tables.make_etd_table(catout_table)
    elif args.type == "html-chy":
        out_str = catout_tables.make_chyron_review_table(catout_table)
    elif args.type == "html-exp":
        out_str = catout_tables.make_exp_table(catout_table)
    elif args.type == "html-key":
        out_str = catout_tables.make_keyed_data_table(catout_table)
    elif args.type[:7] == "csv-con":
        out_str = catout_ingests.make_contrib_ingest(catout_table)

    if args.output:
        out_fname = args.output
    else:
        base = "catout_table"
        if args.type[:4] == "html":
            ext = ".html"
        elif args.type[:3] == "csv":
            ext = ".csv"
        else:
            ext = "txt"
        out_fname = base + ext

    if out_str:
        with open(out_fname, "w") as f:
            f.write(out_str)
            print(f"Wrote output file to to {out_fname}")
    else:
        print("No content to output.")


if __name__ == "__main__":
    main()
