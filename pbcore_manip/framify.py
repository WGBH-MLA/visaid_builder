
# %%
# Import modules from Python standard library
import argparse
import os
import glob
import xml.etree.ElementTree as ET
import csv
from pprint import pprint

# import installed modules
import pandas as pd

# Set the display options to show all rows and columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

pd.set_option('display.width',2000)


# define a batch of PBCore XML records to framify

hardcoded_output_file = "./batch.csv"

#hardcoded_pbcore_dir = "C:/Users/owen_king/localcode/aapb_catalog/pbcxml_digitized_2024-02-28"
#hardcoded_pbcore_dir = "C:/Users/owen_king/localcode/aapb_catalog/digitized_114"

#hardcoded_pbcore_dir = "C:/Users/owen_king/kitchen/stovetop/shipment_34080_34125_NC_PBS/pbcore"
#hardcoded_pbcore_dir = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/wipr_ams2_pbcore"
#hardcoded_pbcore_dir = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/batch_2024-05-06_x131/wipr_ams2_pbcore"
#hardcoded_pbcore_dir = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/batch_2024-05-07_unknowns_x1018/wipr_ams2_xml"
#hardcoded_pbcore_dir = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/batch_2024-05-07_orr_green_x2578/wipr_ams2_pbcore"
#hardcoded_pbcore_dir = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/complete/wipr_ams2_pbcore"
hardcoded_pbcore_dir = "C:/Users/owen_king/kitchen/stovetop/shipment_WVIA_34451_34609/ams2_pbcore"

notebook_mode = True

############################################################################
# %%
# Define tablify function
def tablify( pbcore_dir:str ):
    """
    Build tables of assets and instantiations (as Python lists of lists)
    """

    if not os.path.isdir(pbcore_dir):
        print("Error:  Invalid directory path for PBCore files.")
        raise Exception("Invalid directory path for PBCore files.")

    filenames = os.listdir(pbcore_dir)
    xmlfilenames = glob.glob(pbcore_dir + "/*.xml")

    if len(filenames) > len(xmlfilenames):
        print("Warning: Working directory includes files with extension other than .xml")

    # define namespace prefix for XML elements
    ns = {"pbcore": "http://www.pbcore.org/PBCore/PBCoreNamespace.html"}

    # The initial catalog tables
    assttbl = []
    insttbl = []

    #### CAT-AUD ##############################################
    # variables for counting or compiling weird things
    multici_guids = []
    noci_guids = []
    mismatch_dig_media_types_guids = {}
    #### CAT-AUD ##############################################

    # For each XML file, 
    #   - add a row to the asset table
    #   - add zero or more rows to the instantiations table
    for fn in filenames:

        # read XML file (making sure we can parse it)
        fpath = pbcore_dir + "/" + fn

        try:
            tree = ET.parse(fpath)
        except ET.ParseError as e:
            print(f"Error in XML parsing for file {fn}: {e}")
        except Exception as e:
            print(f"An error occurred with file {fn}: {e}")

        # Get the root element of the XML tree
        # This should be a `pbcoreDescriptionDocument`.
        root = tree.getroot()

        root_tag = root.tag
        root_tag_no_ns = root_tag.split('}')[-1] if '}' in root_tag else root_tag
        if root_tag_no_ns != "pbcoreDescriptionDocument":
            print("Warning: The root element is:", root_tag_no_ns)
            print("Skipping", fn)
            continue
         

        # get all the values we want
        # (If an element is missing, assign empty string to the variable)

        #
        # Identifier elements 
        #
        # Asset.id
        # The raw text from the PBCore is stored as the `aapb_pbcore_id`
        # The normalized "guid" (without / or _) is stored as `asset_id`
        att = "[@source='http://americanarchiveinventory.org']"
        e = root.find("pbcore:pbcoreIdentifier"+att,ns)
        aapb_pbcore_id = e.text if e is not None else ""
        asset_id = aapb_pbcore_id.replace('/', '-').replace('_', '-')

        # Asset.sonyci_id
        #att = "[@source='Sony Ci']"
        #e = root.find("pbcore:pbcoreIdentifier"+att,ns)
        #sonyci_id = e.text if e is not None else ""

        # Asset.sonyci_id
        # Takes the Sony Ci ID from the first non-empty matching element
        att = "[@source='Sony Ci']"
        es = root.findall("pbcore:pbcoreIdentifier"+att,ns)
        sonyci_id = ""
        for e in es:
            if (not sonyci_id and e.text):
                sonyci_id = e.text

        #
        # Annotation elements 
        #
        # Asset.organization
        att = "[@annotationType='organization']"
        e = root.find("pbcore:pbcoreAnnotation"+att,ns)
        organization = e.text if e is not None else ""

        # Asset.level_of_user_access
        att = "[@annotationType='Level of User Access']"
        e = root.find("pbcore:pbcoreAnnotation"+att,ns)
        level_of_user_access = e.text if e is not None else ""

        # Asset.special_collections
        # handling multiple values
        att = "[@annotationType='special_collections']"
        es = root.findall("pbcore:pbcoreAnnotation"+att,ns)
        tlist = [ e.text for e in es ]
        special_collections = ','.join(tlist)

        # Asset.transcript_status
        att = "[@annotationType='Transcript Status']"
        e = root.find("pbcore:pbcoreAnnotation"+att,ns)
        transcript_status = e.text if e is not None else ""

        # Asset.transcript_url
        att = "[@annotationType='Transcript URL']"
        e = root.find("pbcore:pbcoreAnnotation"+att,ns)
        transcript_url = e.text if e is not None else ""

        # Proxy Start Time
        att = "[@annotationType='Proxy Start Time']"
        e = root.find("pbcore:pbcoreAnnotation"+att,ns)
        proxy_start_time = e.text if e is not None else ""

        #
        # Date elements 
        #
        # Asset.broadcast_date
        att = "[@dateType='Broadcast']"
        e = root.find("pbcore:pbcoreAssetDate"+att,ns)
        broadcast_date = e.text if e is not None else ""

        # Asset.created_date
        att = "[@dateType='Created']"
        e = root.find("pbcore:pbcoreAssetDate"+att,ns)
        created_date = e.text if e is not None else ""

        # Asset.copyright_date
        att = "[@dateType='Copyright']"
        e = root.find("pbcore:pbcoreAssetDate"+att,ns)
        copyright_date = e.text if e is not None else ""

        # Asset.date (no @dateType)
        es = root.findall("pbcore:pbcoreAssetDate",ns)
        esnoat = [e for e in es if 'dateType' not in e.attrib]  
        date = esnoat[0].text if len(esnoat) > 0 else ""

        # Canonical date
        # Use a simple heuristic to set a single canonical date, given that 
        # there might be several dates associated with the asset
        if date:
            single_date = date
        elif copyright_date:
            single_date = copyright_date
        elif created_date:
            single_date = created_date
        elif broadcast_date:
            single_date = broadcast_date
        else:
            single_date = ""


        #
        # Title elements 
        #
        # Asset.series_title
        att = "[@titleType='Series']"
        e = root.find("pbcore:pbcoreTitle"+att,ns)
        series_title = e.text if e is not None else ""

        # Asset.program_title
        att = "[@titleType='Program']"
        e = root.find("pbcore:pbcoreTitle"+att,ns)
        program_title = e.text if e is not None else ""

        # Asset.episode_title
        att = "[@titleType='Episode']"
        e = root.find("pbcore:pbcoreTitle"+att,ns)
        episode_title = e.text if e is not None else ""

        # Asset.episode_number
        att = "[@titleType='Episode Number']"
        e = root.find("pbcore:pbcoreTitle"+att,ns)
        episode_number = e.text if e is not None else ""

        # Asset.segment_title
        att = "[@titleType='Segment']"
        e = root.find("pbcore:pbcoreTitle"+att,ns)
        segment_title = e.text if e is not None else ""

        # Asset.raw_footage_title
        att = "[@titleType='Raw Footage']"
        e = root.find("pbcore:pbcoreTitle"+att,ns)
        raw_footage_title = e.text if e is not None else ""

        # Asset.promo_title
        att = "[@titleType='Promo']"
        e = root.find("pbcore:pbcoreTitle"+att,ns)
        promo_title = e.text if e is not None else ""

        # Asset.clip_title
        att = "[@titleType='Clip']"
        e = root.find("pbcore:pbcoreTitle"+att,ns)
        clip_title = e.text if e is not None else ""

        # Asset.title (no @titleType)
        es = root.findall("pbcore:pbcoreTitle",ns)
        esnoat = [e for e in es if 'titleType' not in e.attrib]
        title = esnoat[0].text if len(esnoat) > 0 else ""

        # Canonical title
        # Build a single canonical title, given that there might be several
        # titles associated with the asset
        consolidated_title = ""
        if series_title:
            consolidated_title += (series_title + ": ")
        if episode_number:
            consolidated_title += ("No. " + episode_number + ": ")
        consolidated_title += episode_title
        consolidated_title += program_title
        consolidated_title += segment_title
        consolidated_title += raw_footage_title
        consolidated_title += promo_title
        consolidated_title += clip_title
        if title:
            if consolidated_title:
                consolidated_title += (" " + title)
            else:
                consolidated_title += title


        #
        # Other elements 
        #
        # Asset.asset_types
        att = ""
        e = root.find("pbcore:pbcoreAssetType"+att,ns)
        asset_type = e.text if e is not None else ""


        #
        # Creator and contributor elements
        #

        # Asset.producing_organization
        pbcreators = root.findall("pbcore:pbcoreCreator",ns)
        crole_e = None    
        creator_e = None
        producing_organization = ""
        for pbcreator_e in pbcreators:
            crole_e = pbcreator_e.find("pbcore:creatorRole",ns)
            crole = crole_e.text if crole_e is not None else ""
            creator_e = pbcreator_e.find("pbcore:creator",ns)
            creator = creator_e.text if creator_e is not None else ""
            #print("Creator role:", crole, "Creator:", creator)
            if crole == "Producing Organization":
                producing_organization = creator


        """
        # DigitalInstantiation.media_type for the asset
        # (Note: This is not an element that is part of the asset records, but
        #  we need to associate a media type with the asset; so we make an 
        #  intelligent choice among the media types in the instantiation records.)
        # First, narrow down to the digital instantiations
        # Then, if there are serveral, prioritize video, then audio
        insts = root.findall(".//pbcore:pbcoreInstantiation",ns)
        dig_mts = []  # create list of media types for digial instantiations
        for inst in insts:
            if inst.find("pbcore:instantiationDigital",ns) is not None:
                mte = inst.find("pbcore:instantiationMediaType",ns)
                if mte is not None:
                    dig_mts.append(mte.text)
        if len(dig_mts) == 0:
            media_type = ''
        elif 'Moving Image' in dig_mts:
            media_type = 'Moving Image'
        elif 'Sound' in dig_mts:
            media_type = 'Sound'
        else:
            media_type = dig_mts[0]
        """

        # DigitalInstantiation.media_type for the asset
        # (Note: This is not an element that is part of the asset records, but
        #  we need to associate a media type with the asset; so we make an 
        #  intelligent choice among the media types in the instantiation records.)
        insts = root.findall(".//pbcore:pbcoreInstantiation",ns)
        dig_mts = []  # create list of media types for digial instantiations
        phs_mts = []  # create list of media types for physical instantiations
        for inst in insts:
            mte = inst.find("pbcore:instantiationMediaType",ns)
            if mte is not None:
                if inst.find("pbcore:instantiationDigital",ns) is not None:
                    dig_mts.append(mte.text)
                elif inst.find("pbcore:instantiationPhysical",ns) is not None:
                    phs_mts.append(mte.text)
        if 'Moving Image' in dig_mts:
            media_type = 'Moving Image'
        elif 'Sound' in dig_mts:
            media_type = 'Sound'
        elif 'Moving Image' in phs_mts:
            media_type = 'Moving Image'
        elif 'Sound' in phs_mts:
            media_type = 'Sound'
        elif len(dig_mts) > 0:
            media_type = dig_mts[0]
        elif len(phs_mts) > 0:
            media_type = phs_mts[0]
        else:
            media_type = ''

        # Proxy duration 
        # (Note: This is not an element that is part of the asset records, but it
        #  is useful to infer this where possible.)
        # Take the duration of the first digital instatniation where the generation 
        # equals "Proxy"
        proxy_duration = ""
        insts = root.findall(".//pbcore:pbcoreInstantiation",ns)
        for inst in insts:
            if inst.find("pbcore:instantiationDigital",ns) is not None:
                e = inst.find("pbcore:instantiationGenerations",ns)
                if (not proxy_duration) and e is not None:
                    if e.text == "Proxy":
                        e = inst.find("pbcore:instantiationDuration",ns)
                        if e is not None:
                            proxy_duration = e.text


        # Instantiation records
        insts = root.findall(".//pbcore:pbcoreInstantiation",ns)
        for inst in insts:

            # Instantiation identifers
            # handling multiple values by concatenating all of them into a |-separated list
            att = ""
            es = inst.findall("pbcore:instantiationIdentifier",ns)
            # e.text is cast as str to handle a case where the element exists but
            # has no text as with this guid: cpb-aacip-111-02c8693q        
            tlist = [ str(e.text) for e in es ]
            inst_identifiers = '|'.join(tlist)

            # Instantiation media type
            att = ""
            e = inst.find("pbcore:instantiationMediaType"+att,ns)
            inst_media_type = e.text if e is not None else ""

            # Instantiation date
            att = ""
            e = inst.find("pbcore:instantiationDate"+att,ns)
            inst_date = e.text if e is not None else ""

            # Instantiation digital format
            att = ""
            e = inst.find("pbcore:instantiationDigital"+att,ns)
            inst_digital_format = e.text if e is not None else ""

            # Instantiation physical format
            att = ""
            e = inst.find("pbcore:instantiationPhysical"+att,ns)
            inst_physical_format = e.text if e is not None else ""

            # Instantiation generations
            att = ""
            e = inst.find("pbcore:instantiationGenerations"+att,ns)
            inst_generations = e.text if e is not None else ""

            # Instantiation duration
            att = ""
            e = inst.find("pbcore:instantiationDuration"+att,ns)
            inst_duration = e.text if e is not None else ""

            # Instantiation location
            att = ""
            e = inst.find("pbcore:instantiationLocation"+att,ns)
            inst_location = e.text if e is not None else ""

            # Add the collected instantiation-level values to the table
            insttbl.append([asset_id,
                            inst_identifiers,
                            inst_media_type,
                            inst_digital_format,
                            inst_physical_format,
                            inst_generations,
                            inst_duration,
                            inst_location
                            ])


        # Add the collected asset-level values to the table
        assttbl.append([asset_id,
                        aapb_pbcore_id, 
                        sonyci_id,
                        media_type,
                        asset_type, 
                        organization,
                        level_of_user_access,
                        special_collections,
                        transcript_status,
                        transcript_url,
                        proxy_start_time,
                        broadcast_date,
                        created_date,
                        copyright_date,
                        date,
                        single_date,
                        series_title,
                        program_title,
                        episode_title,
                        episode_number,
                        segment_title,
                        raw_footage_title,
                        promo_title,
                        clip_title,
                        title,
                        consolidated_title,
                        producing_organization,
                        proxy_duration
                        ])


        #### CAT-AUD ##############################################
        # Find all those with multiple SonyCi IDs
        att = "[@source='Sony Ci']"
        es = root.findall(".//pbcore:pbcoreIdentifier"+att,ns)
        if len(es) == 1:
            single_sonyci_id = True
        elif len(es) < 1:
            single_sonyci_id = False
            noci_guids.append(asset_id)
        else:
            single_sonyci_id = False
            multici_guids.append(asset_id)


        # testing for mixed types of digital instantiations
        if ( len(dig_mts) > 1 and 
            not all(mt==dig_mts[0] for mt in dig_mts) and
            'Moving Image' in dig_mts and
            'Sound' in dig_mts ):
            mismatch_dig_media_types_guids[asset_id] = dig_mts

        #### CAT-AUD ##############################################

    return ( assttbl, insttbl )

