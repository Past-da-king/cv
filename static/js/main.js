// General UI enhancements and helper functions

document.addEventListener('DOMContentLoaded', function () {
    // Add loading state to *most* forms on submit, except those handled by specific scripts
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        // Exclude forms with specific IDs handled by other scripts
        if (form.id === 'repoSelectionForm') {
            return; 
        }

        form.addEventListener('submit', function () {
            const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            submitButtons.forEach(button => {
                // Store original state before disabling
                const originalButtonContent = button.innerHTML; // Capture inner HTML for buttons
                const originalButtonValue = button.tagName === 'INPUT' ? button.value : null;

                button.disabled = true;
                // Add spinner and text
                if (button.tagName === 'BUTTON') {
                     // Check if it already has a spinner (e.g., if JS re-initializes)
                    if (!button.querySelector('.spinner')) {
                         button.innerHTML = `<span class="spinner"></span> Loading...`;
                    } else {
                         button.innerHTML = originalButtonContent.replace(/(Loading|Processing|Generating).*$/, 'Loading...'); // Just update text if spinner exists
                    }
                } else if (button.tagName === 'INPUT') {
                     button.value = 'Loading...';
                }
                
                // Handle browser back button restoring the page state from bfcache
                window.addEventListener('pageshow', function(event) {
                    if (event.persisted) { 
                        button.disabled = false;
                        if (button.tagName === 'BUTTON') {
                            button.innerHTML = originalButtonContent; // Restore original HTML
                        } else if (button.tagName === 'INPUT' && originalButtonValue !== null) {
                            button.value = originalButtonValue; // Restore original value
                        }
                    }
                });
            });
        });
    });

    // Smooth scroll for anchor links (if any are added later)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href.length > 1) { 
                const targetElement = document.querySelector(href);
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

});

// Helper function to show a temporary message (toast-like)
// This is a very basic example. For a real SaaS, you'd use a library.
// Not strictly needed for this implementation flow but kept as a general utility
/*
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-5 right-5 p-4 rounded-lg shadow-lg text-white text-sm z-50 transition-opacity duration-300`;
    if (type === 'error') {
        toast.classList.add('bg-red-500');
    } else if (type === 'success') {
        toast.classList.add('bg-green-500');
    } else {
        toast.classList.add('bg-blue-500');
    }
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('opacity-0');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}
*/
