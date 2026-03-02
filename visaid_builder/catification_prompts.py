"""
catification_prompts.py

Text to be used to select prompts for use with the GBH AI Helper.

To variables are defined:

`system_prompt` - a string for the system prompt

`scene_prompts` - a dictionary of prompts for paticular scene types

"""

system_prompt = """
You are sharp and analytical. 
You provide a short, precise answer to each request. 
Do not restate the question or use full sentences. 
Do not add any phrases or punctuation unless they are part of the answer.
Your response must be the answer ONLY.  
If you cannot definitively determining a single answer, then you must respond with exactly this string: 'NO ANSWER'
"""

###########################################################################

_slate_instr_date_01 = """
Look for any dates in the text.
For each date, normalize it in YYYY-MM-DD format.
Output one date per line.
"""

_slate_instr_date_02 = """
Look for any dates in the text.
For each date, normalize it in YYYY-MM-DD format, and prefix the string `*air: `.
Here is an example output:
*air: 1987-09-17
"""

_slate_general_01 = """
This is text read by OCR from the slate in a recording of an archival televsion program.

Try to perform extraction of keyed values from the text.  

Output each key-value pair on a single line.  Make sure to include a blank line between each key-value pair.

Prepend an asterisk(*) to the name of the key, and then include a colon and space (: ) before the value.

Normalize dates in YYYY-MM-DD format.  Put names in title case.

For example, if you find a broadcast date for September 17, 1987, you would output this line:
*air: 1987-09-17

Or, if you see that the director referred to as "REYNOLDS", you output this line:
*dir: Reynolds

Look for values that would correspond to the following keys:
- *air* -- for the air date or broadcast date
- *rec* -- for the date of creation or recording
- *date* -- for a date of unknown type
- *prog-title* -- for program title (for a non-episodic program)
- *series-title* -- for the title of the series
- *ep-title* -- for the title of the episode
- *title* -- for a title of unknown type
- *ep-no* -- for episode number
- *dir* -- for the name of the director
- *prod* -- for the name of the director
- *cam* -- for the name of the camera person

You may not find values for any of those keys.  Output values only for the keys you find.
"""

###########################################################################

_chyron_instr_01 = """
Analyze the given text into several data.  Add one datum per line, skipping lines between items.
*First datum*: Copy exactly the person's name as written, including titles (such as "Miss", "Dr.", "Senator", "Rev.", etc.) and designations (such as "M.D." or "Ph.D."). Preserve capitalization as presented.
*Second datum*: Write the normalized form of the person's name. Normalize capitalization to title case, and change the order to "Lastname, Firstname" or "Lastname, Firstname Middlename, Suffix". For example: "Murray, Patty" or "King, Martin Luther, Jr." Do not add names, initials, characters not found in the name as written.
*Additional data*: Copy any role, location, context, or other characteristics associated with the person, with one attribute per line.  Normalize case to title case as appropriate, but otherwise copy verbatim.  Do not separate attributes into multiple lines unless they could be considered separate attributes of the person. In cases of multiple attributes, skip one line between them.
"""

_chyron_instr_02 = """
This is text read by OCR from from the Chyron on a TV screen.
In this text, we need to extract two or three data elements:

**(1) name as written (without attributes)**:  The person's name as it appears in the text.  Exclude attributes and affiliations.  But include honorifics (such as "Miss", "Dr.", "Senator", "Rev.", "Rabbi", "Captain", "Professor", etc.), post-nominal letters (such as "M.D." or "Ph.D."), and generational suffixes (such as "III" or "Jr.").  If the text is all lower case or all upper case, convert to title case, as apropriate.

**(2) normalized name**:  The normalized form of the person's name.  Normalize capitalization to title case, and change the order to "Surname, Firstname" or "Surname, Firstname Middlename, Suffix". Be sure to insert a comma between the surname and given names, and between given names and any suffix.  For example: "Murray, Patty" or "King, Martin Luther, Jr." Do not add any names or initials not found in the name as written.

**(3) attributes** (optional, if present):  If present in the text, copy the role, affiliation, location, context, or other characteristics given after the person's name.  Exclude titles, honorifics, or other attributes that appear before the person's name.  Preserve the punctuation, including periods, commas, and parenthesis, such as in "(D)" or "(R)".  Normalize case to title case as appropriate. Use all caps for initials and acronyms. Otherwise copy the attributes verbatim.

Since the text was generated with OCR, you may notice errors.  Correct obvious spelling and typographic errors. 

Output the two or three data elements, one per line.  Make sure to include a blank line between each data element.
"""

###########################################################################

scene_prompts = {
    "slate": _slate_general_01,
    "chyron and person": _chyron_instr_02
}