############################################################################
# %%
# Define infrmae function
def inframe( assttbl, insttbl ):
    """
    Create dataframes from tables
    """

    asstcols = ["asset_id",
                "aapb_pbcore_id", 
                "sonyci_id",
                "media_type",
                "asset_type", 
                "organization",
                "level_of_user_access",
                "special_collections",
                "transcript_status",
                "transcript_url",
                "proxy_start_time",
                "broadcast_date",
                "created_date",
                "copyright_date",
                "date",
                "single_date",
                "series_title",
                "program_title",
                "episode_title",
                "episode_number",
                "segment_title",
                "raw_footage_title",
                "promo_title",
                "clip_title",
                "title",
                "consolidated_title",
                "producing_organization",
                "proxy_duration"]

    instcols = ["asset_id",
                "inst_identifiers",
                "inst_media_type",
                "inst_digital_format",
                "inst_physical_format",
                "inst_generations",
                "inst_duration",
                "inst_location"]

    asstdf = pd.DataFrame(assttbl, columns=asstcols)

    instdf = pd.DataFrame(insttbl, columns=instcols)

    joindf = pd.merge(asstdf,instdf, how="left")

    return (asstdf, instdf, joindf)


############################################################################
# %%
# Define frame filter and projection functions
def filterproj1( asstdf ):

    # filter for a list of GUIDs
    
    wipr_1_26_guids = ['cpb-aacip-835c18587e0', 'cpb-aacip-21dd6788785', 'cpb-aacip-68649a312de', 'cpb-aacip-675c1b7c36c', 'cpb-aacip-b16b656ef0d', 'cpb-aacip-3ff5c2f0ddd', 'cpb-aacip-3240db2bc7a', 'cpb-aacip-3912e9e7e3e', 'cpb-aacip-e7606e6ddfe', 'cpb-aacip-1a78c71cc32', 'cpb-aacip-e7a0e4c11a2', 'cpb-aacip-46e26367307', 'cpb-aacip-5d07ca7987c', 'cpb-aacip-4e7c3ed78d8', 'cpb-aacip-c0028eb0268', 'cpb-aacip-58cc99d2da0', 'cpb-aacip-4efe0be68b8', 'cpb-aacip-39d9be74e5a', 'cpb-aacip-c48919b61bc', 'cpb-aacip-4d090735bbd', 'cpb-aacip-4cc437afdd2', 'cpb-aacip-3f4717cfde1', 'cpb-aacip-e6a549a4ffc', 'cpb-aacip-4f867ce7e37', 'cpb-aacip-b865919f9ce', 'cpb-aacip-620562fed97']
    wipr_2_131_guids = ['cpb-aacip-ae3d04aa7a3', 'cpb-aacip-d4c6f2581d8', 'cpb-aacip-db45eb1f7d7', 'cpb-aacip-aa20194c7f0', 'cpb-aacip-53feaa1e5bb', 'cpb-aacip-8c1381db259', 'cpb-aacip-5bfcaf88250', 'cpb-aacip-196d1bed9d1', 'cpb-aacip-f08372679cd', 'cpb-aacip-2b68ba1eae2', 'cpb-aacip-dd258c721cc', 'cpb-aacip-a84ffe3e2d5', 'cpb-aacip-6f87e51e148', 'cpb-aacip-4a301a94ce9', 'cpb-aacip-c5685166a9b', 'cpb-aacip-d0ed4339f02', 'cpb-aacip-6420858c399', 'cpb-aacip-aed11696eb1', 'cpb-aacip-0684ecc0ba3', 'cpb-aacip-d2370235e9b', 'cpb-aacip-0465d5d00f5', 'cpb-aacip-494cb3c6cb4', 'cpb-aacip-7dd5b308eae', 'cpb-aacip-aca213dc3b8', 'cpb-aacip-c57292b2988', 'cpb-aacip-00af8ec1073', 'cpb-aacip-4b4fe0dbcec', 'cpb-aacip-9976fb1bc52', 'cpb-aacip-4463de7407c', 'cpb-aacip-087ee5c0752', 'cpb-aacip-db3bdb3275e', 'cpb-aacip-9eef45c84cc', 'cpb-aacip-19d6fb7391a', 'cpb-aacip-6c70e81fb89', 'cpb-aacip-c3322913f5d', 'cpb-aacip-889d72a9d9c', 'cpb-aacip-aabd7345bb5', 'cpb-aacip-a71f79b4e8c', 'cpb-aacip-1d65786d6ca', 'cpb-aacip-e564e125598', 'cpb-aacip-404ceaa6824', 'cpb-aacip-830961618e3', 'cpb-aacip-0fff4d0ee45', 'cpb-aacip-711a24d3e4a', 'cpb-aacip-2e6e1f3f85b', 'cpb-aacip-60bdd1c17ed', 'cpb-aacip-71f8daaca02', 'cpb-aacip-9241efe949e', 'cpb-aacip-47d9ee531cc', 'cpb-aacip-b03a0c378d4', 'cpb-aacip-e5ca73b64b1', 'cpb-aacip-f3a22dff64f', 'cpb-aacip-c641cfa2177', 'cpb-aacip-bf87f0c780b', 'cpb-aacip-65085d385ff', 'cpb-aacip-39af66bd519', 'cpb-aacip-56057aeae55', 'cpb-aacip-a00d26e0d50', 'cpb-aacip-62c45c0d4cb', 'cpb-aacip-5ea6da58e52', 'cpb-aacip-a44b4d21a08', 'cpb-aacip-820e2520f27', 'cpb-aacip-f6d1f8a0c8b', 'cpb-aacip-7659b68aafe', 'cpb-aacip-412c927c22d', 'cpb-aacip-562d305b704', 'cpb-aacip-e3ce46f2dde', 'cpb-aacip-7f84f7e1e0b', 'cpb-aacip-058292931d7', 'cpb-aacip-19a815c6bb6', 'cpb-aacip-69c76cd30e2', 'cpb-aacip-d039496d9b9', 'cpb-aacip-26c33277911', 'cpb-aacip-c845ef89ac1', 'cpb-aacip-cb44bd0e3d5', 'cpb-aacip-327927e334d', 'cpb-aacip-7a32d8f9708', 'cpb-aacip-29f05113081', 'cpb-aacip-8ced2ec7ef9', 'cpb-aacip-c28b63eb55e', 'cpb-aacip-ffb80fe1407', 'cpb-aacip-d95e364e7ac', 'cpb-aacip-3756c5064a2', 'cpb-aacip-3d3d27038da', 'cpb-aacip-b29ed6c0752', 'cpb-aacip-1f8e6bf6e12', 'cpb-aacip-39697a86c74', 'cpb-aacip-78543e151a1', 'cpb-aacip-0d8a7ea7bbb', 'cpb-aacip-29f517b29a9', 'cpb-aacip-818cb396b5d', 'cpb-aacip-172f707abd9', 'cpb-aacip-3aff91281f5', 'cpb-aacip-b022d549c91', 'cpb-aacip-c3e4fc59c7f', 'cpb-aacip-c56572ceef7', 'cpb-aacip-f1a8f62f804', 'cpb-aacip-6c1ce159441', 'cpb-aacip-f1d2a0c3d17', 'cpb-aacip-4058b25ad37', 'cpb-aacip-d1f3237caa0', 'cpb-aacip-5337f002eec', 'cpb-aacip-f958b3ed8ac', 'cpb-aacip-e406d85add1', 'cpb-aacip-15daf361aef', 'cpb-aacip-593746b30e3', 'cpb-aacip-2ce8e934e26', 'cpb-aacip-a325a4cba27', 'cpb-aacip-71c74b310e8', 'cpb-aacip-b154c6e83e4', 'cpb-aacip-1ec7d37fb67', 'cpb-aacip-bfb4fc01eff', 'cpb-aacip-d5b1d194dfa', 'cpb-aacip-cec8c22c4df', 'cpb-aacip-809170dd7bd', 'cpb-aacip-ff69de912a1', 'cpb-aacip-be77d5ce9cd', 'cpb-aacip-28159e9fd0a', 'cpb-aacip-b22a0162f5d', 'cpb-aacip-8471dfe105d', 'cpb-aacip-f9e02b2e296', 'cpb-aacip-98c8a45156f', 'cpb-aacip-85e214de26e', 'cpb-aacip-0700744f124', 'cpb-aacip-974bfc03016', 'cpb-aacip-674a5391268', 'cpb-aacip-11f204fbaa2', 'cpb-aacip-fddd01a7488', 'cpb-aacip-e8cc0a70a31', 'cpb-aacip-822fc2abe51', 'cpb-aacip-ec3e34e9316']
    wipr_4_1018_guids = ['cpb-aacip-3aff91281f5', 'cpb-aacip-f1a8f62f804', 'cpb-aacip-6c1ce159441', 'cpb-aacip-f1d2a0c3d17', 'cpb-aacip-4058b25ad37', 'cpb-aacip-d1f3237caa0', 'cpb-aacip-5337f002eec', 'cpb-aacip-f958b3ed8ac', 'cpb-aacip-e406d85add1', 'cpb-aacip-15daf361aef', 'cpb-aacip-593746b30e3', 'cpb-aacip-2ce8e934e26', 'cpb-aacip-a325a4cba27', 'cpb-aacip-71c74b310e8', 'cpb-aacip-b154c6e83e4', 'cpb-aacip-1ec7d37fb67', 'cpb-aacip-bfb4fc01eff', 'cpb-aacip-d5b1d194dfa', 'cpb-aacip-cec8c22c4df', 'cpb-aacip-809170dd7bd', 'cpb-aacip-ff69de912a1', 'cpb-aacip-be77d5ce9cd', 'cpb-aacip-cedf3f93375', 'cpb-aacip-d90c4f1bf0f', 'cpb-aacip-a649afd23fe', 'cpb-aacip-7693531ed95', 'cpb-aacip-25a3dc0bac1', 'cpb-aacip-ca3d7842b21', 'cpb-aacip-b221d71d941', 'cpb-aacip-6504c9ece99', 'cpb-aacip-cc6bec0b8e3', 'cpb-aacip-e2b070f944f', 'cpb-aacip-7accbb31c67', 'cpb-aacip-f6db5d2d8ca', 'cpb-aacip-186fa3e955a', 'cpb-aacip-124b68c22c4', 'cpb-aacip-33f7c3a219d', 'cpb-aacip-88ddc09881e', 'cpb-aacip-a8be5dc3d53', 'cpb-aacip-65257f7f72f', 'cpb-aacip-c5fd54c4f36', 'cpb-aacip-65b58cb7a6a', 'cpb-aacip-fa6f43e760d', 'cpb-aacip-b1309bc7fda', 'cpb-aacip-2cedde89333', 'cpb-aacip-e9ff2d131f4', 'cpb-aacip-81637e12db5', 'cpb-aacip-c337e3753b1', 'cpb-aacip-566722520ce', 'cpb-aacip-c469aacf93d', 'cpb-aacip-09919a2128c', 'cpb-aacip-406252f0e3e', 'cpb-aacip-35bff846893', 'cpb-aacip-9d04da5b22a', 'cpb-aacip-d196e5016e0', 'cpb-aacip-b83a918da43', 'cpb-aacip-0d686a04dc1', 'cpb-aacip-f4457e1e515', 'cpb-aacip-f72239167f2', 'cpb-aacip-e082a5d172e', 'cpb-aacip-aa45527af3f', 'cpb-aacip-fe7f2babfd4', 'cpb-aacip-b2b70ac2c9d', 'cpb-aacip-a5b7254ceb3', 'cpb-aacip-83885a49746', 'cpb-aacip-d44e20ec669', 'cpb-aacip-26766bcaf0c', 'cpb-aacip-63b048a872b', 'cpb-aacip-cda152b5402', 'cpb-aacip-fdb2f5f046e', 'cpb-aacip-735110d9854', 'cpb-aacip-5171a89bf2b', 'cpb-aacip-390858a7819', 'cpb-aacip-5789e94a3d1', 'cpb-aacip-12524eb7f80', 'cpb-aacip-f88d6952d30', 'cpb-aacip-e78ad1bfe9a', 'cpb-aacip-b6f57e9db3d', 'cpb-aacip-b7e72718047', 'cpb-aacip-cda81dd3302', 'cpb-aacip-a33fab2c617', 'cpb-aacip-4461d6ebc6b', 'cpb-aacip-f6188f8089e', 'cpb-aacip-963871af64f', 'cpb-aacip-e7a8ec9efdb', 'cpb-aacip-e4093d89de9', 'cpb-aacip-c2c0bfa4556', 'cpb-aacip-39bc13ca7c4', 'cpb-aacip-c630d1d8acd', 'cpb-aacip-b71b2d487d2', 'cpb-aacip-a55bb4a2ba1', 'cpb-aacip-266649aada5', 'cpb-aacip-33610d44b37', 'cpb-aacip-e32ce71619c', 'cpb-aacip-40a91d15119', 'cpb-aacip-fb34fd8d35a', 'cpb-aacip-c90eb260bbb', 'cpb-aacip-b96e5af741c', 'cpb-aacip-fc934c6191b', 'cpb-aacip-e82162c6e5d', 'cpb-aacip-a1eb6be30f8', 'cpb-aacip-36ad0065d37', 'cpb-aacip-0def0a71c01', 'cpb-aacip-8b1ed4df2b4', 'cpb-aacip-9d4e1d3335c', 'cpb-aacip-d02c7a75526', 'cpb-aacip-76e1c833147', 'cpb-aacip-fae0c5c3695', 'cpb-aacip-0632d531eb3', 'cpb-aacip-f9f5ff4fda9', 'cpb-aacip-9aa55467528', 'cpb-aacip-6dd5a4b5078', 'cpb-aacip-cc42702ba3b', 'cpb-aacip-907e3bdca72', 'cpb-aacip-589ccc76e9d', 'cpb-aacip-55f5ff3befd', 'cpb-aacip-a10ef979fdd', 'cpb-aacip-4c68ff22d15', 'cpb-aacip-af136632e59', 'cpb-aacip-5cb85f0844c', 'cpb-aacip-b6a18790417', 'cpb-aacip-7d262bb14c8', 'cpb-aacip-11a2d1ddb03', 'cpb-aacip-81c4dfb1d3e', 'cpb-aacip-681193edf49', 'cpb-aacip-e06b732c72f', 'cpb-aacip-d6e8402741a', 'cpb-aacip-c83f503f694', 'cpb-aacip-d6bf7fdf345', 'cpb-aacip-e314194774f', 'cpb-aacip-650547fe0af', 'cpb-aacip-a98336080c4', 'cpb-aacip-92ccde257c7', 'cpb-aacip-694c0afb927', 'cpb-aacip-dfa3f146dba', 'cpb-aacip-3bc3b06d970', 'cpb-aacip-dba5364b994', 'cpb-aacip-cd1858435c3', 'cpb-aacip-6d146d9bde2', 'cpb-aacip-718a5d757cf', 'cpb-aacip-8e9c9bdcb32', 'cpb-aacip-d3dbaa04401', 'cpb-aacip-585c98e9b5a', 'cpb-aacip-33dff7be3a5', 'cpb-aacip-cd054a2da26', 'cpb-aacip-8338cb30e81', 'cpb-aacip-f4f83ec7886', 'cpb-aacip-98793da7309', 'cpb-aacip-dc0376886ae', 'cpb-aacip-d4915a1b01b', 'cpb-aacip-0eb4c843d33', 'cpb-aacip-fa3eb1cf092', 'cpb-aacip-04d5bc8989f', 'cpb-aacip-443537bc6e6', 'cpb-aacip-19a4beb7e3e', 'cpb-aacip-87193e94c85', 'cpb-aacip-c1a43fb3a82', 'cpb-aacip-afedb0f6b36', 'cpb-aacip-7d6079bd581', 'cpb-aacip-e87f0d6e239', 'cpb-aacip-2156711fa1c', 'cpb-aacip-cff0c5f400b', 'cpb-aacip-e9721ad3744', 'cpb-aacip-01f4687f351', 'cpb-aacip-e09b9c582c2', 'cpb-aacip-3a460648844', 'cpb-aacip-59e7bfd964a', 'cpb-aacip-1f5f7f0932c', 'cpb-aacip-b8315ffafa5', 'cpb-aacip-1479251eda5', 'cpb-aacip-23fb27d9c67', 'cpb-aacip-c6adab4adc1', 'cpb-aacip-580740e99c2', 'cpb-aacip-1acb64462c5', 'cpb-aacip-9a79529e3d1', 'cpb-aacip-89326224244', 'cpb-aacip-36817ecfb0e', 'cpb-aacip-44b65540908', 'cpb-aacip-37cfd9535cc', 'cpb-aacip-d5b09a735f2', 'cpb-aacip-7969643f779', 'cpb-aacip-d0987c6a4cd', 'cpb-aacip-f0e8bf41804', 'cpb-aacip-6499ba41400', 'cpb-aacip-296058a137e', 'cpb-aacip-b683afa71a3', 'cpb-aacip-08f9baf0965', 'cpb-aacip-f4f03c76b01', 'cpb-aacip-288574d2122', 'cpb-aacip-b79fbc51dd8', 'cpb-aacip-0b0a1a5c042', 'cpb-aacip-0e884021023', 'cpb-aacip-13e47e55473', 'cpb-aacip-bf14d4757e3', 'cpb-aacip-1b0ebb5fcba', 'cpb-aacip-46d2b373f2b', 'cpb-aacip-cd5ce428217', 'cpb-aacip-1f1e73f7169', 'cpb-aacip-3c60542c431', 'cpb-aacip-3305b3f62b2', 'cpb-aacip-546ec7bbd2f', 'cpb-aacip-5a916eb5547', 'cpb-aacip-52a3c41db0b', 'cpb-aacip-c062d122e8a', 'cpb-aacip-1565eaf8989', 'cpb-aacip-1a9864ec86d', 'cpb-aacip-12ff3b60798', 'cpb-aacip-28df2fc1d7d', 'cpb-aacip-af92586e0d5', 'cpb-aacip-5d5108e0bff', 'cpb-aacip-cff5fe3b49d', 'cpb-aacip-a246be53df1', 'cpb-aacip-986cd86d002', 'cpb-aacip-dc7a05ffdfa', 'cpb-aacip-4c19fe08cd6', 'cpb-aacip-c164d8bcc65', 'cpb-aacip-d16bc0e40bb', 'cpb-aacip-a745205ac08', 'cpb-aacip-590b270a485', 'cpb-aacip-b29de0793cb', 'cpb-aacip-40c0ef42d18', 'cpb-aacip-67ce31a9186', 'cpb-aacip-f7f779c1cdf', 'cpb-aacip-32c172d5b78', 'cpb-aacip-f7cb6e65279', 'cpb-aacip-f22cd7e0ec1', 'cpb-aacip-90f5ad3b58f', 'cpb-aacip-2fe116ddb22', 'cpb-aacip-bea7f394f81', 'cpb-aacip-7b996739a1b', 'cpb-aacip-e8598953b42', 'cpb-aacip-15ed7e52595', 'cpb-aacip-418b8641f23', 'cpb-aacip-967450bd018', 'cpb-aacip-8d6ffd43862', 'cpb-aacip-b0d6671fce4', 'cpb-aacip-6d9b8bb5ee2', 'cpb-aacip-efa30b53480', 'cpb-aacip-545ff4735c3', 'cpb-aacip-078f23b0097', 'cpb-aacip-d7fcb336937', 'cpb-aacip-a617ae5e263', 'cpb-aacip-35933bc4a8b', 'cpb-aacip-7ef53715a3c', 'cpb-aacip-54252885c8b', 'cpb-aacip-ebbde94751e', 'cpb-aacip-813555c1f15', 'cpb-aacip-ad6d3035f0b', 'cpb-aacip-2638c5ddd5d', 'cpb-aacip-bf006c647fa', 'cpb-aacip-dd13d269b95', 'cpb-aacip-c113b9bf811', 'cpb-aacip-bf99cd39a36', 'cpb-aacip-e217ca8cd98', 'cpb-aacip-dbc5f103862', 'cpb-aacip-53b254ca7b2', 'cpb-aacip-d3224ee6809', 'cpb-aacip-669fe8426bd', 'cpb-aacip-c2fc505fc49', 'cpb-aacip-eb385d2fa1e', 'cpb-aacip-0b9a3d57f57', 'cpb-aacip-82e20dc5a40', 'cpb-aacip-5fb0f748a79', 'cpb-aacip-e640b80441e', 'cpb-aacip-b85fc2f8ba2', 'cpb-aacip-3355fa20012', 'cpb-aacip-c069965b4cc', 'cpb-aacip-8122b187d79', 'cpb-aacip-9da17182a6e', 'cpb-aacip-41169fefbb1', 'cpb-aacip-4d056de3267', 'cpb-aacip-4002d3c54d2', 'cpb-aacip-22153fe51f6', 'cpb-aacip-75dceb1e4cd', 'cpb-aacip-719235baa3f', 'cpb-aacip-2f5837fec5c', 'cpb-aacip-61c763518ce', 'cpb-aacip-6cfa468afb1', 'cpb-aacip-6a69681bd74', 'cpb-aacip-17d46b1830b', 'cpb-aacip-7104728dd2e', 'cpb-aacip-c15b5d8d85a', 'cpb-aacip-988890a99fe', 'cpb-aacip-58ff8ad426b', 'cpb-aacip-2390db7fab4', 'cpb-aacip-761ea2960c5', 'cpb-aacip-ad3f400411a', 'cpb-aacip-3d38e5be3c4', 'cpb-aacip-80d7521aa7b', 'cpb-aacip-6a0bb12a6e9', 'cpb-aacip-e09176f8f22', 'cpb-aacip-51ee0101c04', 'cpb-aacip-5bda9f8d690', 'cpb-aacip-95bf7fc777e', 'cpb-aacip-ea92265768c', 'cpb-aacip-f2cc121f49e', 'cpb-aacip-52629ac5357', 'cpb-aacip-b1feb7336b7', 'cpb-aacip-022424d8aca', 'cpb-aacip-f17e2f7025b', 'cpb-aacip-3a25a55bcbe', 'cpb-aacip-c92d64a914b', 'cpb-aacip-64351e0d020', 'cpb-aacip-1684f7553c2', 'cpb-aacip-c5ebacc1fd4', 'cpb-aacip-2adfb8882d7', 'cpb-aacip-1205c682297', 'cpb-aacip-735ef1fe81c', 'cpb-aacip-cff8385e26b', 'cpb-aacip-d205e99ae1b', 'cpb-aacip-d22f3cee123', 'cpb-aacip-ff59cf069a5', 'cpb-aacip-0b92299eb07', 'cpb-aacip-e17a1940b8b', 'cpb-aacip-5461db3c6e2', 'cpb-aacip-119af4c16e1', 'cpb-aacip-fae0f07f3eb', 'cpb-aacip-09abf2ca6b1', 'cpb-aacip-09396f8b119', 'cpb-aacip-0627cf511de', 'cpb-aacip-662ea577c81', 'cpb-aacip-fcc4fb68d02', 'cpb-aacip-ca62cbcddcd', 'cpb-aacip-73dd61af81e', 'cpb-aacip-3e3d531b28a', 'cpb-aacip-01cc3249744', 'cpb-aacip-5c2cbe4e0cc', 'cpb-aacip-544c5cd12e5', 'cpb-aacip-008f294ea48', 'cpb-aacip-d8142a8c990', 'cpb-aacip-125bd29ab36', 'cpb-aacip-da61b68a991', 'cpb-aacip-c7dfd66b475', 'cpb-aacip-0d05dd338ab', 'cpb-aacip-86dd7a50e4b', 'cpb-aacip-4e653af0603', 'cpb-aacip-8b803781f6b', 'cpb-aacip-b9904947243', 'cpb-aacip-fced03a37df', 'cpb-aacip-dc16e69e570', 'cpb-aacip-08274ed9448', 'cpb-aacip-2bad482bad9', 'cpb-aacip-24e7346aea0', 'cpb-aacip-57787f293ed', 'cpb-aacip-5527f108561', 'cpb-aacip-683e55c1d37', 'cpb-aacip-b633d45b2ee', 'cpb-aacip-0bb25833458', 'cpb-aacip-a4a3aa02961', 'cpb-aacip-e939f7bf494', 'cpb-aacip-89b4795eaaa', 'cpb-aacip-f952e3fce31', 'cpb-aacip-44be4c4eac7', 'cpb-aacip-1740fc0c8d8', 'cpb-aacip-00173b97215', 'cpb-aacip-b0a17af4359', 'cpb-aacip-9312e950eb6', 'cpb-aacip-1e684dbcd79', 'cpb-aacip-076f7735dfc', 'cpb-aacip-4d4ad13ee1c', 'cpb-aacip-7ad81fe103f', 'cpb-aacip-6872029ad06', 'cpb-aacip-79c3419d7a2', 'cpb-aacip-45aebd23049', 'cpb-aacip-9ee5982af9a', 'cpb-aacip-8ce7682f316', 'cpb-aacip-a7eed6ee55b', 'cpb-aacip-263bf78c52f', 'cpb-aacip-113f0ba5ec6', 'cpb-aacip-ed8593884cb', 'cpb-aacip-57d209ee3b3', 'cpb-aacip-59981c8cb4a', 'cpb-aacip-5b90d0312dd', 'cpb-aacip-b93d1a60a40', 'cpb-aacip-6c0b987d9d0', 'cpb-aacip-969b354c141', 'cpb-aacip-70571d3deb6', 'cpb-aacip-a7e9ddd7db4', 'cpb-aacip-d1b56a971d3', 'cpb-aacip-f5a8e5483e6', 'cpb-aacip-6ad1f64d131', 'cpb-aacip-f0d7c1e48ae', 'cpb-aacip-583c794da0d', 'cpb-aacip-bf604f41f9e', 'cpb-aacip-7f384db0dbe', 'cpb-aacip-300d201695b', 'cpb-aacip-7f536faa389', 'cpb-aacip-11889c3701a', 'cpb-aacip-4c5e82e36a5', 'cpb-aacip-3bb149932f7', 'cpb-aacip-d82ab3e529a', 'cpb-aacip-9fc3a977ea4', 'cpb-aacip-1301fb11cb0', 'cpb-aacip-c4554b77c17', 'cpb-aacip-5fb8414c337', 'cpb-aacip-c5acd4f9dc5', 'cpb-aacip-4b27c3b1ed7', 'cpb-aacip-f3e1967d888', 'cpb-aacip-8b777795dbd', 'cpb-aacip-b4d8c22e46b', 'cpb-aacip-ce3a7d40226', 'cpb-aacip-709053dfe68', 'cpb-aacip-0236850c8be', 'cpb-aacip-29548533b2d', 'cpb-aacip-e57c519532e', 'cpb-aacip-801699c6fd6', 'cpb-aacip-499460ed453', 'cpb-aacip-c642a7607d6', 'cpb-aacip-7923d82b87c', 'cpb-aacip-da4cb60a344', 'cpb-aacip-73196b96e50', 'cpb-aacip-c0c0a0a9993', 'cpb-aacip-b3bf32af2f8', 'cpb-aacip-c1173c71a0e', 'cpb-aacip-0d087551c03', 'cpb-aacip-a0e624a70ed', 'cpb-aacip-fa58ffa701c', 'cpb-aacip-cac28347a73', 'cpb-aacip-00fdfca0c25', 'cpb-aacip-f1e5be3df96', 'cpb-aacip-c38370295b3', 'cpb-aacip-00f9ad9aa51', 'cpb-aacip-738a35cb2fb', 'cpb-aacip-2f06f718d9a', 'cpb-aacip-d6a6b6f337d', 'cpb-aacip-9dec3035edd', 'cpb-aacip-c3c834563ca', 'cpb-aacip-654e2df2bf9', 'cpb-aacip-d68ece17033', 'cpb-aacip-ea2ebd81ccf', 'cpb-aacip-6e1c1e2fdec', 'cpb-aacip-f441c533a23', 'cpb-aacip-9cf6cf9a6a2', 'cpb-aacip-ab87f53911b', 'cpb-aacip-74d09111ee4', 'cpb-aacip-fa3b0de7b84', 'cpb-aacip-d3d365de844', 'cpb-aacip-29f89ccacad', 'cpb-aacip-a4c702758f0', 'cpb-aacip-42d9be9e5d3', 'cpb-aacip-8032f7a596e', 'cpb-aacip-a4c7290d6a0', 'cpb-aacip-cbcbbc50091', 'cpb-aacip-b5da8a46580', 'cpb-aacip-9a90d59afaa', 'cpb-aacip-cae529c5e13', 'cpb-aacip-574198e7e12', 'cpb-aacip-e1929476ea9', 'cpb-aacip-a2210828726', 'cpb-aacip-ed9dcccbd98', 'cpb-aacip-b1020be530f', 'cpb-aacip-3804aa0b46b', 'cpb-aacip-6f3491f2814', 'cpb-aacip-6c36286c7d1', 'cpb-aacip-2731cf8bda6', 'cpb-aacip-0f897280d04', 'cpb-aacip-e96c4663d1e', 'cpb-aacip-ad51d136568', 'cpb-aacip-ad074e26a39', 'cpb-aacip-9c4159482bf', 'cpb-aacip-ff6135742a1', 'cpb-aacip-9e4ec77363e', 'cpb-aacip-91adb6301ea', 'cpb-aacip-a9ead34b22d', 'cpb-aacip-914c35338ab', 'cpb-aacip-e2245070ad3', 'cpb-aacip-1db1b7fb855', 'cpb-aacip-89a35d08e6d', 'cpb-aacip-946b4538a5b', 'cpb-aacip-bf437976006', 'cpb-aacip-e35dd527917', 'cpb-aacip-2560d3970f8', 'cpb-aacip-a46f63a575b', 'cpb-aacip-df6bcba3eae', 'cpb-aacip-e939da4615d', 'cpb-aacip-a2bd14a3df7', 'cpb-aacip-35d21cf82d7', 'cpb-aacip-f7f3e177129', 'cpb-aacip-778484d4034', 'cpb-aacip-7c2b3c324ac', 'cpb-aacip-b77bc2db1fb', 'cpb-aacip-e25200b6694', 'cpb-aacip-2f1194600ff', 'cpb-aacip-46534fd444e', 'cpb-aacip-82e7718574a', 'cpb-aacip-1ab9bd11d16', 'cpb-aacip-cf0b93cd9f5', 'cpb-aacip-b61225ece0d', 'cpb-aacip-e517eccf2e3', 'cpb-aacip-f9737614237', 'cpb-aacip-0b7fb2966ef', 'cpb-aacip-0e49f7390bf', 'cpb-aacip-6eed06f689f', 'cpb-aacip-7729eb74884', 'cpb-aacip-77b48e4f75a', 'cpb-aacip-1beb61c0dea', 'cpb-aacip-d89ed3602bb', 'cpb-aacip-1080beb56a4', 'cpb-aacip-d4cf026eb6a', 'cpb-aacip-de28022050d', 'cpb-aacip-26d003efa52', 'cpb-aacip-cef0116bc9c', 'cpb-aacip-f8fac68a733', 'cpb-aacip-82d84d47983', 'cpb-aacip-057ba00aac2', 'cpb-aacip-e98f8b4585c', 'cpb-aacip-fd86ae3b148', 'cpb-aacip-e36f0813602', 'cpb-aacip-e76a7c6b809', 'cpb-aacip-50753df4fa4', 'cpb-aacip-507c22c1fa9', 'cpb-aacip-e794e6ff199', 'cpb-aacip-c2851fe85a7', 'cpb-aacip-b16fe547d13', 'cpb-aacip-d6568185c31', 'cpb-aacip-fa77bf426f9', 'cpb-aacip-a4172990df1', 'cpb-aacip-692d2a6ea42', 'cpb-aacip-52ef285dbe2', 'cpb-aacip-cc367c1fb80', 'cpb-aacip-7d93513fd0a', 'cpb-aacip-accf968344a', 'cpb-aacip-d9efe41ebc2', 'cpb-aacip-b41f1cf510f', 'cpb-aacip-bf3f854ef3f', 'cpb-aacip-0fa090943a3', 'cpb-aacip-f1a8a43596c', 'cpb-aacip-cb72fced10e', 'cpb-aacip-819d4726853', 'cpb-aacip-91237db4bd7', 'cpb-aacip-eba27cfe606', 'cpb-aacip-cf7d4bd8d7a', 'cpb-aacip-173ca843210', 'cpb-aacip-2a87b23256f', 'cpb-aacip-da47f33e8bb', 'cpb-aacip-38c266543ac', 'cpb-aacip-6b4abd9888f', 'cpb-aacip-8e4224e7e77', 'cpb-aacip-e5f58e91590', 'cpb-aacip-1629f87c4bd', 'cpb-aacip-c923ffc4451', 'cpb-aacip-af6d5f4ad1a', 'cpb-aacip-aa200015d8b', 'cpb-aacip-0e62ff06ddc', 'cpb-aacip-79a28a31592', 'cpb-aacip-e7ae8db7426', 'cpb-aacip-9547761a00e', 'cpb-aacip-d858dc9ac53', 'cpb-aacip-9c8192f9083', 'cpb-aacip-16d1920eb5f', 'cpb-aacip-3727d6db4f5', 'cpb-aacip-9f205db58cb', 'cpb-aacip-fc96164f241', 'cpb-aacip-dd9a1e5c940', 'cpb-aacip-454b0a958d5', 'cpb-aacip-be02fba8a3c', 'cpb-aacip-89866d644f1', 'cpb-aacip-0d778000af6', 'cpb-aacip-204301a55c2', 'cpb-aacip-5b97854ffcd', 'cpb-aacip-e40d1efc23a', 'cpb-aacip-4480daded54', 'cpb-aacip-89910a8b005', 'cpb-aacip-a98d2412bf3', 'cpb-aacip-6959f0c7269', 'cpb-aacip-e2ef4a5d5e5', 'cpb-aacip-f7006a07c29', 'cpb-aacip-d8a4fe70054', 'cpb-aacip-2c43f96277a', 'cpb-aacip-59b6f192665', 'cpb-aacip-cbdda672761', 'cpb-aacip-a3cb3157bb9', 'cpb-aacip-08b7e53a45d', 'cpb-aacip-8a1c419f117', 'cpb-aacip-c84d7655929', 'cpb-aacip-e17c4d6546d', 'cpb-aacip-06a79c7bb78', 'cpb-aacip-610f02adf49', 'cpb-aacip-4a8c4a0d372', 'cpb-aacip-bad807ad986', 'cpb-aacip-9d850472220', 'cpb-aacip-70a46a66b47', 'cpb-aacip-75659b7d380', 'cpb-aacip-e8582c3074f', 'cpb-aacip-155201c89ca', 'cpb-aacip-77c47d0556b', 'cpb-aacip-80c5fa633f3', 'cpb-aacip-7f5841ec9f3', 'cpb-aacip-d25d4481513', 'cpb-aacip-e3bf833aea0', 'cpb-aacip-88e2fa92368', 'cpb-aacip-1630e103c3d', 'cpb-aacip-d8968be6ac2', 'cpb-aacip-b34e77f06e9', 'cpb-aacip-231571318cf', 'cpb-aacip-ad52dc81246', 'cpb-aacip-d50dff42667', 'cpb-aacip-ddcb889e1ce', 'cpb-aacip-aee448dba74', 'cpb-aacip-b18dd0bdf56', 'cpb-aacip-eff2d66b2c2', 'cpb-aacip-f16697d572a', 'cpb-aacip-89ec4441964', 'cpb-aacip-88382947fb0', 'cpb-aacip-9ee0f8a4d81', 'cpb-aacip-0665e9c4cd5', 'cpb-aacip-9cd27a9a6bd', 'cpb-aacip-f7eb84bb111', 'cpb-aacip-e01ec7c3497', 'cpb-aacip-5ff335eff9d', 'cpb-aacip-07e4ef5b605', 'cpb-aacip-5b000373807', 'cpb-aacip-51365f1cd38', 'cpb-aacip-31412be77d0', 'cpb-aacip-81529b91149', 'cpb-aacip-1482bc2a58f', 'cpb-aacip-df4f7200110', 'cpb-aacip-b5fe1aae36e', 'cpb-aacip-d53bd693a07', 'cpb-aacip-7909d797e33', 'cpb-aacip-c507b08213b', 'cpb-aacip-b74558782ae', 'cpb-aacip-6b164964e80', 'cpb-aacip-7e37860933b', 'cpb-aacip-23451797793', 'cpb-aacip-2f8597e6db3', 'cpb-aacip-2838b8a7f1e', 'cpb-aacip-0315cc112e4', 'cpb-aacip-f89db3e7fea', 'cpb-aacip-ccba8f4c99d', 'cpb-aacip-7130e889b50', 'cpb-aacip-f59f5465c9d', 'cpb-aacip-7e9edacc499', 'cpb-aacip-4efa360efc8', 'cpb-aacip-c6340502ce7', 'cpb-aacip-f9d8db1148e', 'cpb-aacip-5fe716a4bc2', 'cpb-aacip-577fadac8a2', 'cpb-aacip-fdfc87afe62', 'cpb-aacip-9d1ccc32bcd', 'cpb-aacip-aad7b4e5eb0', 'cpb-aacip-f9e31035b84', 'cpb-aacip-80887fc0985', 'cpb-aacip-5706258807e', 'cpb-aacip-9e41b8f8c0b', 'cpb-aacip-cd52b450c2e', 'cpb-aacip-4189fe448b3', 'cpb-aacip-9c25648e503', 'cpb-aacip-0c0f95f0a74', 'cpb-aacip-66dcb3267da', 'cpb-aacip-c44b5d89502', 'cpb-aacip-398cd4c5978', 'cpb-aacip-5fff19a4353', 'cpb-aacip-9b0a00775e5', 'cpb-aacip-f1510f8e149', 'cpb-aacip-37037238c92', 'cpb-aacip-064f87cd84a', 'cpb-aacip-a62b439fc04', 'cpb-aacip-3c393ecd74e', 'cpb-aacip-3fd7911e323', 'cpb-aacip-cb5501b92a4', 'cpb-aacip-17fa064f7e3', 'cpb-aacip-afe112bc7df', 'cpb-aacip-65ca52b4aa8', 'cpb-aacip-309c39c6246', 'cpb-aacip-9726af9ba5e', 'cpb-aacip-11aa5f7c62d', 'cpb-aacip-342dc60813c', 'cpb-aacip-b694a74a25d', 'cpb-aacip-0057bca30ad', 'cpb-aacip-3078cf155be', 'cpb-aacip-6b258a8296a', 'cpb-aacip-981e7b7d16a', 'cpb-aacip-2924c55044c', 'cpb-aacip-422c7c6b6ff', 'cpb-aacip-7999c086aa1', 'cpb-aacip-109db31f373', 'cpb-aacip-c3527a257f3', 'cpb-aacip-500d0adcd6e', 'cpb-aacip-e422c49c059', 'cpb-aacip-3ad1aa2d9cb', 'cpb-aacip-90af24c415a', 'cpb-aacip-a235813701d', 'cpb-aacip-2ccb6e99d41', 'cpb-aacip-25e9c0a2d29', 'cpb-aacip-4996e7f0037', 'cpb-aacip-c81ae0e5db1', 'cpb-aacip-072f7052053', 'cpb-aacip-ae182e26abf', 'cpb-aacip-a109366571d', 'cpb-aacip-3327f0a04d4', 'cpb-aacip-13053195633', 'cpb-aacip-9c651bd4a77', 'cpb-aacip-f349af1db01', 'cpb-aacip-2cffc974d07', 'cpb-aacip-a48c610b265', 'cpb-aacip-d3a94a6d9b5', 'cpb-aacip-6e2b9772340', 'cpb-aacip-04790b13adb', 'cpb-aacip-c81e67038e9', 'cpb-aacip-0c629464ed6', 'cpb-aacip-d2cb5e15c78', 'cpb-aacip-463cb36887b', 'cpb-aacip-5345c7f2197', 'cpb-aacip-b1275a130c5', 'cpb-aacip-abbfa6027be', 'cpb-aacip-e62a346cb01', 'cpb-aacip-c3e9af15aa7', 'cpb-aacip-30a77d6d096', 'cpb-aacip-90b38f6ac6b', 'cpb-aacip-8b4a6d46294', 'cpb-aacip-b3f6aacfbda', 'cpb-aacip-1a66b622d83', 'cpb-aacip-faf6c4b29d8', 'cpb-aacip-033cdd4b79a', 'cpb-aacip-cdd3176f0c4', 'cpb-aacip-942bc2d2bee', 'cpb-aacip-93894c60f53', 'cpb-aacip-b7569d11573', 'cpb-aacip-57dbed0f589', 'cpb-aacip-73b6149c43e', 'cpb-aacip-1018b0f4ff9', 'cpb-aacip-511c3532572', 'cpb-aacip-c54b40b4f73', 'cpb-aacip-16e20d53c09', 'cpb-aacip-3473c0fce40', 'cpb-aacip-50ee11dafdd', 'cpb-aacip-836892e8a1d', 'cpb-aacip-388c015e9a2', 'cpb-aacip-8cf5b8cf373', 'cpb-aacip-b3b72d8109a', 'cpb-aacip-21514ed0900', 'cpb-aacip-4755ae6253d', 'cpb-aacip-858dd332022', 'cpb-aacip-32b91e4e256', 'cpb-aacip-3de6139b004', 'cpb-aacip-64d8d348d19', 'cpb-aacip-9347da2ca03', 'cpb-aacip-b1dcc7cde81', 'cpb-aacip-53c6fa81eca', 'cpb-aacip-043bd71996d', 'cpb-aacip-e4e08638b09', 'cpb-aacip-b5a1214d479', 'cpb-aacip-2f482bafd08', 'cpb-aacip-dd5831c7ca8', 'cpb-aacip-38255b1c155', 'cpb-aacip-40b7e6d361c', 'cpb-aacip-b51eb3f8e94', 'cpb-aacip-c42d331098a', 'cpb-aacip-b7df390fb0d', 'cpb-aacip-82e6993ae6a', 'cpb-aacip-1c0c9b3484a', 'cpb-aacip-7239c01d99d', 'cpb-aacip-9e7789d26df', 'cpb-aacip-4623ab4d4be', 'cpb-aacip-25bf7127dfc', 'cpb-aacip-d52e39193f0', 'cpb-aacip-de488d8db1a', 'cpb-aacip-3bda5d371cc', 'cpb-aacip-05071729616', 'cpb-aacip-07ae6623173', 'cpb-aacip-f193b76114a', 'cpb-aacip-66bfb7386be', 'cpb-aacip-7134460d030', 'cpb-aacip-202648d85c8', 'cpb-aacip-7202483b506', 'cpb-aacip-c05c9c297cd', 'cpb-aacip-8eb558a7f06', 'cpb-aacip-fb98b6b4e0d', 'cpb-aacip-832d311b049', 'cpb-aacip-9e288fbdee2', 'cpb-aacip-fbe55ace666', 'cpb-aacip-3009c22cc96', 'cpb-aacip-ba7b23940ab', 'cpb-aacip-6c7f3db0828', 'cpb-aacip-d09845b0c6e', 'cpb-aacip-a5b08cebce5', 'cpb-aacip-53eaa1556dd', 'cpb-aacip-9419c0a5497', 'cpb-aacip-4f94e342f30', 'cpb-aacip-d9cc878fbdf', 'cpb-aacip-6a4a5121288', 'cpb-aacip-bf505c703a9', 'cpb-aacip-29581f048a3', 'cpb-aacip-ad3b14610f0', 'cpb-aacip-1872a50dfbd', 'cpb-aacip-2ebce7d7eab', 'cpb-aacip-6f0f07df952', 'cpb-aacip-f3a7f190ff0', 'cpb-aacip-af4ccd6ec8f', 'cpb-aacip-b98bb343226', 'cpb-aacip-b0879b68320', 'cpb-aacip-45f648dcd2f', 'cpb-aacip-948a0528b7f', 'cpb-aacip-d5d48d07198', 'cpb-aacip-9038636228f', 'cpb-aacip-e15640272c3', 'cpb-aacip-f1f24a962dd', 'cpb-aacip-f5487c5f9dd', 'cpb-aacip-0b58b9d8645', 'cpb-aacip-cd1eb094edf', 'cpb-aacip-fca9960daea', 'cpb-aacip-022905b622b', 'cpb-aacip-160c5b87a80', 'cpb-aacip-78e85356b9f', 'cpb-aacip-7706703ec0b', 'cpb-aacip-b1481965054', 'cpb-aacip-6e3b82580f7', 'cpb-aacip-877998821dc', 'cpb-aacip-b95be182039', 'cpb-aacip-880dc509c15', 'cpb-aacip-434b3170634', 'cpb-aacip-3b8055aa308', 'cpb-aacip-513da5076ba', 'cpb-aacip-da932501fe6', 'cpb-aacip-28f748b7497', 'cpb-aacip-13c1281e096', 'cpb-aacip-8a3022260a1', 'cpb-aacip-80000011ff4', 'cpb-aacip-22e22d31374', 'cpb-aacip-9c8ea501a0f', 'cpb-aacip-baeb029b92f', 'cpb-aacip-307f28484eb', 'cpb-aacip-2fa2f2b3201', 'cpb-aacip-d9e14afe451', 'cpb-aacip-d4641d07013', 'cpb-aacip-03a4ed7bc54', 'cpb-aacip-cbea66b660c', 'cpb-aacip-ffd24d30d63', 'cpb-aacip-ba8ad11a314', 'cpb-aacip-dd0c43f88cd', 'cpb-aacip-e9872f65192', 'cpb-aacip-b57b92a9f73', 'cpb-aacip-bc18dce2a09', 'cpb-aacip-45b7f7e047c', 'cpb-aacip-04189e66ae6', 'cpb-aacip-eb5d7b2b99e', 'cpb-aacip-6f549696f6a', 'cpb-aacip-d90af50d491', 'cpb-aacip-97c9ff64d37', 'cpb-aacip-5cb9717a667', 'cpb-aacip-37e5c1a7b50', 'cpb-aacip-c8c8e9d2fbe', 'cpb-aacip-acd7932c39d', 'cpb-aacip-6551a1e587c', 'cpb-aacip-1a6926b9226', 'cpb-aacip-384c89a2545', 'cpb-aacip-9b997d486af', 'cpb-aacip-8866b8f3124', 'cpb-aacip-17ac9c9763d', 'cpb-aacip-28e8a254f02', 'cpb-aacip-5725a773848', 'cpb-aacip-8143d402877', 'cpb-aacip-14ebfc006bc', 'cpb-aacip-d3693d1c7e8', 'cpb-aacip-a1e0d840399', 'cpb-aacip-6e8123c0f8a', 'cpb-aacip-8da9942aea8', 'cpb-aacip-63ebd4bdbdf', 'cpb-aacip-585c3eb7556', 'cpb-aacip-9ea8de360c7', 'cpb-aacip-c7f7ae67883', 'cpb-aacip-7e011ed2ab6', 'cpb-aacip-c74289c7f4b', 'cpb-aacip-e77d877e307', 'cpb-aacip-130b882564e', 'cpb-aacip-e1a090f735e', 'cpb-aacip-6ebb731bc96', 'cpb-aacip-8e04e487f7b', 'cpb-aacip-eef7d27118b', 'cpb-aacip-2266b9affdc', 'cpb-aacip-90f78dd0500', 'cpb-aacip-07485110f4f', 'cpb-aacip-aab5194f5e9', 'cpb-aacip-90b72049411', 'cpb-aacip-3e93792fcd0', 'cpb-aacip-17a506e597c', 'cpb-aacip-d35d53c4149', 'cpb-aacip-eaa2af1f3c7', 'cpb-aacip-43007ee2145', 'cpb-aacip-cc901d82f8a', 'cpb-aacip-19c8389f816', 'cpb-aacip-c726849c733', 'cpb-aacip-f0efcbd66e9', 'cpb-aacip-5edfc89c124', 'cpb-aacip-cac5a997ee3', 'cpb-aacip-aa4511f5050', 'cpb-aacip-fa5bbcfc485', 'cpb-aacip-3c57b18bebb', 'cpb-aacip-8d8fea2a9a4', 'cpb-aacip-9bbddd920a1', 'cpb-aacip-74487bdc3ce', 'cpb-aacip-7b1c1af4858', 'cpb-aacip-533f72a50e9', 'cpb-aacip-dc7c813df9a', 'cpb-aacip-fe16ed67ed6', 'cpb-aacip-972ae4fb1a7', 'cpb-aacip-d44f679dbcb', 'cpb-aacip-f96f1c2bf0c', 'cpb-aacip-5828f4c0eda', 'cpb-aacip-37cf5744c09', 'cpb-aacip-4ed7980cdef', 'cpb-aacip-5fa4a3b593b', 'cpb-aacip-d55435f3702', 'cpb-aacip-34c0407493e', 'cpb-aacip-360c71fdb71', 'cpb-aacip-1fbf03cb9bc', 'cpb-aacip-90bb24bad22', 'cpb-aacip-a7583889e91', 'cpb-aacip-679f7471995', 'cpb-aacip-656fe562453', 'cpb-aacip-6a6013d5d8d', 'cpb-aacip-5abfa920edb', 'cpb-aacip-c17a91fab1b', 'cpb-aacip-fa6004d5e47', 'cpb-aacip-7ab97e50a3e', 'cpb-aacip-76e0d9ed4f2', 'cpb-aacip-c1df135b1c6', 'cpb-aacip-79310f06483', 'cpb-aacip-70692b77f79', 'cpb-aacip-61bb804a2be', 'cpb-aacip-e290facdb54', 'cpb-aacip-cd154c887a8', 'cpb-aacip-5e575927688', 'cpb-aacip-7f153fd18c0', 'cpb-aacip-24964bbaa8e', 'cpb-aacip-2d9d706300e', 'cpb-aacip-13e055d962c', 'cpb-aacip-ab43fca501b', 'cpb-aacip-48cc8a704a6', 'cpb-aacip-cb813d64c31', 'cpb-aacip-0254bb7c3af', 'cpb-aacip-06112b078ec', 'cpb-aacip-6d322feb57a', 'cpb-aacip-7973cc44d7b', 'cpb-aacip-c4f0815c4f6', 'cpb-aacip-bf6b50d0b4a', 'cpb-aacip-7efb071a108', 'cpb-aacip-203b90c7f65', 'cpb-aacip-26d6f3278de', 'cpb-aacip-edb95307dd1', 'cpb-aacip-dd27ced095b', 'cpb-aacip-7cc95495e88', 'cpb-aacip-4ec16090a80', 'cpb-aacip-d96c4038f70', 'cpb-aacip-88d8c3f4523', 'cpb-aacip-f2d46b9fcd8', 'cpb-aacip-ba79bec4e23', 'cpb-aacip-76efdcc5d06', 'cpb-aacip-d2f9d805d7c', 'cpb-aacip-11c6d5cf6e2', 'cpb-aacip-86c3194e41b', 'cpb-aacip-2ae4db60f57', 'cpb-aacip-61be8abbd6c', 'cpb-aacip-67811650018', 'cpb-aacip-4ac14e8a6e0', 'cpb-aacip-75dac5429a6', 'cpb-aacip-999c115d7da', 'cpb-aacip-dd969ffff22', 'cpb-aacip-b5e609c3f52', 'cpb-aacip-50b71a5ea07', 'cpb-aacip-236147fa4a5', 'cpb-aacip-0d6bd56b607', 'cpb-aacip-2bc65f8a1d8', 'cpb-aacip-67c95785ab2', 'cpb-aacip-f055d03c405', 'cpb-aacip-26761f95654', 'cpb-aacip-0b8ca107792', 'cpb-aacip-e4699ccf643', 'cpb-aacip-c6fa45e75ff', 'cpb-aacip-5a5f86e03a3', 'cpb-aacip-a8f54be70ae', 'cpb-aacip-597fe43e64d', 'cpb-aacip-02f9990f8b1', 'cpb-aacip-206d164d1eb', 'cpb-aacip-bc72a59877e', 'cpb-aacip-27f0e09f5cb', 'cpb-aacip-0e914e71732', 'cpb-aacip-149e65956e8', 'cpb-aacip-279c2169824', 'cpb-aacip-09430efb216', 'cpb-aacip-e76fda3a185', 'cpb-aacip-7a011e15de1', 'cpb-aacip-e545ff69d46', 'cpb-aacip-192ff14c734', 'cpb-aacip-9f6d0cbfd0c', 'cpb-aacip-4dd14846151', 'cpb-aacip-b78eb0eb8ee', 'cpb-aacip-09de5b478d4', 'cpb-aacip-fcbecb6c76a', 'cpb-aacip-635691be07b', 'cpb-aacip-b1df95d7985', 'cpb-aacip-4f0b4895b1c', 'cpb-aacip-f1fb32bf089', 'cpb-aacip-f65f6be4837', 'cpb-aacip-977c2d34892', 'cpb-aacip-ba0fe84df3a', 'cpb-aacip-e5622e60e39', 'cpb-aacip-ec9076aede0', 'cpb-aacip-e8b4104f46c', 'cpb-aacip-d018a80536e', 'cpb-aacip-724a463dcd0', 'cpb-aacip-09fdb6bb777', 'cpb-aacip-48973683342', 'cpb-aacip-60111c4ff64', 'cpb-aacip-66907dfff2a', 'cpb-aacip-993af830e7a', 'cpb-aacip-2ac0391dd50', 'cpb-aacip-89e11a8f79b', 'cpb-aacip-3f101671f22', 'cpb-aacip-4e3f663ee46', 'cpb-aacip-d372a2a5018', 'cpb-aacip-fabe19c925c', 'cpb-aacip-e3c359412f8', 'cpb-aacip-0225a621107', 'cpb-aacip-95d5587ea00', 'cpb-aacip-9ac2f5e2455', 'cpb-aacip-8d00d1b32b8']
    challenge_1_guids = ['cpb-aacip-009a00c5120', 'cpb-aacip-00a9ed7f2ba', 'cpb-aacip-02d87284b83', 'cpb-aacip-02e9682f771', 'cpb-aacip-031f8af2a2b', 'cpb-aacip-04dbd31a1d2', 'cpb-aacip-04e93a86176', 'cpb-aacip-04eb5069ac1', 'cpb-aacip-04eec3207c2', 'cpb-aacip-055a6e36ac4', 'cpb-aacip-058470b9940', 'cpb-aacip-05cfae829fa', 'cpb-aacip-063f8c876fa', 'cpb-aacip-064d83c132b', 'cpb-aacip-0662bb05ff5', 'cpb-aacip-06735c1b53f', 'cpb-aacip-06a740f3c62', 'cpb-aacip-07e6a61402f', 'cpb-aacip-08a9a3c638a', 'cpb-aacip-08f1d75f76c', 'cpb-aacip-0ace30f582d', 'cpb-aacip-0ae98c2c4b2', 'cpb-aacip-0b0c0afdb11', 'cpb-aacip-0bb992d2e7f', 'cpb-aacip-0c0374c6c55', 'cpb-aacip-0c727d4cac3', 'cpb-aacip-0c74795718b', 'cpb-aacip-0cb2aebaeba', 'cpb-aacip-0d2fa57d507', 'cpb-aacip-0d74af419eb', 'cpb-aacip-0dbb0610457', 'cpb-aacip-0dfbaaec869', 'cpb-aacip-0e2dc840bc6', 'cpb-aacip-0ed7e315160', 'cpb-aacip-0f3879e2f22', 'cpb-aacip-0f80359ada5', 'cpb-aacip-0f80a4f5ed2', 'cpb-aacip-0fe3e4311e1', 'cpb-aacip-10273b80d90', 'cpb-aacip-107e3b9ebaa', 'cpb-aacip-128e28d359a', 'cpb-aacip-13da11f296c', 'cpb-aacip-143443221d5', 'cpb-aacip-15532842edc', 'cpb-aacip-1599f12aa94', 'cpb-aacip-161aa61b7a4', 'cpb-aacip-1645855556f', 'cpb-aacip-1723f17d4f9', 'cpb-aacip-17a483eadae', 'cpb-aacip-17ddac11002', 'cpb-aacip-17f556e2461', 'cpb-aacip-1865e6c64a4', 'cpb-aacip-18aa78fdd30', 'cpb-aacip-19cca6b1ca0', 'cpb-aacip-1a365705273', 'cpb-aacip-1b295839145', 'cpb-aacip-1b298a35cc4', 'cpb-aacip-1c8b20bddef', 'cpb-aacip-1cc1732ccfd', 'cpb-aacip-1d0024db7c1']
    challenge_2_guids = ['cpb-aacip-110-16c2ftdq', 'cpb-aacip-110-35gb5r94', 'cpb-aacip-111-655dvd99', 'cpb-aacip-120-1615dwkg', 'cpb-aacip-120-19s1rrsp', 'cpb-aacip-120-203xsm67', 'cpb-aacip-120-31qfv097', 'cpb-aacip-120-73pvmn2q', 'cpb-aacip-120-80ht7h8d', 'cpb-aacip-120-8279d01c', 'cpb-aacip-120-83xsjcb2', 'cpb-aacip-15-70msck27', 'cpb-aacip-16-19s1rw84', 'cpb-aacip-17-07tmq941', 'cpb-aacip-17-58bg87rx', 'cpb-aacip-17-65v6xv27', 'cpb-aacip-17-81jhbz0g', 'cpb-aacip-17-88qc0md1', 'cpb-aacip-29-61djhjcx', 'cpb-aacip-29-8380gksn', 'cpb-aacip-35-36tx99h9', 'cpb-aacip-41-322bvxmn', 'cpb-aacip-41-42n5tj3d', 'cpb-aacip-42-504xh4s7', 'cpb-aacip-42-78tb31b1', 'cpb-aacip-52-676t1pbw', 'cpb-aacip-52-84zgn1wb', 'cpb-aacip-52-87pnw5t0', 'cpb-aacip-55-84mkmvwx', 'cpb-aacip-75-13905w9q', 'cpb-aacip-75-54xgxnzg', 'cpb-aacip-77-02q5807j', 'cpb-aacip-77-074tnfhr', 'cpb-aacip-77-1937qsxt', 'cpb-aacip-77-214mx491', 'cpb-aacip-77-24jm6zc8', 'cpb-aacip-77-35t77b2v', 'cpb-aacip-77-44bp0mdh', 'cpb-aacip-77-49t1h3fv', 'cpb-aacip-77-81jhbv89', 'cpb-aacip-83-009w12j3', 'cpb-aacip-83-074tmx7h', 'cpb-aacip-83-23612txx']
    
    my_guids = wipr_4_1018_guids

    mask = asstdf["asset_id"].isin(my_guids)

    selected = asstdf[ mask ]
    cols = ["asset_id", "sonyci_id", "media_type", "asset_type", "level_of_user_access", "organization", "producing_organization", "single_date", "consolidated_title"]

    # apply projection
    projected = selected[ cols ]

    return projected



