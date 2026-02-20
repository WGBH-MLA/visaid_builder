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

chyron_instr = """
Analyze the given text into several data.  Add one datum per line, skipping lines between items.
*First datum*: Copy exactly the person's name as written, including titles (such as "Miss", "Dr.", "Senator", "Rev.", etc.) and designations (such as "M.D." or "Ph.D."). Preserve capitalization as presented.
*Second datum*: Write the normalized form of the person's name. Normalize capitalization to title case, and change the order to "Lastname, Firstname" or "Lastname, Firstname Middlename, Suffix". For example: "Murray, Patty" or "King, Martin Luther, Jr." Do not add names, initials, characters not found in the name as written.
*Additional data*: Copy any role, location, context, or other characteristics associated with the person, with one attribute per line.  Normalize case to title case as appropriate, but otherwise copy verbatim.  Do not separate attributes into multiple lines unless they could be considered separate attributes of the person. In cases of multiple attributes, skip one line between them.
"""

slate_instr_date = """
Look for any dates in the text.
For each date, normalize it in YYYY-MM-DD format.
Output one date per line.
"""

catprompts = {
    "slate": {
        "system": sys_prompt,
        "instr": slate_instr_date
    },
    "chyron and person": {
        "system": sys_prompt,
        "instr": chyron_instr
    }
}
