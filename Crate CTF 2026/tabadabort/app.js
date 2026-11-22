// Meridian Ops -- account page
// API base: /api

async function loadAccount() {
  const card = document.getElementById("card");
  try {
    const res = await fetch("/api/users/me", { method: "GET" });
    const data = await res.json();

    card.innerHTML = `
      <div class="row"><span class="k">User ID</span><span class="v">${data.id}</span></div>
      <div class="row"><span class="k">Username</span><span class="v">${data.username}</span></div>
      <div class="row"><span class="k">Status</span><span class="v"><span class="status ${data.status}">${data.status}</span></span></div>
      <div class="row"><span class="k">Created</span><span class="v">${new Date(data.created_at * 1000).toLocaleString()}</span></div>
    `;
  } catch (err) {
    card.innerHTML = `<div class="row"><span class="k">Unable to load account.</span></div>`;
  }
}

loadAccount();

// TODO(dev): hold off on wiring up the "Delete account" button until the
// identity-team finishes the UX for this. Backend's already live though -- DELETE
// grace period via GET /api/recovery/ with recovery id