def filterproj2( asstdf ):
    """
    Do relational algebra stuff with the dataframes
    """

    # Define mask for selection 

    # filter for a list of GUIDs
    
    #wipr_1_26_guids = ['cpb-aacip-835c18587e0', 'cpb-aacip-21dd6788785', 'cpb-aacip-68649a312de', 'cpb-aacip-675c1b7c36c', 'cpb-aacip-b16b656ef0d', 'cpb-aacip-3ff5c2f0ddd', 'cpb-aacip-3240db2bc7a', 'cpb-aacip-3912e9e7e3e', 'cpb-aacip-e7606e6ddfe', 'cpb-aacip-1a78c71cc32', 'cpb-aacip-e7a0e4c11a2', 'cpb-aacip-46e26367307', 'cpb-aacip-5d07ca7987c', 'cpb-aacip-4e7c3ed78d8', 'cpb-aacip-c0028eb0268', 'cpb-aacip-58cc99d2da0', 'cpb-aacip-4efe0be68b8', 'cpb-aacip-39d9be74e5a', 'cpb-aacip-c48919b61bc', 'cpb-aacip-4d090735bbd', 'cpb-aacip-4cc437afdd2', 'cpb-aacip-3f4717cfde1', 'cpb-aacip-e6a549a4ffc', 'cpb-aacip-4f867ce7e37', 'cpb-aacip-b865919f9ce', 'cpb-aacip-620562fed97']
    #challenge_1_guids = ['cpb-aacip-009a00c5120', 'cpb-aacip-00a9ed7f2ba', 'cpb-aacip-02d87284b83', 'cpb-aacip-02e9682f771', 'cpb-aacip-031f8af2a2b', 'cpb-aacip-04dbd31a1d2', 'cpb-aacip-04e93a86176', 'cpb-aacip-04eb5069ac1', 'cpb-aacip-04eec3207c2', 'cpb-aacip-055a6e36ac4', 'cpb-aacip-058470b9940', 'cpb-aacip-05cfae829fa', 'cpb-aacip-063f8c876fa', 'cpb-aacip-064d83c132b', 'cpb-aacip-0662bb05ff5', 'cpb-aacip-06735c1b53f', 'cpb-aacip-06a740f3c62', 'cpb-aacip-07e6a61402f', 'cpb-aacip-08a9a3c638a', 'cpb-aacip-08f1d75f76c', 'cpb-aacip-0ace30f582d', 'cpb-aacip-0ae98c2c4b2', 'cpb-aacip-0b0c0afdb11', 'cpb-aacip-0bb992d2e7f', 'cpb-aacip-0c0374c6c55', 'cpb-aacip-0c727d4cac3', 'cpb-aacip-0c74795718b', 'cpb-aacip-0cb2aebaeba', 'cpb-aacip-0d2fa57d507', 'cpb-aacip-0d74af419eb', 'cpb-aacip-0dbb0610457', 'cpb-aacip-0dfbaaec869', 'cpb-aacip-0e2dc840bc6', 'cpb-aacip-0ed7e315160', 'cpb-aacip-0f3879e2f22', 'cpb-aacip-0f80359ada5', 'cpb-aacip-0f80a4f5ed2', 'cpb-aacip-0fe3e4311e1', 'cpb-aacip-10273b80d90', 'cpb-aacip-107e3b9ebaa', 'cpb-aacip-128e28d359a', 'cpb-aacip-13da11f296c', 'cpb-aacip-143443221d5', 'cpb-aacip-15532842edc', 'cpb-aacip-1599f12aa94', 'cpb-aacip-161aa61b7a4', 'cpb-aacip-1645855556f', 'cpb-aacip-1723f17d4f9', 'cpb-aacip-17a483eadae', 'cpb-aacip-17ddac11002', 'cpb-aacip-17f556e2461', 'cpb-aacip-1865e6c64a4', 'cpb-aacip-18aa78fdd30', 'cpb-aacip-19cca6b1ca0', 'cpb-aacip-1a365705273', 'cpb-aacip-1b295839145', 'cpb-aacip-1b298a35cc4', 'cpb-aacip-1c8b20bddef', 'cpb-aacip-1cc1732ccfd', 'cpb-aacip-1d0024db7c1']
    #my_guids = challenge_1_guids

    #mask = asstdf["asset_id"].isin(my_guids)

    # filter by a particular special collection
    #sc = 'bill-moyers'
    #sc = 'newshour'
    sc = 'peabody'
    mask1 = asstdf["special_collections"].str.split(',').apply(lambda x: sc in x)
    mask2 = asstdf["media_type"] == "Moving Image"
    mask3 = (asstdf["asset_type"] == "Episode") | (asstdf["asset_type"] == "Program")
    mask4 = asstdf["level_of_user_access"] == "Online Reading Room"
    mask = mask1 & mask2 & mask3 & mask4

    #mask = asstdf["media_type"] == "Moving Image"
    #mask = asstdf["asset_type"] == "Episode"
    #mask = asstdf["special_collections"].str.contains('bill-moyers')
    #mask = (asstdf["proxy_start_time"] != "") & (asstdf["media_type"] != "Moving_Image")

    #mask = (asstdf["transcript_status"] != "") & (asstdf["transcript_url"] == "")

    # filter for old style guids
    #mask = asstdf["aapb_pbcore_id"].str.contains("cpb-aacip/")

    # filter for transitional underscore guids
    #mask = asstdf["aapb_pbcore_id"].str.contains("cpb-aacip_")

    # filter for new style guids
    #mask = asstdf["aapb_pbcore_id"].str.contains("cpb-aacip-")

    # Other operations
    # get a list of special collection lists
    # scs = asstdf.groupby('special_collections')['asset_id'].count().sort_values(ascending=False)


    # default (unrestricted) mask
    #mask = asstdf["asset_id"] != ""

    # apply mask
    selected = asstdf[ mask ]

    # Define columns for projection
    #cols = ["asset_id", "sonyci_id", "proxy_start_time"]
    #cols = ["asset_id", "aapb_pbcore_id"]
    #cols = ["asset_id", "sonyci_id", "media_type", "asset_type"]
    cols = ["asset_id", "sonyci_id", "media_type", "asset_type", "level_of_user_access", "organization", "producing_organization", "single_date", "consolidated_title"]

    # A good informative set of columns.
    # originally for the for WIPR project
    cols = ["asset_id", "sonyci_id", "asset_type", "level_of_user_access", "broadcast_date", "created_date", "consolidated_title", "proxy_duration"]

    # apply projection
    projected = selected[ cols ]
    #projected = selected  # no projection

    return projected

