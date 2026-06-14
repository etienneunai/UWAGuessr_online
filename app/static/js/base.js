/**
 * Global scripts applied to the base template.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        const mainNav = document.getElementById('mainNav');
        const toggler = document.querySelector('.navbar-toggler');
        
        // If the menu is open, the click is outside the menu, and the click is outside the hamburger button
        if (mainNav && mainNav.classList.contains('show') && !mainNav.contains(event.target)) {
            if (toggler && !toggler.contains(event.target)) {
                // Use Bootstrap's Collapse API to safely hide the menu
                const bsCollapse = bootstrap.Collapse.getInstance(mainNav);
                if (bsCollapse) {
                    bsCollapse.hide();
                }
            }
        }
    });
});
