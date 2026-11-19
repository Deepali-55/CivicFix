// Small shared enhancement: close the mobile navigation after choosing a link.
document.querySelectorAll(".nav-links a").forEach(link => {
    link.addEventListener("click", () => {
        const nav = document.querySelector(".nav-links");
        if (nav) nav.classList.remove("nav-open");
    });
});
