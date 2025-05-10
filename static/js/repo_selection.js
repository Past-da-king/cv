document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('repoSelectionForm');
    if (!form) return; // Exit if the form isn't on this page

    const processSelectedButton = document.getElementById('processSelectedButton');
    const autoSelectButton = document.getElementById('autoSelectButton');
    const actionTypeInput = document.getElementById('actionTypeInput');
    const selectedCountSpan = document.getElementById('selectedCount');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const repoCheckboxes = document.querySelectorAll('input[name="selected_repos"]');
    
    // Assuming max_manual_select_repos is passed to the template and available globally or via a data attribute
    // For simplicity, let's try to get it from a data attribute on the button itself
    const maxManualSelectAttr = processSelectedButton.dataset.maxManualSelect;
    const maxManualSelect = maxManualSelectAttr ? parseInt(maxManualSelectAttr, 10) : 5; // Default to 5 if not found

    function updateSelectedCountAndButton() {
        if (!selectedCountSpan || !processSelectedButton) return;
        const checkedCheckboxes = document.querySelectorAll('input[name="selected_repos"]:checked');
        const checkedCount = checkedCheckboxes.length;
        
        selectedCountSpan.textContent = checkedCount;
        processSelectedButton.disabled = checkedCount === 0 || checkedCount > maxManualSelect;

        if (checkedCount > maxManualSelect) {
            processSelectedButton.title = `Please select no more than ${maxManualSelect} repositories for manual processing.`;
            processSelectedButton.classList.add('opacity-50', 'cursor-not-allowed');
            processSelectedButton.classList.remove('hover:bg-indigo-700');
        } else if (checkedCount === 0) {
            processSelectedButton.title = `Select at least one repository.`;
            processSelectedButton.classList.add('opacity-50', 'cursor-not-allowed');
            processSelectedButton.classList.remove('hover:bg-indigo-700');
        }
         else {
            processSelectedButton.title = `Process ${checkedCount} selected repositories.`;
            processSelectedButton.classList.remove('opacity-50', 'cursor-not-allowed');
            processSelectedButton.classList.add('hover:bg-indigo-700');
        }
    }

    repoCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedCountAndButton);
    });

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            repoCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateSelectedCountAndButton();
        });
    }

    if (processSelectedButton) {
        processSelectedButton.addEventListener('click', function() {
            if (this.disabled) return;
            actionTypeInput.value = 'manual_select';
            // Collect selected repo names and add them as hidden inputs to the form
            // This ensures they are POSTed correctly as Form data
            const existingHiddenInputs = form.querySelectorAll('input[type="hidden"][name="selected_repo_names"]');
            existingHiddenInputs.forEach(input => input.remove()); // Clear previous

            const checkedCheckboxes = document.querySelectorAll('input[name="selected_repos"]:checked');
            checkedCheckboxes.forEach(cb => {
                const hiddenInput = document.createElement('input');
                hiddenInput.type = 'hidden';
                hiddenInput.name = 'selected_repo_names'; // FastAPI will expect this
                hiddenInput.value = cb.value;
                form.appendChild(hiddenInput);
            });
            form.submit();
        });
    }

    if (autoSelectButton) {
        autoSelectButton.addEventListener('click', function() {
            actionTypeInput.value = 'auto_select';
            // Clear any manual selections as they won't be used for auto_select
            const existingHiddenInputs = form.querySelectorAll('input[type="hidden"][name="selected_repo_names"]');
            existingHiddenInputs.forEach(input => input.remove());
            repoCheckboxes.forEach(checkbox => checkbox.checked = false); 
            updateSelectedCountAndButton(); // Update UI for checkboxes
            form.submit();
        });
    }
    
    // Initial state
    updateSelectedCountAndButton();
});
