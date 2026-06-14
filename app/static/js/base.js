document.addEventListener('DOMContentLoaded', () => {
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        const mainNav = document.getElementById('mainNav');
        const toggler = document.querySelector('.navbar-toggler');
        
        if (mainNav && mainNav.classList.contains('show') && !mainNav.contains(event.target) && !toggler.contains(event.target)) {
            const bsCollapse = bootstrap.Collapse.getInstance(mainNav) || new bootstrap.Collapse(mainNav, {toggle: false});
            bsCollapse.hide();
        }
    });
});
