let = CATAID_MODE = false;
function cataidMode() {
    const cataidEls = document.querySelectorAll('.cataid-extra');
    for (let el of cataidEls) {
        el.classList.remove('hidden'); 
        el.classList.add('shown');
    }
    CATAID_MODE = true;
}
function visaidMode() {
    const cataidEls = document.querySelectorAll('.cataid-extra');
    for (let el of cataidEls) {
        el.classList.remove('shown'); 
        el.classList.add('hidden');
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

function updateVis() {
    // get status of scenes types from checkbox states
    const sceneVis = {}; 
    const allInputs = document.getElementsByTagName('input');
    for (const input of allInputs) { 
        if (input.type === 'checkbox') {
            sceneVis[input.value] = input.checked;
        }
    }
    // loop through each div of class "item" and set visibility
    const itemElements = document.querySelectorAll('.itemrow');
    for (let el of itemElements) {
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
function initializePage() {
    // set visibility to match checkbox values
    updateVis();
    // attach listeners to all the checkboxes
    const allInputs = document.getElementsByTagName('input');
    for (const input of allInputs) { 
        if (input.type === 'checkbox') {
            input.addEventListener('change', updateVis);
        }
    }
    document.getElementById('mode-toggle').addEventListener('click', toggleMode);
    // starting mode
    cataidMode();
}
document.addEventListener('DOMContentLoaded', initializePage);
