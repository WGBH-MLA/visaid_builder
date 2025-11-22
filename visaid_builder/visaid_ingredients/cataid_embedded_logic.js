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

function initializePage() {
    // set visibility to match checkbox values
    updateVis();
    // attach listeners to all the checkboxes
    for (const input of document.getElementsByTagName('input')) { 
        if (input.type === 'checkbox') {
            input.addEventListener('change', updateVis);
        }
    }
    // attach visaid/cataid toggle function
    document.getElementById('mode-toggle').addEventListener('click', toggleMode);
    
    // attach listeners to edit opener buttons
    for (const el of document.querySelectorAll('.engage-toggle')) {
        el.addEventListener('click', toggleEngagement);
    }

    // starting mode
    visaidMode();
}

document.addEventListener('DOMContentLoaded', initializePage);
