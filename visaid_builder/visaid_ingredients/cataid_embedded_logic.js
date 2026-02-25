function updateVis() {
    // get status of scenes types from checkbox states
    const sceneVis = {}; 
    for (const input of document.getElementsByTagName('input')) { 
        if (input.type === 'checkbox') {
            sceneVis[input.value] = input.checked;
        }
    }
    // loop through each div of class "item" and set visibility
    for (const el of document.querySelectorAll('.itemrow')) {
        let show = false;
        if (sceneVis[el.dataset.scenetype]) {
            if (!el.dataset.label.includes(" - - -") || sceneVis["scene subsample"] ) {
                 show = true;
            }
        }
        if (show) { 
            el.classList.remove('hidden'); 
            el.classList.add('shown');
        }
        else { 
            el.classList.remove('shown')
            el.classList.add('hidden');
        }
    }
}

let = CATAID_MODE = false;
function cataidMode() {
    for (const el of document.querySelectorAll('.cataid-extra')) {
        el.classList.remove('hidden'); 
        el.classList.add('shown');
    }
    for (const el of document.querySelectorAll('.itemrow') ) {
        el.classList.add('fullrow');
    }
    document.getElementById('collect-edits').classList.remove('invisible')
    document.getElementById('cataloger_form').classList.remove('invisible')
    document.getElementById('collect-edits').classList.add('clickable')
    CATAID_MODE = true;
}

function visaidMode() {
    for (const el of document.querySelectorAll('.cataid-extra')) {
        el.classList.remove('shown'); 
        el.classList.add('hidden');
    }
    for (const el of document.querySelectorAll('.itemrow') ) {
        el.classList.remove('fullrow');
    }
    document.getElementById('collect-edits').classList.add('invisible')
    document.getElementById('cataloger_form').classList.add('invisible')
    document.getElementById('collect-edits').classList.remove('clickable')
    CATAID_MODE = false;
}

function toggleMode() {
    if (CATAID_MODE == true) {
        CATAID_MODE = false;
        visaidMode();
    }
    else {
        CATAID_MODE = true;
        cataidMode();
    }
}

function toggleEngagement() {
    const tpTime = this.dataset.tptime;
    
    for (const el of document.querySelectorAll(`.item-editor[data-tptime="${tpTime}"]`)) {
        if (el.classList.contains("engaged")) {
            el.classList.remove('engaged');
        }
        else {
            el.classList.add('engaged');
        }
    }
}

function collectEdits () {
    const dataExport = {};
    dataExport["asset_id"] = document.getElementById("video-id").dataset["videoId"];
    dataExport["cataid_id"] = document.getElementById("cataid-id").dataset["cataidId"];
    dataExport["cataid_ver"] = document.getElementById("cataid-version").innerText.trim();
    dataExport["cataloger"] = document.getElementById("cataloger_blank").innerText.trim();    
    dataExport["export_date"] = new Date().toISOString().slice(0,-5) + "Z";
    dataExport["editor_items"] = [];
    for (const itemEl of document.querySelectorAll(`.item-editor.engaged`)) {
        const editorItem = {};
        editorItem["tp_time"] = tptime = parseInt(itemEl.dataset["tptime"]);
        editorItem["tf_label"] = itemEl.dataset["scenetype"];
        const edtEl = document.querySelector(`.editor-text[data-tptime='${tptime}']`);
        editorItem["etd_text"] = edtEl.innerText.trim();        
        const aidEl = document.querySelector(`.aid-text[data-tptime='${tptime}']`);
        editorItem["aid_text"] = aidEl.innerText.trimEnd();                
        editorItem["tp_id"] = edtEl.dataset["tpid"];
        const fnameEl = document.querySelector(`.img-fname[data-tptime='${tptime}']`);
        editorItem["img_fname"] = fnameEl.textContent.trim();
        const imgEl = document.querySelector(`img[data-tptime='${tptime}']`);
        editorItem["img_data_uri"] = imgEl.getAttribute('src');
        dataExport["editor_items"].push(editorItem);
    }
    const mmifViewsMetadataEl = document.getElementById('mmif-views-metadata');
    dataExport["MMIF_views_metadata"] = JSON.parse(mmifViewsMetadataEl.textContent);
    const outputJSON = JSON.stringify(dataExport, null, 2);
    const filedata = new Blob([outputJSON], {type: "application/json" });
    const url = window.URL.createObjectURL(filedata);
    const filename = dataExport["asset_id"] + "_catout.json"
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    window.URL.revokeObjectURL(url);
}

function initializePage() {
    // set visibility to match checkbox values
    updateVis();
    // attach listeners 
    document.getElementById('mode-toggle').addEventListener('click', toggleMode);
    document.getElementById('collect-edits').addEventListener('click', collectEdits);
    for (const input of document.getElementsByTagName('input')) { 
        if (input.type === 'checkbox') {
            input.addEventListener('change', updateVis);
        }
    }
    for (const el of document.querySelectorAll('.engage-toggle')) {
        el.addEventListener('click', toggleEngagement);
    }
    visaidMode();  // starting in visaid mode
}

document.addEventListener('DOMContentLoaded', initializePage);
