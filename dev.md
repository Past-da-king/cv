
## static/css/custom.css
```css
/* For custom styles that are hard to achieve with Tailwind utility classes alone */
body {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Custom scrollbar for a more modern feel (optional) */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: #f1f5f9; /* slate-100 */
}
::-webkit-scrollbar-thumb {
    background: #94a3b8; /* slate-400 */
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #64748b; /* slate-500 */
}

/* Styling for prose in CV entries if needed beyond plugin */
.cv-content-body ul,
.cv-content-body ol {
    padding-left: 1.25rem; /* Adjust as needed */
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}
.cv-content-body li {
    margin-bottom: 0.25rem;
}

/* Add a subtle animation for button loading states */
.spinner {
    display: inline-block;
    width: 1em;
    height: 1em;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: spin 0.75s linear infinite;
    margin-right: 0.5em; /* Adjust as needed */
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}
```

## static/js/main.js
```javascript
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
```

## static/js/repo_selection.js
```javascript
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('repoSelectionForm');
    if (!form) return; 

    const processSelectedButton = document.getElementById('processSelectedButton');
    const autoSelectButton = document.getElementById('autoSelectButton');
    const actionTypeInput = document.getElementById('actionTypeInput');
    const selectedCountSpan = document.getElementById('selectedCount');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const repoCheckboxes = document.querySelectorAll('input[name="selected_repos"]');
    
    const maxManualSelectAttr = processSelectedButton.dataset.maxManualSelect;
    const maxManualSelect = maxManualSelectAttr ? parseInt(maxManualSelectAttr, 10) : 5; 

    function updateSelectedCountAndButton() {
        if (!selectedCountSpan || !processSelectedButton) return;
        const checkedCheckboxes = document.querySelectorAll('input[name="selected_repos"]:checked');
        const checkedCount = checkedCheckboxes.length;
        
        selectedCountSpan.textContent = checkedCount;
        
        const originalButtonText = `Generate CV for Selected (<span id="selectedCount">${checkedCount}</span>)`; // Store original HTML structure
        const buttonIconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 mr-2"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.06 0l4-5.5z" clip-rule="evenodd" /></svg>`;


        if (checkedCount === 0 || checkedCount > maxManualSelect) {
            processSelectedButton.disabled = true;
            processSelectedButton.classList.add('opacity-60', 'cursor-not-allowed');
            processSelectedButton.classList.remove('hover:bg-indigo-700');
            if (checkedCount > maxManualSelect) {
                processSelectedButton.title = `Please select no more than ${maxManualSelect} repositories.`;
            } else {
                processSelectedButton.title = `Select at least one repository.`;
            }
        } else {
            processSelectedButton.disabled = false;
            processSelectedButton.title = `Process ${checkedCount} selected repositories.`;
            processSelectedButton.classList.remove('opacity-60', 'cursor-not-allowed');
            processSelectedButton.classList.add('hover:bg-indigo-700');
        }
        // Ensure the button text is updated correctly with count
        processSelectedButton.innerHTML = `${buttonIconSvg} Generate CV for Selected (<span id="selectedCount">${checkedCount}</span>)`;

    }

    repoCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedCountAndButton);
    });

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            repoCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
                // Optional: trigger change event for each checkbox if other listeners depend on it
                // checkbox.dispatchEvent(new Event('change'));
            });
            updateSelectedCountAndButton();
        });
    }

    if (processSelectedButton) {
        processSelectedButton.addEventListener('click', function(e) {
            e.preventDefault(); // Prevent default form submission
            if (this.disabled) return;

            this.disabled = true;
            this.innerHTML = `<span class="spinner"></span> Processing Selected...`;


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
            form.submit();
        });
    }

    if (autoSelectButton) {
        autoSelectButton.addEventListener('click', function(e) {
            e.preventDefault(); // Prevent default form submission
            this.disabled = true;
            this.innerHTML = `<span class="spinner"></span> Auto-Generating...`;

            actionTypeInput.value = 'auto_select';
            const existingHiddenInputs = form.querySelectorAll('input[type="hidden"][name="selected_repo_names"]');
            existingHiddenInputs.forEach(input => input.remove());
            repoCheckboxes.forEach(checkbox => checkbox.checked = false); 
            // updateSelectedCountAndButton(); // Not strictly needed before submit for auto
            form.submit();
        });
    }
    
    updateSelectedCountAndButton();
});

