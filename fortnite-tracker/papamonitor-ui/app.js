const toggleConsole = document.getElementById("toggleConsole");
const consoleBox = document.getElementById("consoleBox");

toggleConsole.addEventListener("change", () => {
  if (toggleConsole.checked) {
    consoleBox.classList.remove("hidden");
  } else {
    consoleBox.classList.add("hidden");
  }
});
