document.addEventListener('DOMContentLoaded', function () {
    // processId and finalSummaryUrl are passed from the template in cv_progress.html

    const progressLog = document.getElementById('progress-log');
    const backToReposButton = document.querySelector('a[href$="/repos"]'); // Find the Back to Repos button

    if (!progressLog || typeof processId === 'undefined' || typeof finalSummaryUrl === 'undefined') {
        console.error("Missing required elements or variables for progress page.");
        if (progressLog) progressLog.innerHTML = '<p class="text-red-600">Error initializing progress view. Missing data.</p>';
        return;
    }

    let eventSource = null;

    function addLogEntry(message, type = 'info', repoName = null) {
        const entry = document.createElement('div');
        entry.className = `flex items-center space-x-3 py-1 text-sm ${type === 'error' ? 'text-red-700' : type === 'success' ? 'text-green-700' : 'text-slate-700'}`;
        
        let iconSvg = '';
        // Use Heroicons or similar for icons
        if (type === 'info' || type === 'started') {
            iconSvg = `<svg class="animate-spin h-5 w-5 text-primary-DEFAULT flex-shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l2.001-2.647z"></path>
                    </svg>`;
        } else if (type === 'success' || type === 'complete' || type === 'cv_generated') {
             iconSvg = `<svg class="h-5 w-5 text-green-500 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.06 0l4-5.5z" clip-rule="evenodd" />
                    </svg>`;
        } else if (type === 'error') {
            iconSvg = `<svg class="h-5 w-5 text-red-500 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1.293-8.707a1 1 0 011.414-1.414L10 8.586l1.293-1.293a1 1 0 111.414 1.414L11.414 10l1.293 1.293a1 1 0 01-1.414 1.414L10 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L8.586 10 7.293 8.707z" clip-rule="evenodd" />
                    </svg>`;
        } else if (type === 'processing_context') {
             iconSvg = `<svg class="h-5 w-5 text-blue-500 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                    </svg>`;
        } else if (type === 'generating_cv') {
             iconSvg = `<svg class="h-5 w-5 text-purple-500 flex-shrink-0 animate-pulse" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L18.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18.75 8.25l.49-.465m-6.014 1.012L12 9.75l-.486.957m-4.158-1.707L6.25 8.25l-.485-.465" />
                    </svg>`;
        }
        // Add timestamp
        const timestamp = new Date().toLocaleTimeString();
        entry.innerHTML = `${iconSvg} <span class="text-slate-400">[${timestamp}]</span> ${repoName ? `<strong class="font-medium">${repoName}:</strong> ` : ''}${message}`;
        progressLog.appendChild(entry);
        // Auto-scroll to the bottom
        progressLog.scrollTop = progressLog.scrollHeight;
    }

    function startSSE() {
        // Connect to the stream endpoint
        eventSource = new EventSource(`/cv-progress-stream/${processId}`);

        eventSource.onmessage = function (event) {
            console.log("Received SSE message:", event.data);
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'status') {
                    addLogEntry(data.message, data.status, data.repo);
                } else if (data.type === 'complete') {
                    addLogEntry(data.message, 'success');
                    console.log("Processing complete. Redirecting to summary.");
                    // Redirect to the final summary page
                    // Use replace to prevent going back to the progress page via back button
                    window.location.replace(finalSummaryUrl); 
                } else if (data.type === 'error') {
                     addLogEntry(data.message, 'error', data.repo);
                     // Optionally stop the stream or show a "Retry" button
                     if (eventSource) {
                         eventSource.close();
                         eventSource = null; // Clear the EventSource object
                     }
                     // Make the "Back to Repositories" button more prominent or add a "View Results" button
                     if (backToReposButton) {
                          backToReposButton.classList.remove('text-slate-700', 'ring-slate-300', 'hover:bg-slate-50');
                          backToReposButton.classList.add('text-red-700', 'ring-red-300', 'hover:bg-red-50');
                     }
                     // Show a message indicating process stopped due to error
                     addLogEntry("Process stopped due to error.", 'error');
                } else if (data.type === 'result') {
                    // If you want to show intermediate results during the stream, handle 'result' type here.
                    // For this flow, we redirect after 'complete'.
                     console.log("Received intermediate result (ignored in this flow):", data);
                }
            } catch (e) {
                console.error("Failed to parse SSE message data:", e);
                addLogEntry("Error processing stream update.", 'error');
            }
        };

        eventSource.onerror = function (event) {
            console.error("SSE Error:", event);
            // Check event.eventPhase for type of error (e.g., connection error)
            let error_message = "An unknown error occurred with the processing stream.";
             if (event.target && event.target.readyState === EventSource.CLOSED) {
                 error_message = "Processing stream connection closed unexpectedly.";
             } else if (event.message) {
                 error_message = `Stream error: ${event.message}`;
             }
            addLogEntry(error_message, 'error');
            
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            // Show error state UI
             if (backToReposButton) {
                  backToReposButton.classList.remove('text-slate-700', 'ring-slate-300', 'hover:bg-slate-50');
                  backToReposButton.classList.add('text-red-700', 'ring-red-300', 'hover:bg-red-50');
             }
             addLogEntry("Process stopped due to stream error.", 'error');
        };

        eventSource.onopen = function(event) {
             console.log("SSE connection opened.");
             // Remove the initial "Connecting..." message
             const initialMessage = progressLog.querySelector('.animate-spin');
             if(initialMessage && initialMessage.parentElement) {
                  initialMessage.parentElement.remove();
             }
             addLogEntry("Processing stream connected.", 'info');
        };
    }

    // Start the SSE connection when the page loads
    // Add a small delay to allow the "Connecting..." message to be seen briefly
    setTimeout(startSSE, 100); 
});
