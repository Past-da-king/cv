document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('repoSelectionForm');
    if (!form) return; 

    const processSelectedButton = document.getElementById('processSelectedButton');
    const autoSelectButton = document.getElementById('autoSelectButton');
    const actionTypeInput = document.getElementById('actionTypeInput');
    const selectedCountSpan = document.getElementById('selectedCount');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const repoCheckboxes = document.querySelectorAll('input[name="selected_repos"]');
    
    // Use data attribute from button for max count
    const maxManualSelectAttr = processSelectedButton.dataset.maxManualSelect;
    const maxManualSelect = maxManualSelectAttr ? parseInt(maxManualSelectAttr, 10) : 5; 

    function updateSelectedCountAndButton() {
        if (!selectedCountSpan || !processSelectedButton) return;
        const checkedCheckboxes = document.querySelectorAll('input[name="selected_repos"]:checked');
        const checkedCount = checkedCheckboxes.length;
        
        selectedCountSpan.textContent = checkedCount;
        
        // Update button disabled state and appearance
        if (checkedCount === 0 || checkedCount > maxManualSelect) {
            processSelectedButton.disabled = true;
            processSelectedButton.classList.add('opacity-60', 'cursor-not-allowed');
            processSelectedButton.classList.remove('hover:bg-indigo-700'); // Use specific indigo color
            if (checkedCount > maxManualSelect) {
                processSelectedButton.title = `Please select no more than ${maxManualSelect} repositories.`;
            } else {
                processSelectedButton.title = `Select at least one repository.`;
            }
        } else {
            processSelectedButton.disabled = false;
            processSelectedButton.title = `Process ${checkedCount} selected repositories.`;
            processSelectedButton.classList.remove('opacity-60', 'cursor-not-allowed');
            processSelectedButton.classList.add('hover:bg-indigo-700'); // Use specific indigo color
        }
        
        // Ensure the button text is updated correctly with count and icon
        const buttonIconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 mr-2"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.06 0l4-5.5z" clip-rule="evenodd" /></svg>`;
        processSelectedButton.innerHTML = `${buttonIconSvg} Generate CV for Selected (<span id="selectedCount">${checkedCount}</span>)`;
    }

    // Add event listeners to checkboxes
    repoCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedCountAndButton);
    });

    // Add event listener for Select All checkbox
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            repoCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateSelectedCountAndButton();
        });
    }

    // Handle Manual Select button click
    if (processSelectedButton) {
        processSelectedButton.addEventListener('click', function(e) {
             e.preventDefault(); // Prevent default form submission
             if (this.disabled) return;

            // Set action type and add selected repos as hidden inputs
            actionTypeInput.value = 'manual_select';
            const existingHiddenInputs = form.querySelectorAll('input[type="hidden"][name="selected_repo_names"]');
            existingHiddenInputs.forEach(input => input.remove()); 

            const checkedCheckboxes = document.querySelectorAll('input[name="selected_repos"]:checked');
            checkedCheckboxes.forEach(cb => {
                const hiddenInput = document.createElement('input');
                hiddenInput.type = 'hidden';
                hiddenInput.name = 'selected_repo_names'; 
                hiddenInput.value = cb.value;
                form.appendChild(hiddenInput);
            });
            
            // Let main.js handle the generic form submit loading state
            form.submit(); 
        });
    }

    // Handle Auto Select button click
    if (autoSelectButton) {
        autoSelectButton.addEventListener('click', function(e) {
            e.preventDefault(); // Prevent default form submission
            
            actionTypeInput.value = 'auto_select';
            // Clear manual selections if auto-selecting
            const existingHiddenInputs = form.querySelectorAll('input[type="hidden"][name="selected_repo_names"]');
            existingHiddenInputs.forEach(input => input.remove());
            repoCheckboxes.forEach(checkbox => checkbox.checked = false); 
            // updateSelectedCountAndButton(); // Not strictly needed before submit for auto

            // Let main.js handle the generic form submit loading state
            form.submit(); 
        });
    }
    
    // Initial state update
    updateSelectedCountAndButton();
});
