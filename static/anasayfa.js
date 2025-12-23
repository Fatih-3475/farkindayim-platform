import { RetellWebClient } from "https://esm.sh/retell-client-js-sdk?bundle";

/* =======================================================
   SAYFA AÇILINCA KALICI AYARLARI GERİ YÜKLE
======================================================= */
document.addEventListener("DOMContentLoaded", () => {
  // FONT BOYUTU
  const savedFont = localStorage.getItem("fontSize");
  if (savedFont) {
    document.documentElement.style.fontSize = savedFont + "px";
  }

  // BÜYÜK İMLEÇ
  if (localStorage.getItem("buyukImlec") === "true") {
    document.body.classList.add("buyuk-imlec");
  }
});

/* =======================================================
   RETELL AI
======================================================= */
document.addEventListener("DOMContentLoaded", () => {
  const aiBtn = document.getElementById("ai-toggle-btn");
  const aiIcon = document.getElementById("ai-icon");
  const statusText = document.getElementById("ai-status-text");
  const statusBubble = document.getElementById("ai-status-bubble");

  if (!aiBtn) return;

  let isCallActive = false;
  const retellWebClient = new RetellWebClient();

  retellWebClient.on("call_started", () => {
    isCallActive = true;
    aiBtn.classList.add("active");
    aiIcon.classList.replace("fa-microphone", "fa-stop");
    statusText.innerText = "Seni Dinliyorum...";
    statusBubble.style.opacity = "1";
  });

  retellWebClient.on("call_ended", resetUI);
  retellWebClient.on("error", resetUI);

  function resetUI() {
    isCallActive = false;
    aiBtn.classList.remove("active");
    aiIcon.classList.replace("fa-stop", "fa-microphone");
    statusText.innerText = "Bana Sorabilirsin!";
    setTimeout(() => (statusBubble.style.opacity = "0"), 2000);
  }

  aiBtn.addEventListener("click", async () => {
    if (isCallActive) {
      retellWebClient.stopCall();
      return;
    }

    statusText.innerText = "Bağlanıyor...";
    statusBubble.style.opacity = "1";

    try {
      const res = await fetch("/api/start-call", { method: "POST" });
      const data = await res.json();
      await retellWebClient.startCall({ accessToken: data.access_token });
    } catch {
      resetUI();
    }
  });
});

/* =======================================================
   ERİŞİLEBİLİRLİK (KALICI + GÜVENLİ)
======================================================= */
document.addEventListener("DOMContentLoaded", () => {
  const panelBtn = document.getElementById("erişilebilirlik-btn");
  const panel = document.getElementById("e-panel");
  const buyutBtn = document.getElementById("font-buyut");
  const kucultBtn = document.getElementById("font-kucult");
  const imlecBtn = document.getElementById("buyuk-imlec");

  // PANEL AÇ / KAPA (VARSA)
  if (panelBtn && panel) {
    panelBtn.addEventListener("click", () => {
      panel.classList.toggle("active");
    });
  }

  // YAZI BÜYÜT / KÜÇÜLT
  buyutBtn?.addEventListener("click", () => changeFontSize(2));
  kucultBtn?.addEventListener("click", () => changeFontSize(-2));

  // BÜYÜK İMLEÇ
  imlecBtn?.addEventListener("click", () => {
    document.body.classList.toggle("buyuk-imlec");
    localStorage.setItem(
      "buyukImlec",
      document.body.classList.contains("buyuk-imlec")
    );
  });
});

function changeFontSize(diff) {
  let size = parseFloat(
    getComputedStyle(document.documentElement).fontSize
  );

  size = Math.min(Math.max(size + diff, 12), 22);
  document.documentElement.style.fontSize = size + "px";
  localStorage.setItem("fontSize", size);
}

/* =======================================================
   AOS + ALERT
======================================================= */
if (typeof AOS !== "undefined") {
  AOS.init({ duration: 1500, once: true });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".alert").forEach((alert) => {
    setTimeout(() => {
      alert.style.display = "none";
    }, 5000);
  });
});
