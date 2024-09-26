
// Code to allow user to toggle visibility of samples

function hideSamples( className ) {
    const sampleElements = document.querySelectorAll(`.${className}`);

    // Loop through the elements and make invisible
    for (let el of sampleElements) {
        el.classList.add('hidden');    // hide
    }
}

function toggleVis( className ) {
    const sampleElements = document.querySelectorAll(`.${className}`);

    // Loop through the elements and toggle their visibility
    for (let el of sampleElements) {
        if (el.classList.contains('hidden')) {
            el.classList.remove('hidden');  // show 
        } else {
            el.classList.add('hidden');    // hide
        }    
    }
}

function initializePage() {
    // Hide samples by default
    hideSamples('subsample');
    hideSamples('unsample');

    // Activate and show toggle buttons
    var myButton;
    myButton = document.getElementById('subsamplesVisButton');
    myButton.addEventListener('click', function(){ toggleVis('subsample');});
    if (myButton.classList.contains('hidden')) {
        myButton.classList.remove('hidden');  
    }
    myButton = document.getElementById('unsamplesVisButton');
    myButton.addEventListener('click', function(){ toggleVis('unsample');});
    if (myButton.classList.contains('hidden')) {
        myButton.classList.remove('hidden');  
    }

}

document.addEventListener('DOMContentLoaded', initializePage);

