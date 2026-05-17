function showLeaderboard(type) {
  document.getElementById("board-daily").style.display =
    type === "daily" ? "block" : "none";
  document.getElementById("board-all-time").style.display =
    type === "all-time" ? "block" : "none";

  if (type === "daily") {
    document.getElementById("btn-daily").classList.add("active");
    document.getElementById("btn-all-time").classList.remove("active");
  } else {
    document.getElementById("btn-all-time").classList.add("active");
    document.getElementById("btn-daily").classList.remove("active");
  }
}
