"""
catification_prompts.py

Text to be used to select prompts for use with the GBH AI Helper.
"""

sys_prompt = """
You are sharp and analytical. 
You provide a short, precise answer to each request. 
Do not restate the question or use full sentences. 
Do not add any phrases or punctuation unless they are part of the answer.
Your response must be the answer ONLY.  
If you cannot definitively determining a single answer, then you must respond with exactly this string: 'NO ANSWER'
"""

chyron_instr_01 = """
Analyze the given text into several data.  Add one datum per line, skipping lines between items.
*First datum*: Copy exactly the person's name as written, including titles (such as "Miss", "Dr.", "Senator", "Rev.", etc.) and designations (such as "M.D." or "Ph.D."). Preserve capitalization as presented.
*Second datum*: Write the normalized form of the person's name. Normalize capitalization to title case, and change the order to "Lastname, Firstname" or "Lastname, Firstname Middlename, Suffix". For example: "Murray, Patty" or "King, Martin Luther, Jr." Do not add names, initials, characters not found in the name as written.
*Additional data*: Copy any role, location, context, or other characteristics associated with the person, with one attribute per line.  Normalize case to title case as appropriate, but otherwise copy verbatim.  Do not separate attributes into multiple lines unless they could be considered separate attributes of the person. In cases of multiple attributes, skip one line between them.
"""

chyron_instr_02 = """
This is text read by OCR from from the Chyron on a TV screen.  
In this text, we need to extract two or three data elements:

**(1) name as written (without attributes)**:  The person's name as it appears in the text.  Exclude attributes and affiliations.  But include honorifics (such as "Miss", "Dr.", "Senator", "Rev.", "Rabbi", "Captain", "Professor", etc.), post-nominal letters (such as "M.D." or "Ph.D."), and generational suffixes (such as "III" or "Jr.").  If the text is all lower case or all upper case, convert to title case, as apropriate.

**(2) normalized name**:  The normalized form of the person's name.  Normalize capitalization to title case, and change the order to "Surname, Firstname" or "Surname, Firstname Middlename, Suffix". Be sure to insert a comma between the surname and given names, and between given names and any suffix.  For example: "Murray, Patty" or "King, Martin Luther, Jr." Do not add any names or initials not found in the name as written.

**(3) attributes** (optional, if present):  If present in the text, copy the role, affiliation, location, context, or other characteristics given after the person's name.  Exclude titles,honorifics, or any attributes that appear in the text before the person's name.  Preserve the punctuation, including periods, commas, and parenthesis, such as in "(D)" or "(R)".  Normalize case to title case as appropriate, but otherwise copy the attributes verbatim.

Since the text was generated with OCR, you may notice errors.  Correct obvious spelling and typographic errors.  If you see the word "NIN", "NN", or "NBN", it is likely spurious and can be omitted.

Output the two or three data elements, one per line.  Make sure to include a blank line between each data element.
"""


slate_instr_date_01 = """
Look for any dates in the text.
For each date, normalize it in YYYY-MM-DD format.
Output one date per line.
"""

slate_instr_date_02 = """
Look for any dates in the text.
For each date, normalize it in YYYY-MM-DD format, and prefix the string `*air: `.
Here is an example output:
*air: 1987-09-17
"""

catprompts = {
    "slate": {
        "system": sys_prompt,
        "instr": slate_instr_date_02
    },
    "chyron and person": {
        "system": sys_prompt,
        "instr": chyron_instr_02
    }
}