```

## templates/base.html
```html
<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-50">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ app_title }}{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,typography"></script>
    <script>
      tailwind.config = {
        theme: {
          extend: {
            fontFamily: {
              sans: ['Inter var', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', '"Noto Sans"', 'sans-serif', '"Apple Color Emoji"', '"Segoe UI Emoji"', '"Segoe UI Symbol"', '"Noto Color Emoji"'],
            },
            colors: {
              primary: {
                DEFAULT: '#087EA4', // A calm, professional teal/blue
                hover:  '#066886',
                light: '#E0F2F7',
                text: '#FFFFFF'
              },
              secondary: {
                DEFAULT: '#4A5568', // Cool Gray
                hover: '#2D3748'
              },
              accent: {
                DEFAULT: '#DD6B20', // Orange for contrast (example)
                hover: '#C05621'
              },
              slate: { // Tailwind's slate is great for UIs
                50: '#f8fafc',
                100: '#f1f5f9',
                200: '#e2e8f0',
                300: '#cbd5e1',
                400: '#94a3b8',
                500: '#64748b',
                600: '#475569',
                700: '#334155',
                800: '#1e293b',
                900: '#0f172a',
              }
            }
          }
        },
        plugins: [
            require('@tailwindcss/forms'),
            require('@tailwindcss/typography'),
        ],
      }
    </script>
    <link rel="stylesheet" href="https://rsms.me/inter/inter.css">
    <link rel="stylesheet" href="{{ url_for('static', path='/css/custom.css') }}">
    <script src="{{ url_for('static', path='/js/main.js') }}" defer></script>
    {% block head_extra %}{% endblock %}
</head>
<body class="h-full antialiased text-slate-700">
    <div class="min-h-screen flex flex-col">
        
        <header class="bg-white shadow-sm sticky top-0 z-40">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex items-center justify-between h-16">
                    <div class="flex items-center">
                        <a href="{{ url_for('get_token_form_page') if request.cookies.get('github_pat') else url_for('get_token_form_page') }}" class="flex-shrink-0 flex items-center space-x-2">
                            <svg class="h-8 w-auto text-primary-DEFAULT" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
                            </svg>
                            <span class="font-semibold text-xl text-slate-800">{{ app_title }}</span>
                        </a>
                    </div>
                    <div class="flex items-center">
                        {% if request.url.path != '/' and request.cookies.get('github_pat') %}
                        <a href="{{ url_for('get_token_form_page') }}" class="text-sm font-medium text-slate-600 hover:text-primary-DEFAULT transition-colors">
                            Change Token
                        </a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </header>

        <main class="flex-grow bg-slate-100 py-8 sm:py-12">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {% block content %}
                {% endblock %}
            </div>
        </main>

        <footer class="bg-slate-100 border-t border-slate-200">
            <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 text-center text-sm text-slate-500">
                &copy; {{ app_title }} {{ app_version }}. Powered by a sprinkle of AI.
            </div>
        </footer>
    </div>
</body>
</html>
```

## templates/token_form.html
```html
{% extends "base.html" %}

{% block title %}Connect GitHub - {{ app_title }}{% endblock %}

{% block content %}
<div class="flex flex-col items-center justify-center min-h-[calc(100vh-10rem)] sm:min-h-[calc(100vh-12rem)]">
    <div class="w-full max-w-lg p-8 sm:p-12 bg-white rounded-xl shadow-2xl border border-slate-200">
        <div class="text-center mb-8">
             <svg class="mx-auto h-16 w-16 text-slate-800 mb-4" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.22.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0016 8c0-4.42-3.58-8-8-8z"/>
            </svg>
            <h1 class="text-3xl font-bold tracking-tight text-slate-900">{{ app_title }}</h1>
            <p class="mt-3 text-md text-slate-600">
                Connect your GitHub account using a Personal Access Token (PAT) 
                with <code class="bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded text-xs font-mono">repo</code> scope.
            </p>
        </div>
        
        {% if error_message %}
            <div class="p-4 mb-6 text-sm text-red-700 bg-red-100 rounded-lg border border-red-300 flex items-start space-x-3" role="alert">
                <svg class="flex-shrink-0 w-5 h-5 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1.293-8.707a1 1 0 011.414-1.414L10 8.586l1.293-1.293a1 1 0 111.414 1.414L11.414 10l1.293 1.293a1 1 0 01-1.414 1.414L10 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L8.586 10 7.293 8.707z" clip-rule="evenodd" />
                </svg>
                <div>
                    <h3 class="font-medium">Connection Error</h3>
                    <p class="mt-1">{{ error_message }}</p>
                </div>
            </div>
        {% endif %}
        
        <form method="post" action="{{ url_for('set_github_token') }}" class="space-y-6">
            <div>
                <label for="token" class="block text-sm font-medium text-slate-700 mb-1.5">GitHub PAT</label>
                <input type="password" id="token" name="token" required 
                       class="appearance-none block w-full px-4 py-2.5 border border-slate-300 rounded-lg shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-DEFAULT focus:border-primary-DEFAULT sm:text-sm transition-colors" 
                       placeholder="Enter your GitHub Personal Access Token">
            </div>
            <button type="submit" 
                    class="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-primary-DEFAULT hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-DEFAULT transition duration-150 ease-in-out">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 mr-2 -ml-1">
                  <path fill-rule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clip-rule="evenodd" />
                </svg>
                Connect & List Repositories
            </button>
        </form>
        <p class="text-xs text-slate-500 mt-8 text-center">
            Your token is stored securely in an httpOnly cookie and used solely for accessing your repositories.
            <a href="https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token" target="_blank" rel="noopener noreferrer" class="font-medium text-primary-DEFAULT hover:text-primary-hover hover:underline">
                Learn more about PATs
            </a>.
        </p>
    </div>
</div>
{% endblock %}
```

## templates/repo_list.html
```html
{% extends "base.html" %}

{% block title %}Select Repositories - {{ app_title }}{% endblock %}

{% block head_extra %}
    <script src="{{ url_for('static', path='/js/repo_selection.js') }}" defer></script>
{% endblock %}

{% block content %}
<div class="space-y-8">
    <div class="flex flex-col md:flex-row justify-between items-center gap-4">
        <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Select Repositories</h1>
        <!-- Future filter/sort options could go here -->
    </div>

    {% if error_message %}
    <div class="p-4 text-sm text-red-700 bg-red-100 rounded-lg border border-red-300 flex items-start space-x-3" role="alert">
        <svg class="flex-shrink-0 w-5 h-5 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1.293-8.707a1 1 0 011.414-1.414L10 8.586l1.293-1.293a1 1 0 111.414 1.414L11.414 10l1.293 1.293a1 1 0 01-1.414 1.414L10 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L8.586 10 7.293 8.707z" clip-rule="evenodd" />
        </svg>
        <div>
            <h3 class="font-medium">Error Fetching Repositories</h3>
            <p class="mt-1">{{ error_message }}</p>
        </div>
    </div>
    {% endif %}
    
    <form id="repoSelectionForm" method="post" action="{{ url_for('generate_cv_summary_page') }}">
        <input type="hidden" name="action_type" id="actionTypeInput" value="">
        
        <div class="bg-white p-6 rounded-xl shadow-lg border border-slate-200 mb-8">
            <div class="flex flex-col sm:flex-row justify-between items-center gap-4 sm:gap-6">
                <div class="w-full sm:w-auto flex-grow sm:flex-grow-0">
                    <button type="button" id="processSelectedButton"
                            data-max-manual-select="{{ max_manual_select_repos }}"
                            class="w-full sm:w-auto flex justify-center items-center py-2.5 px-5 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out disabled:opacity-60 disabled:cursor-not-allowed">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 mr-2">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.06 0l4-5.5z" clip-rule="evenodd" />
                        </svg>
                        Generate CV for Selected (<span id="selectedCount">0</span>)
                    </button>
                    <p class="text-xs text-slate-500 mt-1.5 text-center sm:text-left">Manually select up to {{ max_manual_select_repos }} repositories.</p>
                </div>
                <div class="text-center text-sm text-slate-400 hidden sm:block">OR</div>
                <div class="w-full sm:w-auto flex-grow sm:flex-grow-0">
                    <button type="button" id="autoSelectButton"
                            class="w-full sm:w-auto flex justify-center items-center py-2.5 px-5 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-primary-DEFAULT hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-DEFAULT transition duration-150 ease-in-out">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 mr-2">
                          <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM3 10a.75.75 0 01.75-.75h12.5a.75.75 0 010 1.5H3.75A.75.75 0 013 10z" clip-rule="evenodd" />
                        </svg>
                        Auto-Generate for Top {{ auto_select_output_count }}
                    </button>
                     <p class="text-xs text-slate-500 mt-1.5 text-center sm:text-left">Processes {{ auto_select_process_count }} most recent repos.</p>
                </div>
            </div>
             {% if repo_cards_html %}
            <div class="mt-6 pt-6 border-t border-slate-200">
                <label class="flex items-center space-x-2.5 cursor-pointer text-sm text-slate-600 hover:text-primary-DEFAULT mb-4 group">
                    <input type="checkbox" id="selectAllCheckbox" class="h-4 w-4 text-primary-DEFAULT border-slate-300 rounded focus:ring-primary-DEFAULT group-hover:border-primary-DEFAULT transition-colors">
                    <span class="font-medium">Select All / Deselect All Visible Repositories</span>
                </label>
            </div>
            {% endif %}
        </div>

        {% if repo_cards_html %}
            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {{ repo_cards_html | safe }} {# Repo cards HTML is generated in main.py #}
            </div>
        {% else %}
            {% if not error_message %}
            <div class="text-center py-16 bg-white rounded-xl shadow-lg border border-slate-200">
                <svg class="mx-auto h-12 w-12 text-slate-400" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
                <h3 class="mt-2 text-lg font-semibold text-slate-900">No Repositories Found</h3>
                <p class="mt-1 text-sm text-slate-500">Your GitHub account doesn't seem to have any repositories, or we couldn't access them.</p>
                <div class="mt-6">
                  <a href="{{ url_for('get_token_form_page') }}" class="inline-flex items-center rounded-md bg-primary-DEFAULT px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-DEFAULT">
                    <svg class="-ml-0.5 mr-1.5 h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5V4.75z" />
                    </svg>
                    Retry Connection
                  </a>
                </div>
            </div>
            {% endif %}
        {% endif %}
    </form>
</div>
{% endblock %}
```

## templates/repo_contents.html
```html
{% extends "base.html" %}

{% block title %}Contents of {{ repo_full_name }} - {{ app_title }}{% endblock %}

{% block content %}
<div class="space-y-6">
    <nav aria-label="Breadcrumb" class="mb-2">
        <ol role="list" class="flex items-center space-x-2 text-sm">
            <li>
                <a href="{{ url_for('list_repositories_page') }}" class="text-slate-500 hover:text-primary-DEFAULT transition-colors">
                    <svg class="flex-shrink-0 h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M9.293 2.293a1 1 0 011.414 0l7 7A1 1 0 0117 10.707V17.5a1.5 1.5 0 01-1.5 1.5h-3A1.5 1.5 0 0111 17.5V15h-2v2.5A1.5 1.5 0 017.5 19h-3A1.5 1.5 0 013 17.5V10.707a1 1 0 01.293-.707l7-7z" clip-rule="evenodd" />
                    </svg>
                    <span class="sr-only">Repositories</span>
                </a>
            </li>
            <li>
                <div class="flex items-center">
                    <svg class="h-5 w-5 flex-shrink-0 text-slate-400" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                        <path d="M5.555 17.776l8-16 .894.448-8 16-.894-.448z" />
                    </svg>
                    <span class="ml-2 text-slate-700 font-semibold truncate" title="{{ repo_full_name }}">{{ repo_full_name }}</span>
                </div>
            </li>
        </ol>
    </nav>

    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 break-all">{{ repo_full_name }}</h1>
        {% if up_link %}
            {{ up_link | safe }} {# Assumes up_link contains full styled <a> tag from main.py #}
        {% endif %}
    </div>
    
    <div class="bg-slate-100 border border-slate-200 text-slate-600 p-3.5 rounded-lg text-sm font-mono break-all shadow-inner">
        <span class="font-semibold text-slate-800">Current Path:</span> /{{ current_path_display }}
    </div>

    {% if error_message %}
    <div class="p-4 text-sm text-red-700 bg-red-100 rounded-lg border border-red-300 flex items-start space-x-3" role="alert">
        <svg class="flex-shrink-0 w-5 h-5 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1.293-8.707a1 1 0 011.414-1.414L10 8.586l1.293-1.293a1 1 0 111.414 1.414L11.414 10l1.293 1.293a1 1 0 01-1.414 1.414L10 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L8.586 10 7.293 8.707z" clip-rule="evenodd" />
        </svg>
        <div>
            <h3 class="font-medium">Error Browsing Repository</h3>
            <p class="mt-1">{{ error_message }}</p>
        </div>
    </div>
    {% endif %}

    {% if content_list_html_items %}
        <div class="bg-white overflow-hidden rounded-xl shadow-lg border border-slate-200">
            <ul role="list" class="divide-y divide-slate-200">
                {{ content_list_html_items | safe }} {# Items are generated in main.py with new styling #}
            </ul>
        </div>
    {% else %}
         {% if not error_message %}
         <div class="text-center py-16 bg-white rounded-xl shadow-lg border border-slate-200">
            <svg class="mx-auto h-12 w-12 text-slate-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
            </svg>
            <h3 class="mt-2 text-lg font-semibold text-slate-900">Directory Empty</h3>
            <p class="mt-1 text-sm text-slate-500">This directory doesn't contain any files or folders.</p>
         </div>
         {% endif %}
    {% endif %}
</div>
{% endblock %}
```

## templates/file_view.html
```html
{% extends "base.html" %}

{% block title %}File: {{ file_path_display }} - {{ app_title }}{% endblock %}

{% block content %}
<div class="space-y-6">
    <nav aria-label="Breadcrumb" class="mb-2">
      <ol role="list" class="flex items-center space-x-2 text-sm">
        <li>
          <a href="{{ url_for('list_repositories_page') }}" class="text-slate-500 hover:text-primary-DEFAULT transition-colors">
            <svg class="flex-shrink-0 h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M9.293 2.293a1 1 0 011.414 0l7 7A1 1 0 0117 10.707V17.5a1.5 1.5 0 01-1.5 1.5h-3A1.5 1.5 0 0111 17.5V15h-2v2.5A1.5 1.5 0 017.5 19h-3A1.5 1.5 0 013 17.5V10.707a1 1 0 01.293-.707l7-7z" clip-rule="evenodd" /></svg>
            <span class="sr-only">Repositories</span>
          </a>
        </li>
        <li>
          <div class="flex items-center">
            <svg class="h-5 w-5 flex-shrink-0 text-slate-400" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path d="M5.555 17.776l8-16 .894.448-8 16-.894-.448z" /></svg>
            <a href="{{ back_to_dir_link }}" class="ml-2 text-sm font-medium text-slate-500 hover:text-primary-DEFAULT transition-colors truncate" title="{{ repo_full_name }}">{{ repo_full_name }}</a>
          </div>
        </li>
         <li>
          <div class="flex items-center">
            <svg class="h-5 w-5 flex-shrink-0 text-slate-400" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path d="M5.555 17.776l8-16 .894.448-8 16-.894-.448z" /></svg>
            <span class="ml-2 text-sm font-medium text-slate-700" aria-current="page">{{ file_path_display.split('/')[-1] }}</span>
          </div>
        </li>
      </ol>
    </nav>

    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 break-all">{{ file_path_display.split('/')[-1] }}</h1>
        <a href="{{ back_to_dir_link }}" class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50 transition-colors">
            <svg class="-ml-0.5 mr-1.5 h-5 w-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd" />
            </svg>
            Back to Directory
        </a>
    </div>
    <p class="text-sm text-slate-500">Full path: <code class="text-xs bg-slate-100 p-1 rounded">{{ file_path_display }}</code></p>
    
    {% if error_message %}
    <div class="p-4 text-sm text-red-700 bg-red-100 rounded-lg border border-red-300 flex items-start space-x-3" role="alert">
        <svg class="flex-shrink-0 w-5 h-5 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1.293-8.707a1 1 0 011.414-1.414L10 8.586l1.293-1.293a1 1 0 111.414 1.414L11.414 10l1.293 1.293a1 1 0 01-1.414 1.414L10 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L8.586 10 7.293 8.707z" clip-rule="evenodd" />
        </svg>
        <div>
            <h3 class="font-medium">Error Viewing File</h3>
            <p class="mt-1">{{ error_message }}</p>
        </div>
    </div>
    {% endif %}

    {% if file_content_display_html %}
        {% if is_binary_file_message %}
            <div class="p-6 bg-yellow-50 border border-yellow-300 rounded-xl shadow-lg text-sm text-yellow-700" role="alert">
                <div class="flex items-start space-x-3">
                    <svg class="flex-shrink-0 w-5 h-5 text-yellow-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
                    </svg>
                    <div>{{ file_content_display_html | safe }}</div>
                </div>
            </div>
        {% else %}
            <div class="bg-slate-900 text-slate-200 p-4 sm:p-6 border border-slate-700 rounded-xl overflow-x-auto text-sm shadow-inner">
                <pre class="font-mono whitespace-pre-wrap break-words leading-relaxed"><code>{{- file_content_display_html | safe -}}</code></pre>
            </div>
        {% endif %}
    {% else %}
        {% if not error_message %}
        <div class="text-center py-16 bg-white rounded-xl shadow-lg border border-slate-200">
            <svg class="mx-auto h-12 w-12 text-slate-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <h3 class="mt-2 text-lg font-semibold text-slate-900">No Content</h3>
            <p class="mt-1 text-sm text-slate-500">This file appears to be empty or its content could not be displayed.</p>
        </div>
        {% endif %}
    {% endif %}
</div>
{% endblock %}
```

## templates/cv_summary.html
```html
{% extends "base.html" %}

{% block title %}CV Summaries - {{ app_title }}{% endblock %}

{% block content %}
<div class="space-y-8">
    <div class="flex flex-col md:flex-row justify-between items-center gap-4">
        <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Generated CV Summaries</h1>
        <a href="{{ url_for('list_repositories_page') }}" class="inline-flex items-center rounded-md bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50 transition-colors">
            <svg class="-ml-0.5 mr-1.5 h-5 w-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd" />
            </svg>
            Back to Repositories
        </a>
    </div>

    {% if message %}
        <div class="p-4 text-sm rounded-lg border shadow-sm flex items-start space-x-3
                    {% if 'error' in message.lower() or 'failed' in message.lower() or 'disabled' in message.lower() or 'could not' in message.lower() %} 
                        text-red-700 bg-red-50 border-red-300
                    {% elif 'warning' in message.lower() or 'some errors' in message.lower() %}
                        text-amber-700 bg-amber-50 border-amber-300
                    {% else %} 
                        text-green-700 bg-green-50 border-green-300
                    {% endif %}" role="alert">
            {% if 'error' in message.lower() or 'failed' in message.lower() or 'disabled' in message.lower() or 'could not' in message.lower() %}
                <svg class="flex-shrink-0 w-5 h-5 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1.293-8.707a1 1 0 011.414-1.414L10 8.586l1.293-1.293a1 1 0 111.414 1.414L11.414 10l1.293 1.293a1 1 0 01-1.414 1.414L10 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L8.586 10 7.293 8.707z" clip-rule="evenodd" />
                </svg>
            {% elif 'warning' in message.lower() or 'some errors' in message.lower() %}
                <svg class="flex-shrink-0 w-5 h-5 text-amber-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
                </svg>
            {% else %} 
                <svg class="flex-shrink-0 w-5 h-5 text-green-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.06 0l4-5.5z" clip-rule="evenodd" />
                </svg>
            {% endif %}
            <div><p class="font-medium">Processsing Summary</p>{{ message | safe }}</div>
        </div>
    {% endif %}

    {% if cv_entries_html_parts %}
        <div class="space-y-10">
            {% for entry_html in cv_entries_html_parts %}
                {{ entry_html | safe }} {# HTML for each entry is generated in main.py #}
            {% endfor %}
        </div>
    {% else %}
        {% if not message or ('error' not in message.lower() and 'failed' not in message.lower() and 'disabled' not in message.lower()) %}
         <div class="text-center py-16 bg-white rounded-xl shadow-lg border border-slate-200">
            <svg class="mx-auto h-12 w-12 text-slate-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <h3 class="mt-2 text-lg font-semibold text-slate-900">No CV Entries Generated</h3>
            <p class="mt-1 text-sm text-slate-500">This might be because no repositories were processed, or an issue occurred.</p>
        </div>
        {% endif %}
    {% endif %}
</div>
{% endblock %}

```


## main.py

```python
import uvicorn
from fastapi import FastAPI, Request, Form, Query, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates 
from typing import Optional, List
import os
from urllib.parse import quote, unquote
import re 
import html as html_escaper 

import config 
from config import (
    APP_TITLE, APP_VERSION, GOOGLE_API_KEY,
    MAX_REPOS_TO_DISPLAY_FOR_SELECTION,
    AUTO_SELECT_PROCESS_COUNT, AUTO_SELECT_FINAL_OUTPUT_COUNT,
    MAX_MANUAL_SELECT_REPOS_FOR_CV,
    USE_LOCAL_EMBEDDINGS 
)
from github_service import (
    fetch_user_repos, fetch_repo_contents_list,
    fetch_raw_file_content_from_url
)
from cv_generator_logic import orchestrate_cv_generation_for_repos
from utils import escape_html_chars
from vector_store_service import load_vector_store 
from local_embedding_service import local_embedder_model 

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# Ensure the templates directory is correctly referenced relative to main.py
# If templates is in 'cv/templates' and main.py is in 'cv/', then "templates" is correct.
templates = Jinja2Templates(directory="templates") 
app.state.user_repos_cache = None 

if os.path.exists("static"):
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    # Attempt to mount from 'cv/static' if main.py is in the root above 'cv'
    static_dir_alt = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir_alt):
         app.mount("/static", StaticFiles(directory=static_dir_alt), name="static")
    else:
        print("Warning: Static directory not found at 'static/' or 'cv/static/'. Ensure it's correctly placed.")


@app.on_event("startup")
async def startup_event():
    print(f"Starting {APP_TITLE} v{APP_VERSION}...")
    if not GOOGLE_API_KEY:
        print("CRITICAL WARNING: GOOGLE_API_KEY not set. CV Generation (Gemini) will NOT work.")
    else:
        print("GOOGLE_API_KEY found.")
    if local_embedder_model is None and USE_LOCAL_EMBEDDINGS: 
         print("CRITICAL WARNING: Local embedding model failed to load. CV context building will not work correctly.")
    elif USE_LOCAL_EMBEDDINGS: 
        print(f"Using local embeddings with model: {config.LOCAL_EMBEDDING_MODEL_NAME}")
    else:
        print(f"Using Gemini API for embeddings with model: {config.GEMINI_EMBEDDING_MODEL_NAME} (Rate limits apply!)")
    
    print("Attempting to load vector store from disk...")
    load_vector_store() 

@app.get("/", response_class=HTMLResponse)
async def get_token_form_page(request: Request, error: Optional[str] = None):
    # Check if already authenticated, redirect to repos if so
    if request.cookies.get("github_pat"):
        # Before redirecting, try fetching repos to see if token is still valid
        # This is a bit heavy for just a check, could be a lighter ping to GitHub API
        # For now, this check is removed for simplicity, relying on user to re-auth if token invalid.
        # User will hit an error on /repos if token is bad.
        pass # Pass, means token_form will be shown. Can be adjusted.
             # Consider a redirect to /repos if request.cookies.get("github_pat")
             # but handle token expiry gracefully.

    return templates.TemplateResponse("token_form.html", {
        "request": request, 
        "error_message": unquote(error) if error else None,
        "app_title": APP_TITLE,
        "app_version": APP_VERSION,
    })

@app.post("/auth/set-token")
async def set_github_token(request: Request, token: str = Form(...)):
    if not token or not token.strip():
        error_msg = quote("GitHub PAT cannot be empty.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)
    
    response = RedirectResponse(url="/repos", status_code=303)
    response.set_cookie(
        key="github_pat", value=token, httponly=True, 
        samesite="lax", max_age=3600 * 24 * 7, # Cookie for 7 days
        secure=request.url.scheme == "https", path="/"
    ) 
    return response

@app.get("/repos", response_class=HTMLResponse)
async def list_repositories_page(request: Request, github_pat: Optional[str] = Cookie(None)):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired. Please enter it again to connect.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    result = fetch_user_repos(github_pat) 
    
    repo_cards_html = ""
    error_message_for_template = None

    if result["error"]:
        error_message_for_template = f'{escape_html_chars(result["error"])} You might need to re-enter your token.'
    elif not result["data"]:
        repo_cards_html = "" # No specific message here, template will handle "No Repositories Found"
    else:
        card_items = []
        repos_to_display = result["data"][:MAX_REPOS_TO_DISPLAY_FOR_SELECTION]
        app.state.user_repos_cache = result["data"] 

        for repo in repos_to_display:
            repo_full_name = repo.get("full_name", "N/A")
            repo_full_name_escaped = escape_html_chars(repo_full_name)
            owner_login = escape_html_chars(repo.get("owner", {}).get("login", ""))
            repo_name_only = escape_html_chars(repo.get("name", ""))
            
            language = repo.get("language")
            language_escaped = escape_html_chars(language if language else "N/A")
            
            pushed_at_raw = repo.get("pushed_at", "N/A")
            pushed_at_date = pushed_at_raw[:10] if pushed_at_raw != "N/A" else "N/A"
            pushed_at_escaped = escape_html_chars(pushed_at_date)

            visibility = repo.get("visibility", "N/A")
            visibility_escaped = escape_html_chars(visibility.capitalize())
            
            description_raw = repo.get("description") 
            if description_raw and isinstance(description_raw, str): 
                description_truncated = description_raw[:120] # Slightly more
                if len(description_raw) > 120:
                    description_truncated += "..."
                description_escaped = escape_html_chars(description_truncated)
            else:
                description_escaped = "No description provided."
            
            star_count = repo.get("stargazers_count", 0)
            fork_count = repo.get("forks_count", 0)

            card_items.append(f'''
<div class="bg-white rounded-xl shadow-lg border border-slate-200 hover:shadow-xl transition-shadow duration-300 ease-in-out flex flex-col overflow-hidden">
    <div class="p-5 sm:p-6 flex-grow">
        <div class="flex items-start space-x-3 mb-3">
            <input type="checkbox" name="selected_repos" value="{repo_full_name_escaped}" class="h-5 w-5 text-primary-DEFAULT border-slate-300 rounded focus:ring-primary-DEFAULT mt-1 cursor-pointer">
            <div class="flex-1 min-w-0">
                <h3 class="text-lg font-semibold text-slate-800 hover:text-primary-DEFAULT transition-colors leading-tight">
                    <a href="/repo/{owner_login}/{repo_name_only}" class="block truncate" title="Browse {repo_full_name_escaped}">{repo_full_name_escaped}</a>
                </h3>
                <p class="text-xs text-slate-500 mt-0.5">
                    Last pushed: {pushed_at_escaped}
                </p>
            </div>
        </div>
        <p class="text-sm text-slate-600 mb-4 h-16 overflow-hidden leading-relaxed">{description_escaped}</p> 
    </div>
    <div class="px-5 sm:px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
        <span class="inline-flex items-center gap-1.5">
            <span class="capitalize px-2 py-0.5 bg-slate-200 text-slate-700 rounded-full font-medium">{visibility_escaped}</span>
            {(f'<span class="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full font-medium">{language_escaped}</span>') if language else ''}
        </span>
        <span class="flex items-center gap-3">
            <span class="flex items-center" title="{star_count} stars">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-amber-400 mr-0.5"><path fill-rule="evenodd" d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.393c-.83.069-.996 1.033-.464 1.491l3.493 3.01-1.057 4.637c-.19.825.743 1.44 1.482 1.06l4.116-2.512 4.116 2.512c.74.38 1.673-.235 1.482-1.06l-1.057-4.637 3.494-3.01c.531-.458.366-1.422-.464-1.491l-4.753-.393-1.83-4.401z" clip-rule="evenodd" /></svg>
                {star_count}
            </span>
            <span class="flex items-center" title="{fork_count} forks">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-slate-400 mr-0.5"><path fill-rule="evenodd" d="M10 2c-2.236 0-4.048.032-5.454.144C3.044 2.264 2 3.22 2 4.544v8.912c0 1.324 1.043 2.28 2.546 2.402C6.03 16.005 8.005 16 10 16s3.97-.005 5.454-.144c1.503-.122 2.546-1.078 2.546-2.402V4.544c0-1.324-1.043-2.28-2.546-2.402C13.969 2.032 12.236 2 10 2zM6.67 10.43a2.5 2.5 0 100-5 2.5 2.5 0 000 5zm6.66 0a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" clip-rule="evenodd" /></svg>
                {fork_count}
            </span>
        </span>
    </div>
</div>
            ''')
        repo_cards_html = "".join(card_items)
        
    return templates.TemplateResponse("repo_list.html", {
        "request": request,
        "error_message": error_message_for_template,
        "repo_cards_html": repo_cards_html,
        "max_manual_select_repos": MAX_MANUAL_SELECT_REPOS_FOR_CV,
        "auto_select_process_count": AUTO_SELECT_PROCESS_COUNT,
        "auto_select_output_count": AUTO_SELECT_FINAL_OUTPUT_COUNT,
        "app_title": APP_TITLE,
        "app_version": APP_VERSION,
    })

@app.get("/repo/{owner}/{repo_name}", response_class=HTMLResponse)
async def view_repo_directory_contents(
    request: Request, owner: str, repo_name: str,
    path: str = Query(""), github_pat: Optional[str] = Cookie(None)
):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired. Please connect again.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    current_path_unquoted = unquote(path)
    result = fetch_repo_contents_list(github_pat, owner, repo_name, current_path_unquoted)
    
    content_list_html_items = "" 
    error_message_for_template = None

    if result["error"]:
        error_message_for_template = escape_html_chars(result["error"])
    elif not result["data"] and not current_path_unquoted: # Empty repo root
         pass # Template will show "Directory Empty"
    elif not result["data"] and current_path_unquoted: # Empty subdirectory
         pass # Template will show "Directory Empty"
    else:
        items = []
        for item in result["data"]:
            item_name_escaped = escape_html_chars(item.get("name", "N/A"))
            item_path_raw = item.get("path", "")
            encoded_item_path = quote(item_path_raw)
            item_type = item.get("type", "unknown")

            icon_svg = ""
            link_class = "font-medium text-slate-700 hover:text-primary-DEFAULT transition-colors group-hover:text-primary-DEFAULT"
            item_details = ""
            action_text = "Open"

            if item_type == "dir":
                icon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-amber-500 group-hover:text-amber-600 transition-colors"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" /></svg>'''
                link_target = f'/repo/{owner}/{repo_name}?path={encoded_item_path}'
                item_details = f"<span class='text-xs text-slate-400'>Directory</span>"
                action_text = "Browse"
            elif item_type == "file":
                icon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-slate-400 group-hover:text-slate-500 transition-colors"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V8a2 2 0 00-2-2h-5L9 4H4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z" clip-rule="evenodd" /></svg>'''
                link_target = f'/repo/{owner}/{repo_name}/file?path={encoded_item_path}'
                item_size_bytes = item.get('size', 0)
                item_details = f"<span class='text-xs text-slate-400'>{item_size_bytes} bytes</span>"
                action_text = "View File"
            else: # Symlink or other
                icon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-slate-400"><path fill-rule="evenodd" d="M12.207 2.207a1 1 0 011.414 0l4.25 4.25a1 1 0 010 1.414l-4.25 4.25a1 1 0 01-1.414-1.414L14.586 9H4.75a1 1 0 110-2h9.836L12.207 3.621a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>'''
                link_target = "#" 
                link_class = "text-slate-500 cursor-default"
                item_details = f"<span class='text-xs text-slate-400'>(type: {escape_html_chars(item_type)})</span>"
                action_text = "N/A"
            
            items.append(f'''
            <li class="group">
                <a href="{link_target}" class="block hover:bg-slate-50 transition-colors">
                    <div class="flex items-center justify-between px-4 py-4 sm:px-6">
                        <div class="flex items-center min-w-0 space-x-3">
                            {icon_svg}
                            <p class="truncate text-sm {link_class}">{item_name_escaped}</p>
                        </div>
                        <div class="flex items-center space-x-3 ml-2">
                            {item_details}
                            <svg class="h-5 w-5 text-slate-400 group-hover:text-slate-500 transition-colors" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
                            </svg>
                        </div>
                    </div>
                </a>
            </li>
            ''')
        content_list_html_items = "".join(items)
    
    up_link_html = ""
    if current_path_unquoted:
        parent_path = os.path.dirname(current_path_unquoted)
        encoded_parent_path = quote(parent_path)
        # This will be used in the template's header/breadcrumb area now
        up_link_html = f'''
        <a href="/repo/{owner}/{repo_name}?path={encoded_parent_path}" 
           class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50 transition-colors">
            <svg class="-ml-0.5 mr-1.5 h-5 w-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd"></path>
            </svg>
            Up one level
        </a>'''
    
    return templates.TemplateResponse("repo_contents.html", {
        "request": request,
        "repo_full_name": escape_html_chars(f"{owner}/{repo_name}"),
        "current_path_display": escape_html_chars(current_path_unquoted if current_path_unquoted else "(root)"),
        "up_link": up_link_html, 
        "content_list_html_items": content_list_html_items,
        "error_message": error_message_for_template,
        "app_title": APP_TITLE,
        "app_version": APP_VERSION,
    })


@app.post("/generate-cv-summary", response_class=HTMLResponse)
async def generate_cv_summary_page(
    request: Request, 
    github_pat: Optional[str] = Cookie(None),
    action_type: str = Form(...), 
    selected_repo_names: Optional[List[str]] = Form(None) 
):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired. Cannot generate CV summary.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    if not GOOGLE_API_KEY: 
        message = "Google API Key not configured. CV generation feature is disabled."
        return templates.TemplateResponse("cv_summary.html", {
            "request": request, "message": message, "cv_entries_html_parts": [], 
            "app_title": APP_TITLE, "app_version": APP_VERSION,
        })

    all_fetched_repos = getattr(app.state, 'user_repos_cache', None)
    if not all_fetched_repos:
        fetch_result = fetch_user_repos(github_pat)
        if fetch_result["error"] or not fetch_result["data"]:
            message = f'Could not fetch repositories for CV generation: {escape_html_chars(fetch_result.get("error", "No data"))}'
            return templates.TemplateResponse("cv_summary.html", {
                "request": request, "message": message, "cv_entries_html_parts": [], 
                "app_title": APP_TITLE, "app_version": APP_VERSION,
            })
        all_fetched_repos = fetch_result["data"]
        app.state.user_repos_cache = all_fetched_repos

    repos_to_actually_process = []
    if action_type == 'manual_select':
        if not selected_repo_names: 
            message = "No repositories were selected for manual processing."
            return templates.TemplateResponse("cv_summary.html", {
                "request": request, "message": message, "cv_entries_html_parts": [],
                "app_title": APP_TITLE, "app_version": APP_VERSION,
            })
        
        selected_repo_names_set = set(selected_repo_names)
        repos_to_actually_process = [repo for repo in all_fetched_repos if repo.get("full_name") in selected_repo_names_set]
        
        if len(repos_to_actually_process) > MAX_MANUAL_SELECT_REPOS_FOR_CV:
            message = f"Too many repositories selected. Please select no more than {MAX_MANUAL_SELECT_REPOS_FOR_CV}."
            return templates.TemplateResponse("cv_summary.html", {
                "request": request, "message": message, "cv_entries_html_parts": [],
                "app_title": APP_TITLE, "app_version": APP_VERSION,
            })

    elif action_type == 'auto_select':
        repos_to_actually_process = all_fetched_repos[:AUTO_SELECT_PROCESS_COUNT]
    else:
        message = "Invalid action type for CV generation."
        return templates.TemplateResponse("cv_summary.html", {
            "request": request, "message": message, "cv_entries_html_parts": [],
            "app_title": APP_TITLE, "app_version": APP_VERSION,
        })

    if not repos_to_actually_process:
        message = 'No repositories selected or available for CV summary processing.'
        return templates.TemplateResponse("cv_summary.html", {
            "request": request, "message": message, "cv_entries_html_parts": [],
            "app_title": APP_TITLE, "app_version": APP_VERSION,
        })

    print(f"Starting CV generation. Action: '{action_type}'. Repos to process: {[r.get('full_name') for r in repos_to_actually_process]}")
    generated_cvs_data = orchestrate_cv_generation_for_repos(github_pat, repos_to_actually_process, action_type)
    print("Finished CV generation orchestration.")

    cv_entries_html_result_parts = [] 
    successful_cv_count = 0
    
    for cv_data in generated_cvs_data: 
        repo_name_esc = escape_html_chars(cv_data.get("repo", "Unknown Repo"))
        if cv_data.get("cv_entry"):
            successful_cv_count +=1
            cv_text_raw = cv_data["cv_entry"]
            # Apply HTML escaping first, then nl2br, then regex for bolding and lists
            cv_text_html = escape_html_chars(cv_text_raw).replace("\n", "<br />\n")
            cv_text_html = re.sub(r'\*\*(Project Description|Key Features/Accomplishments|Technologies Used|Key Highlights|Project Overview):\*\*', r'<strong class="block mt-3 mb-1.5 text-slate-800 font-semibold text-base">\1:</strong>', cv_text_html)
            # Improved list item handling:
            # This regex tries to match list items more robustly after <br /> tags.
            # It wraps the content after the bullet in a span for better styling control if needed.
            cv_text_html = re.sub(r'(?:<br />\s*)+([\*\-•]\s+)(.+)', r'<br /><span class="list-bullet">• </span><span class="list-item-content">\2</span>', cv_text_html, flags=re.MULTILINE)
            # If the above is too complex or has issues, revert to simpler one:
            # cv_text_html = re.sub(r'(<br />\s*[\*\-•]\s+)', r'<br /><span class="ml-4 inline-block text-slate-600">•&nbsp;</span>', cv_text_html, flags=re.MULTILINE)


            cv_entries_html_result_parts.append(f"""
            <article class="bg-white p-6 sm:p-8 rounded-xl shadow-xl border border-slate-200">
                <h3 class="text-xl font-semibold text-primary-DEFAULT mb-4">{repo_name_esc}</h3>
                <div class="prose prose-slate max-w-none cv-content-body">
                    {cv_text_html}
                </div>
            </article>
            """)
        elif cv_data.get("error"):
            cv_entries_html_result_parts.append(f"""
            <article class="bg-red-50 p-6 sm:p-8 rounded-xl shadow-lg border border-red-200 text-red-700">
                <div class="flex items-start space-x-3">
                    <svg class="flex-shrink-0 w-6 h-6 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286zm0 13.036h.008v.008H12v-.008z" />
                    </svg>
                    <div>
                        <h3 class="text-xl font-semibold mb-2">{repo_name_esc}</h3>
                        <p class="text-sm"><strong class="font-medium">CV Generation Failed:</strong> {escape_html_chars(cv_data["error"])}</p>
                    </div>
                </div>
            </article>
            """)
    
    actual_processed_count = len(repos_to_actually_process)
    final_message_text = f"Attempted processing for {actual_processed_count} repositories. "
    
    if action_type == 'auto_select':
        final_message_text += f"Selected top {successful_cv_count} of {AUTO_SELECT_FINAL_OUTPUT_COUNT} targeted successful CV entries from {AUTO_SELECT_PROCESS_COUNT} processed. "
    else: # manual_select
        final_message_text += f"Generated {successful_cv_count} CV entries. "

    errors_occurred_in_displayed_results = any(cv_data.get("error") for cv_data in generated_cvs_data if not cv_data.get("cv_entry"))
    not_all_targeted_successful = (action_type == 'auto_select' and successful_cv_count < AUTO_SELECT_FINAL_OUTPUT_COUNT) or \
                                  (action_type == 'manual_select' and successful_cv_count < len(repos_to_actually_process))


    if errors_occurred_in_displayed_results or not_all_targeted_successful:
         final_message_text += " Some summaries may not have been generated due to errors or selection criteria. Check entries below or server logs."
        
    return templates.TemplateResponse("cv_summary.html", {
        "request": request,
        "message": final_message_text,
        "cv_entries_html_parts": cv_entries_html_result_parts,
        "app_title": APP_TITLE,
        "app_version": APP_VERSION,
    })

# --- Main Execution ---
if __name__ == "__main__":
    # This check allows running with `python main.py` or `python cv/main.py`
    # It assumes uvicorn is in PATH or accessible.
    is_direct_run = __file__.endswith("main.py") 
    app_module_path = "main:app" if is_direct_run else "cv.main:app"
    
    # Ensure current working directory is the project root for uvicorn reload
    project_root = os.path.dirname(os.path.abspath(__file__))
    if not is_direct_run: # if running cv/main.py, root is one level up
        project_root = os.path.dirname(project_root)
    
    print(f"Running uvicorn for module: {app_module_path} from CWD: {project_root}")

    try:
        # Change CWD for uvicorn if necessary, especially for reload
        os.chdir(project_root) 
        uvicorn.run(app_module_path, host="127.0.0.1", port=8000, reload=True, reload_dirs=[os.path.join(project_root, "cv")])
    except ImportError as e:
        print(f"ImportError: {e}. Could not run uvicorn. Is it installed and in PATH?")
        print("Try: pip install uvicorn[standard]")
        print(f"To run manually: uvicorn {app_module_path} --reload --host 127.0.0.1 --port 8000 --reload-dir cv")
    except Exception as e:
        print(f"An error occurred: {e}")

```
