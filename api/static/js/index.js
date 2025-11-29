document.addEventListener("DOMContentLoaded", () => {
    const overlay = document.getElementById("loading-overlay");

    document.querySelectorAll("button").forEach(btn => {
        if (btn.id !== "ignore-overlay") {
            btn.addEventListener("click", () => {
                overlay.style.display = "flex";
            });
        }
    });

    // Also catch form submissions (buttons aren’t always clicked)
    document.querySelectorAll("form").forEach(form => {
        form.addEventListener("submit", () => {
            overlay.style.display = "flex";
        });
    });
});