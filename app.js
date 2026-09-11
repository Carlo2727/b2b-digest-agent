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

  // 2. Waitlist Form Submission
  const form = document.getElementById("hero-waitlist-form");
  const emailInput = document.getElementById("hero-email");
  const feedback = document.getElementById("hero-feedback");

  if (form) {
    form.addEventListener("submit", (e) => {
      const actionUrl = form.getAttribute("action") || "";
      const isPlaceholder = actionUrl === "#" || actionUrl.includes("tuo_id") || actionUrl.includes("your_id");

      // If form action is still placeholder, handle via client-side simulation
      if (isPlaceholder) {
        e.preventDefault();

        const email = emailInput.value.trim();
        if (!email || !email.includes("@")) {
          showFeedback("Inserisci un indirizzo email valido.", false);
          return;
        }

        // Store email in localStorage as a mock leads collection
        try {
          const leads = JSON.parse(localStorage.getItem("b2b_waitlist_leads") || "[]");
          if (!leads.includes(email)) {
            leads.push({ email, registered_at: new Date().toISOString() });
            localStorage.setItem("b2b_waitlist_leads", JSON.stringify(leads));
          }
        } catch (err) {
          console.warn("LocalStorage access restricted:", err);
        }

        // Display instant success state
        showFeedback(
          "🎉 Complimenti! Ti sei unito alla lista prioritaria. Riceverai a breve un'email di conferma con l'accesso gratuito al primo briefing.",
          true
        );

        emailInput.value = "";
        emailInput.disabled = true;
        const submitBtn = form.querySelector("button[type='submit']");
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = "<span>Iscritto con Successo ✓</span>";
        }
      }
      // If form action points to Formspree/Make, standard POST proceeds automatically!
    });
  }

  function showFeedback(message, isSuccess) {
    if (!feedback) return;
    feedback.textContent = message;
    feedback.className = isSuccess ? "form-feedback success" : "form-feedback error";
    feedback.classList.remove("hidden");
  }
});
