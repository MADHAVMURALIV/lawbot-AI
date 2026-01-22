document.addEventListener('DOMContentLoaded', () => {
  // ====== Chat Handling ======
  const promptForm = document.getElementById('prompt-form');
  const promptInput = document.getElementById('prompt-input');
  const chatScreen = document.querySelector('.chat-screen');

  function addMessage(sender, text) {
    const msg = document.createElement('div');
    msg.classList.add('msg', sender);
    msg.textContent = text;
    chatScreen.appendChild(msg);
    chatScreen.scrollTop = chatScreen.scrollHeight;
  }

  if (promptForm) {
    promptForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const q = (promptInput?.value || '').trim();
      if (!q) return;

      addMessage('user', q);
      promptInput.value = '';

      // show "thinking..."
      const loadingMsg = document.createElement('div');
      loadingMsg.classList.add('msg', 'bot');
      loadingMsg.textContent = '...';
      chatScreen.appendChild(loadingMsg);

      try {
        const res = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: q })
        });

        const data = await res.json();
        loadingMsg.remove();

        if (data.reply) {
          addMessage('bot', data.reply);
        } else {
          addMessage('bot', "⚠ Error: " + (data.error || "No reply from server"));
        }
      } catch (err) {
        loadingMsg.remove();
        addMessage('bot', "⚠ Failed to reach server.");
      }
    });

    // Toolbar actions
    promptForm.querySelector('[title="Attach file"]')?.addEventListener('click', () => alert('📎 Attach file coming soon!'));
    promptForm.querySelector('[title="Record voice"]')?.addEventListener('click', () => alert('🎙️ Voice recording coming soon!'));
    promptForm.querySelector('[title="Open camera"]')?.addEventListener('click', () => alert('📷 Camera access coming soon!'));
  }

  // ====== Sign Out Handling ======
  document.getElementById('signout-btn')?.addEventListener('click', () => {
    alert('You have been signed out!');
    window.location.href = 'signin.html';
  });

  // ====== Card Actions ======
  document.getElementById('emergency-alert')?.addEventListener('click', (e) => {
    e.preventDefault();
    alert('🚨 Emergency Alert Sent!\nAuthorities have been notified.');
  });

  document.getElementById('quick-support')?.addEventListener('click', () => {
    window.location.href = "chat.html";
  });

  document.getElementById('location-spread')?.addEventListener('click', (e) => {
    e.preventDefault();
    alert('📍 Map integration coming soon!');
  });

  document.getElementById('legal-articles')?.addEventListener('click', (e) => {
    e.preventDefault();
    alert('📚 Legal Articles section coming soon.');
  });

  document.getElementById('legal-faqs')?.addEventListener('click', (e) => {
    e.preventDefault();
    alert('❓ FAQs section coming soon.');
  });

  document.getElementById('case-tracker')?.addEventListener('click', (e) => {
    e.preventDefault();
    alert('📊 Case Tracker integration coming soon.');
  });

  // ====== Emergency Contacts ======
  const emergencyContactsCard = document.getElementById("emergency-contacts");
  const contactsList = document.getElementById("contacts-list");

  emergencyContactsCard?.addEventListener("click", async (e) => {
    e.preventDefault();

    if (contactsList.style.display === "block") {
      contactsList.style.display = "none";
      return;
    }

    try {
      const res = await fetch("emergency.json");
      const data = await res.json();

      contactsList.innerHTML = "<h3>📞 Emergency Numbers</h3><ul></ul>";
      const ul = contactsList.querySelector("ul");

      for (let key in data) {
        const li = document.createElement("li");
        li.innerHTML = `<strong>${key}:</strong> <a href="tel:${data[key].split(' ')[0]}">${data[key]}</a>`;
        ul.appendChild(li);
      }

      contactsList.style.display = "block";
    } catch (err) {
      alert("⚠️ Could not load emergency contacts.");
    }
  });

  // ====== File a Complaint (State Selection Modal) ======
  const fileComplaintCard = document.getElementById("file-complaint");
  const stateModal = document.createElement("div");
  stateModal.classList.add("modal");
  stateModal.innerHTML = `
    <div class="modal-content">
      <button class="modal-close">&times;</button>
      <h2>Choose Your State</h2>
      <ul class="state-list"></ul>
    </div>
  `;
  document.body.appendChild(stateModal);

  const stateList = stateModal.querySelector(".state-list");
  const closeBtn = stateModal.querySelector(".modal-close");

  const stateLinks = {
    "National Cyber Crime Portal": "https://cybercrime.gov.in/",
    "Emergency Response (ERSS)": "https://112india.com/",
    "Andhra Pradesh": "https://citizen.appolice.gov.in/",
    "Arunachal Pradesh": "http://arunpol.nic.in/",
    "Assam": "https://police.assam.gov.in/",
    "Bihar": "http://police.bihar.gov.in/",
    "Chhattisgarh": "http://cgpolice.gov.in/",
    "Goa": "https://citizen.goapolice.gov.in/",
    "Gujarat": "http://www.police.gujarat.gov.in/",
    "Haryana": "https://haryanapolice.gov.in/",
    "Himachal Pradesh": "https://citizenportal.hppolice.gov.in/citizen/login.htm",
    "Jharkhand": "https://www.jhpolice.gov.in/",
    "Karnataka": "https://ksp.karnataka.gov.in/",
    "Kerala": "https://thuna.keralapolice.gov.in/",
    "Madhya Pradesh": "https://www.mppolice.gov.in/",
    "Maharashtra": "https://www.mahapolice.gov.in/",
    "Manipur": "http://www.manipurpolice.gov.in/",
    "Meghalaya": "https://megpolice.gov.in/",
    "Nagaland": "https://police.nagaland.gov.in/",
    "Odisha": "https://odishapolice.gov.in/",
    "Punjab": "http://www.punjabpolice.gov.in/",
    "Rajasthan": "http://police.rajasthan.gov.in/",
    "Sikkim": "https://police.sikkim.gov.in/",
    "Tamil Nadu": "http://www.tnpolice.gov.in/",
    "Telangana": "https://www.tspolice.gov.in/",
    "Tripura": "https://tripurapolice.gov.in/",
    "Uttar Pradesh": "https://uppolice.gov.in/",
    "Uttarakhand": "https://uttarakhandpolice.uk.gov.in/",
    "West Bengal": "https://wbpolice.gov.in/",
    "Andaman & Nicobar": "https://police.andaman.gov.in/",
    "Chandigarh": "https://chandigarhpolice.gov.in/",
    "Dadra & Nagar Haveli and Daman & Diu": "https://daman.nic.in/",
    "Delhi": "https://delhipolice.gov.in/",
    "Jammu and Kashmir": "http://www.jkpolice.gov.in/",
    "Ladakh": "https://police.ladakh.gov.in/",
    "Lakshadweep": "https://lakshadweeppolice.gov.in/",
    "Puducherry": "https://police.py.gov.in/"
  };

  for (let state in stateLinks) {
    const li = document.createElement("li");
    li.innerHTML = `<a href="${stateLinks[state]}" target="_blank" rel="noopener">${state}</a>`;
    stateList.appendChild(li);
  }

  fileComplaintCard?.addEventListener("click", (e) => {
    e.preventDefault();
    stateModal.style.display = "flex";
  });

  closeBtn.addEventListener("click", () => {
    stateModal.style.display = "none";
  });

  stateModal.addEventListener("click", (e) => {
    if (e.target === stateModal) {
      stateModal.style.display = "none";
    }
  });

  // ====== Profile Menu ======
  const profileBtn = document.getElementById("profile-btn");
  const profileMenu = document.getElementById("profile-menu");
  const signoutOption = document.getElementById("signout-option");

  profileBtn?.addEventListener("click", () => {
    profileMenu.style.display = (profileMenu.style.display === "block") ? "none" : "block";
  });

  document.addEventListener("click", (e) => {
    if (profileMenu && !profileBtn.contains(e.target) && !profileMenu.contains(e.target)) {
      profileMenu.style.display = "none";
    }
  });

  signoutOption?.addEventListener("click", () => {
    alert("You have been signed out!");
    window.location.href = "signin.html";
  });
});