############################################################################
# %%
# Define functions for I/O -- reading parameters and writing out results
def write_csv( df, csv_filename: str ):
    # write out selected and projected dataframe to CSV

    df.to_csv(csv_filename, index=False)


############################################################################
def main():
    
    parser = parser = argparse.ArgumentParser(
        prog='framify.py',
        description='routines for working with AAPB PBcore in Pandas Dataframes',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("pbcore_dir", metavar="DIR", nargs="?",
        help="Path to directory containing PBCore XML files")
    parser.add_argument("batch_csv", metavar="OUTPUT", nargs="?",
        help="Path of the CSV file to define a batch")

    global hardcoded_pbcore_dir
    global hardcoded_output_file

    args = parser.parse_args() 

    if args.pbcore_dir is not None:
        pbcore_dir = args.pbcore_dir
    else:
        pbcore_dir = hardcoded_pbcore_dir
    
    if args.batch_csv is not None:
        batch_csv = args.batch_csv
    else:
        batch_csv = hardcoded_output_file

    assttbl, insttbl = tablify( pbcore_dir )

    asstdf, instdf, joindf = inframe( assttbl, insttbl )

    projected = filterproj1( asstdf )

    write_csv( projected, batch_csv )


def build_full_frames():

    global hardcoded_pbcore_dir
    global hardcoded_output_file

    assttbl, insttbl = tablify( hardcoded_pbcore_dir )
    asstdf, instdf, joindf = inframe( assttbl, insttbl )

    return (asstdf, instdf, joindf)



# %%
# Execute 
if __name__ == "__main__":
    
    if notebook_mode:
        print("NOTE: execution of  `main()` function disabled for testing and notebook mode")
        print("")
        
        print("Building full dataframes . . .")
        assttbl, insttbl = tablify( hardcoded_pbcore_dir )
        asstdf, instdf, joindf = inframe( assttbl, insttbl )
        print("Done.")
        print("Built dataframes: asstdf, instdf, joindf")

    else:
        main()

