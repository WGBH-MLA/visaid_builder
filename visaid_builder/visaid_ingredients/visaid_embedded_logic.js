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
    const itemElements = document.querySelectorAll('.item');
    for (let el of itemElements) {
        let show = false;
        if (sceneVis[el.dataset.scenetype]) {
            if (!el.dataset.label.includes(" - - -") || sceneVis["scene subsample"] ) {
                 show = true;
            }
        }
        if (show) el.classList.remove('hidden'); 
        else el.classList.add('hidden');
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
}
document.addEventListener('DOMContentLoaded', initializePage);
