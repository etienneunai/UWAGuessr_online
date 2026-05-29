// Preload map removed — it was creating a hidden second map instance that
// wasted API calls. The game page creates its own map when needed.

document.addEventListener("DOMContentLoaded", function () {
  let sidebar = document.getElementById("friends-sidebar");
  let toggle = document.getElementById("friends-toggle");
  let closeButton = document.getElementById("friends-close");
  let backdrop = document.getElementById("friends-backdrop");

  if (!sidebar || !toggle || !closeButton || !backdrop) {
    return;
  }

  function openSidebar() {
    sidebar.classList.add("open");
    backdrop.classList.add("active");
    sidebar.setAttribute("aria-hidden", "false");
    toggle.classList.add("hidden");
    if (typeof loadFriends === "function") loadFriends();
    if (typeof loadPendingRequests === "function") loadPendingRequests();
  }

  function closeSidebar() {
    sidebar.classList.remove("open");
    backdrop.classList.remove("active");
    sidebar.setAttribute("aria-hidden", "true");
    toggle.classList.remove("hidden");
  }

  toggle.addEventListener('click', openSidebar);
  closeButton.addEventListener('click', closeSidebar);
  backdrop.addEventListener('click', closeSidebar);

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && sidebar.classList.contains("open")) {
      closeSidebar();
    }
  });
});
