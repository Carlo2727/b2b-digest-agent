/**
 * B2B Digest Agent - Landing Page Logic
 * Handles interactive tabs and waitlist form submission.
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Tab Switching (Telegram vs Email View)
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".view-tab");

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");

      // Update button active state
      tabButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Update panel visibility
      tabPanels.forEach((panel) => {
        if (panel.id === targetId) {
          panel.classList.add("active");
        } else {
          panel.classList.remove("active");
        }
      });
    });
  });

  // Form submission is handled seamlessly via handleWaitlistSubmit in index.html
});
