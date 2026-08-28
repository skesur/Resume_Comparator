// Custom client-side scripts for Resume Comparator
document.addEventListener("DOMContentLoaded", function() {
    // Enable Bootstrap tooltips if any exist
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    console.log("Resume Comparator JS engine active.");
});
