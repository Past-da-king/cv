// General UI enhancements and helper functions

document.addEventListener('DOMContentLoaded', function () {
    // Example: Add loading state to forms on submit
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function () {
            const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            submitButtons.forEach(button => {
                button.disabled = true;
                // Check if it's a button element to add spinner, or input
                if (button.tagName === 'BUTTON') {
                    const originalText = button.innerHTML;
                    button.innerHTML = `<span class="spinner"></span> Processing...`;
                    // Restore button text if user navigates back
                    window.addEventListener('pageshow', function(event) {
                        if (event.persisted) { // Check if page was loaded from bfcache
                            button.disabled = false;
                            button.innerHTML = originalText;
                        }
                    });
                } else if (button.tagName === 'INPUT') {
                    button.value = 'Processing...';
                     window.addEventListener('pageshow', function(event) {
                        if (event.persisted) {
                            button.disabled = false;
                            // For input, you might need to store original value differently
                        }
                    });
                }
            });
        });
    });

    // Smooth scroll for anchor links (if any are added later)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href.length > 1) { // Ensure it's not just "#"
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
